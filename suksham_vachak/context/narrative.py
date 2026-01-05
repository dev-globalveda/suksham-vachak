"""Narrative tracking for cricket match storytelling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .models import MomentumState, NarrativeState

if TYPE_CHECKING:
    from suksham_vachak.parser import CricketEvent


@dataclass
class StorylineEvent:
    """A notable event for narrative callbacks."""

    ball_number: str
    description: str
    event_type: str  # "wicket", "milestone", "boundary_spree", "collapse", etc.
    player: str
    significance: float  # 0.0-1.0


class NarrativeTracker:
    """Track match narrative and storylines.

    Responsibilities:
    - Identify the current storyline
    - Track momentum shifts
    - Detect subplots (player milestones, spells, partnerships)
    - Provide callbacks to earlier moments
    - Assess dramatic potential
    """

    def __init__(self) -> None:
        """Initialize narrative tracker."""
        self.storyline_events: list[StorylineEvent] = []
        self.current_momentum = MomentumState.BALANCED
        self.momentum_shift_ball: str | None = None
        self.active_subplots: list[str] = []

        # Tracking state
        self._consecutive_boundaries = 0
        self._consecutive_dots = 0
        self._wickets_in_spell = 0
        self._runs_since_wicket = 0
        self._current_spell_bowler: str | None = None

    def update(
        self,
        event: CricketEvent,
        batter_runs: int,
        batter_balls: int,
        bowler_wickets: int,
        partnership_runs: int,
    ) -> NarrativeState:
        """Update narrative state based on new event.

        Args:
            event: The current cricket event
            batter_runs: Batter's total runs
            batter_balls: Batter's balls faced
            bowler_wickets: Bowler's wickets in match
            partnership_runs: Current partnership runs

        Returns:
            Updated NarrativeState
        """
        # Update tracking metrics
        self._update_tracking(event)

        # Detect momentum
        new_momentum = self._detect_momentum(event)
        if new_momentum != self.current_momentum:
            self.momentum_shift_ball = event.ball_number
            self.current_momentum = new_momentum

        # Identify subplots
        subplots = self._identify_subplots(event, batter_runs, batter_balls, bowler_wickets, partnership_runs)
        self.active_subplots = subplots

        # Build storyline
        storyline = self._build_storyline(event)

        # Assess dramatic potential
        dramatic_potential = self._assess_dramatic_potential(event, batter_runs, partnership_runs)

        # Get callbacks
        callbacks = self._get_relevant_callbacks(event)

        # Calculate tension
        tension = self._calculate_tension(event)

        return NarrativeState(
            current_storyline=storyline,
            tension_level=tension,
            momentum=self.current_momentum,
            key_subplot=subplots[0] if subplots else None,
            dramatic_potential=dramatic_potential,
            callbacks_available=callbacks,
        )

    def _update_tracking(self, event: CricketEvent) -> None:
        """Update internal tracking metrics."""
        # Boundary tracking
        if event.is_boundary:
            self._consecutive_boundaries += 1
            self._consecutive_dots = 0
        elif event.runs_total == 0 and not event.is_wicket:
            self._consecutive_dots += 1
            self._consecutive_boundaries = 0
        else:
            self._consecutive_boundaries = 0
            self._consecutive_dots = 0

        # Wicket tracking
        if event.is_wicket:
            self._runs_since_wicket = 0
            self._wickets_in_spell += 1

            # Record significant event
            self.storyline_events.append(
                StorylineEvent(
                    ball_number=event.ball_number,
                    description=f"{event.batter} dismissed by {event.bowler}",
                    event_type="wicket",
                    player=event.bowler,
                    significance=0.7,
                )
            )
        else:
            self._runs_since_wicket += event.runs_total

        # Bowler spell tracking
        if event.bowler != self._current_spell_bowler:
            self._current_spell_bowler = event.bowler
            self._wickets_in_spell = 0

    def _detect_momentum(self, event: CricketEvent) -> MomentumState:
        """Detect current match momentum."""
        # Boundary spree = batting dominant
        if self._consecutive_boundaries >= 3:
            return MomentumState.BATTING_DOMINANT

        # Dot ball pressure = bowling dominant
        if self._consecutive_dots >= 6:
            return MomentumState.BOWLING_DOMINANT

        # Multiple wickets in spell
        if self._wickets_in_spell >= 2:
            return MomentumState.BOWLING_DOMINANT

        # Big runs since wicket = batting recovering/dominant
        if self._runs_since_wicket >= 50:
            return MomentumState.BATTING_DOMINANT

        # Recent wicket = potential shift
        if event.is_wicket:
            return MomentumState.MOMENTUM_SHIFT

        return MomentumState.BALANCED

    def _identify_subplots(
        self,
        event: CricketEvent,
        batter_runs: int,
        batter_balls: int,
        bowler_wickets: int,
        partnership_runs: int,
    ) -> list[str]:
        """Identify active subplots in the match."""
        subplots = []

        # Batter approaching milestone
        for milestone in [50, 100, 150, 200]:
            if milestone - 10 <= batter_runs < milestone:
                balls_to_go = milestone - batter_runs
                subplots.append(f"{event.batter} {balls_to_go} away from {milestone}")
                break

        # Bowler on fire
        if bowler_wickets >= 3:
            subplots.append(f"{event.bowler}'s devastating spell ({bowler_wickets} wickets)")
        elif self._wickets_in_spell >= 2:
            subplots.append(f"{event.bowler} on a roll in this spell")

        # Partnership building
        if partnership_runs >= 50:
            subplots.append(f"Partnership building: {partnership_runs} runs")

        # New batter settling
        if batter_balls < 10:
            subplots.append(f"{event.batter} looking to settle in")

        # Batter in form
        if batter_balls >= 20 and batter_runs / batter_balls > 1.5:
            subplots.append(f"{event.batter} in imperious form")

        return subplots

    def _build_storyline(self, event: CricketEvent) -> str:
        """Build the current storyline description."""
        if event.is_wicket:
            if self._wickets_in_spell >= 2:
                return f"{event.bowler} is wreaking havoc, another one falls!"
            return f"Breakthrough! {event.batter} departs"

        if self._consecutive_boundaries >= 3:
            return f"Boundaries flowing! {event.batter} taking control"

        if self._consecutive_dots >= 6:
            return f"Pressure building, {self._consecutive_dots} dots in a row"

        if self.current_momentum == MomentumState.BATTING_DOMINANT:
            return "Batters on top, scoring freely"

        if self.current_momentum == MomentumState.BOWLING_DOMINANT:
            return "Bowlers creating chances, batters under pressure"

        return "Contest evenly poised"

    def _assess_dramatic_potential(
        self,
        event: CricketEvent,
        batter_runs: int,
        partnership_runs: int,
    ) -> str | None:
        """Assess what could happen next."""
        potentials = []

        # Milestone watch
        for milestone in [50, 100]:
            if milestone - 5 <= batter_runs < milestone:
                potentials.append(f"{event.batter} could reach {milestone} soon")

        # Partnership milestone
        if 45 <= partnership_runs < 50:
            potentials.append("50 partnership within reach")
        elif 95 <= partnership_runs < 100:
            potentials.append("Century partnership beckons")

        # Bowler on hat-trick potential
        if self._wickets_in_spell >= 2 and event.is_wicket:
            potentials.append(f"Could {event.bowler} get another?")

        # Pressure could tell
        if self._consecutive_dots >= 6:
            potentials.append("Something has to give")

        return potentials[0] if potentials else None

    def _get_relevant_callbacks(self, event: CricketEvent) -> list[str]:
        """Get callbacks to earlier moments."""
        callbacks = []

        # Find relevant earlier events
        for story_event in self.storyline_events[-10:]:  # Last 10 significant events
            # Same player involved
            if story_event.player in [event.batter, event.bowler]:
                callbacks.append(f"Earlier: {story_event.description} ({story_event.ball_number})")

        return callbacks[:3]  # Limit to 3 callbacks

    def _calculate_tension(self, event: CricketEvent) -> float:
        """Calculate narrative tension level 0.0-1.0."""
        tension = 0.3  # Base tension

        # Recent wickets increase tension
        if event.is_wicket:
            tension += 0.3

        # Dot ball pressure
        if self._consecutive_dots >= 6:
            tension += 0.2

        # Close to milestone
        # (Would need batter runs passed in for this)

        # Momentum shift
        if self.current_momentum == MomentumState.MOMENTUM_SHIFT:
            tension += 0.2

        return min(1.0, tension)

    def record_milestone(self, ball_number: str, player: str, milestone: str) -> None:
        """Record a milestone achievement."""
        self.storyline_events.append(
            StorylineEvent(
                ball_number=ball_number,
                description=f"{player} reaches {milestone}!",
                event_type="milestone",
                player=player,
                significance=0.9,
            )
        )

    def record_spell_end(self, bowler: str, overs: float, wickets: int, runs: int) -> None:
        """Record end of a bowling spell."""
        if wickets >= 2 or (overs >= 4 and runs / overs < 5):
            self.storyline_events.append(
                StorylineEvent(
                    ball_number="",
                    description=f"{bowler}'s spell: {overs}-{wickets}-{runs}",
                    event_type="spell",
                    player=bowler,
                    significance=0.6 if wickets < 3 else 0.8,
                )
            )
