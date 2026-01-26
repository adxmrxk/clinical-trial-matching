import { ClinicalTrial, ChatResponse, TrialMatch } from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

class ApiService {
  private sessionId: string | null = null;

  async sendMessage(message: string): Promise<{
    response: string;
    trials: ClinicalTrial[];
    sessionId: string;
  }> {
    const res = await fetch(`${API_BASE_URL}/chat/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: this.sessionId,
        message,
      }),
    });

    if (!res.ok) {
      throw new Error(`API error: ${res.status}`);
    }

    const data: ChatResponse = await res.json();
    this.sessionId = data.session_id;

    // Convert trial matches to simplified format for UI
    const trials = data.trial_matches.map(this.convertTrialMatch);

    return {
      response: data.message.content,
      trials,
      sessionId: data.session_id,
    };
  }

  private convertTrialMatch(match: TrialMatch): ClinicalTrial {
    const trial = match.trial;

    // Format location from first location in array
    const location = trial.locations.length > 0
      ? [trial.locations[0].city, trial.locations[0].state, trial.locations[0].country]
          .filter(Boolean)
          .join(', ')
      : 'Location not specified';

    return {
      id: trial.nct_id,
      title: trial.title,
      status: trial.overall_status,
      condition: trial.conditions.join(', ') || 'Not specified',
      location,
      eligibility: match.eligibility_status,
      explanation: match.explanation,
      criteriaMatched: match.criteria_satisfied.map(c => c.original_text),
      criteriaViolated: match.criteria_violated.map(c => c.original_text),
      criteriaUnknown: match.criteria_unknown.map(c => c.original_text),
    };
  }

  async searchTrials(condition: string, location?: string): Promise<ClinicalTrial[]> {
    const params = new URLSearchParams();
    if (condition) params.append('condition', condition);
    if (location) params.append('location', location);

    const res = await fetch(`${API_BASE_URL}/trials/search?${params}`);

    if (!res.ok) {
      throw new Error(`API error: ${res.status}`);
    }

    const trials = await res.json();

    return trials.map((trial: any) => ({
      id: trial.nct_id,
      title: trial.title,
      status: trial.overall_status,
      condition: trial.conditions.join(', '),
      location: trial.locations[0]
        ? `${trial.locations[0].city}, ${trial.locations[0].country}`
        : 'Not specified',
      eligibility: 'uncertain' as const,
      explanation: 'Eligibility not yet evaluated',
      criteriaMatched: [],
      criteriaViolated: [],
      criteriaUnknown: [],
    }));
  }

  resetSession() {
    this.sessionId = null;
  }
}

export const apiService = new ApiService();
