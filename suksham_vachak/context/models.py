"""Data models for rich match context."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from suksham_vachak.parser import CricketEvent


class MatchPhase(Enum):
    """Phase of the match."""

    POWERPLAY = "powerplay"  # Overs 1-6 in limited overs
    MIDDLE_OVERS = "middle_overs"  # Overs 7-15 in T20, 7-40 in ODI
    DEATH_OVERS = "death_overs"  # Final overs
    FIRST_SESSION = "first_session"  # Test: morning session
    SECOND_SESSION = "second_session"  # Test: afternoon
    THIRD_SESSION = "third_session"  # Test: evening
    EARLY_INNINGS = "early_innings"  # Generic early phase
    MIDDLE_INNINGS = "middle_innings"  # Generic middle
    LATE_INNINGS = "late_innings"  # Generic late/climax


class PressureLevel(Enum):
    """Pressure intensity levels."""

    CALM = "calm"  # Low pressure, comfortable situation
    BUILDING = "building"  # Pressure starting to mount
    TENSE = "tense"  # Significant pressure
    INTENSE = "intense"  # High pressure moment
    CRITICAL = "critical"  # Match-defining pressure


class MomentumState(Enum):
    """Current momentum in the match."""

    BATTING_DOMINANT = "batting_dominant"  # Batters on top
    BOWLING_DOMINANT = "bowling_dominant"  # Bowlers on top
    BALANCED = "balanced"  # Even contest
    MOMENTUM_SHIFT = "momentum_shift"  # Just changed
    UNCERTAIN = "uncertain"  # Hard to tell


@dataclass
class BatterContext:
    """Context about the current batter."""

    name: str
    runs_scored: int = 0
    balls_faced: int = 0
    fours: int = 0
    sixes: int = 0
    strike_rate: float = 0.0
    is_on_strike: bool = True
    approaching_milestone: str | None = None  # "50", "100", "150", etc.
    balls_to_milestone: int | None = None
    recent_scoring: list[int] = field(default_factory=list)  # Last 6 balls
    dot_ball_pressure: int = 0  # Consecutive dots faced

    @property
    def is_new_batter(self) -> bool:
        """Batter just arrived (< 10 balls)."""
        return self.balls_faced < 10

    @property
    def is_settled(self) -> bool:
        """Batter is settled (20+ balls, decent SR)."""
        return self.balls_faced >= 20 and self.strike_rate >= 50

    @property
    def is_struggling(self) -> bool:
        """Batter struggling (low SR after 15+ balls)."""
        return self.balls_faced >= 15 and self.strike_rate < 60


@dataclass
class BowlerContext:
    """Context about the current bowler."""

    name: str
    overs_bowled: float = 0.0
    maidens: int = 0
    runs_conceded: int = 0
    wickets: int = 0
    economy: float = 0.0
    current_spell_overs: float = 0.0
    current_spell_wickets: int = 0
    current_spell_runs: int = 0
    recent_deliveries: list[str] = field(default_factory=list)  # Last 6: "W", "4", "1", "."
    is_on_hat_trick: bool = False
    consecutive_dots: int = 0

    @property
    def is_bowling_well(self) -> bool:
        """Bowler having a good spell."""
        return self.economy < 6.0 or self.current_spell_wickets >= 2

    @property
    def is_expensive(self) -> bool:
        """Bowler being hit around."""
        return self.economy > 9.0 and self.overs_bowled >= 2


@dataclass
class PartnershipContext:
    """Context about the current batting partnership."""

    runs: int = 0
    balls: int = 0
    batter1_name: str = ""
    batter1_contribution: int = 0
    batter2_name: str = ""
    batter2_contribution: int = 0
    run_rate: float = 0.0
    is_rebuilding: bool = False  # After early wickets
    is_dominant: bool = False  # Partnership taking control

    @property
    def is_significant(self) -> bool:
        """Partnership of note (50+)."""
        return self.runs >= 50

    @property
    def is_century_stand(self) -> bool:
        """Century partnership."""
        return self.runs >= 100


@dataclass
class RecentEvents:
    """Recent events for context."""

    last_6_balls: list[CricketEvent] = field(default_factory=list)
    last_over_summary: str = ""
    wickets_in_last_5_overs: int = 0
    boundaries_in_last_5_overs: int = 0
    runs_in_last_5_overs: int = 0
    last_wicket_description: str | None = None
    balls_since_last_boundary: int = 0
    balls_since_last_wicket: int = 0

    @property
    def is_quiet_period(self) -> bool:
        """No boundaries or wickets recently."""
        return self.balls_since_last_boundary > 18 and self.balls_since_last_wicket > 30

    @property
    def is_action_packed(self) -> bool:
        """Lots happening recently."""
        return self.boundaries_in_last_5_overs >= 4 or self.wickets_in_last_5_overs >= 2


@dataclass
class MatchSituation:
    """Overall match situation."""

    batting_team: str
    bowling_team: str
    innings_number: int
    total_runs: int
    total_wickets: int
    overs_completed: float
    balls_remaining: int | None = None  # For limited overs
    target: int | None = None  # For chases
    runs_required: int | None = None
    required_rate: float | None = None
    current_run_rate: float = 0.0
    phase: MatchPhase = MatchPhase.EARLY_INNINGS
    match_format: str = "Test"  # Test, ODI, T20

    @property
    def score_string(self) -> str:
        """Format: 245/6 (42.3)."""
        return f"{self.total_runs}/{self.total_wickets} ({self.overs_completed})"

    @property
    def is_chase(self) -> bool:
        """Team is chasing a target."""
        return self.target is not None

    @property
    def is_close_chase(self) -> bool:
        """Chase is tight (RRR within 2 of CRR)."""
        if not self.is_chase or self.required_rate is None:
            return False
        return abs(self.required_rate - self.current_run_rate) <= 2.0

    @property
    def wickets_in_hand(self) -> int:
        """Wickets remaining."""
        return 10 - self.total_wickets


@dataclass
class NarrativeState:
    """Narrative/storytelling state."""

    current_storyline: str = ""  # Brief description of what's unfolding
    tension_level: float = 0.5  # 0.0 to 1.0
    momentum: MomentumState = MomentumState.BALANCED
    key_subplot: str | None = None  # "Kohli approaching 100", "Bumrah's spell"
    dramatic_potential: str | None = None  # What could happen next
    callbacks_available: list[str] = field(default_factory=list)  # Earlier moments to reference

    def to_prompt_context(self) -> str:
        """Convert to text for LLM prompt."""
        lines = [f"Storyline: {self.current_storyline}"]
        if self.key_subplot:
            lines.append(f"Subplot: {self.key_subplot}")
        lines.append(f"Momentum: {self.momentum.value}")
        lines.append(
            f"Tension: {'High' if self.tension_level > 0.7 else 'Medium' if self.tension_level > 0.4 else 'Low'}"
        )
        if self.dramatic_potential:
            lines.append(f"Potential: {self.dramatic_potential}")
        return "\n".join(lines)


@dataclass
class RichContext:
    """Complete rich context for commentary generation."""

    # Current event being commented on
    event: CricketEvent

    # Match situation
    match: MatchSituation

    # Player contexts
    batter: BatterContext
    bowler: BowlerContext
    partnership: PartnershipContext

    # Recent history
    recent: RecentEvents

    # Narrative state
    narrative: NarrativeState

    # Pressure assessment
    pressure: PressureLevel = PressureLevel.CALM
    pressure_score: float = 0.0  # 0.0 to 1.0

    # Commentary hints
    suggested_tone: str = "neutral"  # excited, tense, calm, dramatic
    suggested_length: str = "medium"  # short, medium, long
    avoid_phrases: list[str] = field(default_factory=list)  # Don't repeat these

    def to_prompt_context(self) -> str:  # noqa: C901
        """Convert full context to text for LLM prompt."""
        sections = []

        # Match situation
        sections.append("=== MATCH SITUATION ===")
        sections.append(f"{self.match.batting_team} vs {self.match.bowling_team}")
        sections.append(f"Score: {self.match.score_string}")
        if self.match.is_chase:
            sections.append(
                f"Target: {self.match.target}, Need: {self.match.runs_required} from {self.match.balls_remaining} balls"
            )
            sections.append(
                f"Required rate: {self.match.required_rate:.2f}, Current rate: {self.match.current_run_rate:.2f}"
            )
        sections.append(f"Phase: {self.match.phase.value}")

        # Current ball
        sections.append("\n=== THIS DELIVERY ===")
        sections.append(f"{self.bowler.name} to {self.batter.name}")
        sections.append(f"Result: {self._describe_event()}")

        # Batter context
        sections.append("\n=== BATTER ===")
        sections.append(
            f"{self.batter.name}: {self.batter.runs_scored} ({self.batter.balls_faced}), SR: {self.batter.strike_rate:.1f}"
        )
        if self.batter.approaching_milestone:
            sections.append(f"Approaching: {self.batter.approaching_milestone}")
        if self.batter.is_new_batter:
            sections.append("Status: New at crease")
        elif self.batter.is_struggling:
            sections.append("Status: Struggling")
        elif self.batter.is_settled:
            sections.append("Status: Well set")

        # Bowler context
        sections.append("\n=== BOWLER ===")
        sections.append(
            f"{self.bowler.name}: {self.bowler.overs_bowled}-{self.bowler.maidens}-{self.bowler.runs_conceded}-{self.bowler.wickets}"
        )
        if self.bowler.is_on_hat_trick:
            sections.append("ON A HAT-TRICK!")
        if self.bowler.is_bowling_well:
            sections.append("Status: Bowling well")
        elif self.bowler.is_expensive:
            sections.append("Status: Under pressure")

        # Partnership
        if self.partnership.runs > 0:
            sections.append("\n=== PARTNERSHIP ===")
            sections.append(f"{self.partnership.runs} runs, {self.partnership.balls} balls")

        # Narrative
        sections.append("\n=== NARRATIVE ===")
        sections.append(self.narrative.to_prompt_context())

        # Pressure
        sections.append(f"\n=== PRESSURE: {self.pressure.value.upper()} ===")

        # Tone guidance
        sections.append("\n=== COMMENTARY GUIDANCE ===")
        sections.append(f"Tone: {self.suggested_tone}")
        sections.append(f"Length: {self.suggested_length}")
        if self.avoid_phrases:
            sections.append(f"Avoid: {', '.join(self.avoid_phrases[:3])}")

        return "\n".join(sections)

    def _describe_event(self) -> str:
        """Brief description of the current event."""
        event = self.event
        if event.is_wicket:
            return f"WICKET! {event.wicket_type}"
        if event.runs_batter == 6:
            return "SIX!"
        if event.runs_batter == 4:
            return "FOUR!"
        if event.runs_total == 0:
            return "Dot ball"
        return f"{event.runs_total} run(s)"
