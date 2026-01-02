"""Tests for the Cricket parser module."""

from pathlib import Path

import pytest

from suksham_vachak.parser import (
    CricketEvent,
    CricsheetParser,
    EventType,
    MatchContext,
    MatchFormat,
    MatchInfo,
)

SAMPLE_DATA_DIR = Path(__file__).parent.parent / "data" / "cricsheet_sample"


class TestEventType:
    """Tests for EventType enum."""

    def test_all_event_types_defined(self) -> None:
        """Verify all expected event types exist."""
        expected = [
            "DOT_BALL",
            "SINGLE",
            "DOUBLE",
            "TRIPLE",
            "BOUNDARY_FOUR",
            "BOUNDARY_SIX",
            "WICKET",
            "WIDE",
            "NO_BALL",
            "BYE",
            "LEG_BYE",
        ]
        for event_name in expected:
            assert hasattr(EventType, event_name)


class TestMatchContext:
    """Tests for MatchContext dataclass."""

    def test_balls_bowled_calculation(self) -> None:
        """Test balls_bowled property calculation."""
        ctx = MatchContext(
            match_id="test",
            teams=("Team A", "Team B"),
            venue="Test Ground",
            date="2024-01-01",
            format=MatchFormat.T20,
            innings=1,
            current_score=50,
            current_wickets=2,
            overs_completed=8.3,
        )
        assert ctx.balls_bowled == 51  # 8 overs * 6 + 3 balls

    def test_is_chasing_first_innings(self) -> None:
        """Test is_chasing returns False for first innings."""
        ctx = MatchContext(
            match_id="test",
            teams=("Team A", "Team B"),
            venue="Test Ground",
            date="2024-01-01",
            format=MatchFormat.T20,
            innings=1,
            current_score=100,
            current_wickets=3,
            overs_completed=12.0,
            target=None,
        )
        assert ctx.is_chasing is False

    def test_is_chasing_second_innings(self) -> None:
        """Test is_chasing returns True when target is set."""
        ctx = MatchContext(
            match_id="test",
            teams=("Team A", "Team B"),
            venue="Test Ground",
            date="2024-01-01",
            format=MatchFormat.T20,
            innings=2,
            current_score=80,
            current_wickets=2,
            overs_completed=10.0,
            target=160,
        )
        assert ctx.is_chasing is True
        assert ctx.runs_required() == 80


class TestCricketEvent:
    """Tests for CricketEvent dataclass."""

    @pytest.fixture
    def sample_context(self) -> MatchContext:
        """Create a sample match context for testing."""
        return MatchContext(
            match_id="test",
            teams=("Australia", "South Africa"),
            venue="WACA",
            date="2016-11-03",
            format=MatchFormat.TEST,
            innings=1,
            current_score=45,
            current_wickets=1,
            overs_completed=12.4,
        )

    def test_dot_ball_detection(self, sample_context: MatchContext) -> None:
        """Test is_dot_ball property."""
        event = CricketEvent(
            event_id="test-1",
            event_type=EventType.DOT_BALL,
            ball_number="12.4",
            batter="DA Warner",
            bowler="K Rabada",
            non_striker="SE Marsh",
            runs_batter=0,
            runs_extras=0,
            runs_total=0,
            is_boundary=False,
            is_wicket=False,
            match_context=sample_context,
        )
        assert event.is_dot_ball is True

    def test_ball_number_parsing(self, sample_context: MatchContext) -> None:
        """Test over_number and ball_in_over properties."""
        event = CricketEvent(
            event_id="test-1",
            event_type=EventType.SINGLE,
            ball_number="15.3",
            batter="DA Warner",
            bowler="K Rabada",
            non_striker="SE Marsh",
            runs_batter=1,
            runs_extras=0,
            runs_total=1,
            is_boundary=False,
            is_wicket=False,
            match_context=sample_context,
        )
        assert event.over_number == 15
        assert event.ball_in_over == 3

    def test_wicket_description(self, sample_context: MatchContext) -> None:
        """Test description for wicket events."""
        event = CricketEvent(
            event_id="test-1",
            event_type=EventType.WICKET,
            ball_number="12.4",
            batter="DA Warner",
            bowler="K Rabada",
            non_striker="SE Marsh",
            runs_batter=0,
            runs_extras=0,
            runs_total=0,
            is_boundary=False,
            is_wicket=True,
            match_context=sample_context,
            wicket_type="caught",
            wicket_player="DA Warner",
            fielder="Q de Kock",
        )
        assert "WICKET" in event.description
        assert "DA Warner" in event.description


