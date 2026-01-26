from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class EligibilityStatus(str, Enum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    UNCERTAIN = "uncertain"


class CriterionStatus(str, Enum):
    SATISFIED = "satisfied"
    VIOLATED = "violated"
    UNKNOWN = "unknown"


class StructuredCriterion(BaseModel):
    """A single eligibility criterion parsed from free text."""
    criterion_id: str
    original_text: str = Field(..., description="Original criterion text from trial")
    criterion_type: str = Field(..., description="inclusion or exclusion")

    # Parsed structure
    attribute: Optional[str] = Field(None, description="Patient attribute being checked (e.g., 'age', 'diagnosis')")
    operator: Optional[str] = Field(None, description="Comparison operator (e.g., '>=', 'has', 'not')")
    value: Optional[str] = Field(None, description="Required value or threshold")

    # Evaluation
    status: CriterionStatus = Field(CriterionStatus.UNKNOWN)
    patient_value: Optional[str] = Field(None, description="Patient's value for this attribute")
    explanation: Optional[str] = Field(None, description="Why this status was assigned")


class ClinicalTrial(BaseModel):
    """Clinical trial data from ClinicalTrials.gov."""
    nct_id: str = Field(..., description="ClinicalTrials.gov identifier")
    title: str
    brief_summary: Optional[str] = None
    detailed_description: Optional[str] = None

    # Status
    overall_status: str = Field(..., description="e.g., Recruiting, Active, Completed")
    phase: Optional[str] = None
    study_type: Optional[str] = None

    # Conditions
    conditions: List[str] = Field(default_factory=list)

    # Eligibility (raw)
    eligibility_criteria_text: Optional[str] = Field(None, description="Raw eligibility text")
    minimum_age: Optional[str] = None
    maximum_age: Optional[str] = None
    sex: Optional[str] = None

    # Eligibility (parsed)
    inclusion_criteria: List[StructuredCriterion] = Field(default_factory=list)
    exclusion_criteria: List[StructuredCriterion] = Field(default_factory=list)

    # Locations
    locations: List[dict] = Field(default_factory=list)

    # Contact
    contacts: List[dict] = Field(default_factory=list)

    # Sponsor
    lead_sponsor: Optional[str] = None


class TrialMatch(BaseModel):
    """Result of matching a patient to a trial."""
    trial: ClinicalTrial
    eligibility_status: EligibilityStatus

    # Criterion-level results
    criteria_satisfied: List[StructuredCriterion] = Field(default_factory=list)
    criteria_violated: List[StructuredCriterion] = Field(default_factory=list)
    criteria_unknown: List[StructuredCriterion] = Field(default_factory=list)

    # Overall explanation
    explanation: str = Field(..., description="Human-readable eligibility explanation")
    confidence_score: float = Field(0.0, ge=0.0, le=1.0)

    # Missing info that could change the result
    missing_information: List[str] = Field(default_factory=list)


class TrialSearchParams(BaseModel):
    """Parameters for searching clinical trials."""
    condition: Optional[str] = None
    location: Optional[str] = None
    status: List[str] = Field(default_factory=lambda: ["RECRUITING"])
    phase: Optional[List[str]] = None
    max_results: int = Field(20, le=100)
