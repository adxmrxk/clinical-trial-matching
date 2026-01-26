from typing import Any, Dict, List
import json
from .base_agent import BaseAgent
from ..schemas.patient import PatientProfile
from ..schemas.trial import TrialMatch, CriterionStatus


class GapAnalysisAgent(BaseAgent):
    """
    Analyzes trial matches to identify missing patient information
    that could resolve 'uncertain' eligibility determinations.

    This enables Phase 2 (trial-driven) and Phase 3 (gap-filling) questioning.
    """

    def __init__(self):
        super().__init__(
            name="Gap Analysis Agent",
            description="Identifies missing patient information needed to evaluate trial eligibility criteria"
        )

        # Map of common criteria attributes to patient profile fields
        self.attribute_mapping = {
            "age": "age",
            "sex": "biological_sex",
            "gender": "biological_sex",
            "diagnosis": "primary_condition",
            "condition": "primary_condition",
            "stage": "condition_stage",
            "ecog": "ecog_status",
            "performance_status": "ecog_status",
            "smoking": "smoking_status",
            "tobacco": "smoking_status",
            "alcohol": "alcohol_use",
            "pregnancy": "pregnancy_status",
            "pregnant": "pregnancy_status",
            "medication": "current_medications",
            "medications": "current_medications",
            "treatment": "prior_treatments",
            "prior_treatment": "prior_treatments",
            "comorbidity": "comorbidities",
            "comorbidities": "comorbidities",
            "allergy": "allergies",
            "allergies": "allergies",
        }

    def get_system_prompt(self) -> str:
        return """You are a Gap Analysis Agent for clinical trial matching.

Your job is to analyze trial eligibility criteria that have UNKNOWN status and identify
what specific patient information is missing that would allow evaluation of those criteria.

For each unknown criterion, determine:
1. What patient attribute is needed (e.g., lab value, medical history, lifestyle factor)
2. Why this information is important for the specific trial
3. Priority level (high = needed for multiple trials, medium = important for one trial, low = nice to have)

Be specific about what information is needed. For example:
- Instead of "lab values", specify "HbA1c level" or "creatinine clearance"
- Instead of "medical history", specify "history of heart disease" or "prior chemotherapy"

Respond in JSON format."""

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze trial matches and patient profile to identify information gaps.

        Input:
            trial_matches: List[TrialMatch] - Trials with eligibility evaluations
            patient_profile: PatientProfile - Current patient profile

        Output:
            gaps: List of missing information items with priority
            gap_summary: Summary of what's missing
            prioritized_attributes: Ordered list of attributes to ask about
        """
        trial_matches: List[TrialMatch] = input_data.get("trial_matches", [])
        patient_profile: PatientProfile = input_data.get("patient_profile", PatientProfile())

        if not trial_matches:
            return {
                "gaps": [],
                "gap_summary": "No trials to analyze",
                "prioritized_attributes": []
            }

        # Collect all unknown criteria across trials
        unknown_criteria_by_trial = {}
        all_unknown_criteria = []

        for match in trial_matches:
            trial_id = match.trial.nct_id
            unknown_criteria_by_trial[trial_id] = []

            for criterion in match.criteria_unknown:
                unknown_criteria_by_trial[trial_id].append({
                    "criterion_id": criterion.criterion_id,
                    "text": criterion.original_text,
                    "type": criterion.criterion_type,
                    "attribute": criterion.attribute,
                    "trial_id": trial_id,
                    "trial_title": match.trial.title
                })
                all_unknown_criteria.append({
                    "criterion_id": criterion.criterion_id,
                    "text": criterion.original_text,
                    "type": criterion.criterion_type,
                    "attribute": criterion.attribute,
                    "trial_id": trial_id
                })

        if not all_unknown_criteria:
            return {
                "gaps": [],
                "gap_summary": "All criteria have been evaluated",
                "prioritized_attributes": []
            }

        # Use LLM to analyze gaps and prioritize
        gaps = await self._analyze_gaps_with_llm(
            all_unknown_criteria,
            patient_profile,
            trial_matches
        )

        # Also do rule-based gap detection for common attributes
        rule_based_gaps = self._detect_common_gaps(patient_profile, all_unknown_criteria)

        # Merge and deduplicate gaps
        merged_gaps = self._merge_gaps(gaps, rule_based_gaps)

        # Prioritize by frequency (how many trials need this info)
        prioritized = self._prioritize_gaps(merged_gaps, all_unknown_criteria)

        return {
            "gaps": prioritized,
            "gap_summary": self._generate_summary(prioritized),
            "prioritized_attributes": [g["attribute"] for g in prioritized[:5]],
            "unknown_criteria_count": len(all_unknown_criteria),
            "trials_with_unknowns": len([m for m in trial_matches if m.criteria_unknown])
        }

    def _detect_common_gaps(
        self,
        profile: PatientProfile,
        unknown_criteria: List[dict]
    ) -> List[dict]:
        """Rule-based detection of common missing attributes."""
        gaps = []

        # Check what attributes are mentioned in unknown criteria
        mentioned_attributes = set()
        for criterion in unknown_criteria:
            attr = criterion.get("attribute", "").lower()
            text = criterion.get("text", "").lower()

            # Check attribute field
            if attr:
                mentioned_attributes.add(attr)

            # Check text for common keywords
            for keyword, profile_field in self.attribute_mapping.items():
                if keyword in text:
                    mentioned_attributes.add(profile_field)

        # Check if mentioned attributes are missing from profile
        profile_dict = profile.model_dump()

        for attr in mentioned_attributes:
            profile_field = self.attribute_mapping.get(attr, attr)
            value = profile_dict.get(profile_field)

            # Check if value is missing or empty
            is_missing = (
                value is None or
                value == "" or
                (isinstance(value, list) and len(value) == 0) or
                (isinstance(value, dict) and len(value) == 0)
            )

            if is_missing:
                gaps.append({
                    "attribute": profile_field,
                    "reason": f"Required to evaluate criteria mentioning '{attr}'",
                    "priority": "high",
                    "criteria_count": sum(1 for c in unknown_criteria if attr in c.get("text", "").lower())
                })

        return gaps

    async def _analyze_gaps_with_llm(
        self,
        unknown_criteria: List[dict],
        profile: PatientProfile,
        trial_matches: List[TrialMatch]
    ) -> List[dict]:
        """Use LLM to identify specific information gaps."""

        # Limit to first 10 unknown criteria to avoid token limits
        criteria_sample = unknown_criteria[:10]

        prompt = f"""Analyze these unknown eligibility criteria and identify what patient information is missing.

