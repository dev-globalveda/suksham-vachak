"""Tests for the context module."""

from pathlib import Path

import pytest

from suksham_vachak.context import (
    BatterContext,
    BowlerContext,
    ContextBuilder,
    MatchPhase,
    MatchSituation,
    MomentumState,
    NarrativeState,
    NarrativeTracker,
    PartnershipContext,
    PressureCalculator,
    PressureLevel,
    RecentEvents,
    RichContext,
)
from suksham_vachak.parser import (
    CricketEvent,
    CricsheetParser,
    EventType,
    MatchContext,
    MatchFormat,
)

SAMPLE_DATA_DIR = Path(__file__).parent.parent / "data" / "cricsheet_sample"


class TestMatchPhase:
    """Tests for MatchPhase enum."""

    def test_limited_overs_phases(self) -> None:
        """Test limited overs phases exist."""
        assert MatchPhase.POWERPLAY.value == "powerplay"
        assert MatchPhase.MIDDLE_OVERS.value == "middle_overs"
        assert MatchPhase.DEATH_OVERS.value == "death_overs"

    def test_test_match_phases(self) -> None:
        """Test test match phases exist."""
        assert MatchPhase.FIRST_SESSION.value == "first_session"
        assert MatchPhase.SECOND_SESSION.value == "second_session"
        assert MatchPhase.THIRD_SESSION.value == "third_session"


class TestPressureLevel:
    """Tests for PressureLevel enum."""

    def test_all_levels_defined(self) -> None:
        """Verify all pressure levels."""
        expected = ["CALM", "BUILDING", "TENSE", "INTENSE", "CRITICAL"]
        for level in expected:
            assert hasattr(PressureLevel, level)


class TestMomentumState:
    """Tests for MomentumState enum."""

    def test_all_states_defined(self) -> None:
        """Verify all momentum states."""
        expected = [
            "BATTING_DOMINANT",
            "BOWLING_DOMINANT",
            "BALANCED",
            "MOMENTUM_SHIFT",
            "UNCERTAIN",
        ]
        for state in expected:
            assert hasattr(MomentumState, state)


class TestBatterContext:
    """Tests for BatterContext dataclass."""

    def test_is_new_batter(self) -> None:
        """Test new batter detection."""
        batter = BatterContext(name="Test", balls_faced=5)
        assert batter.is_new_batter is True

        settled = BatterContext(name="Test", balls_faced=15)
        assert settled.is_new_batter is False

    def test_is_settled(self) -> None:
        """Test settled batter detection."""
        # Not settled (too few balls)
        batter1 = BatterContext(name="Test", balls_faced=15, runs_scored=20, strike_rate=133.0)
        assert batter1.is_settled is False

        # Settled (20+ balls, good SR)
        batter2 = BatterContext(name="Test", balls_faced=25, runs_scored=30, strike_rate=120.0)
        assert batter2.is_settled is True

        # Not settled (low SR)
        batter3 = BatterContext(name="Test", balls_faced=25, runs_scored=10, strike_rate=40.0)
        assert batter3.is_settled is False

    def test_is_struggling(self) -> None:
        """Test struggling batter detection."""
        # Struggling (low SR after 15+ balls)
        batter = BatterContext(name="Test", balls_faced=20, runs_scored=8, strike_rate=40.0)
        assert batter.is_struggling is True

        # Not struggling (good SR)
        batter2 = BatterContext(name="Test", balls_faced=20, runs_scored=20, strike_rate=100.0)
        assert batter2.is_struggling is False


class TestBowlerContext:
    """Tests for BowlerContext dataclass."""

    def test_is_bowling_well(self) -> None:
        """Test good bowling detection."""
        # Good economy
        bowler1 = BowlerContext(name="Test", economy=5.0, overs_bowled=4.0)
        assert bowler1.is_bowling_well is True

        # Multiple wickets
        bowler2 = BowlerContext(name="Test", economy=8.0, current_spell_wickets=2)
        assert bowler2.is_bowling_well is True

    def test_is_expensive(self) -> None:
        """Test expensive bowling detection."""
        # Expensive (high economy after 2+ overs)
        bowler = BowlerContext(name="Test", economy=10.0, overs_bowled=3.0)
        assert bowler.is_expensive is True

        # Not expensive enough overs
        bowler2 = BowlerContext(name="Test", economy=10.0, overs_bowled=1.0)
        assert bowler2.is_expensive is False


