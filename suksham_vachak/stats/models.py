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
    phase: str | None = None  # "powerplay", "middle", "death", "session1/2/3"


@dataclass
class PhaseStats:
    """Performance statistics for a specific match phase."""

    player_id: str
    player_name: str
    phase: str  # "powerplay", "middle", "death", "session1", "session2", "session3"
    match_format: str
    role: str  # "batter" or "bowler"

    # Aggregated stats
    matches: int
    balls: int  # balls faced (batter) or bowled (bowler)
    runs: int  # runs scored (batter) or conceded (bowler)
    dots: int
    fours: int
    sixes: int
    wickets: int  # dismissals (batter) or taken (bowler)

    @property
    def strike_rate(self) -> float:
        """Calculate strike rate (runs per 100 balls). For batters."""
        if self.balls == 0:
            return 0.0
        return (self.runs / self.balls) * 100

    @property
    def economy(self) -> float:
        """Calculate economy rate (runs per over). For bowlers."""
        if self.balls == 0:
            return 0.0
        overs = self.balls / 6
        return self.runs / overs

    @property
    def average(self) -> float:
        """Calculate average (runs per dismissal for batter, runs per wicket for bowler)."""
        if self.wickets == 0:
            return float("inf") if self.runs > 0 else 0.0
        return self.runs / self.wickets

    def to_context(self, role: str = "batter") -> str:
        """Format stats for LLM prompt context."""
        if role == "batter":
            return (
                f"{self.player_name} in {self.phase}: SR {self.strike_rate:.0f} ({self.balls} balls, {self.runs} runs)"
            )
        else:
            return f"{self.player_name} in {self.phase}: Econ {self.economy:.1f} ({self.wickets} wkts)"


@dataclass
class MatchPerformance:
    """Single match performance for form tracking."""

    match_id: str
    match_date: str
    match_format: str
    venue: str

    # Performance
    runs: int
    balls: int
    dismissals: int
    fours: int
    sixes: int

    @property
    def strike_rate(self) -> float:
        """Calculate strike rate for this match."""
        if self.balls == 0:
            return 0.0
        return (self.runs / self.balls) * 100


@dataclass
class RecentForm:
    """Recent form analysis for a player."""

    player_id: str
    player_name: str
    role: str  # "batter" or "bowler"

    # Last N matches
    matches: list[MatchPerformance]

    # Aggregated
    total_runs: int
    total_balls: int
    total_dismissals: int

    # Trend
    trend: str  # "improving", "declining", "stable"
    trend_description: str

    @property
    def average_strike_rate(self) -> float:
        """Calculate average strike rate across recent matches."""
        if self.total_balls == 0:
            return 0.0
        return (self.total_runs / self.total_balls) * 100

    @property
    def average(self) -> float:
        """Calculate batting average across recent matches."""
        if self.total_dismissals == 0:
            return float("inf") if self.total_runs > 0 else 0.0
        return self.total_runs / self.total_dismissals

    def to_context(self) -> str:
        """Format form for LLM prompt context."""
        match_count = len(self.matches)
        if self.role == "batter":
            avg_str = f"avg {self.average:.0f}" if self.total_dismissals > 0 else "not out"
            return f"Last {match_count}: {self.total_runs} runs, SR {self.average_strike_rate:.0f}, {avg_str} ({self.trend})"
        else:
            return f"Last {match_count}: {self.total_dismissals} wickets, {self.total_runs} runs ({self.trend})"
