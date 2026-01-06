"""Query engine for player vs bowler matchup statistics."""

from __future__ import annotations

from .db import StatsDatabase
from .models import PlayerMatchupStats
from .normalize import normalize_player_id


class MatchupEngine:
    """Query engine for player matchup statistics.

    Provides methods to query head-to-head statistics between batters
    and bowlers from the stats database.
    """

    def __init__(self, db: StatsDatabase) -> None:
        """Initialize engine with database connection.

        Args:
            db: Initialized StatsDatabase instance.
        """
        self.db = db

    def get_head_to_head(
        self,
        batter: str,
        bowler: str,
        match_format: str | None = None,
    ) -> PlayerMatchupStats | None:
        """Get aggregated stats for a specific batter vs bowler matchup.

        Args:
            batter: Batter name or normalized ID.
            bowler: Bowler name or normalized ID.
            match_format: Optional filter by format (T20, ODI, Test).

        Returns:
            PlayerMatchupStats if matchup exists, None otherwise.
        """
        batter_id = normalize_player_id(batter)
        bowler_id = normalize_player_id(bowler)

        query = """
            SELECT
                m.batter_id,
                m.bowler_id,
                COUNT(DISTINCT m.match_id) as matches,
                SUM(m.balls_faced) as balls_faced,
                SUM(m.runs_scored) as runs_scored,
                SUM(m.dismissals) as dismissals,
                SUM(m.dots) as dots,
                SUM(m.fours) as fours,
                SUM(m.sixes) as sixes
            FROM matchups m
            WHERE m.batter_id = ? AND m.bowler_id = ?
        """
        params: list = [batter_id, bowler_id]

        if match_format:
            query += " AND m.match_format = ?"
            params.append(match_format)

        query += " GROUP BY m.batter_id, m.bowler_id"

        with self.db._connection() as conn:
            result = conn.execute(query, params).fetchone()

            if not result or result["balls_faced"] == 0:
                return None

            # Get display names
            batter_name = self.db.get_player_name(batter_id) or batter
            bowler_name = self.db.get_player_name(bowler_id) or bowler

            return PlayerMatchupStats(
                batter_id=result["batter_id"],
                batter_name=batter_name,
                bowler_id=result["bowler_id"],
                bowler_name=bowler_name,
                matches=result["matches"],
                balls_faced=result["balls_faced"],
                runs_scored=result["runs_scored"],
                dismissals=result["dismissals"],
                dots=result["dots"],
                fours=result["fours"],
                sixes=result["sixes"],
            )

    def get_batter_vs_all(
        self,
        batter: str,
        min_balls: int = 6,
        limit: int = 10,
    ) -> list[PlayerMatchupStats]:
        """Get a batter's stats against all bowlers they've faced.

        Args:
            batter: Batter name or normalized ID.
            min_balls: Minimum balls faced to include (default: 6).
            limit: Maximum number of results (default: 10).

        Returns:
            List of PlayerMatchupStats sorted by balls faced (desc).
        """
        batter_id = normalize_player_id(batter)

        query = """
            SELECT
                m.batter_id,
                m.bowler_id,
                COUNT(DISTINCT m.match_id) as matches,
                SUM(m.balls_faced) as balls_faced,
                SUM(m.runs_scored) as runs_scored,
                SUM(m.dismissals) as dismissals,
                SUM(m.dots) as dots,
                SUM(m.fours) as fours,
                SUM(m.sixes) as sixes
            FROM matchups m
            WHERE m.batter_id = ?
            GROUP BY m.batter_id, m.bowler_id
            HAVING balls_faced >= ?
            ORDER BY balls_faced DESC
            LIMIT ?
        """

        with self.db._connection() as conn:
            results = conn.execute(query, [batter_id, min_balls, limit]).fetchall()
            batter_name = self.db.get_player_name(batter_id) or batter

            return [
                PlayerMatchupStats(
                    batter_id=row["batter_id"],
                    batter_name=batter_name,
                    bowler_id=row["bowler_id"],
                    bowler_name=self.db.get_player_name(row["bowler_id"]) or row["bowler_id"],
                    matches=row["matches"],
                    balls_faced=row["balls_faced"],
                    runs_scored=row["runs_scored"],
                    dismissals=row["dismissals"],
                    dots=row["dots"],
                    fours=row["fours"],
                    sixes=row["sixes"],
                )
                for row in results
            ]

    def get_bowler_vs_all(
        self,
        bowler: str,
        min_balls: int = 6,
        limit: int = 10,
    ) -> list[PlayerMatchupStats]:
        """Get a bowler's stats against all batters they've bowled to.

        Args:
            bowler: Bowler name or normalized ID.
            min_balls: Minimum balls bowled to include (default: 6).
            limit: Maximum number of results (default: 10).

        Returns:
            List of PlayerMatchupStats sorted by balls bowled (desc).
        """
        bowler_id = normalize_player_id(bowler)

        query = """
            SELECT
                m.batter_id,
                m.bowler_id,
                COUNT(DISTINCT m.match_id) as matches,
                SUM(m.balls_faced) as balls_faced,
                SUM(m.runs_scored) as runs_scored,
                SUM(m.dismissals) as dismissals,
                SUM(m.dots) as dots,
                SUM(m.fours) as fours,
                SUM(m.sixes) as sixes
            FROM matchups m
            WHERE m.bowler_id = ?
            GROUP BY m.batter_id, m.bowler_id
            HAVING balls_faced >= ?
            ORDER BY balls_faced DESC
            LIMIT ?
        """

        with self.db._connection() as conn:
            results = conn.execute(query, [bowler_id, min_balls, limit]).fetchall()
            bowler_name = self.db.get_player_name(bowler_id) or bowler

            return [
                PlayerMatchupStats(
                    batter_id=row["batter_id"],
                    batter_name=self.db.get_player_name(row["batter_id"]) or row["batter_id"],
                    bowler_id=row["bowler_id"],
                    bowler_name=bowler_name,
                    matches=row["matches"],
                    balls_faced=row["balls_faced"],
                    runs_scored=row["runs_scored"],
                    dismissals=row["dismissals"],
                    dots=row["dots"],
                    fours=row["fours"],
                    sixes=row["sixes"],
                )
                for row in results
            ]

    def get_batter_nemesis(
        self,
        batter: str,
        min_dismissals: int = 2,
    ) -> list[PlayerMatchupStats]:
        """Get bowlers who have dismissed a batter the most.

        Args:
            batter: Batter name or normalized ID.
            min_dismissals: Minimum dismissals to include (default: 2).

        Returns:
            List of PlayerMatchupStats sorted by dismissals (desc).
        """
        batter_id = normalize_player_id(batter)

        query = """
            SELECT
                m.batter_id,
                m.bowler_id,
                COUNT(DISTINCT m.match_id) as matches,
                SUM(m.balls_faced) as balls_faced,
                SUM(m.runs_scored) as runs_scored,
                SUM(m.dismissals) as dismissals,
                SUM(m.dots) as dots,
                SUM(m.fours) as fours,
                SUM(m.sixes) as sixes
            FROM matchups m
            WHERE m.batter_id = ?
            GROUP BY m.batter_id, m.bowler_id
            HAVING dismissals >= ?
            ORDER BY dismissals DESC, balls_faced ASC
            LIMIT 5
        """

        with self.db._connection() as conn:
            results = conn.execute(query, [batter_id, min_dismissals]).fetchall()
            batter_name = self.db.get_player_name(batter_id) or batter

            return [
                PlayerMatchupStats(
                    batter_id=row["batter_id"],
                    batter_name=batter_name,
                    bowler_id=row["bowler_id"],
                    bowler_name=self.db.get_player_name(row["bowler_id"]) or row["bowler_id"],
                    matches=row["matches"],
                    balls_faced=row["balls_faced"],
                    runs_scored=row["runs_scored"],
                    dismissals=row["dismissals"],
                    dots=row["dots"],
                    fours=row["fours"],
                    sixes=row["sixes"],
                )
                for row in results
            ]

    def get_bowler_bunnies(
        self,
        bowler: str,
        min_dismissals: int = 2,
    ) -> list[PlayerMatchupStats]:
        """Get batters that a bowler has dismissed the most.

        Args:
            bowler: Bowler name or normalized ID.
            min_dismissals: Minimum dismissals to include (default: 2).

        Returns:
            List of PlayerMatchupStats sorted by dismissals (desc).
        """
        bowler_id = normalize_player_id(bowler)

        query = """
            SELECT
                m.batter_id,
                m.bowler_id,
                COUNT(DISTINCT m.match_id) as matches,
                SUM(m.balls_faced) as balls_faced,
                SUM(m.runs_scored) as runs_scored,
                SUM(m.dismissals) as dismissals,
                SUM(m.dots) as dots,
                SUM(m.fours) as fours,
                SUM(m.sixes) as sixes
            FROM matchups m
            WHERE m.bowler_id = ?
            GROUP BY m.batter_id, m.bowler_id
            HAVING dismissals >= ?
            ORDER BY dismissals DESC, balls_faced ASC
            LIMIT 5
        """

        with self.db._connection() as conn:
            results = conn.execute(query, [bowler_id, min_dismissals]).fetchall()
            bowler_name = self.db.get_player_name(bowler_id) or bowler

            return [
                PlayerMatchupStats(
                    batter_id=row["batter_id"],
                    batter_name=self.db.get_player_name(row["batter_id"]) or row["batter_id"],
                    bowler_id=row["bowler_id"],
                    bowler_name=bowler_name,
                    matches=row["matches"],
                    balls_faced=row["balls_faced"],
                    runs_scored=row["runs_scored"],
                    dismissals=row["dismissals"],
                    dots=row["dots"],
                    fours=row["fours"],
                    sixes=row["sixes"],
                )
                for row in results
            ]
