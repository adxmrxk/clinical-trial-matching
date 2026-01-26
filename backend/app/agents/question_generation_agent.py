from typing import Any, Dict, List, Optional
import json
from .base_agent import BaseAgent
from ..schemas.patient import PatientProfile


class QuestionGenerationAgent(BaseAgent):
    """
    Generates natural, empathetic follow-up questions based on identified
    information gaps. Implements the three-phase questioning strategy:

    Phase 1: Baseline screening (universal attributes)
    Phase 2: Trial-driven questioning (criteria-aware)
    Phase 3: Gap-filling and clarification (adaptive)
    """

    def __init__(self):
        super().__init__(
            name="Question Generation Agent",
            description="Generates targeted, criteria-driven follow-up questions for patients"
        )

        # Phase 1 baseline questions (asked first, regardless of trials)
        self.phase1_questions = {
            "age": {
                "question": "Could you tell me your age?",
                "context": "This helps us find trials with matching age requirements.",
                "priority": 1
            },
            "biological_sex": {
                "question": "What is your biological sex?",
                "context": "Some trials are specific to certain biological sexes.",
                "priority": 2
            },
            "primary_condition": {
                "question": "What medical condition are you seeking treatment for?",
                "context": "This is the main factor in finding relevant trials.",
                "priority": 0
            },
            "country": {
                "question": "What country are you located in?",
                "context": "This helps us find trials in your area.",
                "priority": 3
            },
            "state_province": {
                "question": "What state or province are you in?",
                "context": "This helps narrow down nearby trial locations.",
                "priority": 4
            }
        }

        # Sensitive topics that need careful phrasing
        self.sensitive_topics = {
            "pregnancy_status": "pregnancy or reproductive health",
            "smoking_status": "tobacco use",
            "alcohol_use": "alcohol consumption",
            "mental_health": "mental health conditions",
            "hiv_status": "HIV status",
            "substance_use": "substance use"
        }

    def get_system_prompt(self) -> str:
        return """You are a compassionate clinical trial assistant helping patients find suitable trials.

Your role is to generate follow-up questions that:
1. Are natural and conversational, not clinical or robotic
2. Are empathetic and non-judgmental
3. Explain why the information is needed (transparency)
4. Avoid medical jargon when possible
5. Never ask about multiple unrelated topics in one question
6. Respect patient privacy and comfort

For sensitive topics (pregnancy, substance use, mental health), be especially gentle and explain that:
- The information is optional
- It's only used to find appropriate trials
- Their privacy is protected

Always prioritize the patient's comfort while gathering necessary information."""

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate follow-up questions based on current phase and information gaps.

        Input:
            patient_profile: PatientProfile - Current patient profile
            phase: int - Current conversation phase (1, 2, or 3)
            gaps: List[dict] - Information gaps from Gap Analysis Agent (for phases 2-3)
            trial_context: Optional context about specific trials

        Output:
            questions: List of question objects with text and metadata
            phase_explanation: Why these questions are being asked
            suggested_response: A natural response incorporating questions
        """
        profile: PatientProfile = input_data.get("patient_profile", PatientProfile())
        phase: int = input_data.get("phase", 1)
        gaps: List[dict] = input_data.get("gaps", [])
        trial_context: Optional[str] = input_data.get("trial_context")

        if phase == 1:
            return await self._generate_phase1_questions(profile)
        elif phase == 2:
            return await self._generate_phase2_questions(profile, gaps, trial_context)
        else:  # Phase 3
            return await self._generate_phase3_questions(profile, gaps, trial_context)

    async def _generate_phase1_questions(self, profile: PatientProfile) -> Dict[str, Any]:
        """Generate baseline screening questions (Phase 1)."""
        profile_dict = profile.model_dump()
        missing = []

        # Find missing Phase 1 attributes
        for attr, q_info in self.phase1_questions.items():
            value = profile_dict.get(attr)
            if value is None or value == "":
                missing.append({
                    "attribute": attr,
                    "question": q_info["question"],
                    "context": q_info["context"],
                    "priority": q_info["priority"],
                    "phase": 1
                })

        # Sort by priority
        missing.sort(key=lambda x: x["priority"])

        # Take top 2 questions
        questions = missing[:2]

        # Generate a natural response incorporating the questions
        if questions:
            suggested_response = await self._generate_natural_response(
                questions,
                phase=1,
                profile=profile
            )
        else:
            suggested_response = None

        return {
            "questions": questions,
            "phase": 1,
            "phase_explanation": "Gathering basic information to start searching for trials.",
            "suggested_response": suggested_response,
            "all_baseline_collected": len(missing) == 0
        }

    async def _generate_phase2_questions(
        self,
        profile: PatientProfile,
        gaps: List[dict],
        trial_context: Optional[str]
    ) -> Dict[str, Any]:
        """Generate trial-driven questions (Phase 2)."""

        if not gaps:
            return {
                "questions": [],
                "phase": 2,
                "phase_explanation": "No additional information needed from trials.",
                "suggested_response": None
            }

        # Convert gaps to questions using LLM
        questions = await self._gaps_to_questions(gaps, profile, trial_context)

        # Generate natural response
        if questions:
            suggested_response = await self._generate_natural_response(
                questions[:2],  # Limit to 2 questions at a time
                phase=2,
                profile=profile,
                trial_context=trial_context
            )
        else:
            suggested_response = None

        return {
            "questions": questions[:3],  # Return up to 3 for display
            "phase": 2,
            "phase_explanation": "Asking about specific requirements from potential trial matches.",
            "suggested_response": suggested_response
        }

    async def _generate_phase3_questions(
        self,
        profile: PatientProfile,
        gaps: List[dict],
        trial_context: Optional[str]
    ) -> Dict[str, Any]:
        """Generate gap-filling questions (Phase 3)."""

        if not gaps:
            return {
                "questions": [],
                "phase": 3,
                "phase_explanation": "All necessary information collected.",
                "suggested_response": None
            }

        # Focus on remaining unknowns and clarifications
        questions = await self._gaps_to_questions(
            gaps,
            profile,
            trial_context,
            is_clarification=True
        )

        if questions:
            suggested_response = await self._generate_natural_response(
                questions[:2],
                phase=3,
                profile=profile,
                trial_context=trial_context
            )
        else:
            suggested_response = None

        return {
            "questions": questions[:2],
            "phase": 3,
            "phase_explanation": "Clarifying remaining details to finalize eligibility.",
            "suggested_response": suggested_response
        }

    async def _gaps_to_questions(
        self,
        gaps: List[dict],
        profile: PatientProfile,
        trial_context: Optional[str],
        is_clarification: bool = False
    ) -> List[dict]:
        """Convert information gaps to natural questions using LLM."""

        if not gaps:
            return []

        # Check for sensitive topics
        sensitive_gaps = []
        regular_gaps = []

        for gap in gaps:
            attr = gap.get("attribute", "").lower()
            is_sensitive = any(s in attr for s in self.sensitive_topics.keys())
            if is_sensitive:
                sensitive_gaps.append(gap)
            else:
                regular_gaps.append(gap)

        # Prioritize regular gaps, then sensitive
        ordered_gaps = regular_gaps + sensitive_gaps

        prompt = f"""Convert these information gaps into natural, empathetic patient questions.

