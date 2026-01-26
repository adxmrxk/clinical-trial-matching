import httpx
from typing import List, Optional
from ..core.config import settings
from ..schemas.trial import ClinicalTrial, TrialSearchParams


class ClinicalTrialsAPIService:
    """
    Service for querying ClinicalTrials.gov API v2.
    Documentation: https://clinicaltrials.gov/data-api/api
    """

    def __init__(self):
        self.base_url = settings.CLINICAL_TRIALS_API_BASE
        self.client = httpx.AsyncClient(timeout=30.0)

    async def search_trials(self, params: TrialSearchParams) -> List[ClinicalTrial]:
        """
        Search for clinical trials based on condition, location, and status.
        """
        query_parts = []

        # Build query string
        if params.condition:
            query_parts.append(f"CONDITION:{params.condition}")

        if params.location:
            query_parts.append(f"LOCATION:{params.location}")

        # API parameters
        api_params = {
            "format": "json",
            "pageSize": params.max_results,
            "fields": ",".join([
                "NCTId",
                "BriefTitle",
                "OfficialTitle",
                "BriefSummary",
                "DetailedDescription",
                "OverallStatus",
                "Phase",
                "StudyType",
                "Condition",
                "EligibilityCriteria",
                "MinimumAge",
                "MaximumAge",
                "Sex",
                "LocationCity",
                "LocationState",
                "LocationCountry",
                "LocationFacility",
                "LeadSponsorName",
                "CentralContactName",
                "CentralContactPhone",
                "CentralContactEMail"
            ])
        }

        # Filter by status
        if params.status:
            status_filter = " OR ".join([f"SEARCH[OverallStatus]:{s}" for s in params.status])
            query_parts.append(f"({status_filter})")

        if query_parts:
            api_params["query.cond"] = params.condition if params.condition else ""

        # Add status filter
        if params.status:
            api_params["filter.overallStatus"] = ",".join(params.status)

        try:
            response = await self.client.get(
                f"{self.base_url}/studies",
                params=api_params
            )
            response.raise_for_status()
            data = response.json()

            trials = []
            for study in data.get("studies", []):
                trial = self._parse_study(study)
                if trial:
                    trials.append(trial)

            return trials

        except httpx.HTTPError as e:
            print(f"Error fetching trials: {e}")
            return []

    async def get_trial_by_id(self, nct_id: str) -> Optional[ClinicalTrial]:
        """
        Get a specific trial by NCT ID.
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/studies/{nct_id}",
                params={"format": "json"}
            )
            response.raise_for_status()
            data = response.json()
            return self._parse_study(data)

        except httpx.HTTPError as e:
            print(f"Error fetching trial {nct_id}: {e}")
            return None

    def _parse_study(self, study_data: dict) -> Optional[ClinicalTrial]:
        """
        Parse raw API response into ClinicalTrial model.
        """
        try:
            protocol = study_data.get("protocolSection", {})
            id_module = protocol.get("identificationModule", {})
            status_module = protocol.get("statusModule", {})
            desc_module = protocol.get("descriptionModule", {})
            design_module = protocol.get("designModule", {})
            eligibility_module = protocol.get("eligibilityModule", {})
            conditions_module = protocol.get("conditionsModule", {})
            contacts_module = protocol.get("contactsLocationsModule", {})
            sponsor_module = protocol.get("sponsorCollaboratorsModule", {})

            # Extract locations
            locations = []
            for loc in contacts_module.get("locations", []):
                locations.append({
                    "facility": loc.get("facility"),
                    "city": loc.get("city"),
                    "state": loc.get("state"),
                    "country": loc.get("country")
                })

            # Extract contacts
            contacts = []
            for contact in contacts_module.get("centralContacts", []):
                contacts.append({
                    "name": contact.get("name"),
                    "phone": contact.get("phone"),
                    "email": contact.get("email")
                })

            # Get lead sponsor
            lead_sponsor = None
            if sponsor_module.get("leadSponsor"):
                lead_sponsor = sponsor_module["leadSponsor"].get("name")

            return ClinicalTrial(
                nct_id=id_module.get("nctId", ""),
                title=id_module.get("briefTitle", id_module.get("officialTitle", "")),
                brief_summary=desc_module.get("briefSummary"),
                detailed_description=desc_module.get("detailedDescription"),
                overall_status=status_module.get("overallStatus", "Unknown"),
                phase=", ".join(design_module.get("phases", [])) if design_module.get("phases") else None,
                study_type=design_module.get("studyType"),
                conditions=conditions_module.get("conditions", []),
                eligibility_criteria_text=eligibility_module.get("eligibilityCriteria"),
                minimum_age=eligibility_module.get("minimumAge"),
                maximum_age=eligibility_module.get("maximumAge"),
                sex=eligibility_module.get("sex"),
                locations=locations,
                contacts=contacts,
                lead_sponsor=lead_sponsor
            )

        except Exception as e:
            print(f"Error parsing study: {e}")
            return None

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Singleton instance
clinical_trials_service = ClinicalTrialsAPIService()