UNKNOWN CRITERIA:
{json.dumps(criteria_sample, indent=2)}

CURRENT PATIENT PROFILE:
{profile.model_dump_json(indent=2)}

For each piece of missing information, provide:
1. attribute: The specific attribute needed (e.g., "hemoglobin_level", "prior_chemotherapy", "heart_disease_history")
2. reason: Why this is needed (reference the specific criterion)
3. priority: "high", "medium", or "low"
4. question_hint: A natural way to ask about this

Respond with a JSON array of gap objects:
[
  {{
    "attribute": "string",
    "reason": "string",
    "priority": "high|medium|low",
    "question_hint": "string"
  }}
]"""

        try:
            response = await self.llm.generate_json(prompt, self.get_system_prompt())
            gaps = json.loads(response)
            if isinstance(gaps, list):
                return gaps
        except Exception as e:
            print(f"Gap analysis LLM error: {e}")

        return []

    def _merge_gaps(self, llm_gaps: List[dict], rule_gaps: List[dict]) -> List[dict]:
        """Merge LLM and rule-based gaps, deduplicating by attribute."""
        seen_attributes = set()
        merged = []

        # LLM gaps first (usually more specific)
        for gap in llm_gaps:
            attr = gap.get("attribute", "").lower()
            if attr and attr not in seen_attributes:
                seen_attributes.add(attr)
                merged.append(gap)

        # Then rule-based gaps
        for gap in rule_gaps:
            attr = gap.get("attribute", "").lower()
            if attr and attr not in seen_attributes:
                seen_attributes.add(attr)
                merged.append(gap)

        return merged

    def _prioritize_gaps(self, gaps: List[dict], unknown_criteria: List[dict]) -> List[dict]:
        """Prioritize gaps by importance and frequency."""

        priority_order = {"high": 0, "medium": 1, "low": 2}

        # Count how many criteria each gap attribute appears in
        for gap in gaps:
            attr = gap.get("attribute", "").lower()
            count = sum(
                1 for c in unknown_criteria
                if attr in c.get("text", "").lower() or attr in c.get("attribute", "").lower()
            )
            gap["criteria_count"] = max(count, gap.get("criteria_count", 1))

        # Sort by priority, then by criteria count
        sorted_gaps = sorted(
            gaps,
            key=lambda g: (
                priority_order.get(g.get("priority", "low"), 2),
                -g.get("criteria_count", 0)
            )
        )

        return sorted_gaps

    def _generate_summary(self, gaps: List[dict]) -> str:
        """Generate a human-readable summary of gaps."""
        if not gaps:
            return "No information gaps identified."

        high_priority = [g for g in gaps if g.get("priority") == "high"]

        if high_priority:
            attrs = [g.get("attribute", "unknown") for g in high_priority[:3]]
            return f"Key missing information: {', '.join(attrs)}. This information is needed to evaluate eligibility for multiple trials."

        return f"Found {len(gaps)} pieces of missing information that could help clarify eligibility."


# Singleton instance
gap_analysis_agent = GapAnalysisAgent()
