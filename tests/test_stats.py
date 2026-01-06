"""Tests for the stats engine module."""

import pytest

from suksham_vachak.stats.db import StatsDatabase
from suksham_vachak.stats.matchups import MatchupEngine
from suksham_vachak.stats.models import MatchupRecord, PlayerMatchupStats
from suksham_vachak.stats.normalize import normalize_display_name, normalize_player_id


class TestNormalization:
    """Test player name normalization functions."""

    def test_normalize_basic(self):
        """Test basic name normalization."""
        assert normalize_player_id("V Kohli") == "v_kohli"
        assert normalize_player_id("Virat Kohli") == "virat_kohli"

    def test_normalize_with_periods(self):
        """Test normalization removes periods."""
        assert normalize_player_id("M.S. Dhoni") == "ms_dhoni"
        assert normalize_player_id("J.M. Anderson") == "jm_anderson"

    def test_normalize_with_apostrophe(self):
        """Test normalization removes apostrophes."""
        assert normalize_player_id("D'Arcy Short") == "darcy_short"

    def test_normalize_multiple_spaces(self):
        """Test normalization handles multiple spaces."""
        assert normalize_player_id("Shaheen  Shah   Afridi") == "shaheen_shah_afridi"

    def test_normalize_empty(self):
        """Test normalization of empty string."""
        assert normalize_player_id("") == ""

    def test_display_name_cleanup(self):
        """Test display name cleanup."""
        assert normalize_display_name("  V  Kohli  ") == "V Kohli"
        assert normalize_display_name("Multiple   Spaces") == "Multiple Spaces"


class TestPlayerMatchupStats:
    """Test PlayerMatchupStats calculations."""

    def test_strike_rate(self):
        """Test strike rate calculation."""
        stats = PlayerMatchupStats(
            batter_id="v_kohli",
            batter_name="V Kohli",
            bowler_id="jm_anderson",
            bowler_name="JM Anderson",
            matches=5,
            balls_faced=100,
            runs_scored=150,
            dismissals=2,
            dots=30,
            fours=10,
            sixes=5,
        )
        assert stats.strike_rate == 150.0

    def test_strike_rate_zero_balls(self):
        """Test strike rate with zero balls faced."""
        stats = PlayerMatchupStats(
            batter_id="v_kohli",
            batter_name="V Kohli",
            bowler_id="jm_anderson",
            bowler_name="JM Anderson",
            matches=0,
            balls_faced=0,
            runs_scored=0,
            dismissals=0,
            dots=0,
            fours=0,
            sixes=0,
        )
        assert stats.strike_rate == 0.0

    def test_average(self):
        """Test batting average calculation."""
        stats = PlayerMatchupStats(
            batter_id="v_kohli",
            batter_name="V Kohli",
            bowler_id="jm_anderson",
            bowler_name="JM Anderson",
            matches=5,
            balls_faced=100,
            runs_scored=150,
            dismissals=3,
            dots=30,
            fours=10,
            sixes=5,
        )
        assert stats.average == 50.0

    def test_average_not_out(self):
        """Test average when never dismissed."""
        stats = PlayerMatchupStats(
            batter_id="v_kohli",
            batter_name="V Kohli",
            bowler_id="jm_anderson",
            bowler_name="JM Anderson",
            matches=3,
            balls_faced=50,
            runs_scored=75,
            dismissals=0,
            dots=10,
            fours=5,
            sixes=2,
        )
        assert stats.average == float("inf")

    def test_dot_percentage(self):
        """Test dot ball percentage calculation."""
        stats = PlayerMatchupStats(
            batter_id="v_kohli",
            batter_name="V Kohli",
            bowler_id="jm_anderson",
            bowler_name="JM Anderson",
            matches=5,
            balls_faced=100,
            runs_scored=150,
            dismissals=2,
            dots=40,
            fours=10,
            sixes=5,
        )
        assert stats.dot_percentage == 40.0

    def test_boundary_percentage(self):
        """Test boundary percentage calculation."""
        stats = PlayerMatchupStats(
            batter_id="v_kohli",
            batter_name="V Kohli",
            bowler_id="jm_anderson",
            bowler_name="JM Anderson",
            matches=5,
            balls_faced=100,
            runs_scored=150,
            dismissals=2,
            dots=30,
            fours=10,
            sixes=5,
        )
        assert stats.boundary_percentage == 15.0

    def test_to_commentary_context(self):
        """Test commentary context generation."""
        stats = PlayerMatchupStats(
            batter_id="v_kohli",
            batter_name="V Kohli",
            bowler_id="jm_anderson",
            bowler_name="JM Anderson",
            matches=5,
            balls_faced=100,
            runs_scored=150,
            dismissals=3,
            dots=30,
            fours=10,
            sixes=5,
        )
        context = stats.to_commentary_context()
        assert "V Kohli vs JM Anderson" in context
        assert "150 runs" in context
        assert "100 balls" in context
        assert "SR 150.0" in context

    def test_to_short_context(self):
        """Test short context generation."""
        stats = PlayerMatchupStats(
            batter_id="v_kohli",
            batter_name="V Kohli",
            bowler_id="jm_anderson",
            bowler_name="JM Anderson",
            matches=5,
            balls_faced=100,
            runs_scored=150,
            dismissals=3,
            dots=30,
            fours=10,
            sixes=5,
        )
        context = stats.to_short_context()
        assert "V Kohli vs JM Anderson" in context
        assert "150/100" in context


