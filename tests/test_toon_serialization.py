"""Tests for TOON serialization module."""

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
    PartnershipContext,
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
from suksham_vachak.serialization import CRICKET_TOON_SCHEMA, decode, encode_rich_context

SAMPLE_DATA_DIR = Path(__file__).parent.parent / "data" / "cricsheet_sample"


@pytest.fixture
def sample_match_context() -> MatchContext:
    """Create a sample match context."""
    return MatchContext(
        match_id="test-123",
        teams=("India", "Australia"),
        venue="MCG",
        date="2024-01-15",
        format=MatchFormat.T20,
        innings=1,
        current_score=145,
        current_wickets=3,
        overs_completed=15.4,
        target=180,
        required_rate=8.75,
        current_rate=9.26,
    )


@pytest.fixture
def sample_event(sample_match_context: MatchContext) -> CricketEvent:
    """Create a sample cricket event."""
    return CricketEvent(
        event_id="test-event-1",
        event_type=EventType.BOUNDARY_FOUR,
        ball_number="15.4",
        batter="V Kohli",
        bowler="P Cummins",
        non_striker="R Sharma",
        runs_batter=4,
        runs_extras=0,
        runs_total=4,
        is_boundary=True,
        is_wicket=False,
        match_context=sample_match_context,
    )


@pytest.fixture
def sample_rich_context(sample_event: CricketEvent) -> RichContext:
    """Create a sample RichContext for testing."""
    return RichContext(
        event=sample_event,
        match=MatchSituation(
            batting_team="India",
            bowling_team="Australia",
            innings_number=2,
            total_runs=145,
            total_wickets=3,
            overs_completed=15.4,
            balls_remaining=26,
            target=180,
            runs_required=35,
            required_rate=8.08,
            current_run_rate=9.26,
            phase=MatchPhase.DEATH_OVERS,
            match_format="T20",
        ),
        batter=BatterContext(
            name="V Kohli",
            runs_scored=52,
            balls_faced=38,
            fours=6,
            sixes=1,
            strike_rate=136.84,
            is_on_strike=True,
            approaching_milestone="50",
        ),
        bowler=BowlerContext(
            name="P Cummins",
            overs_bowled=3.4,
            maidens=0,
            runs_conceded=32,
            wickets=1,
            economy=8.73,
            current_spell_overs=3.4,
            current_spell_wickets=1,
            current_spell_runs=32,
        ),
        partnership=PartnershipContext(
            runs=67,
            balls=48,
            batter1_name="V Kohli",
            batter1_contribution=52,
            batter2_name="R Sharma",
            batter2_contribution=15,
            run_rate=8.38,
        ),
        recent=RecentEvents(
            last_over_summary="4 1 0 1 2 4",
            wickets_in_last_5_overs=1,
            boundaries_in_last_5_overs=4,
            runs_in_last_5_overs=42,
            balls_since_last_boundary=0,
            balls_since_last_wicket=18,
        ),
        narrative=NarrativeState(
            current_storyline="Chase heating up in death overs",
            tension_level=0.75,
            momentum=MomentumState.BATTING_DOMINANT,
            key_subplot="Kohli anchoring the chase",
            dramatic_potential="Can India finish this off?",
            callbacks_available=["Kohli's 50", "Partnership milestone"],
        ),
        pressure=PressureLevel.INTENSE,
        pressure_score=0.72,
        suggested_tone="excited",
        suggested_length="medium",
    )


class TestCricketToonSchema:
    """Tests for the TOON schema constant."""

    def test_schema_includes_key_fields(self) -> None:
        """Test schema documentation includes key field abbreviations."""
        assert "M=match" in CRICKET_TOON_SCHEMA
        assert "B=batter" in CRICKET_TOON_SCHEMA
        assert "W=bowler" in CRICKET_TOON_SCHEMA
        assert "P=partnership" in CRICKET_TOON_SCHEMA

    def test_schema_includes_example(self) -> None:
        """Test schema includes a readable example."""
        assert "Example:" in CRICKET_TOON_SCHEMA
        assert "teams" in CRICKET_TOON_SCHEMA
        assert "score" in CRICKET_TOON_SCHEMA


