from fastapi import APIRouter, HTTPException
from typing import Dict, List, Optional
import uuid
from datetime import datetime

from ...schemas.chat import ChatRequest, ChatResponse, ChatMessage
from ...schemas.patient import PatientProfile, ConversationState
from ...schemas.trial import TrialMatch, EligibilityStatus
from ...agents.patient_profiling_agent import patient_profiling_agent
from ...agents.trial_discovery_agent import trial_discovery_agent
from ...agents.criteria_extraction_agent import criteria_extraction_agent
from ...agents.eligibility_matching_agent import eligibility_matching_agent
from ...agents.gap_analysis_agent import gap_analysis_agent
from ...agents.question_generation_agent import question_generation_agent
from ...services.llm_service import llm_service

router = APIRouter()

# In-memory session storage (use Redis in production)
sessions: Dict[str, ConversationState] = {}

# Cache for trial matches to avoid re-querying
trial_cache: Dict[str, List[TrialMatch]] = {}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process a chat message and return response with potential trial matches.

    Implements three-phase questioning strategy:
    - Phase 1: Baseline screening (age, condition, location)
    - Phase 2: Trial-driven questioning (based on specific trial criteria)
    - Phase 3: Gap-filling and clarification (resolve uncertain eligibility)
    """
    # Get or create session
    session_id = request.session_id or str(uuid.uuid4())

    if session_id not in sessions:
        sessions[session_id] = ConversationState(
            session_id=session_id,
            patient_profile=PatientProfile(),
            phase=1,
            messages=[]
        )

    state = sessions[session_id]

    # Add user message to history
    state.messages.append({
        "role": "user",
        "content": request.message,
        "timestamp": datetime.utcnow().isoformat()
    })

    # Step 1: Extract patient information from message
    profile_result = await patient_profiling_agent.process({
        "message": request.message,
        "current_profile": state.patient_profile
    })

    state.patient_profile = profile_result["updated_profile"]
    profile_updated = bool(profile_result["extracted_attributes"])

    # Step 2: Determine current phase and get trial matches if applicable
    trial_matches = []
    gaps = []
    phase_changed = False

    if state.phase == 1:
        # Phase 1: Check if we have minimum info to search for trials
        if _has_minimum_profile(state.patient_profile):
            trial_matches = await _find_matching_trials(state.patient_profile)

            if trial_matches:
                # Cache trial matches for this session
                trial_cache[session_id] = trial_matches

                # Transition to Phase 2
                state.phase = 2
                phase_changed = True

                # Analyze gaps for Phase 2 questioning
                gaps = await _analyze_gaps(trial_matches, state.patient_profile)

    elif state.phase == 2:
        # Phase 2: Trial-driven questioning
        # Re-evaluate trials with updated profile
        if profile_updated:
            trial_matches = await _find_matching_trials(state.patient_profile)
            trial_cache[session_id] = trial_matches
        else:
            trial_matches = trial_cache.get(session_id, [])

        # Analyze remaining gaps
        gaps = await _analyze_gaps(trial_matches, state.patient_profile)

        # Check if we should move to Phase 3
        if _should_transition_to_phase3(trial_matches, gaps):
            state.phase = 3
            phase_changed = True

    else:  # Phase 3
        # Phase 3: Gap-filling and final clarification
        if profile_updated:
            trial_matches = await _find_matching_trials(state.patient_profile)
            trial_cache[session_id] = trial_matches
        else:
            trial_matches = trial_cache.get(session_id, [])

        gaps = await _analyze_gaps(trial_matches, state.patient_profile)

    # Step 3: Generate follow-up questions based on phase
    question_result = await question_generation_agent.process({
        "patient_profile": state.patient_profile,
        "phase": state.phase,
        "gaps": gaps,
        "trial_context": _get_trial_context(trial_matches) if trial_matches else None
    })

    follow_up_questions = [q["question"] for q in question_result.get("questions", [])]

    # Step 4: Generate response
    response_content = await _generate_response(
        state=state,
        user_message=request.message,
        trial_matches=trial_matches,
        phase_changed=phase_changed,
        question_result=question_result,
        gaps=gaps
    )

    # Create response message
    assistant_message = ChatMessage(
        id=str(uuid.uuid4()),
        role="assistant",
        content=response_content,
        timestamp=datetime.utcnow()
    )

    # Add to history
    state.messages.append({
        "role": "assistant",
        "content": response_content,
        "timestamp": datetime.utcnow().isoformat()
    })

    return ChatResponse(
        session_id=session_id,
        message=assistant_message,
        trial_matches=trial_matches,
        patient_profile_updated=profile_updated,
        current_phase=state.phase,
        follow_up_questions=follow_up_questions
    )


async def _generate_response(
    state: ConversationState,
    user_message: str,
    trial_matches: List[TrialMatch],
    phase_changed: bool,
    question_result: dict,
    gaps: List[dict]
) -> str:
    """Generate an appropriate response based on conversation state and phase."""

    profile = state.patient_profile
    phase = state.phase
    suggested_response = question_result.get("suggested_response")

    # Build phase-specific system prompt
    if phase == 1:
        phase_instruction = """You are in Phase 1 (Baseline Screening).
