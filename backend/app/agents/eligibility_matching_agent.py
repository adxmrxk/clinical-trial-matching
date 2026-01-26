import json
from typing import Any, Dict, List
from .base_agent import BaseAgent
from ..schemas.patient import PatientProfile
from ..schemas.trial import (
    ClinicalTrial,
    StructuredCriterion,
    CriterionStatus,
    EligibilityStatus,
    TrialMatch
)


class EligibilityMatchingAgent(BaseAgent):
    """
    Agent responsible for matching patient profiles against
    trial eligibility criteria and generating explainable outcomes.
    """

    def __init__(self):
        super().__init__(
            name="Eligibility Matching Agent",
            description="Match patients to clinical trial criteria with explainable reasoning."
        )

    def get_system_prompt(self) -> str:
        return """You are a clinical trial eligibility evaluator. Your job is to determine if a patient meets specific eligibility criteria.

For each criterion, you must:
1. Compare the patient's attributes against the criterion
2. Determine status: "satisfied", "violated", or "unknown"
3. Provide a clear explanation

Rules:
- SATISFIED: Patient clearly meets the criterion
- VIOLATED: Patient clearly does not meet the criterion
- UNKNOWN: Insufficient patient information to determine

Be conservative - if there's any ambiguity, mark as "unknown".

Return JSON:
{
    "criterion_id": "...",
    "status": "satisfied|violated|unknown",
    "patient_value": "what the patient has",
    "explanation": "Clear explanation of why this status"
}"""

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Match a patient against a trial's eligibility criteria.

        Input:
            - patient_profile: The patient's profile
            - trial: The clinical trial with parsed criteria

        Output:
            - trial_match: Complete TrialMatch with explanations
        """
        profile: PatientProfile = input_data.get("patient_profile")
        trial: ClinicalTrial = input_data.get("trial")

        if not profile or not trial:
            return {"trial_match": None, "error": "Missing patient profile or trial"}

        all_criteria = trial.inclusion_criteria + trial.exclusion_criteria

        satisfied = []
        violated = []
        unknown = []
        missing_info = []

        for criterion in all_criteria:
            result = await self._evaluate_criterion(criterion, profile)

            criterion.status = result["status"]
            criterion.patient_value = result.get("patient_value")
            criterion.explanation = result.get("explanation")

            if result["status"] == CriterionStatus.SATISFIED:
                satisfied.append(criterion)
            elif result["status"] == CriterionStatus.VIOLATED:
                violated.append(criterion)
            else:
                unknown.append(criterion)
                missing_attr = result.get("missing_attribute")
                if missing_attr:
                    # Handle both string and list types
                    if isinstance(missing_attr, list):
                        missing_info.extend([str(a) for a in missing_attr])
                    else:
                        missing_info.append(str(missing_attr))

        # Determine overall eligibility
        eligibility_status = self._determine_eligibility(satisfied, violated, unknown, trial)

        # Generate overall explanation
        explanation = await self._generate_explanation(profile, trial, satisfied, violated, unknown)

        # Calculate confidence
        total_criteria = len(all_criteria)
        known_criteria = len(satisfied) + len(violated)
        confidence = known_criteria / total_criteria if total_criteria > 0 else 0.0

        trial_match = TrialMatch(
            trial=trial,
            eligibility_status=eligibility_status,
            criteria_satisfied=satisfied,
            criteria_violated=violated,
            criteria_unknown=unknown,
            explanation=explanation,
            confidence_score=confidence,
            missing_information=list(set(missing_info))
        )

        return {"trial_match": trial_match}

    async def _evaluate_criterion(
            self,
            criterion: StructuredCriterion,
            profile: PatientProfile
    ) -> Dict[str, Any]:
        """Evaluate a single criterion against the patient profile."""

        # Try rule-based evaluation first for common criteria
        rule_result = self._rule_based_evaluation(criterion, profile)
        if rule_result:
            return rule_result

        # Fall back to LLM evaluation for complex criteria
        prompt = f"""Evaluate if this patient meets this criterion:

Criterion: {criterion.original_text}
Criterion Type: {criterion.criterion_type}

Patient Profile:
{profile.model_dump_json(indent=2)}