class TestEncodeRichContext:
    """Tests for encode_rich_context function."""

    def test_encode_produces_string(self, sample_rich_context: RichContext) -> None:
        """Test encoding produces a non-empty string."""
        result = encode_rich_context(sample_rich_context)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_encode_is_decodable(self, sample_rich_context: RichContext) -> None:
        """Test encoded TOON can be decoded back."""
        encoded = encode_rich_context(sample_rich_context)
        decoded = decode(encoded)

        assert isinstance(decoded, dict)
        assert "M" in decoded  # Match
        assert "E" in decoded  # Event
        assert "B" in decoded  # Batter
        assert "W" in decoded  # Bowler (wicket-taker context)

    def test_encode_preserves_match_data(self, sample_rich_context: RichContext) -> None:
        """Test encoding preserves match situation data."""
        encoded = encode_rich_context(sample_rich_context)
        decoded = decode(encoded)

        match_data = decoded["M"]
        assert match_data["teams"] == ["India", "Australia"]
        assert match_data["score"] == "145/3"
        assert match_data["phase"] == "death_overs"
        assert match_data["target"] == 180

    def test_encode_preserves_event_data(self, sample_rich_context: RichContext) -> None:
        """Test encoding preserves current event data."""
        encoded = encode_rich_context(sample_rich_context)
        decoded = decode(encoded)

        event_data = decoded["E"]
        assert event_data["type"] == "boundary_four"
        # Ball number may be parsed as float (15.4) or string ("15.4")
        assert str(event_data["ball"]) == "15.4"
        assert event_data["batter"] == "V Kohli"
        assert event_data["bowler"] == "P Cummins"

    def test_encode_preserves_batter_data(self, sample_rich_context: RichContext) -> None:
        """Test encoding preserves batter context data."""
        encoded = encode_rich_context(sample_rich_context)
        decoded = decode(encoded)

        batter_data = decoded["B"]
        assert batter_data["name"] == "V Kohli"
        assert batter_data["runs"] == 52
        assert batter_data["balls"] == 38
        # Milestone may be parsed as int (50) or string ("50")
        assert str(batter_data["milestone"]) == "50"

    def test_encode_preserves_bowler_data(self, sample_rich_context: RichContext) -> None:
        """Test encoding preserves bowler context data."""
        encoded = encode_rich_context(sample_rich_context)
        decoded = decode(encoded)

        bowler_data = decoded["W"]
        assert bowler_data["name"] == "P Cummins"
        assert bowler_data["wkts"] == 1

    def test_encode_preserves_pressure_data(self, sample_rich_context: RichContext) -> None:
        """Test encoding preserves pressure data."""
        encoded = encode_rich_context(sample_rich_context)
        decoded = decode(encoded)

        pressure_data = decoded["P"]
        assert pressure_data["level"] == "intense"
        assert pressure_data["score"] == 0.72

    def test_encode_includes_tone_and_length(self, sample_rich_context: RichContext) -> None:
        """Test encoding includes tone and length suggestions."""
        encoded = encode_rich_context(sample_rich_context)
        decoded = decode(encoded)

        assert decoded["tone"] == "excited"
        assert decoded["length"] == "medium"


class TestRichContextToToon:
    """Tests for RichContext.to_toon() method."""

    def test_to_toon_returns_string(self, sample_rich_context: RichContext) -> None:
        """Test to_toon() method returns string."""
        result = sample_rich_context.to_toon()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_to_toon_matches_encode_function(self, sample_rich_context: RichContext) -> None:
        """Test to_toon() produces same output as encode_rich_context()."""
        method_result = sample_rich_context.to_toon()
        function_result = encode_rich_context(sample_rich_context)
        assert method_result == function_result