class TestStatsDatabase:
    """Test SQLite database operations."""

    def test_initialize(self):
        """Test database initialization creates tables."""
        db = StatsDatabase(":memory:")
        db.initialize()
        assert db.get_player_count() == 0
        assert db.get_matchup_count() == 0

    def test_upsert_player(self):
        """Test player upsert."""
        db = StatsDatabase(":memory:")
        db.initialize()

        db.upsert_player("v_kohli", "V Kohli", "Virat Kohli", "India")
        assert db.get_player_count() == 1
        assert db.get_player_name("v_kohli") == "V Kohli"

    def test_add_matchup_record(self):
        """Test adding a matchup record."""
        db = StatsDatabase(":memory:")
        db.initialize()

        record = MatchupRecord(
            batter_id="v_kohli",
            batter_name="V Kohli",
            bowler_id="jm_anderson",
            bowler_name="JM Anderson",
            match_id="m123",
            match_date="2024-01-01",
            match_format="Test",
            venue="Lord's",
            balls_faced=20,
            runs_scored=35,
            dots=8,
            fours=3,
            sixes=1,
            dismissals=1,
            dismissal_type="caught",
        )

        db.add_matchup_record(record)

        assert db.get_player_count() == 2
        assert db.get_matchup_count() == 1

    def test_add_matchup_records_batch(self):
        """Test batch adding matchup records."""
        db = StatsDatabase(":memory:")
        db.initialize()

        records = [
            MatchupRecord(
                batter_id="v_kohli",
                batter_name="V Kohli",
                bowler_id="jm_anderson",
                bowler_name="JM Anderson",
                match_id="m1",
                match_date="2024-01-01",
                match_format="Test",
                venue="Lord's",
                balls_faced=20,
                runs_scored=35,
                dots=8,
                fours=3,
                sixes=1,
                dismissals=0,
                dismissal_type=None,
            ),
            MatchupRecord(
                batter_id="v_kohli",
                batter_name="V Kohli",
                bowler_id="s_broad",
                bowler_name="S Broad",
                match_id="m1",
                match_date="2024-01-01",
                match_format="Test",
                venue="Lord's",
                balls_faced=15,
                runs_scored=22,
                dots=5,
                fours=2,
                sixes=0,
                dismissals=1,
                dismissal_type="bowled",
            ),
        ]

        db.add_matchup_records_batch(records)

        assert db.get_player_count() == 3
        assert db.get_matchup_count() == 2

    def test_clear(self):
        """Test clearing the database."""
        db = StatsDatabase(":memory:")
        db.initialize()

        db.upsert_player("v_kohli", "V Kohli")
        assert db.get_player_count() == 1

        db.clear()
        assert db.get_player_count() == 0


class TestMatchupEngine:
    """Test MatchupEngine queries."""

    @pytest.fixture
    def db_with_data(self):
        """Create a database with test data."""
        db = StatsDatabase(":memory:")
        db.initialize()

        records = [
            MatchupRecord(
                batter_id="v_kohli",
                batter_name="V Kohli",
                bowler_id="jm_anderson",
                bowler_name="JM Anderson",
                match_id="m1",
                match_date="2024-01-01",
                match_format="Test",
                venue="Lord's",
                balls_faced=30,
                runs_scored=45,
                dots=12,
                fours=4,
                sixes=1,
                dismissals=1,
                dismissal_type="caught",
            ),
            MatchupRecord(
                batter_id="v_kohli",
                batter_name="V Kohli",
                bowler_id="jm_anderson",
                bowler_name="JM Anderson",
                match_id="m2",
                match_date="2024-02-01",
                match_format="Test",
                venue="Oval",
                balls_faced=25,
                runs_scored=40,
                dots=8,
                fours=5,
                sixes=0,
                dismissals=0,
                dismissal_type=None,
            ),
            MatchupRecord(
                batter_id="v_kohli",
                batter_name="V Kohli",
                bowler_id="s_broad",
                bowler_name="S Broad",
                match_id="m1",
                match_date="2024-01-01",
                match_format="Test",
                venue="Lord's",
                balls_faced=20,
                runs_scored=30,
                dots=6,
                fours=3,
                sixes=1,
                dismissals=0,
                dismissal_type=None,
            ),
        ]

        db.add_matchup_records_batch(records)
        return db

    def test_get_head_to_head(self, db_with_data):
        """Test head-to-head query."""
        engine = MatchupEngine(db_with_data)

        stats = engine.get_head_to_head("V Kohli", "JM Anderson")
        assert stats is not None
        assert stats.matches == 2
        assert stats.balls_faced == 55
        assert stats.runs_scored == 85
        assert stats.dismissals == 1
        assert stats.fours == 9
        assert stats.sixes == 1

    def test_get_head_to_head_not_found(self, db_with_data):
        """Test head-to-head when matchup doesn't exist."""
        engine = MatchupEngine(db_with_data)

        stats = engine.get_head_to_head("Unknown Player", "JM Anderson")
        assert stats is None

    def test_get_batter_vs_all(self, db_with_data):
        """Test getting batter's stats against all bowlers."""
        engine = MatchupEngine(db_with_data)

        matchups = engine.get_batter_vs_all("V Kohli", min_balls=10)
        assert len(matchups) == 2
        # Sorted by balls faced desc
        assert matchups[0].bowler_name == "JM Anderson"
        assert matchups[1].bowler_name == "S Broad"

    def test_get_bowler_vs_all(self, db_with_data):
        """Test getting bowler's stats against all batters."""
        engine = MatchupEngine(db_with_data)

        matchups = engine.get_bowler_vs_all("JM Anderson", min_balls=10)
        assert len(matchups) == 1
        assert matchups[0].batter_name == "V Kohli"
