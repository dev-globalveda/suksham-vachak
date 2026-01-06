"""Phase-based statistics queries."""

from __future__ import annotations

from enum import Enum

from .db import StatsDatabase
from .models import PhaseStats
from .normalize import normalize_player_id


class Phase(Enum):
    """Match phases for different formats."""

    # Limited overs phases
    POWERPLAY = "powerplay"
    MIDDLE = "middle"
    DEATH = "death"

    # Test match sessions (heuristic)
    SESSION1 = "session1"
    SESSION2 = "session2"
    SESSION3 = "session3"


class PhaseEngine:
    """Query engine for phase-based statistics."""

    def __init__(self, db: StatsDatabase) -> None:
        """Initialize with database connection.

        Args:
            db: StatsDatabase instance.
        """
        self.db = db

    def get_phase_performance(
        self,
        player: str,
        phase: str | Phase,
        match_format: str | None = None,
        role: str = "batter",
    ) -> PhaseStats | None:
        """Get player performance in a specific phase.

        Args:
            player: Player name or ID.
            phase: Match phase (powerplay, middle, death, session1/2/3).
            match_format: Optional format filter (T20, ODI, Test).
            role: "batter" or "bowler".

        Returns:
            PhaseStats if data exists, None otherwise.
        """
        player_id = normalize_player_id(player)
        phase_val = phase.value if isinstance(phase, Phase) else phase

        if role == "batter":
            query = """
                SELECT
                    batter_id as player_id,
                    (SELECT name FROM players WHERE id = batter_id) as player_name,
                    COUNT(DISTINCT match_id) as matches,
                    SUM(balls_faced) as balls,
                    SUM(runs_scored) as runs,
                    SUM(dots) as dots,
                    SUM(fours) as fours,
                    SUM(sixes) as sixes,
                    SUM(dismissals) as wickets
                FROM matchups
                WHERE batter_id = ? AND phase = ?
            """
            params: list = [player_id, phase_val]
        else:
            query = """
                SELECT
                    bowler_id as player_id,
                    (SELECT name FROM players WHERE id = bowler_id) as player_name,
                    COUNT(DISTINCT match_id) as matches,
                    SUM(balls_faced) as balls,
                    SUM(runs_scored) as runs,
                    SUM(dots) as dots,
                    SUM(fours) as fours,
                    SUM(sixes) as sixes,
                    SUM(dismissals) as wickets
                FROM matchups
                WHERE bowler_id = ? AND phase = ?
            """
            params = [player_id, phase_val]

        if match_format:
            query += " AND match_format = ?"
            params.append(match_format)

        query += " GROUP BY player_id"

        with self.db._connection() as conn:
            result = conn.execute(query, params).fetchone()

            if not result or result["balls"] is None or result["balls"] == 0:
                return None

            return PhaseStats(
                player_id=result["player_id"],
                player_name=result["player_name"] or player,
                phase=phase_val,
                match_format=match_format or "all",
                role=role,
                matches=result["matches"],
                balls=result["balls"],
                runs=result["runs"],
                dots=result["dots"] or 0,
                fours=result["fours"] or 0,
                sixes=result["sixes"] or 0,
                wickets=result["wickets"] or 0,
            )

    def get_all_phases(
        self,
        player: str,
        match_format: str,
        role: str = "batter",
    ) -> dict[str, PhaseStats]:
        """Get player performance across all phases for a format.

        Args:
            player: Player name or ID.
            match_format: Match format (T20, ODI, Test).
            role: "batter" or "bowler".

        Returns:
            Dict mapping phase name to PhaseStats.
        """
        # Determine phases based on format
        if match_format == "Test":
            phases = [Phase.SESSION1, Phase.SESSION2, Phase.SESSION3]
        else:
            phases = [Phase.POWERPLAY, Phase.MIDDLE, Phase.DEATH]

        result = {}
        for phase in phases:
            stats = self.get_phase_performance(player, phase, match_format, role)
            if stats:
                result[phase.value] = stats

        return result

    def get_phase_leaders(
        self,
        phase: str | Phase,
        match_format: str,
        role: str = "batter",
        min_balls: int = 30,
        limit: int = 10,
    ) -> list[PhaseStats]:
        """Get top performers in a specific phase.

        Args:
            phase: Match phase to query.
            match_format: Match format filter.
            role: "batter" or "bowler".
            min_balls: Minimum balls for qualification.
            limit: Maximum results to return.

        Returns:
            List of PhaseStats sorted by performance.
        """
        phase_val = phase.value if isinstance(phase, Phase) else phase

        if role == "batter":
            # Sort by strike rate for batters
            query = """
                SELECT
                    batter_id as player_id,
                    (SELECT name FROM players WHERE id = batter_id) as player_name,
                    COUNT(DISTINCT match_id) as matches,
                    SUM(balls_faced) as balls,
                    SUM(runs_scored) as runs,
                    SUM(dots) as dots,
                    SUM(fours) as fours,
                    SUM(sixes) as sixes,
                    SUM(dismissals) as wickets
                FROM matchups
                WHERE phase = ? AND match_format = ?
                GROUP BY batter_id
                HAVING balls >= ?
                ORDER BY (CAST(runs AS REAL) / balls * 100) DESC
                LIMIT ?
            """
        else:
            # Sort by economy for bowlers
            query = """
                SELECT
                    bowler_id as player_id,
                    (SELECT name FROM players WHERE id = bowler_id) as player_name,
                    COUNT(DISTINCT match_id) as matches,
                    SUM(balls_faced) as balls,
                    SUM(runs_scored) as runs,
                    SUM(dots) as dots,
                    SUM(fours) as fours,
                    SUM(sixes) as sixes,
                    SUM(dismissals) as wickets
                FROM matchups
                WHERE phase = ? AND match_format = ?
                GROUP BY bowler_id
                HAVING balls >= ?
                ORDER BY (CAST(runs AS REAL) / balls * 6) ASC
                LIMIT ?
            """

        with self.db._connection() as conn:
            results = conn.execute(query, [phase_val, match_format, min_balls, limit]).fetchall()

            return [
                PhaseStats(
                    player_id=row["player_id"],
                    player_name=row["player_name"] or row["player_id"],
                    phase=phase_val,
                    match_format=match_format,
                    role=role,
                    matches=row["matches"],
                    balls=row["balls"],
                    runs=row["runs"],
                    dots=row["dots"] or 0,
                    fours=row["fours"] or 0,
                    sixes=row["sixes"] or 0,
                    wickets=row["wickets"] or 0,
                )
                for row in results
            ]