class TestPartnershipContext:
    """Tests for PartnershipContext dataclass."""

    def test_is_significant(self) -> None:
        """Test significant partnership detection."""
        partnership = PartnershipContext(runs=55)
        assert partnership.is_significant is True

        small = PartnershipContext(runs=30)
        assert small.is_significant is False

    def test_is_century_stand(self) -> None:
        """Test century stand detection."""
        partnership = PartnershipContext(runs=105)
        assert partnership.is_century_stand is True

        not_yet = PartnershipContext(runs=95)
        assert not_yet.is_century_stand is False


class TestRecentEvents:
    """Tests for RecentEvents dataclass."""

    def test_is_quiet_period(self) -> None:
        """Test quiet period detection."""
        quiet = RecentEvents(
            balls_since_last_boundary=25,
            balls_since_last_wicket=40,
        )
        assert quiet.is_quiet_period is True

        active = RecentEvents(
            balls_since_last_boundary=10,
            balls_since_last_wicket=5,
        )
        assert active.is_quiet_period is False

    def test_is_action_packed(self) -> None:
        """Test action-packed period detection."""
        action = RecentEvents(boundaries_in_last_5_overs=5)
        assert action.is_action_packed is True

        wickets = RecentEvents(wickets_in_last_5_overs=3)
        assert wickets.is_action_packed is True

        calm = RecentEvents(boundaries_in_last_5_overs=2, wickets_in_last_5_overs=1)
        assert calm.is_action_packed is False


class TestMatchSituation:
    """Tests for MatchSituation dataclass."""

    def test_score_string(self) -> None:
        """Test score string formatting."""
        match = MatchSituation(
            batting_team="India",
            bowling_team="Australia",
            innings_number=1,
            total_runs=156,
            total_wickets=4,
            overs_completed=18.2,
        )
        assert match.score_string == "156/4 (18.2)"

    def test_is_chase(self) -> None:
        """Test chase detection."""
        # First innings
        match1 = MatchSituation(
            batting_team="India",
            bowling_team="Australia",
            innings_number=1,
            total_runs=100,
            total_wickets=3,
            overs_completed=15.0,
            target=None,
        )
        assert match1.is_chase is False

        # Second innings with target
        match2 = MatchSituation(
            batting_team="Australia",
            bowling_team="India",
            innings_number=2,
            total_runs=80,
            total_wickets=2,
            overs_completed=12.0,
            target=165,
        )
        assert match2.is_chase is True

    def test_is_close_chase(self) -> None:
        """Test close chase detection."""
        close = MatchSituation(
            batting_team="Australia",
            bowling_team="India",
            innings_number=2,
            total_runs=100,
            total_wickets=3,
            overs_completed=15.0,
            target=160,
            required_rate=8.0,
            current_run_rate=6.67,
        )
        assert close.is_close_chase is True

        not_close = MatchSituation(
            batting_team="Australia",
            bowling_team="India",
            innings_number=2,
            total_runs=100,
            total_wickets=3,
            overs_completed=15.0,
            target=200,
            required_rate=12.0,
            current_run_rate=6.67,
        )
        assert not_close.is_close_chase is False

    def test_wickets_in_hand(self) -> None:
        """Test wickets in hand calculation."""
        match = MatchSituation(
            batting_team="India",
            bowling_team="Australia",
            innings_number=1,
            total_runs=150,
            total_wickets=6,
            overs_completed=18.0,
        )
        assert match.wickets_in_hand == 4


class TestNarrativeState:
    """Tests for NarrativeState dataclass."""

    def test_to_prompt_context(self) -> None:
        """Test prompt context generation."""
        narrative = NarrativeState(
            current_storyline="Batters on top",
            tension_level=0.8,
            momentum=MomentumState.BATTING_DOMINANT,
            key_subplot="Kohli approaching 100",
            dramatic_potential="Century beckons",
        )
        context = narrative.to_prompt_context()

        assert "Batters on top" in context
        assert "Kohli approaching 100" in context
        assert "batting_dominant" in context
        assert "High" in context  # High tension
        assert "Century beckons" in context