class TestTokenSavings:
    """Tests to verify TOON provides token savings.

    Note: Actual token savings are typically higher than character savings
    because tokenizers break up verbose natural language more than compact formats.
    """

    def test_toon_shorter_than_text(self, sample_rich_context: RichContext) -> None:
        """Test TOON output is shorter than plain text output."""
        toon_output = sample_rich_context.to_toon()
        text_output = sample_rich_context.to_prompt_context()

        # TOON should be shorter (character savings will be less than token savings)
        # Actual token savings are typically 40-50% due to tokenizer behavior
        assert len(toon_output) < len(text_output)

    def test_toon_fewer_words(self, sample_rich_context: RichContext) -> None:
        """Test TOON has fewer words than plain text."""
        toon_output = sample_rich_context.to_toon()
        text_output = sample_rich_context.to_prompt_context()

        toon_words = len(toon_output.split())
        text_words = len(text_output.split())

        # TOON should have significantly fewer words
        assert toon_words < text_words


class TestIntegrationWithRealData:
    """Integration tests using real Cricsheet data."""

    @pytest.fixture
    def sample_match_path(self) -> Path:
        """Get path to a sample match file."""
        sample_files = list(SAMPLE_DATA_DIR.glob("*.json"))
        if not sample_files:
            pytest.skip("No sample data files found")
        return sample_files[0]

    def test_encode_real_match_context(self, sample_match_path: Path) -> None:
        """Test encoding context from real match data."""
        parser = CricsheetParser(sample_match_path)
        builder = ContextBuilder(parser.match_info)

        events = list(parser.parse_innings(1))
        if not events:
            pytest.skip("No events in match")

        # Process a few events to build context
        for event in events[:10]:
            context = builder.build(event)

        # Encode to TOON
        toon_output = context.to_toon()

        # Should be valid TOON
        decoded = decode(toon_output)
        assert "M" in decoded
        assert "E" in decoded
        assert "B" in decoded
        assert "W" in decoded

    def test_toon_savings_on_real_data(self, sample_match_path: Path) -> None:
        """Test TOON provides savings on real match data."""
        parser = CricsheetParser(sample_match_path)
        builder = ContextBuilder(parser.match_info)

        events = list(parser.parse_innings(1))
        if len(events) < 20:
            pytest.skip("Not enough events in match")

        # Build context for multiple events and check savings
        total_toon_len = 0
        total_text_len = 0

        for event in events[:20]:
            context = builder.build(event)
            toon_output = context.to_toon()
            text_output = context.to_prompt_context()

            total_toon_len += len(toon_output)
            total_text_len += len(text_output)

        # TOON should be shorter than plain text (token savings are typically
        # higher than character savings due to tokenizer behavior)
        assert total_toon_len < total_text_len, "TOON should be more compact than text"


