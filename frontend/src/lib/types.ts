export type Challenge = {
  id: string;
  title: string;
  prompt: string;
  category: string;
  difficulty: number;
  estimated_minutes: number;
};

export type ChallengeResponse = {
  challenge: Challenge;
  personalization_note: string | null;
};

export type Discovery = {
  id: string;
  challenge_id: string;
  image_url: string;
  title: string;
  description: string;
  score: number;
  confidence: number;
  category: string;
  completed: boolean;
  feedback: string;
  reasoning: string;
  interesting_detail: string;
  visual_description: string;
  points_awarded: number;
  tagline: string;
  created_at: string;
};

export type DiscoveryResponse = {
  discovery: Discovery;
  profile: Profile | null;
};

export type Profile = {
  id: string;
  email: string;
  display_name: string;
  total_points: number;
  discoveries_count: number;
  current_streak: number;
  completed_challenges: number;
  outdoor_minutes_estimate: number;
  favorite_categories: Record<string, number>;
};

export type AuthUser = {
  id: string;
  email: string;
  display_name: string;
};

export type AuthResponse = {
  token: string;
  user: AuthUser;
};

/** Shown while Gemma is thinking. Kept calm and short on purpose (SPEC §38). */
export const THINKING_LINES = [
  "Looking closely...",
  "Finding something interesting...",
  "Reading the photograph...",
] as const;
