"""Tests for the stats engine module."""

import pytest

from suksham_vachak.stats.aggregator import MatchupAccumulator
from suksham_vachak.stats.db import StatsDatabase
from suksham_vachak.stats.form import FormEngine
from suksham_vachak.stats.matchups import MatchupEngine
from suksham_vachak.stats.models import MatchPerformance, MatchupRecord, PhaseStats, PlayerMatchupStats, RecentForm
from suksham_vachak.stats.normalize import normalize_display_name, normalize_player_id
from suksham_vachak.stats.phases import Phase, PhaseEngine


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


class TestPhaseDetection:
    """Test phase detection in MatchupAccumulator."""

    def test_t20_powerplay(self):
        """Test T20 powerplay detection (overs 1-6)."""
        acc = MatchupAccumulator("m1", "2024-01-01", "T20", "Stadium")
        # 0-indexed over numbers
        assert acc._determine_phase(0) == "powerplay"  # Over 1
        assert acc._determine_phase(5) == "powerplay"  # Over 6

    def test_t20_middle(self):
        """Test T20 middle overs detection (overs 7-15)."""
        acc = MatchupAccumulator("m1", "2024-01-01", "T20", "Stadium")
        assert acc._determine_phase(6) == "middle"  # Over 7
        assert acc._determine_phase(14) == "middle"  # Over 15

    def test_t20_death(self):
        """Test T20 death overs detection (overs 16-20)."""
        acc = MatchupAccumulator("m1", "2024-01-01", "T20", "Stadium")
        assert acc._determine_phase(15) == "death"  # Over 16
        assert acc._determine_phase(19) == "death"  # Over 20

    def test_odi_powerplay(self):
        """Test ODI powerplay detection (overs 1-10)."""
        acc = MatchupAccumulator("m1", "2024-01-01", "ODI", "Stadium")
        assert acc._determine_phase(0) == "powerplay"  # Over 1
        assert acc._determine_phase(9) == "powerplay"  # Over 10

    def test_odi_middle(self):
        """Test ODI middle overs detection (overs 11-40)."""
        acc = MatchupAccumulator("m1", "2024-01-01", "ODI", "Stadium")
        assert acc._determine_phase(10) == "middle"  # Over 11
        assert acc._determine_phase(39) == "middle"  # Over 40

    def test_odi_death(self):
        """Test ODI death overs detection (overs 41-50)."""
        acc = MatchupAccumulator("m1", "2024-01-01", "ODI", "Stadium")
        assert acc._determine_phase(40) == "death"  # Over 41
        assert acc._determine_phase(49) == "death"  # Over 50

    def test_test_session1(self):
        """Test Test session1 detection (overs 1-30)."""
        acc = MatchupAccumulator("m1", "2024-01-01", "Test", "Stadium")
        assert acc._determine_phase(0) == "session1"  # Over 1
        assert acc._determine_phase(29) == "session1"  # Over 30

    def test_test_session2(self):
        """Test Test session2 detection (overs 31-60)."""
        acc = MatchupAccumulator("m1", "2024-01-01", "Test", "Stadium")
        assert acc._determine_phase(30) == "session2"  # Over 31
        assert acc._determine_phase(59) == "session2"  # Over 60

    def test_test_session3(self):
        """Test Test session3 detection (overs 61-90)."""
        acc = MatchupAccumulator("m1", "2024-01-01", "Test", "Stadium")
        assert acc._determine_phase(60) == "session3"  # Over 61
        assert acc._determine_phase(89) == "session3"  # Over 90

    def test_test_session_wraps(self):
        """Test that Test sessions wrap after 90 overs (new day)."""
        acc = MatchupAccumulator("m1", "2024-01-01", "Test", "Stadium")
        # Over 91 should be session1 of day 2
        assert acc._determine_phase(90) == "session1"
        # Over 120 should still be session1
        assert acc._determine_phase(119) == "session1"
        # Over 121 should be session2
        assert acc._determine_phase(120) == "session2"

    def test_unknown_format(self):
        """Test unknown format returns None."""
        acc = MatchupAccumulator("m1", "2024-01-01", "Unknown", "Stadium")
        assert acc._determine_phase(5) is None