INFORMATION GAPS:
{json.dumps(ordered_gaps[:5], indent=2)}

CURRENT PATIENT INFO:
- Condition: {profile.primary_condition or 'Not yet provided'}
- Age: {profile.age or 'Not yet provided'}

{"TRIAL CONTEXT: " + trial_context if trial_context else ""}

{"These are CLARIFICATION questions - be extra gentle and explain why we're asking again." if is_clarification else ""}

For each gap, generate a question object with:
1. attribute: The attribute being asked about
2. question: A natural, conversational question
3. context: Brief explanation of why this matters (1 sentence)
4. is_sensitive: true if this is a sensitive topic
5. optional_note: If sensitive, a note that answering is optional

IMPORTANT:
- Don't be robotic or clinical
- Show empathy
- Keep questions short and clear
- For sensitive topics, add reassurance

Respond with a JSON array:
[
  {{
    "attribute": "string",
    "question": "string",
    "context": "string",
    "is_sensitive": boolean,
    "optional_note": "string or null"
  }}
]"""

        try:
            response = await self.llm.generate_json(prompt, self.get_system_prompt())
            questions = json.loads(response)
            if isinstance(questions, list):
                # Add phase info
                for q in questions:
                    q["phase"] = 3 if is_clarification else 2
                return questions
        except Exception as e:
            print(f"Question generation error: {e}")

        # Fallback: use question hints from gaps
        fallback_questions = []
        for gap in ordered_gaps[:3]:
            hint = gap.get("question_hint", gap.get("reason", ""))
            if hint:
                fallback_questions.append({
                    "attribute": gap.get("attribute", "unknown"),
                    "question": hint if "?" in hint else f"Could you tell me about your {gap.get('attribute', 'medical history')}?",
                    "context": gap.get("reason", "This helps us evaluate trial eligibility."),
                    "is_sensitive": False,
                    "phase": 3 if is_clarification else 2
                })

        return fallback_questions

    async def _generate_natural_response(
        self,
        questions: List[dict],
        phase: int,
        profile: PatientProfile,
        trial_context: Optional[str] = None
    ) -> str:
        """Generate a natural conversational response incorporating questions."""

        if not questions:
            return ""

        # Simple template-based response for efficiency
        if phase == 1:
            if not profile.primary_condition:
                return questions[0]["question"]

            intro = "Thank you for that information. "
            q_text = " ".join([q["question"] for q in questions[:2]])
            return intro + q_text

        elif phase == 2:
            intro = "I've found some potential trial matches. To better evaluate your eligibility, "
            if len(questions) == 1:
                return intro + questions[0]["question"].lower()
            else:
                q1 = questions[0]["question"]
                return intro + q1

        else:  # Phase 3
            intro = "Just a few more details to clarify: "
            return intro + questions[0]["question"]


# Singleton instance
question_generation_agent = QuestionGenerationAgent()
