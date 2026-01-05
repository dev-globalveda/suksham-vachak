"""Pressure calculation for cricket match situations."""

from __future__ import annotations

from typing import ClassVar

from .models import MatchPhase, MatchSituation, PressureLevel


class PressureCalculator:
    """Calculate pressure levels based on match situation.

    Factors considered:
    - Match phase (death overs = higher base pressure)
    - Required run rate vs current run rate
    - Wickets in hand
    - Recent wickets fallen
    - Batter situation (new vs settled)
    - Target proximity
    """

    # Base pressure by match phase
    PHASE_BASE_PRESSURE: ClassVar[dict[MatchPhase, float]] = {
        MatchPhase.POWERPLAY: 0.3,
        MatchPhase.MIDDLE_OVERS: 0.2,
        MatchPhase.DEATH_OVERS: 0.5,
        MatchPhase.FIRST_SESSION: 0.3,
        MatchPhase.SECOND_SESSION: 0.25,
        MatchPhase.THIRD_SESSION: 0.4,
        MatchPhase.EARLY_INNINGS: 0.2,
        MatchPhase.MIDDLE_INNINGS: 0.3,
        MatchPhase.LATE_INNINGS: 0.5,
    }

    # Pressure thresholds for level mapping
    LEVEL_THRESHOLDS: ClassVar[list[tuple[float, PressureLevel]]] = [
        (0.8, PressureLevel.CRITICAL),
        (0.6, PressureLevel.INTENSE),
        (0.4, PressureLevel.TENSE),
        (0.2, PressureLevel.BUILDING),
        (0.0, PressureLevel.CALM),
    ]

    def calculate(
        self,
        match: MatchSituation,
        wickets_in_last_5_overs: int = 0,
        is_new_batter: bool = False,
        balls_since_boundary: int = 0,
    ) -> tuple[PressureLevel, float]:
        """Calculate pressure level and score.

        Args:
            match: Current match situation
            wickets_in_last_5_overs: Recent wickets fallen
            is_new_batter: Whether current batter is new
            balls_since_boundary: Balls since last boundary

        Returns:
            Tuple of (PressureLevel, pressure_score 0.0-1.0)
        """
        pressure_score = 0.0

        # Base pressure from match phase
        pressure_score += self.PHASE_BASE_PRESSURE.get(match.phase, 0.3)

        # Chase pressure
        if match.is_chase and match.required_rate is not None:
            pressure_score += self._calculate_chase_pressure(match)

        # Wickets pressure
        pressure_score += self._calculate_wickets_pressure(match.total_wickets, wickets_in_last_5_overs)

        # Dot ball pressure (building tension)
        if balls_since_boundary > 12:
            pressure_score += min(0.15, (balls_since_boundary - 12) * 0.01)

        # New batter vulnerability
        if is_new_batter:
            pressure_score += 0.1

        # Clamp to 0-1 range
        pressure_score = max(0.0, min(1.0, pressure_score))

        # Map to level
        level = self._score_to_level(pressure_score)

        return level, pressure_score

    def _calculate_chase_pressure(self, match: MatchSituation) -> float:
        """Calculate pressure from chase situation."""
        if not match.is_chase or match.required_rate is None:
            return 0.0

        pressure = 0.0

        # Required rate above current rate
        if match.current_run_rate > 0:
            rate_diff = match.required_rate - match.current_run_rate
            if rate_diff > 0:
                # Higher required rate = more pressure
                pressure += min(0.3, rate_diff * 0.05)
            elif rate_diff < -2:
                # Well ahead of rate = less pressure
                pressure -= 0.1

        # Balls remaining pressure
        if match.balls_remaining is not None and match.runs_required is not None:
            if match.balls_remaining <= 30:  # Last 5 overs
                # Pressure increases as balls decrease
                pressure += (30 - match.balls_remaining) * 0.01

            # Very close finish
            if match.runs_required <= 20 and match.balls_remaining <= 12:
                pressure += 0.2

        # Wickets in hand vs runs needed
        if match.runs_required is not None:
            runs_per_wicket_needed = match.runs_required / max(1, match.wickets_in_hand)
            if runs_per_wicket_needed > 30:
                pressure += 0.15

        return pressure

    def _calculate_wickets_pressure(self, total_wickets: int, recent_wickets: int) -> float:
        """Calculate pressure from wicket situation."""
        pressure = 0.0

        # Overall wickets lost
        if total_wickets >= 7:
            pressure += 0.25
        elif total_wickets >= 5:
            pressure += 0.15
        elif total_wickets >= 3:
            pressure += 0.1

        # Recent wicket cluster (collapse)
        if recent_wickets >= 3:
            pressure += 0.2
        elif recent_wickets >= 2:
            pressure += 0.1

        return pressure

    def _score_to_level(self, score: float) -> PressureLevel:
        """Convert pressure score to discrete level."""
        for threshold, level in self.LEVEL_THRESHOLDS:
            if score >= threshold:
                return level
        return PressureLevel.CALM

    def get_pressure_description(self, level: PressureLevel, score: float) -> str:
        """Get human-readable pressure description."""
        descriptions = {
            PressureLevel.CALM: "Comfortable situation, batters can play freely",
            PressureLevel.BUILDING: "Pressure starting to mount, need to rotate strike",
            PressureLevel.TENSE: "Tense situation, every run matters",
            PressureLevel.INTENSE: "High pressure moment, crucial phase of the match",
            PressureLevel.CRITICAL: "Match on a knife's edge, one ball could change everything",
        }
        return descriptions.get(level, "Unknown pressure level")