class TestPressureCalculator:
    """Tests for PressureCalculator class."""

    @pytest.fixture
    def calculator(self) -> PressureCalculator:
        """Create a pressure calculator."""
        return PressureCalculator()

    def test_calm_situation(self, calculator: PressureCalculator) -> None:
        """Test calm situation detection."""
        match = MatchSituation(
            batting_team="India",
            bowling_team="Australia",
            innings_number=1,
            total_runs=80,
            total_wickets=1,
            overs_completed=12.0,
            phase=MatchPhase.MIDDLE_OVERS,
        )
        level, score = calculator.calculate(match)
        assert level in [PressureLevel.CALM, PressureLevel.BUILDING]
        assert score < 0.5

    def test_death_overs_pressure(self, calculator: PressureCalculator) -> None:
        """Test death overs increase pressure."""
        match = MatchSituation(
            batting_team="India",
            bowling_team="Australia",
            innings_number=2,
            total_runs=140,
            total_wickets=4,
            overs_completed=18.0,
            phase=MatchPhase.DEATH_OVERS,
            target=180,
            runs_required=40,
            required_rate=10.0,
            current_run_rate=7.78,
            balls_remaining=12,
        )
        level, score = calculator.calculate(match)
        assert score > 0.5
        assert level in [PressureLevel.TENSE, PressureLevel.INTENSE, PressureLevel.CRITICAL]

    def test_recent_wickets_increase_pressure(self, calculator: PressureCalculator) -> None:
        """Test recent wickets increase pressure."""
        match = MatchSituation(
            batting_team="India",
            bowling_team="Australia",
            innings_number=1,
            total_runs=50,
            total_wickets=4,
            overs_completed=10.0,
            phase=MatchPhase.MIDDLE_OVERS,
        )
        level, score = calculator.calculate(match, wickets_in_last_5_overs=3)
        assert score > 0.4

    def test_pressure_description(self, calculator: PressureCalculator) -> None:
        """Test pressure description generation."""
        desc = calculator.get_pressure_description(PressureLevel.CRITICAL, 0.9)
        assert "knife's edge" in desc.lower() or "change everything" in desc.lower()


class TestNarrativeTracker:
    """Tests for NarrativeTracker class."""

    @pytest.fixture
    def tracker(self) -> NarrativeTracker:
        """Create a narrative tracker."""
        return NarrativeTracker()

    @pytest.fixture
    def sample_event(self) -> CricketEvent:
        """Create a sample event."""
        ctx = MatchContext(
            match_id="test",
            teams=("India", "Australia"),
            venue="MCG",
            date="2024-01-01",
            format=MatchFormat.T20,
            innings=1,
            current_score=100,
            current_wickets=3,
            overs_completed=12.0,
        )
        return CricketEvent(
            event_id="test-1",
            event_type=EventType.BOUNDARY_FOUR,
            ball_number="12.1",
            batter="V Kohli",
            bowler="P Cummins",
            non_striker="R Sharma",
            runs_batter=4,
            runs_extras=0,
            runs_total=4,
            is_boundary=True,
            is_wicket=False,
            match_context=ctx,
        )

    def test_update_returns_narrative_state(self, tracker: NarrativeTracker, sample_event: CricketEvent) -> None:
        """Test update returns NarrativeState."""
        state = tracker.update(
            event=sample_event,
            batter_runs=45,
            batter_balls=30,
            bowler_wickets=1,
            partnership_runs=60,
        )
        assert isinstance(state, NarrativeState)
        assert state.current_storyline != ""

    def test_milestone_subplot_detection(self, tracker: NarrativeTracker, sample_event: CricketEvent) -> None:
        """Test milestone subplot detection."""
        state = tracker.update(
            event=sample_event,
            batter_runs=47,  # Close to 50
            batter_balls=35,
            bowler_wickets=0,
            partnership_runs=30,
        )
        # Should detect approaching 50
        assert state.key_subplot is not None or len(tracker.active_subplots) > 0


