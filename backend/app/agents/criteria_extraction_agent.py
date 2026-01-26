import json
from typing import Any, Dict, List
from .base_agent import BaseAgent
from ..schemas.trial import ClinicalTrial, StructuredCriterion


class CriteriaExtractionAgent(BaseAgent):
    """
    Agent responsible for parsing free-text eligibility criteria
    into structured, machine-readable format.
    """

    def __init__(self):
        super().__init__(
            name="Criteria Extraction Agent",
            description="Parse eligibility criteria from clinical trials into structured format."
        )

    def get_system_prompt(self) -> str:
        return """You are a clinical trial eligibility criteria parser. Your job is to convert free-text eligibility criteria into structured rules.

For each criterion, extract:
1. criterion_type: "inclusion" or "exclusion"
2. original_text: The exact original text
3. attribute: The patient attribute being checked (e.g., "age", "diagnosis", "medication", "lab_value", "comorbidity")
4. operator: The comparison (e.g., ">=", "<=", "equals", "has", "has_not", "between")
5. value: The required value or threshold

Return a JSON array of structured criteria:
[
    {
        "criterion_type": "inclusion",
        "original_text": "Age 18 years or older",
        "attribute": "age",
        "operator": ">=",
        "value": "18"
    },
    ...
]

Be thorough but precise. Some criteria may not fit this structure - still include them with best-effort parsing."""

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract structured criteria from a clinical trial.

        Input:
            - trial: ClinicalTrial with eligibility_criteria_text

        Output:
            - inclusion_criteria: List of structured inclusion criteria
            - exclusion_criteria: List of structured exclusion criteria
            - parsing_confidence: Confidence in the parsing
        """
        trial: ClinicalTrial = input_data.get("trial")

        if not trial or not trial.eligibility_criteria_text:
            return {
                "inclusion_criteria": [],
                "exclusion_criteria": [],
                "parsing_confidence": 0.0
            }

        prompt = f"""Parse the following eligibility criteria into structured format:

{trial.eligibility_criteria_text}

Return a JSON array of structured criteria."""

        try:
            response = await self.llm.generate_json(prompt, self.get_system_prompt())
            criteria_list = json.loads(response)

            inclusion = []
            exclusion = []

            for i, crit in enumerate(criteria_list):
                # Ensure value is always a string
                raw_value = crit.get("value")
                if raw_value is None:
                    value_str = None
                elif isinstance(raw_value, (dict, list)):
                    value_str = json.dumps(raw_value)
                else:
                    value_str = str(raw_value)

                structured = StructuredCriterion(
                    criterion_id=f"{trial.nct_id}_C{i+1}",
                    original_text=str(crit.get("original_text", "")),
                    criterion_type=crit.get("criterion_type", "inclusion"),
                    attribute=crit.get("attribute"),
                    operator=crit.get("operator"),
                    value=value_str
                )

                if crit.get("criterion_type") == "exclusion":
                    exclusion.append(structured)
                else:
                    inclusion.append(structured)

            return {
                "inclusion_criteria": inclusion,
                "exclusion_criteria": exclusion,
                "parsing_confidence": 0.8 if criteria_list else 0.0
            }

        except json.JSONDecodeError as e:
            print(f"Failed to parse criteria: {e}")
            return {
                "inclusion_criteria": [],
                "exclusion_criteria": [],
                "parsing_confidence": 0.0
            }
        except Exception as e:
            print(f"Error extracting criteria: {e}")
            return {
                "inclusion_criteria": [],
                "exclusion_criteria": [],
                "parsing_confidence": 0.0
            }


# Singleton instance
criteria_extraction_agent = CriteriaExtractionAgent()
