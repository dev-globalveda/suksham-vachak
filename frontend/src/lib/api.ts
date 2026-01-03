// API client for Suksham Vachak backend

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchMatches() {
  const res = await fetch(`${API_BASE}/api/matches`);
  if (!res.ok) throw new Error("Failed to fetch matches");
  return res.json();
}

export async function fetchMatch(matchId: string) {
  const res = await fetch(`${API_BASE}/api/matches/${matchId}`);
  if (!res.ok) throw new Error("Failed to fetch match");
  return res.json();
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