class TestEdgeCases:
    """Tests for edge cases in TOON encoding."""

    def test_encode_without_chase_context(self, sample_event: CricketEvent) -> None:
        """Test encoding when not chasing (no target)."""
        context = RichContext(
            event=sample_event,
            match=MatchSituation(
                batting_team="India",
                bowling_team="Australia",
                innings_number=1,
                total_runs=100,
                total_wickets=2,
                overs_completed=12.0,
                phase=MatchPhase.MIDDLE_OVERS,
                match_format="T20",
                # No target, runs_required, required_rate, balls_remaining
            ),
            batter=BatterContext(name="V Kohli", runs_scored=45, balls_faced=30, strike_rate=150.0),
            bowler=BowlerContext(name="P Cummins", overs_bowled=3.0, wickets=0, economy=8.0),
            partnership=PartnershipContext(runs=50, balls=40),
            recent=RecentEvents(),
            narrative=NarrativeState(
                current_storyline="India building",
                tension_level=0.4,
                momentum=MomentumState.BALANCED,
            ),
            pressure=PressureLevel.CALM,
            pressure_score=0.3,
            suggested_tone="neutral",
            suggested_length="medium",
        )

        encoded = encode_rich_context(context)
        decoded = decode(encoded)

        # Should not have chase-specific fields
        assert "target" not in decoded["M"]
        assert "RRR" not in decoded["M"]
        assert "need" not in decoded["M"]

    def test_encode_wicket_event(self, sample_match_context: MatchContext) -> None:
        """Test encoding a wicket event."""
        wicket_event = CricketEvent(
            event_id="test-wicket",
            event_type=EventType.WICKET,
            ball_number="10.3",
            batter="S Smith",
            bowler="J Bumrah",
            non_striker="M Labuschagne",
            runs_batter=0,
            runs_extras=0,
            runs_total=0,
            is_boundary=False,
            is_wicket=True,
            wicket_type="bowled",
            wicket_player="S Smith",
            match_context=sample_match_context,
        )

        context = RichContext(
            event=wicket_event,
            match=MatchSituation(
                batting_team="Australia",
                bowling_team="India",
                innings_number=1,
                total_runs=78,
                total_wickets=3,
                overs_completed=10.3,
                phase=MatchPhase.MIDDLE_OVERS,
                match_format="T20",
            ),
            batter=BatterContext(name="S Smith", runs_scored=23, balls_faced=18, strike_rate=127.78),
            bowler=BowlerContext(name="J Bumrah", overs_bowled=2.3, wickets=2, economy=6.0),
            partnership=PartnershipContext(runs=0, balls=0),
            recent=RecentEvents(),
            narrative=NarrativeState(
                current_storyline="Bumrah strikes again!",
                tension_level=0.8,
                momentum=MomentumState.BOWLING_DOMINANT,
            ),
            pressure=PressureLevel.TENSE,
            pressure_score=0.65,
            suggested_tone="dramatic",
            suggested_length="short",
        )

        encoded = encode_rich_context(context)
        decoded = decode(encoded)

        # Should have wicket info in event
        assert decoded["E"]["type"] == "wicket"
        assert decoded["E"]["wicket"] == "bowled"

    def test_encode_hat_trick_ball(self, sample_match_context: MatchContext) -> None:
        """Test encoding when bowler is on a hat-trick."""
        event = CricketEvent(
            event_id="test-hat-trick",
            event_type=EventType.DOT_BALL,
            ball_number="12.1",
            batter="M Wade",
            bowler="J Bumrah",
            non_striker="A Zampa",
            runs_batter=0,
            runs_extras=0,
            runs_total=0,
            is_boundary=False,
            is_wicket=False,
            match_context=sample_match_context,
        )

        context = RichContext(
            event=event,
            match=MatchSituation(
                batting_team="Australia",
                bowling_team="India",
                innings_number=1,
                total_runs=98,
                total_wickets=7,
                overs_completed=12.1,
                phase=MatchPhase.DEATH_OVERS,
                match_format="T20",
            ),
            batter=BatterContext(name="M Wade", runs_scored=0, balls_faced=1, strike_rate=0.0),
            bowler=BowlerContext(
                name="J Bumrah",
                overs_bowled=3.1,
                wickets=4,
                economy=5.5,
                is_on_hat_trick=True,
            ),
            partnership=PartnershipContext(runs=0, balls=1),
            recent=RecentEvents(),
            narrative=NarrativeState(
                current_storyline="Bumrah on a HAT-TRICK!",
                tension_level=0.95,
                momentum=MomentumState.BOWLING_DOMINANT,
            ),
            pressure=PressureLevel.CRITICAL,
            pressure_score=0.92,
            suggested_tone="tense",
            suggested_length="short",
        )

        encoded = encode_rich_context(context)
        decoded = decode(encoded)

        # Should have hat-trick flag
        assert decoded["W"]["hat_trick"] is True
