import json
from typing import Any, Dict
from .base_agent import BaseAgent
from ..schemas.patient import PatientProfile


class PatientProfilingAgent(BaseAgent):
    """
    Agent responsible for extracting structured patient information
    from conversational free-text input.
    """

    def __init__(self):
        super().__init__(
            name="Patient Profiling Agent",
            description="Extract structured patient attributes from natural language conversation."
        )

    def get_system_prompt(self) -> str:
        return """You are a medical information extraction specialist. Your job is to extract patient attributes from conversational text.

Extract ONLY information that is explicitly stated. Do not infer or assume.

Return a JSON object with these fields (use null for unknown):
{
    "age": <integer or null>,
    "biological_sex": <"male", "female", "other", or null>,
    "primary_condition": <string or null>,
    "condition_stage": <string or null>,
    "country": <string or null>,
    "state_province": <string or null>,
    "city": <string or null>,
    "comorbidities": [<list of strings>],
    "current_medications": [<list of strings>],
    "prior_treatments": [<list of strings>],
    "allergies": [<list of strings>],
    "smoking_status": <string or null>,
    "additional_attributes": {<any other relevant medical info>}
}

Be precise and medical. Convert informal language to proper medical terms where appropriate."""

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract patient attributes from user message.

        Input:
            - message: The user's message text
            - current_profile: Existing patient profile to update

        Output:
            - extracted_attributes: New attributes found in this message
            - updated_profile: Merged profile with new attributes
            - confidence: Confidence in extractions
        """
        message = input_data.get("message", "")
        current_profile = input_data.get("current_profile", PatientProfile())

        prompt = f"""Extract patient information from this message:

"{message}"

Current known profile:
{current_profile.model_dump_json(indent=2)}

Return JSON with any NEW information found in this message."""

        try:
            response = await self.llm.generate_json(prompt, self.get_system_prompt())

            # Parse the JSON response
            extracted = json.loads(response)

            # Merge with existing profile
            updated_profile = self._merge_profiles(current_profile, extracted)

            return {
                "extracted_attributes": extracted,
                "updated_profile": updated_profile,
                "confidence": self._calculate_confidence(extracted)
            }

        except json.JSONDecodeError as e:
            print(f"Failed to parse LLM response as JSON: {e}")
            return {
                "extracted_attributes": {},
                "updated_profile": current_profile,
                "confidence": 0.0
            }

    def _merge_profiles(self, current: PatientProfile, new_data: dict) -> PatientProfile:
        """Merge new extracted data into existing profile."""
        profile_dict = current.model_dump()

        for key, value in new_data.items():
            if value is not None and key in profile_dict:
                if isinstance(value, list) and isinstance(profile_dict[key], list):
                    # Extend lists without duplicates
                    existing = set(profile_dict[key])
                    profile_dict[key] = list(existing.union(set(value)))
                elif isinstance(value, dict) and isinstance(profile_dict[key], dict):
                    # Merge dicts
                    profile_dict[key].update(value)
                else:
                    # Overwrite scalar values
                    profile_dict[key] = value

        return PatientProfile(**profile_dict)

    def _calculate_confidence(self, extracted: dict) -> float:
        """Calculate confidence based on how many fields were extracted."""
        key_fields = ["age", "biological_sex", "primary_condition", "country"]
        extracted_key_fields = sum(1 for f in key_fields if extracted.get(f) is not None)
        return extracted_key_fields / len(key_fields)


# Singleton instance
patient_profiling_agent = PatientProfilingAgent()
