"""RAG retriever for cricket commentary - Déjà Vu Engine.

Retrieves historical cricket moments that are similar to the
current match situation for contextual "reminds me of..." commentary.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .models import RetrievedMoment

if TYPE_CHECKING:
    from suksham_vachak.context.models import MatchSituation, PressureLevel
    from suksham_vachak.parser.events import CricketEvent

    from .store import MomentVectorStore


class DejaVuRetriever:
    """Retriever for historical parallels.

    Query strategy:
    1. Player-based: Find moments with same batter/bowler
    2. Situation-based: Find similar pressure/phase/momentum
    3. Format-based: Prefer same format (T20/ODI/Test)

    Results are combined and de-duplicated, with curated moments
    given priority over auto-indexed moments.
    """

    def __init__(
        self,
        store: MomentVectorStore,
        max_callbacks: int = 2,
        min_similarity: float = 0.3,
    ) -> None:
        """Initialize retriever.

        Args:
            store: Vector store for moments.
            max_callbacks: Maximum historical callbacks to return.
            min_similarity: Minimum similarity score threshold.
        """
        self.store = store
        self.max_callbacks = max_callbacks
        self.min_similarity = min_similarity

    def retrieve(
        self,
        event: CricketEvent,
        match: MatchSituation,
        pressure: PressureLevel,
    ) -> list[str]:
        """Retrieve historical parallels for current situation.

        Args:
            event: Current cricket event.
            match: Current match situation.
            pressure: Current pressure level.

        Returns:
            List of callback strings for NarrativeState.
        """
        # Build query context
        query_text = self._build_query_text(event, match, pressure)

        # Retrieve with multiple strategies
        retrieved: list[RetrievedMoment] = []

        # Strategy 1: Player-based retrieval
        player_moments = self._retrieve_by_player(event.batter, event.bowler)
        retrieved.extend(player_moments)

        # Strategy 2: Situation-based retrieval
        situation_moments = self._retrieve_by_situation(
            query_text=query_text,
            match_format=match.match_format,
            phase=match.phase.value,
            pressure=pressure.value,
        )
        retrieved.extend(situation_moments)

        # De-duplicate and rank
        unique_moments = self._deduplicate(retrieved)

        # Filter by similarity threshold
        filtered = [m for m in unique_moments if m.similarity_score >= self.min_similarity]

        # Convert to callback strings
        callbacks = [m.to_callback_string() for m in filtered[: self.max_callbacks]]

        return callbacks

    def _build_query_text(
        self,
        event: CricketEvent,
        match: MatchSituation,
        pressure: PressureLevel,
    ) -> str:
        """Build semantic query text from current context."""
        parts = [
            event.batter,
            f"vs {event.bowler}",
            match.match_format,
            match.phase.value,
            f"{pressure.value} pressure",
            f"{match.total_runs}/{match.total_wickets}",
        ]

        if event.is_wicket:
            parts.append(f"wicket {event.wicket_type}")
        elif event.is_boundary:
            parts.append("boundary" if event.runs_batter == 4 else "six")

        if match.is_chase:
            parts.append(f"chasing {match.target}")
            if match.runs_required is not None:
                parts.append(f"needing {match.runs_required}")

        return " | ".join(parts)

    def _retrieve_by_player(
        self,
        batter: str,
        bowler: str,
    ) -> list[RetrievedMoment]:
        """Retrieve moments involving current players."""
        moments: list[RetrievedMoment] = []

        # Batter's moments
        batter_moments = self.store.query_by_player(batter, n_results=2)
        moments.extend(batter_moments)

        # Bowler's moments (as secondary player)
        bowler_moments = self.store.query(
            query_text=f"cricket moment bowler {bowler}",
            n_results=2,
            where={"secondary_player": {"$eq": bowler}},
        )
        moments.extend(bowler_moments)

        return moments

    def _retrieve_by_situation(
        self,
        query_text: str,
        match_format: str,
        phase: str,
        pressure: str,
    ) -> list[RetrievedMoment]:
        """Retrieve moments from similar situations."""
        # Try format-specific first
        format_moments = self.store.query(
            query_text=query_text,
            n_results=3,
            where={"match_format": {"$eq": match_format}},
        )

        # Also get general moments
        general_moments = self.store.query(
            query_text=query_text,
            n_results=3,
        )

        return format_moments + general_moments

    def _deduplicate(
        self,
        moments: list[RetrievedMoment],
    ) -> list[RetrievedMoment]:
        """Remove duplicate moments, keeping highest score."""
        seen: dict[str, RetrievedMoment] = {}

        for moment in moments:
            mid = moment.moment.moment_id
            if mid not in seen or moment.similarity_score > seen[mid].similarity_score:
                seen[mid] = moment

        # Sort by score
        result = list(seen.values())
        result.sort(key=lambda x: x.similarity_score, reverse=True)

        return result
