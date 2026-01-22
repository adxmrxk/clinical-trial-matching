export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export interface ClinicalTrial {
  id: string;
  title: string;
  status: string;
  condition: string;
  location: string;
  eligibility: 'eligible' | 'ineligible' | 'uncertain';
  explanation: string;
  criteriaMatched: string[];
  criteriaViolated: string[];
  criteriaUnknown: string[];
}

export interface PatientProfile {
  age?: number;
  sex?: string;
  conditions?: string[];
  medications?: string[];
  labValues?: Record<string, number>;
  comorbidities?: string[];
}

export type EligibilityStatus = 'eligible' | 'ineligible' | 'uncertain';