Your goal is to gather basic information: medical condition, age, biological sex, and location.
Ask naturally and conversationally. Don't overwhelm with too many questions at once."""

    elif phase == 2:
        phase_instruction = f"""You are in Phase 2 (Trial-Driven Questioning).
You have found {len(trial_matches)} potential trial matches.
Now ask questions specifically related to trial eligibility criteria.
Be specific about why you're asking - reference that trials have certain requirements."""

    else:
        phase_instruction = """You are in Phase 3 (Gap-Filling & Clarification).
Focus on resolving any remaining uncertainties in eligibility.
Be gentle and explain that these final details will help finalize the recommendations."""

    system_prompt = f"""You are a friendly and professional clinical trial assistant.

{phase_instruction}

Guidelines:
- Be empathetic and conversational
- Avoid medical jargon
- Never provide medical advice
- Keep responses concise (2-4 sentences max)
- If you have questions to ask, incorporate them naturally

Current patient profile:
{profile.model_dump_json(indent=2)}

{"Suggested follow-up: " + suggested_response if suggested_response else ""}"""

    # Build context from recent messages
    recent_messages = state.messages[-6:]
    context = "\n".join([f"{m['role']}: {m['content']}" for m in recent_messages])

    # Phase-specific prompts
    if phase_changed and phase == 2:
        prompt = f"""The patient just provided enough information to search for trials.
You found {len(trial_matches)} potential matches.

Recent conversation:
{context}

Patient's message: {user_message}

Respond by:
1. Acknowledging their information
2. Letting them know you found some potential trials
3. Asking the first trial-specific question (if any): {suggested_response or 'Ask about their medical history details'}

Keep it warm and encouraging."""

    elif phase == 1 and not profile.primary_condition:
        prompt = f"""This is the start of the conversation or we still need to know their condition.

Recent conversation:
{context}

Patient's message: {user_message}

Respond warmly and ask about their medical condition if they haven't shared it.
If they did share it, acknowledge and ask a follow-up from: {suggested_response or 'age or location'}"""

    else:
        # Default prompt
        trial_info = ""
        if trial_matches:
            eligible_count = sum(1 for m in trial_matches if m.eligibility_status == EligibilityStatus.ELIGIBLE)
            uncertain_count = sum(1 for m in trial_matches if m.eligibility_status == EligibilityStatus.UNCERTAIN)
            trial_info = f"\nCurrent matches: {eligible_count} eligible, {uncertain_count} uncertain eligibility."

        prompt = f"""Continue the conversation naturally.
{trial_info}

Recent conversation:
{context}

Patient's message: {user_message}

{"Incorporate this question: " + suggested_response if suggested_response else "Respond helpfully to their message."}

Keep your response concise and natural."""

    try:
        response = await llm_service.generate(prompt, system_prompt, temperature=0.7)
        return response
    except Exception as e:
        print(f"Response generation error: {e}")
        # Fallback responses by phase
        if phase == 1:
            if not profile.primary_condition:
                return "Thank you for reaching out. I'm here to help you find clinical trials. Could you tell me about the medical condition you're seeking treatment for?"
            elif not profile.age:
                return "That's helpful, thank you. May I ask your age? This helps us find trials with matching eligibility criteria."
            else:
                return "Thanks for sharing. What country are you located in? This will help us find trials near you."
        elif phase == 2:
            return f"I've found {len(trial_matches)} potential trial matches for you. To better evaluate your eligibility, could you tell me more about your medical history and any current medications?"
        else:
            return "Thank you for that information. Just a few more details will help me finalize the best trial recommendations for you."