class TestPhaseStatsModel:
    """Test PhaseStats dataclass properties."""

    def test_strike_rate(self):
        """Test strike rate calculation."""
        stats = PhaseStats(
            player_id="v_kohli",
            player_name="V Kohli",
            phase="powerplay",
            match_format="T20",
            role="batter",
            matches=5,
            balls=100,
            runs=150,
            dots=30,
            fours=15,
            sixes=8,
            wickets=2,
        )
        assert stats.strike_rate == 150.0

    def test_strike_rate_zero_balls(self):
        """Test strike rate with zero balls."""
        stats = PhaseStats(
            player_id="v_kohli",
            player_name="V Kohli",
            phase="powerplay",
            match_format="T20",
            role="batter",
            matches=0,
            balls=0,
            runs=0,
            dots=0,
            fours=0,
            sixes=0,
            wickets=0,
        )
        assert stats.strike_rate == 0.0

    def test_economy(self):
        """Test economy rate calculation."""
        stats = PhaseStats(
            player_id="jm_anderson",
            player_name="JM Anderson",
            phase="death",
            match_format="T20",
            role="bowler",
            matches=5,
            balls=24,  # 4 overs
            runs=36,
            dots=10,
            fours=2,
            sixes=2,
            wickets=3,
        )
        assert stats.economy == 9.0  # 36 runs / 4 overs

    def test_average_batter(self):
        """Test batting average calculation."""
        stats = PhaseStats(
            player_id="v_kohli",
            player_name="V Kohli",
            phase="middle",
            match_format="T20",
            role="batter",
            matches=5,
            balls=100,
            runs=150,
            dots=30,
            fours=10,
            sixes=5,
            wickets=3,  # dismissals for batter
        )
        assert stats.average == 50.0

    def test_average_not_out(self):
        """Test average when never dismissed."""
        stats = PhaseStats(
            player_id="v_kohli",
            player_name="V Kohli",
            phase="powerplay",
            match_format="T20",
            role="batter",
            matches=3,
            balls=50,
            runs=75,
            dots=10,
            fours=5,
            sixes=2,
            wickets=0,
        )
        assert stats.average == float("inf")

    def test_to_context_batter(self):
        """Test context string for batter."""
        stats = PhaseStats(
            player_id="v_kohli",
            player_name="V Kohli",
            phase="powerplay",
            match_format="T20",
            role="batter",
            matches=5,
            balls=100,
            runs=150,
            dots=30,
            fours=10,
            sixes=5,
            wickets=2,
        )
        context = stats.to_context("batter")
        assert "V Kohli" in context
        assert "powerplay" in context
        assert "SR 150" in context

    def test_to_context_bowler(self):
        """Test context string for bowler."""
        stats = PhaseStats(
            player_id="jm_anderson",
            player_name="JM Anderson",
            phase="death",
            match_format="T20",
            role="bowler",
            matches=5,
            balls=24,
            runs=36,
            dots=10,
            fours=2,
            sixes=2,
            wickets=3,
        )
        context = stats.to_context("bowler")
        assert "JM Anderson" in context
        assert "death" in context
        assert "Econ" in context


