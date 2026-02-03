"""
Agent API endpoints for n8n workflow orchestration.

Each agent is exposed as a separate endpoint that n8n can call.
This enables transparent workflow orchestration with:
- Conditional branching
- Iterative loops
- Logging and debugging
- Visual workflow representation
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any, Optional

from ...agents.patient_profiling_agent import patient_profiling_agent
from ...agents.trial_discovery_agent import trial_discovery_agent
from ...agents.criteria_extraction_agent import criteria_extraction_agent
from ...agents.eligibility_matching_agent import eligibility_matching_agent
from ...agents.gap_analysis_agent import gap_analysis_agent
from ...agents.question_generation_agent import question_generation_agent
from ...schemas.patient import PatientProfile
from ...schemas.trial import ClinicalTrial, TrialMatch

router = APIRouter()


# ============== Request/Response Models ==============

class PatientProfilingRequest(BaseModel):
    message: str
    current_profile: Optional[Dict[str, Any]] = None


class PatientProfilingResponse(BaseModel):
    extracted_attributes: Dict[str, Any]
    updated_profile: Dict[str, Any]
    confidence: float
    validation_errors: List[str]


class TrialDiscoveryRequest(BaseModel):
    patient_profile: Dict[str, Any]
    max_results: int = 10


class TrialDiscoveryResponse(BaseModel):
    trials: List[Dict[str, Any]]
    total_found: int


class CriteriaExtractionRequest(BaseModel):
    trial: Dict[str, Any]


class CriteriaExtractionResponse(BaseModel):
    trial_id: str
    inclusion_criteria: List[Dict[str, Any]]
    exclusion_criteria: List[Dict[str, Any]]


class EligibilityMatchingRequest(BaseModel):
    patient_profile: Dict[str, Any]
    trial: Dict[str, Any]


class EligibilityMatchingResponse(BaseModel):
    trial_id: str
    eligibility_status: str  # "eligible", "ineligible", "uncertain"
    criteria_satisfied: List[Dict[str, Any]]
    criteria_violated: List[Dict[str, Any]]
    criteria_unknown: List[Dict[str, Any]]
    explanation: str


class GapAnalysisRequest(BaseModel):
    patient_profile: Dict[str, Any]
    trial_matches: List[Dict[str, Any]]


class GapAnalysisResponse(BaseModel):
    gaps: List[Dict[str, Any]]
    priority_order: List[str]


class QuestionGenerationRequest(BaseModel):
    patient_profile: Dict[str, Any]
    phase: int
    gaps: List[Dict[str, Any]] = []
    trial_context: Optional[str] = None


class QuestionGenerationResponse(BaseModel):
    questions: List[Dict[str, Any]]
    suggested_response: Optional[str]


# ============== Agent Endpoints ==============

@router.post("/profile", response_model=PatientProfilingResponse)
async def run_patient_profiling(request: PatientProfilingRequest):
    """
    Patient Profiling Agent: Extract structured patient information from text.

    Called by n8n after receiving user input to extract:
    - Demographics (age, sex, location)
    - Medical info (condition, medications, treatments)
    - Preferences (willing to travel)
    """
    try:
        current_profile = PatientProfile()
        if request.current_profile:
            current_profile = PatientProfile(**request.current_profile)

        result = await patient_profiling_agent.process({
            "message": request.message,
            "current_profile": current_profile
        })

        return PatientProfilingResponse(
            extracted_attributes=result["extracted_attributes"],
            updated_profile=result["updated_profile"].model_dump(),
            confidence=result["confidence"],
            validation_errors=result.get("validation_errors", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/discover", response_model=TrialDiscoveryResponse)
async def run_trial_discovery(request: TrialDiscoveryRequest):
    """
    Trial Discovery Agent: Find clinical trials matching patient profile.

    Called by n8n after patient profile is complete to:
    - Query ClinicalTrials.gov API
    - Filter by condition, location, status
    - Return relevant trials
    """
    try:
        patient_profile = PatientProfile(**request.patient_profile)

        result = await trial_discovery_agent.process({
            "patient_profile": patient_profile,
            "max_results": request.max_results
        })

        trials = result.get("trials", [])

        return TrialDiscoveryResponse(
            trials=[t.model_dump() if hasattr(t, 'model_dump') else t for t in trials],
            total_found=len(trials)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract", response_model=CriteriaExtractionResponse)
async def run_criteria_extraction(request: CriteriaExtractionRequest):
    """
    Criteria Extraction Agent: Parse eligibility criteria from trial.

    Called by n8n for each trial to:
    - Parse inclusion/exclusion criteria text
    - Convert to structured format
    - Identify required patient attributes
    """
    try:
        trial = ClinicalTrial(**request.trial)

        result = await criteria_extraction_agent.process({
            "trial": trial
        })

        return CriteriaExtractionResponse(
            trial_id=trial.nct_id,
            inclusion_criteria=[c.model_dump() if hasattr(c, 'model_dump') else c
                               for c in result.get("inclusion_criteria", [])],
            exclusion_criteria=[c.model_dump() if hasattr(c, 'model_dump') else c
                               for c in result.get("exclusion_criteria", [])]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/match", response_model=EligibilityMatchingResponse)
async def run_eligibility_matching(request: EligibilityMatchingRequest):
    """
    Eligibility Matching Agent: Check patient against trial criteria.

    Called by n8n after criteria extraction to:
    - Compare patient profile vs each criterion
    - Label as satisfied/violated/unknown
    - Determine overall eligibility status
    - Generate explanation
    """
    try:
        patient_profile = PatientProfile(**request.patient_profile)
        trial = ClinicalTrial(**request.trial)

        result = await eligibility_matching_agent.process({
            "patient_profile": patient_profile,
            "trial": trial
        })

        match = result.get("trial_match")
        if not match:
            raise HTTPException(status_code=500, detail="No match result returned")

        return EligibilityMatchingResponse(
            trial_id=trial.nct_id,
            eligibility_status=match.eligibility_status.value,
            criteria_satisfied=[c.model_dump() for c in match.criteria_satisfied],
            criteria_violated=[c.model_dump() for c in match.criteria_violated],
            criteria_unknown=[c.model_dump() for c in match.criteria_unknown],
            explanation=match.explanation
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gaps", response_model=GapAnalysisResponse)
async def run_gap_analysis(request: GapAnalysisRequest):
    """
    Gap Analysis Agent: Identify missing patient information.

    Called by n8n after matching to:
    - Find criteria marked as 'unknown'
    - Identify what patient info would resolve them
    - Prioritize by impact on eligibility
    """
    try:
        patient_profile = PatientProfile(**request.patient_profile)

        # Convert trial matches to proper format
        trial_matches = []
        for tm in request.trial_matches:
            trial_matches.append(TrialMatch(**tm))

        result = await gap_analysis_agent.process({
            "patient_profile": patient_profile,
            "trial_matches": trial_matches
        })

        gaps = result.get("gaps", [])

        return GapAnalysisResponse(
            gaps=gaps,
            priority_order=[g.get("attribute", "") for g in gaps]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/questions", response_model=QuestionGenerationResponse)
async def run_question_generation(request: QuestionGenerationRequest):
    """
    Question Generation Agent: Generate follow-up questions.

    Called by n8n when gaps exist to:
    - Generate targeted questions for missing info
    - Adapt questions to conversation phase
    - Avoid redundant questions
    """
    try:
        patient_profile = PatientProfile(**request.patient_profile)

        result = await question_generation_agent.process({
            "patient_profile": patient_profile,
            "phase": request.phase,
            "gaps": request.gaps,
            "trial_context": request.trial_context
        })

        return QuestionGenerationResponse(
            questions=result.get("questions", []),
            suggested_response=result.get("suggested_response")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== Orchestration Helpers ==============

class PipelineStatusRequest(BaseModel):
    session_id: str


@router.get("/health")
async def agent_health():
    """Health check for agent endpoints."""
    return {
        "status": "healthy",
        "agents": [
            "patient_profiling",
            "trial_discovery",
            "criteria_extraction",
            "eligibility_matching",
            "gap_analysis",
            "question_generation"
        ]
    }
