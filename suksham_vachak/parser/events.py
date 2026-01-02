"""Cricket event dataclasses for the Suksham Vachak commentary engine."""

from dataclasses import dataclass, field
from enum import Enum


class EventType(Enum):
    """Types of cricket events that can occur on a delivery."""

    DOT_BALL = "dot_ball"
    SINGLE = "single"
    DOUBLE = "double"
    TRIPLE = "triple"
    BOUNDARY_FOUR = "boundary_four"
    BOUNDARY_SIX = "boundary_six"
    WICKET = "wicket"
    WIDE = "wide"
    NO_BALL = "no_ball"
    BYE = "bye"
    LEG_BYE = "leg_bye"


class MatchFormat(Enum):
    """Cricket match formats."""

    TEST = "Test"
    ODI = "ODI"
    T20 = "T20"
    T20I = "T20I"


@dataclass
class MatchContext:
    """Context about the current match state."""

    match_id: str
    teams: tuple[str, str]
    venue: str
    date: str
    format: MatchFormat
    innings: int
    current_score: int
    current_wickets: int
    overs_completed: float
    target: int | None = None
    required_rate: float | None = None
    current_rate: float = 0.0

    @property
    def balls_bowled(self) -> int:
        """Total balls bowled in the current innings."""
        overs = int(self.overs_completed)
        balls = round((self.overs_completed - overs) * 10)
        return overs * 6 + balls

    @property
    def is_chasing(self) -> bool:
        """Whether the batting team is chasing a target."""
        return self.target is not None

    def runs_required(self) -> int | None:
        """Runs needed to win, if chasing."""
        if self.target is None:
            return None
        return self.target - self.current_score


@dataclass
class CricketEvent:
    """A single cricket event (delivery/ball)."""

    event_id: str
    event_type: EventType
    ball_number: str  # Format: "15.3" = over 15, ball 3
    batter: str
    bowler: str
    non_striker: str
    runs_batter: int
    runs_extras: int
    runs_total: int
    is_boundary: bool
    is_wicket: bool
    match_context: MatchContext
    wicket_type: str | None = None
    wicket_player: str | None = None
    fielder: str | None = None
    extras_type: str | None = None  # "wide", "noball", "bye", "legbye"

    # Future: from vision pipeline
    shot_type: str | None = None
    ball_speed: float | None = None
    ball_trajectory: str | None = None

    @property
    def is_dot_ball(self) -> bool:
        """Whether this was a dot ball (no runs scored)."""
        return self.runs_total == 0 and not self.is_wicket

    @property
    def over_number(self) -> int:
        """The over number (0-indexed)."""
        return int(self.ball_number.split(".")[0])

    @property
    def ball_in_over(self) -> int:
        """The ball number within the over (1-6)."""
        return int(self.ball_number.split(".")[1])

    @property
    def description(self) -> str:
        """Human-readable description of the event."""
        if self.is_wicket:
            return f"WICKET! {self.wicket_player} {self.wicket_type}"
        if self.event_type == EventType.BOUNDARY_SIX:
            return f"SIX! {self.batter} hits {self.bowler} for 6"
        if self.event_type == EventType.BOUNDARY_FOUR:
            return f"FOUR! {self.batter} hits {self.bowler} for 4"
        if self.extras_type:
            return f"{self.extras_type.upper()}: {self.runs_extras} runs"
        if self.runs_batter > 0:
            return f"{self.batter} takes {self.runs_batter}"
        return f"Dot ball to {self.batter}"


@dataclass
class MatchInfo:
    """Metadata about a cricket match from Cricsheet."""

    match_id: str
    teams: tuple[str, str]
    venue: str
    city: str | None
    dates: list[str]
    format: MatchFormat
    gender: str
    toss_winner: str
    toss_decision: str
    outcome_winner: str | None = None
    outcome_by_runs: int | None = None
    outcome_by_wickets: int | None = None
    player_of_match: list[str] | None = None
    players: dict[str, list[str]] = field(default_factory=lambda: {})