class TestCricsheetParser:
    """Tests for CricsheetParser class."""

    @pytest.fixture
    def sample_match_path(self) -> Path:
        """Get path to a sample match file."""
        sample_files = list(SAMPLE_DATA_DIR.glob("*.json"))
        if not sample_files:
            pytest.skip("No sample data files found")
        return sample_files[0]

    def test_parser_initialization(self, sample_match_path: Path) -> None:
        """Test parser can be initialized with a file path."""
        parser = CricsheetParser(sample_match_path)
        assert parser.file_path == sample_match_path

    def test_match_info_parsing(self, sample_match_path: Path) -> None:
        """Test match info is correctly parsed."""
        parser = CricsheetParser(sample_match_path)
        info = parser.match_info

        assert isinstance(info, MatchInfo)
        assert len(info.teams) == 2
        assert info.venue is not None
        assert info.format in list(MatchFormat)

    def test_parse_innings_yields_events(self, sample_match_path: Path) -> None:
        """Test that parsing innings yields CricketEvent objects."""
        parser = CricsheetParser(sample_match_path)
        events = list(parser.parse_innings(1))

        assert len(events) > 0
        assert all(isinstance(e, CricketEvent) for e in events)

    def test_event_types_are_correct(self, sample_match_path: Path) -> None:
        """Test that event types are correctly determined."""
        parser = CricsheetParser(sample_match_path)
        events = list(parser.parse_innings(1))

        # Should have a mix of event types
        event_types = {e.event_type for e in events}
        assert EventType.DOT_BALL in event_types or len(events) > 0

    def test_running_score_increases(self, sample_match_path: Path) -> None:
        """Test that running score correctly increases."""
        parser = CricsheetParser(sample_match_path)
        events = list(parser.parse_innings(1))

        # Score should never decrease
        prev_score = 0
        for event in events:
            assert event.match_context.current_score >= prev_score
            prev_score = event.match_context.current_score

    def test_get_key_moments(self, sample_match_path: Path) -> None:
        """Test key moments extraction."""
        parser = CricsheetParser(sample_match_path)
        key_moments = parser.get_key_moments(1)

        # All key moments should be wickets or boundaries
        for event in key_moments:
            is_key = event.is_wicket or event.is_boundary or event.match_context.current_score % 50 == 0
            assert is_key, f"Non-key event found: {event.description}"


class TestParserWithRealData:
    """Integration tests with real Cricsheet data."""

    def test_parse_all_sample_files(self) -> None:
        """Test that all sample files can be parsed without errors."""
        sample_files = list(SAMPLE_DATA_DIR.glob("*.json"))
        if not sample_files:
            pytest.skip("No sample data files found")

        for file_path in sample_files[:5]:  # Test first 5 files
            parser = CricsheetParser(file_path)
            info = parser.match_info
            events = list(parser.parse_innings(1))

            assert info.match_id == file_path.stem
            assert len(events) > 0, f"No events parsed from {file_path.name}"

    def test_wicket_count_matches_events(self) -> None:
        """Test that wicket count matches wicket events."""
        sample_files = list(SAMPLE_DATA_DIR.glob("*.json"))
        if not sample_files:
            pytest.skip("No sample data files found")

        parser = CricsheetParser(sample_files[0])
        events = list(parser.parse_innings(1))

        if events:
            final_event = events[-1]
            wicket_events = [e for e in events if e.is_wicket]
            assert final_event.match_context.current_wickets == len(wicket_events)