class TestPhaseEngine:
    """Test PhaseEngine queries."""

    @pytest.fixture
    def db_with_phase_data(self):
        """Create a database with phase-annotated test data."""
        db = StatsDatabase(":memory:")
        db.initialize()

        records = [
            # Kohli in powerplay - T20
            MatchupRecord(
                batter_id="v_kohli",
                batter_name="V Kohli",
                bowler_id="jm_anderson",
                bowler_name="JM Anderson",
                match_id="m1",
                match_date="2024-01-01",
                match_format="T20",
                venue="Stadium",
                balls_faced=20,
                runs_scored=35,
                dots=5,
                fours=4,
                sixes=2,
                dismissals=0,
                dismissal_type=None,
                phase="powerplay",
            ),
            # Kohli in death - T20
            MatchupRecord(
                batter_id="v_kohli",
                batter_name="V Kohli",
                bowler_id="jm_anderson",
                bowler_name="JM Anderson",
                match_id="m1",
                match_date="2024-01-01",
                match_format="T20",
                venue="Stadium",
                balls_faced=10,
                runs_scored=25,
                dots=2,
                fours=2,
                sixes=2,
                dismissals=1,
                dismissal_type="caught",
                phase="death",
            ),
            # Kohli in powerplay - match 2
            MatchupRecord(
                batter_id="v_kohli",
                batter_name="V Kohli",
                bowler_id="s_broad",
                bowler_name="S Broad",
                match_id="m2",
                match_date="2024-01-15",
                match_format="T20",
                venue="Stadium",
                balls_faced=15,
                runs_scored=28,
                dots=3,
                fours=3,
                sixes=1,
                dismissals=0,
                dismissal_type=None,
                phase="powerplay",
            ),
        ]

        db.add_matchup_records_batch(records)
        return db

    def test_get_phase_performance(self, db_with_phase_data):
        """Test getting phase performance."""
        engine = PhaseEngine(db_with_phase_data)

        stats = engine.get_phase_performance("V Kohli", "powerplay", "T20")
        assert stats is not None
        assert stats.matches == 2
        assert stats.balls == 35  # 20 + 15
        assert stats.runs == 63  # 35 + 28
        assert stats.phase == "powerplay"

    def test_get_phase_performance_not_found(self, db_with_phase_data):
        """Test phase performance when no data."""
        engine = PhaseEngine(db_with_phase_data)

        stats = engine.get_phase_performance("Unknown Player", "powerplay", "T20")
        assert stats is None

    def test_get_phase_performance_with_phase_enum(self, db_with_phase_data):
        """Test using Phase enum."""
        engine = PhaseEngine(db_with_phase_data)

        stats = engine.get_phase_performance("V Kohli", Phase.POWERPLAY, "T20")
        assert stats is not None
        assert stats.phase == "powerplay"

    def test_get_all_phases(self, db_with_phase_data):
        """Test getting all phases for a player."""
        engine = PhaseEngine(db_with_phase_data)

        phases = engine.get_all_phases("V Kohli", "T20")
        assert "powerplay" in phases
        assert "death" in phases
        # middle phase not in test data
        assert "middle" not in phases


class TestRecentFormModel:
    """Test RecentForm dataclass."""

    def test_average_strike_rate(self):
        """Test average strike rate calculation."""
        form = RecentForm(
            player_id="v_kohli",
            player_name="V Kohli",
            role="batter",
            matches=[],
            total_runs=150,
            total_balls=100,
            total_dismissals=3,
            trend="stable",
            trend_description="Steady form",
        )
        assert form.average_strike_rate == 150.0

    def test_average_strike_rate_zero_balls(self):
        """Test average strike rate with zero balls."""
        form = RecentForm(
            player_id="v_kohli",
            player_name="V Kohli",
            role="batter",
            matches=[],
            total_runs=0,
            total_balls=0,
            total_dismissals=0,
            trend="stable",
            trend_description="No data",
        )
        assert form.average_strike_rate == 0.0

    def test_average(self):
        """Test batting average calculation."""
        form = RecentForm(
            player_id="v_kohli",
            player_name="V Kohli",
            role="batter",
            matches=[],
            total_runs=150,
            total_balls=100,
            total_dismissals=3,
            trend="improving",
            trend_description="Hot form",
        )
        assert form.average == 50.0

    def test_to_context(self):
        """Test context string generation."""
        matches = [
            MatchPerformance(
                match_id="m1",
                match_date="2024-01-01",
                match_format="T20",
                venue="Stadium",
                runs=50,
                balls=30,
                dismissals=1,
                fours=5,
                sixes=2,
            )
        ]
        form = RecentForm(
            player_id="v_kohli",
            player_name="V Kohli",
            role="batter",
            matches=matches,
            total_runs=50,
            total_balls=30,
            total_dismissals=1,
            trend="improving",
            trend_description="Hot form",
        )
        context = form.to_context()
        assert "Last 1" in context
        assert "50 runs" in context
        assert "improving" in context