def _has_minimum_profile(profile: PatientProfile) -> bool:
    """Check if we have minimum information to search for trials."""
    return bool(profile.primary_condition)


def _should_transition_to_phase3(trial_matches: List[TrialMatch], gaps: List[dict]) -> bool:
    """Determine if we should move from Phase 2 to Phase 3."""
    if not trial_matches:
        return False

    # Move to Phase 3 if:
    # 1. We have at least one eligible trial, OR
    # 2. Most gaps have been addressed (few high-priority gaps remain)
    has_eligible = any(m.eligibility_status == EligibilityStatus.ELIGIBLE for m in trial_matches)

    high_priority_gaps = [g for g in gaps if g.get("priority") == "high"]

    return has_eligible or len(high_priority_gaps) <= 1


async def _analyze_gaps(trial_matches: List[TrialMatch], profile: PatientProfile) -> List[dict]:
    """Use Gap Analysis Agent to identify missing information."""
    if not trial_matches:
        return []

    gap_result = await gap_analysis_agent.process({
        "trial_matches": trial_matches,
        "patient_profile": profile
    })

    return gap_result.get("gaps", [])


def _get_trial_context(trial_matches: List[TrialMatch]) -> str:
    """Generate context about matched trials for question generation."""
    if not trial_matches:
        return ""

    contexts = []
    for match in trial_matches[:3]:  # Top 3 trials
        status = match.eligibility_status.value
        unknown_count = len(match.criteria_unknown)
        contexts.append(
            f"Trial {match.trial.nct_id}: {status}, {unknown_count} criteria need clarification"
        )

    return "; ".join(contexts)


async def _find_matching_trials(profile: PatientProfile) -> List[TrialMatch]:
    """Find and evaluate trials matching the patient profile."""

    # Discover trials
    discovery_result = await trial_discovery_agent.process({
        "patient_profile": profile,
        "max_results": 10
    })

    trials = discovery_result.get("trials", [])
    matches = []

    for trial in trials[:5]:  # Limit to top 5 for performance
        # Extract criteria
        criteria_result = await criteria_extraction_agent.process({"trial": trial})

        trial.inclusion_criteria = criteria_result.get("inclusion_criteria", [])
        trial.exclusion_criteria = criteria_result.get("exclusion_criteria", [])

        # Match against patient
        match_result = await eligibility_matching_agent.process({
            "patient_profile": profile,
            "trial": trial
        })

        if match_result.get("trial_match"):
            matches.append(match_result["trial_match"])

    # Sort by eligibility (eligible first, then uncertain, then ineligible)
    eligibility_order = {"eligible": 0, "uncertain": 1, "ineligible": 2}
    matches.sort(key=lambda m: eligibility_order.get(m.eligibility_status.value, 3))

    return matches


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get session state for debugging/monitoring."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    state = sessions[session_id]
    return {
        "session_id": session_id,
        "patient_profile": state.patient_profile.model_dump(),
        "phase": state.phase,
        "message_count": len(state.messages),
        "cached_trials": len(trial_cache.get(session_id, []))
    }


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    if session_id in sessions:
        del sessions[session_id]
    if session_id in trial_cache:
        del trial_cache[session_id]
    return {"status": "deleted"}
