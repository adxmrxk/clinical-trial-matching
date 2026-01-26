from fastapi import APIRouter, Query
from typing import List, Optional

from ...schemas.trial import ClinicalTrial, TrialSearchParams
from ...services.clinical_trials_api import clinical_trials_service

router = APIRouter()


@router.get("/search", response_model=List[ClinicalTrial])
async def search_trials(
        condition: Optional[str] = Query(None, description="Medical condition to search for"),
        location: Optional[str] = Query(None, description="Location (city, state, or country)"),
        status: List[str] = Query(default=["RECRUITING"], description="Trial status filter"),
        max_results: int = Query(20, le=100, description="Maximum number of results")
):
    """
    Search for clinical trials based on condition and location.
    """
    params = TrialSearchParams(
        condition=condition,
        location=location,
        status=status,
        max_results=max_results
    )

    trials = await clinical_trials_service.search_trials(params)
    return trials


@router.get("/{nct_id}", response_model=ClinicalTrial)
async def get_trial(nct_id: str):
    """
    Get a specific clinical trial by NCT ID.
    """
    trial = await clinical_trials_service.get_trial_by_id(nct_id)

    if not trial:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Trial {nct_id} not found")

    return trial