class TestFormEngine:
    """Test FormEngine queries and trend detection."""

    @pytest.fixture
    def db_with_form_data(self):
        """Create database with data for form analysis."""
        db = StatsDatabase(":memory:")
        db.initialize()

        # Create 6 matches with varying performance (newest first by date)
        records = [
            # Match 6 - Most recent, high score
            MatchupRecord(
                batter_id="v_kohli",
                batter_name="V Kohli",
                bowler_id="b1",
                bowler_name="Bowler 1",
                match_id="m6",
                match_date="2024-06-01",
                match_format="T20",
                venue="Stadium",
                balls_faced=30,
                runs_scored=55,
                dots=5,
                fours=6,
                sixes=2,
                dismissals=0,
                dismissal_type=None,
                phase="powerplay",
            ),
            # Match 5
            MatchupRecord(
                batter_id="v_kohli",
                batter_name="V Kohli",
                bowler_id="b2",
                bowler_name="Bowler 2",
                match_id="m5",
                match_date="2024-05-01",
                match_format="T20",
                venue="Stadium",
                balls_faced=28,
                runs_scored=50,
                dots=6,
                fours=5,
                sixes=2,
                dismissals=1,
                dismissal_type="caught",
                phase="middle",
            ),
            # Match 4
            MatchupRecord(
                batter_id="v_kohli",
                batter_name="V Kohli",
                bowler_id="b1",
                bowler_name="Bowler 1",
                match_id="m4",
                match_date="2024-04-01",
                match_format="T20",
                venue="Stadium",
                balls_faced=25,
                runs_scored=42,
                dots=7,
                fours=4,
                sixes=1,
                dismissals=0,
                dismissal_type=None,
                phase="death",
            ),
            # Match 3 - Older, lower score
            MatchupRecord(
                batter_id="v_kohli",
                batter_name="V Kohli",
                bowler_id="b3",
                bowler_name="Bowler 3",
                match_id="m3",
                match_date="2024-03-01",
                match_format="T20",
                venue="Stadium",
                balls_faced=30,
                runs_scored=25,
                dots=12,
                fours=2,
                sixes=0,
                dismissals=1,
                dismissal_type="bowled",
                phase="powerplay",
            ),
            # Match 2
            MatchupRecord(
                batter_id="v_kohli",
                batter_name="V Kohli",
                bowler_id="b2",
                bowler_name="Bowler 2",
                match_id="m2",
                match_date="2024-02-01",
                match_format="T20",
                venue="Stadium",
                balls_faced=28,
                runs_scored=20,
                dots=14,
                fours=1,
                sixes=0,
                dismissals=1,
                dismissal_type="lbw",
                phase="middle",
            ),
            # Match 1 - Oldest
            MatchupRecord(
                batter_id="v_kohli",
                batter_name="V Kohli",
                bowler_id="b1",
                bowler_name="Bowler 1",
                match_id="m1",
                match_date="2024-01-01",
                match_format="T20",
                venue="Stadium",
                balls_faced=22,
                runs_scored=18,
                dots=10,
                fours=1,
                sixes=0,
                dismissals=1,
                dismissal_type="caught",
                phase="death",
            ),
        ]

        db.add_matchup_records_batch(records)
        return db

    def test_get_recent_form(self, db_with_form_data):
        """Test getting recent form."""
        engine = FormEngine(db_with_form_data, window_size=5)

        form = engine.get_recent_form("V Kohli")
        assert form is not None
        assert len(form.matches) == 5
        assert form.player_name == "V Kohli"

    def test_get_recent_form_not_found(self, db_with_form_data):
        """Test recent form when player not found."""
        engine = FormEngine(db_with_form_data)

        form = engine.get_recent_form("Unknown Player")
        assert form is None

    def test_trend_improving(self, db_with_form_data):
        """Test improving trend detection."""
        engine = FormEngine(db_with_form_data, window_size=6)

        form = engine.get_recent_form("V Kohli")
        # Recent matches (m6, m5, m4) have higher SR than older (m3, m2, m1)
        assert form is not None
        assert form.trend == "improving"

    def test_trend_stable(self):
        """Test stable trend detection."""
        db = StatsDatabase(":memory:")
        db.initialize()

        # Create matches with consistent performance
        records = [
            MatchupRecord(
                batter_id="player",
                batter_name="Player",
                bowler_id="b1",
                bowler_name="Bowler",
                match_id=f"m{i}",
                match_date=f"2024-0{i}-01",
                match_format="T20",
                venue="Stadium",
                balls_faced=30,
                runs_scored=40,  # Consistent SR ~133
                dots=10,
                fours=4,
                sixes=1,
                dismissals=1,
                dismissal_type="caught",
                phase="powerplay",
            )
            for i in range(1, 7)
        ]
        db.add_matchup_records_batch(records)

        engine = FormEngine(db, window_size=6)
        form = engine.get_recent_form("Player")
        assert form is not None
        assert form.trend == "stable"

    def test_form_trend_description(self, db_with_form_data):
        """Test trend description is generated."""
        engine = FormEngine(db_with_form_data, window_size=5)

        form = engine.get_recent_form("V Kohli")
        assert form is not None
        assert form.trend_description != ""
        # Should contain run count
        assert "runs" in form.trend_description.lower() or str(form.total_runs) in form.trend_description