class TestContextBuilder:
    """Tests for ContextBuilder class."""

    @pytest.fixture
    def sample_match_path(self) -> Path:
        """Get path to a sample match file."""
        sample_files = list(SAMPLE_DATA_DIR.glob("*.json"))
        if not sample_files:
            pytest.skip("No sample data files found")
        return sample_files[0]

    def test_build_returns_rich_context(self, sample_match_path: Path) -> None:
        """Test build returns RichContext."""
        parser = CricsheetParser(sample_match_path)
        builder = ContextBuilder(parser.match_info)

        events = list(parser.parse_innings(1))
        if not events:
            pytest.skip("No events in match")

        context = builder.build(events[0])

        assert isinstance(context, RichContext)
        assert context.event == events[0]
        assert isinstance(context.match, MatchSituation)
        assert isinstance(context.batter, BatterContext)
        assert isinstance(context.bowler, BowlerContext)
        assert isinstance(context.partnership, PartnershipContext)
        assert isinstance(context.recent, RecentEvents)
        assert isinstance(context.narrative, NarrativeState)
        assert isinstance(context.pressure, PressureLevel)

    def test_context_accumulates_correctly(self, sample_match_path: Path) -> None:
        """Test context accumulates over multiple events."""
        parser = CricsheetParser(sample_match_path)
        builder = ContextBuilder(parser.match_info)

        events = list(parser.parse_innings(1))[:20]  # First 20 balls
        if not events:
            pytest.skip("No events in match")

        prev_runs = 0
        for event in events:
            context = builder.build(event)
            # Score should never decrease
            assert context.match.total_runs >= prev_runs
            prev_runs = context.match.total_runs

    def test_to_prompt_context(self, sample_match_path: Path) -> None:
        """Test to_prompt_context generates readable output."""
        parser = CricsheetParser(sample_match_path)
        builder = ContextBuilder(parser.match_info)

        events = list(parser.parse_innings(1))
        if not events:
            pytest.skip("No events in match")

        context = builder.build(events[5])  # Get some context built up
        prompt_text = context.to_prompt_context()

        assert "MATCH SITUATION" in prompt_text
        assert "BATTER" in prompt_text
        assert "BOWLER" in prompt_text
        assert "NARRATIVE" in prompt_text
        assert "PRESSURE" in prompt_text

    def test_phase_detection_t20(self, sample_match_path: Path) -> None:
        """Test phase detection for T20."""
        parser = CricsheetParser(sample_match_path)

        # Skip if not T20
        if parser.match_info.format != MatchFormat.T20:
            pytest.skip("Need T20 match for this test")

        builder = ContextBuilder(parser.match_info)
        events = list(parser.parse_innings(1))

        if len(events) < 36:  # Need at least 6 overs
            pytest.skip("Not enough events")

        # First 36 balls = powerplay
        context = builder.build(events[30])
        assert context.match.phase == MatchPhase.POWERPLAY

    def test_new_innings_resets_state(self, sample_match_path: Path) -> None:
        """Test new innings resets builder state."""
        parser = CricsheetParser(sample_match_path)
        builder = ContextBuilder(parser.match_info)

        # Build context for first innings
        events = list(parser.parse_innings(1))[:10]
        for event in events:
            builder.build(event)

        # Reset for second innings
        builder.new_innings(2)

        # State should be reset
        assert builder._total_runs == 0
        assert builder._total_wickets == 0
        assert builder._balls_in_innings == 0


class TestContextIntegration:
    """Integration tests for the context module."""

    def test_full_innings_processing(self) -> None:
        """Test processing a full innings."""
        sample_files = list(SAMPLE_DATA_DIR.glob("*.json"))
        if not sample_files:
            pytest.skip("No sample data files found")

        parser = CricsheetParser(sample_files[0])
        builder = ContextBuilder(parser.match_info)

        events = list(parser.parse_innings(1))
        if not events:
            pytest.skip("No events in match")

        # Process all events
        final_context = None
        for event in events:
            final_context = builder.build(event)

        # Verify final state
        assert final_context is not None
        assert final_context.match.total_runs > 0
        assert final_context.match.overs_completed > 0

    def test_key_moment_context(self) -> None:
        """Test context for key moments (wickets, boundaries)."""
        sample_files = list(SAMPLE_DATA_DIR.glob("*.json"))
        if not sample_files:
            pytest.skip("No sample data files found")

        parser = CricsheetParser(sample_files[0])
        builder = ContextBuilder(parser.match_info)

        key_moments = parser.get_key_moments(1)
        if not key_moments:
            pytest.skip("No key moments in match")

        # Process events up to first key moment
        events = list(parser.parse_innings(1))
        for event in events:
            context = builder.build(event)
            if event.is_wicket:
                # Wickets should suggest dramatic tone
                assert context.suggested_tone in ["dramatic", "tense"]
                break
            elif event.is_boundary:
                # Boundaries should be excited/enthusiastic
                assert context.suggested_tone in ["excited", "enthusiastic"]
