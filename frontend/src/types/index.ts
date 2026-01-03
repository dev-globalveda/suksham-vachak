// TypeScript types for Suksham Vachak

export interface Match {
  id: string;
  teams: string[];
  date: string;
  venue: string;
  format: string;
  winner: string | null;
  file: string;
}

export interface MatchDetails extends Match {
  toss: {
    winner: string;
    decision: string;
  };
}

export interface Moment {
  id: string;
  ball_number: string;
  innings: number;
  event_type: string;
  batter: string;
  bowler: string;
  runs: number;
  score: string;
  description: string;
  is_wicket: boolean;
  is_boundary: boolean;
  wicket_type?: string;
  fielder?: string;
}

export interface Persona {
  id: string;
  name: string;
  tagline: string;
  style: string;
  accent: string;
  language: string;
  description: string;
  color: string;
  accentColor: string;
}

export interface CommentaryRequest {
  match_id: string;
  ball_number: string;
  persona_id: string;
}

export interface CommentaryResponse {
  text: string;
  audio_base64: string | null;
  audio_format: string;
  persona_id: string;
  event_type: string;
  duration_seconds: number;
}
