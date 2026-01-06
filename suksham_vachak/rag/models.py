"""Data models for RAG moments - Déjà Vu Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MomentType(Enum):
    """Types of cricket moments for retrieval."""

    WICKET = "wicket"
    MILESTONE = "milestone"  # 50, 100, 200, etc.
    BOUNDARY_FOUR = "boundary_four"
    BOUNDARY_SIX = "boundary_six"
    COLLAPSE = "collapse"
    COMEBACK = "comeback"
    CLUTCH = "clutch"  # Clutch performance under pressure
    HAT_TRICK = "hat_trick"
    LAST_OVER_THRILLER = "last_over_thriller"
    DEBUT = "debut"
    FAREWELL = "farewell"
    ICONIC = "iconic"  # Curated iconic moments


class MomentSource(Enum):
    """Source of the moment."""

    CRICSHEET = "cricsheet"  # Auto-indexed from match data
    CURATED = "curated"  # Hand-curated iconic moments


@dataclass
class CricketMoment:
    """A cricket moment for RAG retrieval.

    Represents a significant moment in cricket history that can be
    retrieved for contextual commentary (e.g., "reminds me of...").
    """

    # Unique identifier
    moment_id: str

    # Source and priority
    source: MomentSource
    priority: float = 1.0  # Higher = more likely to be retrieved

    # Match context
    match_id: str = ""
    match_format: str = "ODI"  # Test, ODI, T20
    date: str = ""  # YYYY-MM-DD
    venue: str = ""
    teams: tuple[str, str] = ("", "")

    # Moment details
    moment_type: MomentType = MomentType.ICONIC
    ball_number: str | None = None  # e.g., "19.4"
    innings: int = 1

    # Players involved
    primary_player: str = ""  # Main player in the moment
    secondary_player: str | None = None  # e.g., bowler for a wicket
    fielder: str | None = None

    # Situation context (for similarity matching)
    score: int = 0
    wickets: int = 0
    overs: float = 0.0
    phase: str = "middle"  # powerplay, middle, death
    pressure_level: str = "medium"  # calm, medium, high, critical
    momentum: str = "balanced"  # batting_dominant, bowling_dominant, balanced

    # Chase context (if applicable)
    target: int | None = None
    runs_required: int | None = None
    required_rate: float | None = None

    # Narrative text
    description: str = ""  # Human-readable description
    significance: str = ""  # Why this moment matters

    # For embedding generation
    embedding_text: str = ""  # Pre-computed text for embedding

    # Metadata for filtering
    tags: list[str] = field(default_factory=list)

    def to_embedding_text(self) -> str:
        """Generate text for embedding.

        Combines key attributes into a composite text that captures
        the essence of the moment for semantic similarity.
        """
        if self.embedding_text:
            return self.embedding_text

        parts = [
            self.primary_player,
            self.moment_type.value,
            self.match_format,
            f"{self.phase} phase",
            f"{self.pressure_level} pressure",
            f"{self.momentum} momentum",
        ]

        if self.secondary_player:
            parts.append(f"against {self.secondary_player}")

        if self.target:
            parts.append(f"chasing {self.target}")
            if self.runs_required:
                parts.append(f"needing {self.runs_required} runs")

        parts.append(f"score {self.score}/{self.wickets}")

        if self.description:
            parts.append(self.description)

        return " | ".join(parts)

    def to_metadata(self) -> dict[str, Any]:
        """Convert to ChromaDB metadata dict."""
        return {
            "moment_id": self.moment_id,
            "source": self.source.value,
            "priority": self.priority,
            "match_id": self.match_id,
            "match_format": self.match_format,
            "date": self.date,
            "venue": self.venue,
            "team1": self.teams[0],
            "team2": self.teams[1],
            "moment_type": self.moment_type.value,
            "ball_number": self.ball_number or "",
            "innings": self.innings,
            "primary_player": self.primary_player,
            "secondary_player": self.secondary_player or "",
            "phase": self.phase,
            "pressure_level": self.pressure_level,
            "momentum": self.momentum,
            "target": self.target or 0,
            "tags": ",".join(self.tags),
        }

    @classmethod
    def from_metadata(cls, metadata: dict[str, Any], description: str) -> CricketMoment:
        """Reconstruct from ChromaDB metadata."""
        return cls(
            moment_id=metadata["moment_id"],
            source=MomentSource(metadata["source"]),
            priority=metadata.get("priority", 1.0),
            match_id=metadata["match_id"],
            match_format=metadata["match_format"],
            date=metadata["date"],
            venue=metadata["venue"],
            teams=(metadata["team1"], metadata["team2"]),
            moment_type=MomentType(metadata["moment_type"]),
            ball_number=metadata.get("ball_number") or None,
            innings=metadata.get("innings", 1),
            primary_player=metadata["primary_player"],
            secondary_player=metadata.get("secondary_player") or None,
            phase=metadata.get("phase", "middle"),
            pressure_level=metadata.get("pressure_level", "medium"),
            momentum=metadata.get("momentum", "balanced"),
            target=metadata.get("target") or None,
            description=description,
            tags=metadata.get("tags", "").split(",") if metadata.get("tags") else [],
        )


@dataclass
class RetrievedMoment:
    """A moment retrieved from the vector store."""

    moment: CricketMoment
    similarity_score: float

    def to_callback_string(self) -> str:
        """Format as callback for NarrativeState.

        Returns a string suitable for inclusion in the commentary prompt
        as a historical parallel.
        """
        teams = f"{self.moment.teams[0]} vs {self.moment.teams[1]}"
        return f"History: {self.moment.description} ({teams}, {self.moment.date})"