Return JSON with status, patient_value, explanation, and missing_attribute (if unknown)."""

        try:
            response = await self.llm.generate_json(prompt, self.get_system_prompt())
            result = json.loads(response)
            result["status"] = CriterionStatus(result.get("status", "unknown"))
            return result
        except:
            return {
                "status": CriterionStatus.UNKNOWN,
                "explanation": "Could not evaluate criterion"
            }

    def _rule_based_evaluation(
            self,
            criterion: StructuredCriterion,
            profile: PatientProfile
    ) -> Dict[str, Any] | None:
        """
        Evaluate common criteria using rules instead of LLM.
        Returns None if rule-based evaluation not possible.
        """

        # Age criteria
        if criterion.attribute == "age" and profile.age is not None:
            try:
                threshold = int(criterion.value)
                if criterion.operator == ">=":
                    status = CriterionStatus.SATISFIED if profile.age >= threshold else CriterionStatus.VIOLATED
                elif criterion.operator == "<=":
                    status = CriterionStatus.SATISFIED if profile.age <= threshold else CriterionStatus.VIOLATED
                elif criterion.operator == ">":
                    status = CriterionStatus.SATISFIED if profile.age > threshold else CriterionStatus.VIOLATED
                elif criterion.operator == "<":
                    status = CriterionStatus.SATISFIED if profile.age < threshold else CriterionStatus.VIOLATED
                else:
                    return None

                return {
                    "status": status,
                    "patient_value": str(profile.age),
                    "explanation": f"Patient age is {profile.age}, criterion requires {criterion.operator} {threshold}"
                }
            except ValueError:
                return None

        # Sex criteria
        if criterion.attribute in ["sex", "biological_sex", "gender"] and profile.biological_sex:
            criterion_sex = criterion.value.lower() if criterion.value else ""
            patient_sex = profile.biological_sex.value.lower()

            if criterion_sex == "all" or criterion_sex == patient_sex:
                return {
                    "status": CriterionStatus.SATISFIED,
                    "patient_value": patient_sex,
                    "explanation": f"Patient sex ({patient_sex}) matches criterion"
                }
            elif criterion_sex and criterion_sex != patient_sex:
                return {
                    "status": CriterionStatus.VIOLATED,
                    "patient_value": patient_sex,
                    "explanation": f"Criterion requires {criterion_sex}, patient is {patient_sex}"
                }

        return None

    def _determine_eligibility(
            self,
            satisfied: List[StructuredCriterion],
            violated: List[StructuredCriterion],
            unknown: List[StructuredCriterion],
            trial: ClinicalTrial
    ) -> EligibilityStatus:
        """Determine overall eligibility status."""

        # Check for violated exclusion criteria (makes ineligible)
        for crit in violated:
            if crit.criterion_type == "exclusion":
                # Violated exclusion = they DO have what should exclude them
                # Actually, this logic is inverted. Let me fix:
                # Exclusion criterion VIOLATED means patient HAS the exclusion condition
                pass

        # Any violated inclusion criterion = ineligible
        inclusion_violated = [c for c in violated if c.criterion_type == "inclusion"]
        if inclusion_violated:
            return EligibilityStatus.INELIGIBLE

        # Check for exclusion criteria
        # If an exclusion criterion is SATISFIED, patient is INELIGIBLE
        # (because they meet a condition that should exclude them)
        exclusion_satisfied = [c for c in satisfied if c.criterion_type == "exclusion"]
        # Wait, this is confusing. Let me reconsider:
        # Exclusion: "No history of heart disease"
        # If patient has no heart disease -> criterion is SATISFIED -> eligible
        # If patient has heart disease -> criterion is VIOLATED -> ineligible

        exclusion_violated = [c for c in violated if c.criterion_type == "exclusion"]
        if exclusion_violated:
            return EligibilityStatus.INELIGIBLE

        # If there are unknown criteria, status is uncertain
        if unknown:
            return EligibilityStatus.UNCERTAIN

        # All criteria satisfied
        return EligibilityStatus.ELIGIBLE

    async def _generate_explanation(
            self,
            profile: PatientProfile,
            trial: ClinicalTrial,
            satisfied: List[StructuredCriterion],
            violated: List[StructuredCriterion],
            unknown: List[StructuredCriterion]
    ) -> str:
        """Generate a human-readable eligibility explanation."""

        if not violated and not unknown:
            return f"Based on your profile, you appear to meet all eligibility criteria for this trial."

        if violated:
            violated_texts = [c.original_text for c in violated[:3]]
            return f"You may not be eligible because: {'; '.join(violated_texts)}"

        if unknown:
            unknown_texts = [c.original_text for c in unknown[:3]]
            return f"We need more information to determine eligibility. Unclear criteria: {'; '.join(unknown_texts)}"

        return "Eligibility could not be determined."


# Singleton instance
eligibility_matching_agent = EligibilityMatchingAgent()
