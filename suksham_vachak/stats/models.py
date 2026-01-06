"""Data models for cricket statistics."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PlayerMatchupStats:
    """Aggregated head-to-head statistics between a batter and bowler."""

    batter_id: str
    batter_name: str
    bowler_id: str
    bowler_name: str

    # Aggregated stats across all matches
    matches: int
    balls_faced: int
    runs_scored: int
    dismissals: int
    dots: int
    fours: int
    sixes: int

    @property
    def strike_rate(self) -> float:
        """Calculate strike rate (runs per 100 balls)."""
        if self.balls_faced == 0:
            return 0.0
        return (self.runs_scored / self.balls_faced) * 100

    @property
    def average(self) -> float:
        """Calculate batting average (runs per dismissal)."""
        if self.dismissals == 0:
            return float("inf") if self.runs_scored > 0 else 0.0
        return self.runs_scored / self.dismissals

    @property
    def dot_percentage(self) -> float:
        """Calculate percentage of dot balls."""
        if self.balls_faced == 0:
            return 0.0
        return (self.dots / self.balls_faced) * 100

    @property
    def boundary_percentage(self) -> float:
        """Calculate percentage of boundaries (4s + 6s)."""
        if self.balls_faced == 0:
            return 0.0
        return ((self.fours + self.sixes) / self.balls_faced) * 100

    def to_commentary_context(self) -> str:
        """Format stats for LLM prompt context."""
        parts = [
            f"{self.batter_name} vs {self.bowler_name}:",
            f"{self.runs_scored} runs",
            f"{self.balls_faced} balls",
            f"SR {self.strike_rate:.1f}",
        ]

        if self.dismissals > 0:
            parts.append(f"{self.dismissals}x dismissed")
            parts.append(f"avg {self.average:.1f}")

        if self.fours > 0 or self.sixes > 0:
            boundary_parts = []
            if self.fours > 0:
                boundary_parts.append(f"{self.fours} fours")
            if self.sixes > 0:
                boundary_parts.append(f"{self.sixes} sixes")
            parts.append(f"({', '.join(boundary_parts)})")

        return " | ".join(parts[:4]) + (" | " + " | ".join(parts[4:]) if len(parts) > 4 else "")

    def to_short_context(self) -> str:
        """Brief one-line summary for commentary."""
        avg_str = f"avg {self.average:.1f}" if self.dismissals > 0 else "not out"
        return f"{self.batter_name} vs {self.bowler_name}: {self.runs_scored}/{self.balls_faced} SR {self.strike_rate:.0f}, {avg_str}"


@dataclass
class MatchupRecord:
    """Single match record for a batter-bowler matchup.

    This represents the aggregated stats from one match between a specific
    batter and bowler pair. Used for storing in the database.
    """

    batter_id: str
    batter_name: str
    bowler_id: str
    bowler_name: str
    match_id: str
    match_date: str
    match_format: str
    venue: str

    balls_faced: int
    runs_scored: int
    dots: int
    fours: int
    sixes: int
    dismissals: int  # 0 or 1
    dismissal_type: str | None  # "bowled", "caught", etc.
