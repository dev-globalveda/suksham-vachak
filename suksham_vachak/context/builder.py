"""Context builder that assembles rich match context."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .models import (
    BatterContext,
    BowlerContext,
    MatchPhase,
    MatchSituation,
    PartnershipContext,
    RecentEvents,
    RichContext,
)
from .narrative import NarrativeTracker
from .pressure import PressureCalculator

if TYPE_CHECKING:
    from suksham_vachak.parser import CricketEvent, MatchInfo
    from suksham_vachak.rag import DejaVuRetriever
    from suksham_vachak.stats import MatchupEngine


class ContextBuilder:
    """Build rich context for commentary generation.

    This class aggregates data from parsed events and maintains
    state to provide comprehensive context for each delivery.

    Optionally integrates with RAG retriever for historical parallels
    and Stats engine for player matchup data.
    """

    def __init__(
        self,
        match_info: MatchInfo,
        rag_retriever: DejaVuRetriever | None = None,
        stats_engine: MatchupEngine | None = None,
    ) -> None:
        """Initialize context builder.

        Args:
            match_info: Match metadata from parser
            rag_retriever: Optional RAG retriever for historical parallels
            stats_engine: Optional stats engine for player matchup data
        """
        self.match_info = match_info
        self.pressure_calc = PressureCalculator()
        self.narrative_tracker = NarrativeTracker()
        self.rag_retriever = rag_retriever
        self.stats_engine = stats_engine

        # Match state tracking
        self._innings_number = 1
        self._total_runs = 0
        self._total_wickets = 0
        self._overs_completed = 0.0
        self._target: int | None = None

        # Batter tracking: name -> {runs, balls, fours, sixes}
        self._batter_stats: dict[str, dict] = {}
        self._current_striker: str | None = None
        self._current_non_striker: str | None = None

        # Bowler tracking: name -> {overs, maidens, runs, wickets, balls_this_over}
        self._bowler_stats: dict[str, dict] = {}
        self._current_bowler: str | None = None

        # Partnership tracking
        self._partnership_runs = 0
        self._partnership_balls = 0
        self._partnership_batter1: str | None = None
        self._partnership_batter2: str | None = None

        # Recent events for context
        self._recent_events: list[CricketEvent] = []
        self._balls_since_boundary = 0
        self._balls_since_wicket = 0
        self._wickets_last_5_overs = 0
        self._boundaries_last_5_overs = 0
        self._runs_last_5_overs = 0

        # Over tracking for phase detection
        self._balls_in_innings = 0

        # Phrases to avoid (recently used)
        self._recent_phrases: list[str] = []

    def build(self, event: CricketEvent) -> RichContext:
        """Build rich context for an event.

        Args:
            event: The cricket event to build context for

        Returns:
            RichContext with all relevant information
        """
        # Update internal state
        self._update_state(event)

        # Build component contexts
        match_situation = self._build_match_situation(event)
        batter_context = self._build_batter_context(event)
        bowler_context = self._build_bowler_context(event)
        partnership_context = self._build_partnership_context()
        recent_events = self._build_recent_events(event)

        # Calculate pressure
        pressure_level, pressure_score = self.pressure_calc.calculate(
            match=match_situation,
            wickets_in_last_5_overs=self._wickets_last_5_overs,
            is_new_batter=batter_context.is_new_batter,
            balls_since_boundary=self._balls_since_boundary,
        )

        # Update narrative
        batter_stats = self._batter_stats.get(event.batter, {})
        narrative_state = self.narrative_tracker.update(
            event=event,
            batter_runs=batter_stats.get("runs", 0),
            batter_balls=batter_stats.get("balls", 0),
            bowler_wickets=self._bowler_stats.get(event.bowler, {}).get("wickets", 0),
            partnership_runs=self._partnership_runs,
        )

        # Enhance with player matchup statistics (Stats Engine)
        if self.stats_engine is not None:
            try:
                matchup = self.stats_engine.get_head_to_head(event.batter, event.bowler)
                if matchup and matchup.balls_faced >= 10:
                    narrative_state.matchup_context = matchup.to_short_context()
            except Exception:  # noqa: S110
                # Stats failures shouldn't break commentary generation
                pass

        # Enhance with RAG historical parallels (Déjà Vu Engine)
        if self.rag_retriever is not None:
            try:
                historical_callbacks = self.rag_retriever.retrieve(
                    event=event,
                    match=match_situation,
                    pressure=pressure_level,
                )
                # Prepend historical callbacks (higher priority)
                narrative_state.callbacks_available = (historical_callbacks + narrative_state.callbacks_available)[
                    :5
                ]  # Limit total callbacks
            except Exception:  # noqa: S110
                # RAG failures shouldn't break commentary generation
                pass

        # Determine suggested tone and length
        suggested_tone = self._determine_tone(event, pressure_level)
        suggested_length = self._determine_length(event)

        return RichContext(
            event=event,
            match=match_situation,
            batter=batter_context,
            bowler=bowler_context,
            partnership=partnership_context,
            recent=recent_events,
            narrative=narrative_state,
            pressure=pressure_level,
            pressure_score=pressure_score,
            suggested_tone=suggested_tone,
            suggested_length=suggested_length,
            avoid_phrases=self._recent_phrases[-5:],
        )

    def _update_state(self, event: CricketEvent) -> None:
        """Update internal state from event."""
        # Update match totals
        self._total_runs += event.runs_total
        self._balls_in_innings += 1

        # Calculate overs
        balls = self._balls_in_innings
        self._overs_completed = (balls // 6) + (balls % 6) / 10

        # Update boundary/wicket tracking
        if event.is_boundary:
            self._balls_since_boundary = 0
            self._boundaries_last_5_overs += 1
        else:
            self._balls_since_boundary += 1

        if event.is_wicket:
            self._total_wickets += 1
            self._balls_since_wicket = 0
            self._wickets_last_5_overs += 1
            self._reset_partnership(event)
        else:
            self._balls_since_wicket += 1

        # Update batter stats
        self._update_batter_stats(event)

        # Update bowler stats
        self._update_bowler_stats(event)

        # Update partnership
        self._partnership_runs += event.runs_batter
        self._partnership_balls += 1

        # Track recent events
        self._recent_events.append(event)
        if len(self._recent_events) > 30:  # Keep ~5 overs
            self._recent_events.pop(0)

        # Update 5-over window stats
        self._runs_last_5_overs += event.runs_total
        if len(self._recent_events) > 30:
            # Remove contribution of oldest event
            oldest = self._recent_events[0]
            self._runs_last_5_overs -= oldest.runs_total
            if oldest.is_wicket:
                self._wickets_last_5_overs = max(0, self._wickets_last_5_overs - 1)
            if oldest.is_boundary:
                self._boundaries_last_5_overs = max(0, self._boundaries_last_5_overs - 1)

    def _update_batter_stats(self, event: CricketEvent) -> None:
        """Update batter statistics."""
        batter = event.batter
        if batter not in self._batter_stats:
            self._batter_stats[batter] = {
                "runs": 0,
                "balls": 0,
                "fours": 0,
                "sixes": 0,
                "recent": [],
            }

        stats = self._batter_stats[batter]
        stats["runs"] += event.runs_batter
        stats["balls"] += 1
        stats["recent"].append(event.runs_batter)
        if len(stats["recent"]) > 6:
            stats["recent"].pop(0)

        if event.runs_batter == 4:
            stats["fours"] += 1
        elif event.runs_batter == 6:
            stats["sixes"] += 1

        self._current_striker = batter

    def _update_bowler_stats(self, event: CricketEvent) -> None:
        """Update bowler statistics."""
        bowler = event.bowler
        if bowler not in self._bowler_stats:
            self._bowler_stats[bowler] = {
                "overs": 0.0,
                "maidens": 0,
                "runs": 0,
                "wickets": 0,
                "balls_this_over": 0,
                "runs_this_over": 0,
                "spell_overs": 0.0,
                "spell_wickets": 0,
                "spell_runs": 0,
                "recent": [],
            }

        stats = self._bowler_stats[bowler]
        stats["runs"] += event.runs_total
        stats["balls_this_over"] += 1
        stats["runs_this_over"] += event.runs_total
        stats["spell_runs"] += event.runs_total

        if event.is_wicket:
            stats["wickets"] += 1
            stats["spell_wickets"] += 1
            stats["recent"].append("W")
        elif event.runs_batter == 4:
            stats["recent"].append("4")
        elif event.runs_batter == 6:
            stats["recent"].append("6")
        elif event.runs_total == 0:
            stats["recent"].append(".")
        else:
            stats["recent"].append(str(event.runs_total))

        if len(stats["recent"]) > 6:
            stats["recent"].pop(0)

        # End of over
        if stats["balls_this_over"] == 6:
            stats["overs"] += 1
            stats["spell_overs"] += 1
            if stats["runs_this_over"] == 0:
                stats["maidens"] += 1
            stats["balls_this_over"] = 0
            stats["runs_this_over"] = 0

        self._current_bowler = bowler

    def _reset_partnership(self, event: CricketEvent) -> None:
        """Reset partnership after wicket."""
        self._partnership_runs = 0
        self._partnership_balls = 0
        # The dismissed batter is out, non-striker continues
        self._partnership_batter1 = event.non_striker if hasattr(event, "non_striker") else None
        self._partnership_batter2 = None  # New batter coming in

    def _build_match_situation(self, event: CricketEvent) -> MatchSituation:
        """Build match situation context."""
        # Determine teams from match context
        # The parser's MatchContext has teams as tuple - first team bats first in innings 1
        if event.match_context:
            teams = event.match_context.teams
            innings = event.match_context.innings
            # In first innings, first team bats; in second innings, second team bats
            batting_team = teams[0] if innings == 1 else teams[1]
            bowling_team = teams[1] if innings == 1 else teams[0]
        else:
            batting_team = ""
            bowling_team = ""

        # Calculate rates
        current_rr = self._total_runs / self._overs_completed if self._overs_completed > 0 else 0.0

        # Calculate required rate if chasing
        runs_required = None
        required_rate = None
        balls_remaining = None

        if self._target is not None:
            runs_required = self._target - self._total_runs
            total_overs = self._get_total_overs()
            if total_overs:
                balls_remaining = int((total_overs * 6) - self._balls_in_innings)
                if balls_remaining > 0:
                    overs_remaining = balls_remaining / 6
                    required_rate = runs_required / overs_remaining if overs_remaining > 0 else 999.0

        # Detect phase
        phase = self._detect_phase()

        return MatchSituation(
            batting_team=batting_team,
            bowling_team=bowling_team,
            innings_number=self._innings_number,
            total_runs=self._total_runs,
            total_wickets=self._total_wickets,
            overs_completed=self._overs_completed,
            balls_remaining=balls_remaining,
            target=self._target,
            runs_required=runs_required,
            required_rate=required_rate,
            current_run_rate=current_rr,
            phase=phase,
            match_format=self.match_info.format.value,
        )

    def _build_batter_context(self, event: CricketEvent) -> BatterContext:
        """Build batter context."""
        stats = self._batter_stats.get(event.batter, {"runs": 0, "balls": 0, "fours": 0, "sixes": 0, "recent": []})

        runs = stats["runs"]
        balls = stats["balls"]
        strike_rate = (runs / balls * 100) if balls > 0 else 0.0

        # Check milestone approach
        milestone = None
        balls_to_milestone = None
        for m in [50, 100, 150, 200]:
            if runs < m <= runs + 15:
                milestone = str(m)
                balls_to_milestone = m - runs
                break

        # Count consecutive dots
        dot_pressure = 0
        for r in reversed(stats.get("recent", [])):
            if r == 0:
                dot_pressure += 1
            else:
                break

        return BatterContext(
            name=event.batter,
            runs_scored=runs,
            balls_faced=balls,
            fours=stats["fours"],
            sixes=stats["sixes"],
            strike_rate=strike_rate,
            is_on_strike=True,
            approaching_milestone=milestone,
            balls_to_milestone=balls_to_milestone,
            recent_scoring=stats.get("recent", [])[-6:],
            dot_ball_pressure=dot_pressure,
        )

    def _build_bowler_context(self, event: CricketEvent) -> BowlerContext:
        """Build bowler context."""
        stats = self._bowler_stats.get(
            event.bowler,
            {
                "overs": 0,
                "maidens": 0,
                "runs": 0,
                "wickets": 0,
                "spell_overs": 0,
                "spell_wickets": 0,
                "spell_runs": 0,
                "balls_this_over": 0,
                "recent": [],
            },
        )

        overs = stats["overs"] + stats["balls_this_over"] / 10
        economy = stats["runs"] / stats["overs"] if stats["overs"] > 0 else 0.0

        # Check for hat-trick
        recent = stats.get("recent", [])
        is_hat_trick = len(recent) >= 2 and recent[-1] == "W" and recent[-2] == "W"

        # Consecutive dots
        consecutive_dots = 0
        for r in reversed(recent):
            if r == ".":
                consecutive_dots += 1
            else:
                break

        return BowlerContext(
            name=event.bowler,
            overs_bowled=overs,
            maidens=stats["maidens"],
            runs_conceded=stats["runs"],
            wickets=stats["wickets"],
            economy=economy,
            current_spell_overs=stats["spell_overs"] + stats["balls_this_over"] / 10,
            current_spell_wickets=stats["spell_wickets"],
            current_spell_runs=stats["spell_runs"],
            recent_deliveries=recent[-6:],
            is_on_hat_trick=is_hat_trick,
            consecutive_dots=consecutive_dots,
        )

    def _build_partnership_context(self) -> PartnershipContext:
        """Build partnership context."""
        run_rate = 0.0
        if self._partnership_balls > 0:
            overs = self._partnership_balls / 6
            run_rate = self._partnership_runs / overs if overs > 0 else 0.0

        # Determine if rebuilding (after collapse)
        is_rebuilding = self._wickets_last_5_overs >= 2 and self._partnership_runs < 30

        # Determine if dominant
        is_dominant = self._partnership_runs >= 50 and run_rate >= 6.0

        return PartnershipContext(
            runs=self._partnership_runs,
            balls=self._partnership_balls,
            batter1_name=self._partnership_batter1 or "",
            batter1_contribution=0,  # Would need per-batter partnership tracking
            batter2_name=self._partnership_batter2 or "",
            batter2_contribution=0,
            run_rate=run_rate,
            is_rebuilding=is_rebuilding,
            is_dominant=is_dominant,
        )

    def _build_recent_events(self, event: CricketEvent) -> RecentEvents:
        """Build recent events context."""
        last_wicket = None
        for e in reversed(self._recent_events):
            if e.is_wicket:
                last_wicket = f"{e.batter} {e.wicket_type} by {e.bowler}"
                break

        # Build last over summary
        last_over_events = self._recent_events[-6:] if len(self._recent_events) >= 6 else self._recent_events
        last_over_summary = " ".join(
            "W" if e.is_wicket else str(e.runs_total) if e.runs_total > 0 else "." for e in last_over_events
        )

        return RecentEvents(
            last_6_balls=self._recent_events[-6:],
            last_over_summary=last_over_summary,
            wickets_in_last_5_overs=self._wickets_last_5_overs,
            boundaries_in_last_5_overs=self._boundaries_last_5_overs,
            runs_in_last_5_overs=self._runs_last_5_overs,
            last_wicket_description=last_wicket,
            balls_since_last_boundary=self._balls_since_boundary,
            balls_since_last_wicket=self._balls_since_wicket,
        )

    def _detect_phase(self) -> MatchPhase:
        """Detect current match phase based on format and overs."""
        format_type = self.match_info.format.value.lower()
        overs = self._overs_completed

        if format_type == "t20":
            if overs <= 6:
                return MatchPhase.POWERPLAY
            elif overs <= 15:
                return MatchPhase.MIDDLE_OVERS
            else:
                return MatchPhase.DEATH_OVERS

        elif format_type == "odi":
            if overs <= 10:
                return MatchPhase.POWERPLAY
            elif overs <= 40:
                return MatchPhase.MIDDLE_OVERS
            else:
                return MatchPhase.DEATH_OVERS

        else:  # Test or generic
            if self._balls_in_innings < 180:  # ~30 overs
                return MatchPhase.EARLY_INNINGS
            elif self._balls_in_innings < 360:  # ~60 overs
                return MatchPhase.MIDDLE_INNINGS
            else:
                return MatchPhase.LATE_INNINGS

    def _get_total_overs(self) -> int | None:
        """Get total overs for the format."""
        format_type = self.match_info.format.value.lower()
        if format_type == "t20":
            return 20
        elif format_type == "odi":
            return 50
        return None  # Tests don't have fixed overs

    def _determine_tone(self, event: CricketEvent, pressure_level) -> str:
        """Determine suggested commentary tone."""
        from .models import PressureLevel

        if event.is_wicket:
            return "dramatic"
        if event.runs_batter == 6:
            return "excited"
        if event.runs_batter == 4:
            return "enthusiastic"
        if pressure_level in [PressureLevel.CRITICAL, PressureLevel.INTENSE]:
            return "tense"
        if pressure_level == PressureLevel.CALM:
            return "calm"
        return "neutral"

    def _determine_length(self, event: CricketEvent) -> str:
        """Determine suggested commentary length."""
        if event.is_wicket:
            return "long"
        if event.is_boundary:
            return "medium"
        if event.runs_total == 0:
            return "short"
        return "medium"

    def set_target(self, target: int) -> None:
        """Set chase target for second innings."""
        self._target = target

    def new_innings(self, innings_number: int) -> None:
        """Reset for new innings."""
        self._innings_number = innings_number
        self._total_runs = 0
        self._total_wickets = 0
        self._overs_completed = 0.0
        self._balls_in_innings = 0
        self._batter_stats.clear()
        self._bowler_stats.clear()
        self._partnership_runs = 0
        self._partnership_balls = 0
        self._recent_events.clear()
        self._balls_since_boundary = 0
        self._balls_since_wicket = 0
        self._wickets_last_5_overs = 0
        self._boundaries_last_5_overs = 0
        self._runs_last_5_overs = 0

    def add_phrase_to_avoid(self, phrase: str) -> None:
        """Add a phrase to avoid in future commentary."""
        self._recent_phrases.append(phrase)
        if len(self._recent_phrases) > 20:
            self._recent_phrases.pop(0)
