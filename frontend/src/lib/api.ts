// API client for Suksham Vachak backend

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Curated match IDs for the homepage - exciting India matches
export const CURATED_MATCH_IDS = [
  "951341", // India vs Pakistan T20 World Cup 2016 - Eden Gardens
  "895819", // Australia vs India T20 2016 - MCG
  "667731", // England vs India T20 2014 - Edgbaston
  "966751", // India vs Pakistan Asia Cup T20 2016
  "895815", // Australia vs India ODI 2016 - SCG
];

export interface MatchFilters {
  format?: string;
  team?: string;
  limit?: number;
}

export async function fetchMatches(filters?: MatchFilters) {
  const params = new URLSearchParams();
  if (filters?.format) params.set("match_format", filters.format);
  if (filters?.team) params.set("team", filters.team);
  if (filters?.limit) params.set("limit", filters.limit.toString());

  const url = params.toString()
    ? `${API_BASE}/api/matches?${params}`
    : `${API_BASE}/api/matches`;

  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to fetch matches");
  return res.json();
}

export async function fetchMatch(matchId: string) {
  const res = await fetch(`${API_BASE}/api/matches/${matchId}`);
  if (!res.ok) throw new Error("Failed to fetch match");
  return res.json();
}

export async function fetchCuratedMatches() {
  // Fetch the curated matches by their IDs
  const matches = await Promise.all(
    CURATED_MATCH_IDS.map(async (id) => {
      try {
        return await fetchMatch(id);
      } catch {
        return null;
      }
    }),
  );
  return matches.filter((m) => m !== null);
}

export async function fetchMoments(matchId: string) {
  const res = await fetch(`${API_BASE}/api/matches/${matchId}/moments`);
  if (!res.ok) throw new Error("Failed to fetch moments");
  return res.json();
}

export async function fetchPersonas() {
  const res = await fetch(`${API_BASE}/api/personas`);
  if (!res.ok) throw new Error("Failed to fetch personas");
  return res.json();
}

export async function generateCommentary(
  matchId: string,
  ballNumber: string,
  personaId: string,
  language: "en" | "hi" = "en",
) {
  const res = await fetch(`${API_BASE}/api/commentary`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      match_id: matchId,
      ball_number: ballNumber,
      persona_id: personaId,
      language: language,
    }),
  });
  if (!res.ok) throw new Error("Failed to generate commentary");
  return res.json();
}
