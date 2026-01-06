"""Recent form analysis for players."""

from __future__ import annotations

from enum import Enum

from .db import StatsDatabase
from .models import MatchPerformance, RecentForm
from .normalize import normalize_player_id


class FormTrend(Enum):
    """Player form trend."""

    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"


class FormEngine:
    """Query engine for recent form analysis."""

    def __init__(self, db: StatsDatabase, window_size: int = 5) -> None:
        """Initialize with database connection.

        Args:
            db: StatsDatabase instance.
            window_size: Number of recent matches to analyze.
        """
        self.db = db
        self.window_size = window_size

    def get_recent_form(
        self,
        player: str,
        role: str = "batter",
        match_format: str | None = None,
    ) -> RecentForm | None:
        """Get recent form for a player.

        Args:
            player: Player name or ID.
            role: "batter" or "bowler".
            match_format: Optional format filter.

        Returns:
            RecentForm with last N matches and trend analysis.
        """
        player_id = normalize_player_id(player)

        if role == "batter":
            query = """
                SELECT
                    match_id,
                    match_date,
                    match_format,
                    venue,
                    SUM(balls_faced) as balls,
                    SUM(runs_scored) as runs,
                    SUM(dismissals) as dismissals,
                    SUM(fours) as fours,
                    SUM(sixes) as sixes
                FROM matchups
                WHERE batter_id = ?
            """
            params: list = [player_id]
        else:
            query = """
                SELECT
                    match_id,
                    match_date,
                    match_format,
                    venue,
                    SUM(balls_faced) as balls,
                    SUM(runs_scored) as runs,
                    SUM(dismissals) as wickets,
                    SUM(fours) as fours,
                    SUM(sixes) as sixes
                FROM matchups
                WHERE bowler_id = ?
            """
            params = [player_id]

        if match_format:
            query += " AND match_format = ?"
            params.append(match_format)

        query += """
            GROUP BY match_id
            ORDER BY match_date DESC
            LIMIT ?
        """
        params.append(self.window_size)

        with self.db._connection() as conn:
            results = conn.execute(query, params).fetchall()

            if not results:
                return None

            # Get player name
            player_name = self.db.get_player_name(player_id) or player

            # Build match performances
            matches = [
                MatchPerformance(
                    match_id=row["match_id"],
                    match_date=row["match_date"] or "",
                    match_format=row["match_format"] or "",
                    venue=row["venue"] or "",
                    runs=row["runs"] or 0,
                    balls=row["balls"] or 0,
                    dismissals=row["dismissals"] if role == "batter" else row["wickets"],
                    fours=row["fours"] or 0,
                    sixes=row["sixes"] or 0,
                )
                for row in results
            ]

            # Calculate aggregates
            total_runs = sum(m.runs for m in matches)
            total_balls = sum(m.balls for m in matches)
            total_dismissals = sum(m.dismissals for m in matches)

            # Calculate trend
            trend = self._calculate_trend(matches, role)
            trend_description = self._get_trend_description(matches, trend, role)

            return RecentForm(
                player_id=player_id,
                player_name=player_name,
                role=role,
                matches=matches,
                total_runs=total_runs,
                total_balls=total_balls,
                total_dismissals=total_dismissals,
                trend=trend.value,
                trend_description=trend_description,
            )

    def _calculate_trend(self, performances: list[MatchPerformance], role: str) -> FormTrend:
        """Calculate trend from recent performances.

        Uses simple moving average comparison:
        - Compare first half (recent) vs second half (older)
        - If recent half > older half by 10%+: improving
        - If recent half < older half by 10%+: declining
        - Otherwise: stable
        """
        if len(performances) < 3:
            return FormTrend.STABLE

        mid = len(performances) // 2
        recent = performances[:mid]  # More recent (list is DESC by date)
        older = performances[mid:]

        if role == "batter":
            # Compare strike rates
            recent_sr = self._avg_strike_rate(recent)
            older_sr = self._avg_strike_rate(older)

            if older_sr == 0:
                return FormTrend.STABLE

            if recent_sr > older_sr * 1.1:
                return FormTrend.IMPROVING
            elif recent_sr < older_sr * 0.9:
                return FormTrend.DECLINING
        else:
            # For bowlers, compare economy (lower is better)
            recent_econ = self._avg_economy(recent)
            older_econ = self._avg_economy(older)

            if older_econ == 0:
                return FormTrend.STABLE

            if recent_econ < older_econ * 0.9:
                return FormTrend.IMPROVING
            elif recent_econ > older_econ * 1.1:
                return FormTrend.DECLINING

        return FormTrend.STABLE

    def _avg_strike_rate(self, performances: list[MatchPerformance]) -> float:
        """Calculate average strike rate across performances."""
        total_runs = sum(p.runs for p in performances)
        total_balls = sum(p.balls for p in performances)
        if total_balls == 0:
            return 0.0
        return (total_runs / total_balls) * 100

    def _avg_economy(self, performances: list[MatchPerformance]) -> float:
        """Calculate average economy across performances."""
        total_runs = sum(p.runs for p in performances)
        total_balls = sum(p.balls for p in performances)
        if total_balls == 0:
            return 0.0
        overs = total_balls / 6
        return total_runs / overs

    def _get_trend_description(
        self,
        performances: list[MatchPerformance],
        trend: FormTrend,
        role: str,
    ) -> str:
        """Generate human-readable trend description."""
        match_count = len(performances)
        total_runs = sum(p.runs for p in performances)
        total_balls = sum(p.balls for p in performances)

        if role == "batter":
            avg_sr = (total_runs / total_balls * 100) if total_balls > 0 else 0
            if trend == FormTrend.IMPROVING:
                return f"Hot form: {total_runs} runs in last {match_count}, SR {avg_sr:.0f}"
            elif trend == FormTrend.DECLINING:
                return f"Struggling: {total_runs} runs in last {match_count}, SR {avg_sr:.0f}"
            else:
                return f"Steady: {total_runs} runs in last {match_count}, SR {avg_sr:.0f}"
        else:
            total_wickets = sum(p.dismissals for p in performances)
            if trend == FormTrend.IMPROVING:
                return f"In form: {total_wickets} wkts in last {match_count}"
            elif trend == FormTrend.DECLINING:
                return f"Struggling: {total_wickets} wkts in last {match_count}"
            else:
                return f"Steady: {total_wickets} wkts in last {match_count}"
