"""Tests for the commentary engine and personas."""

import pytest

from suksham_vachak.commentary import Commentary, CommentaryEngine
from suksham_vachak.parser import CricketEvent, EventType, MatchContext, MatchFormat
from suksham_vachak.personas import BENAUD, CommentaryStyle, Persona


@pytest.fixture
def sample_context() -> MatchContext:
    """Create a sample match context for testing."""
    return MatchContext(
        match_id="test-match",
        teams=("Australia", "England"),
        venue="MCG",
        date="2024-01-01",
        format=MatchFormat.TEST,
        innings=1,
        current_score=150,
        current_wickets=3,
        overs_completed=45.2,
    )


@pytest.fixture
def wicket_event(sample_context: MatchContext) -> CricketEvent:
    """Create a wicket event for testing."""
    return CricketEvent(
        event_id="test-wicket-1",
        event_type=EventType.WICKET,
        ball_number="45.2",
        batter="Joe Root",
        bowler="Pat Cummins",
        non_striker="Ben Stokes",
        runs_batter=0,
        runs_extras=0,
        runs_total=0,
        is_boundary=False,
        is_wicket=True,
        match_context=sample_context,
        wicket_type="caught",
        wicket_player="Joe Root",
        fielder="Steve Smith",
    )


@pytest.fixture
def boundary_four_event(sample_context: MatchContext) -> CricketEvent:
    """Create a boundary four event for testing."""
    return CricketEvent(
        event_id="test-four-1",
        event_type=EventType.BOUNDARY_FOUR,
        ball_number="45.3",
        batter="Joe Root",
        bowler="Pat Cummins",
        non_striker="Ben Stokes",
        runs_batter=4,
        runs_extras=0,
        runs_total=4,
        is_boundary=True,
        is_wicket=False,
        match_context=sample_context,
    )


@pytest.fixture
def boundary_six_event(sample_context: MatchContext) -> CricketEvent:
    """Create a boundary six event for testing."""
    return CricketEvent(
        event_id="test-six-1",
        event_type=EventType.BOUNDARY_SIX,
        ball_number="45.4",
        batter="Ben Stokes",
        bowler="Pat Cummins",
        non_striker="Joe Root",
        runs_batter=6,
        runs_extras=0,
        runs_total=6,
        is_boundary=True,
        is_wicket=False,
        match_context=sample_context,
    )


@pytest.fixture
def dot_ball_event(sample_context: MatchContext) -> CricketEvent:
    """Create a dot ball event for testing."""
    return CricketEvent(
        event_id="test-dot-1",
        event_type=EventType.DOT_BALL,
        ball_number="45.5",
        batter="Joe Root",
        bowler="Pat Cummins",
        non_striker="Ben Stokes",
        runs_batter=0,
        runs_extras=0,
        runs_total=0,
        is_boundary=False,
        is_wicket=False,
        match_context=sample_context,
    )


@pytest.fixture
def verbose_persona() -> Persona:
    """Create a verbose persona for testing."""
    return Persona(
        name="Test Verbose",
        style=CommentaryStyle.DRAMATIC,
        minimalism_score=0.2,
        signature_phrases=["What a moment!", "Incredible!"],
    )


class TestPersona:
    """Tests for Persona dataclass."""

    def test_benaud_exists(self) -> None:
        """Test BENAUD persona is properly defined."""
        assert BENAUD.name == "Richie Benaud"
        assert BENAUD.minimalism_score == 0.95
        assert BENAUD.style == CommentaryStyle.MINIMALIST

    def test_benaud_is_minimalist(self) -> None:
        """Test BENAUD is classified as minimalist."""
        assert BENAUD.is_minimalist is True

    def test_benaud_has_emotion_range(self) -> None:
        """Test BENAUD has emotion mappings."""
        assert BENAUD.emotion_range.get("wicket") == "Gone."
        assert BENAUD.emotion_range.get("boundary_six") == "Magnificent."

    def test_verbose_persona_not_minimalist(self, verbose_persona: Persona) -> None:
        """Test low minimalism score personas are not minimalist."""
        assert verbose_persona.is_minimalist is False


class TestCommentaryEngine:
    """Tests for CommentaryEngine class."""

    def test_engine_initialization(self) -> None:
        """Test engine can be initialized."""
        engine = CommentaryEngine()
        assert engine.default_language == "en"

    def test_generate_returns_commentary(self, wicket_event: CricketEvent) -> None:
        """Test generate returns a Commentary object."""
        engine = CommentaryEngine()
        result = engine.generate(wicket_event, BENAUD)

        assert isinstance(result, Commentary)
        assert result.event == wicket_event
        assert result.persona == BENAUD

    def test_commentary_has_text(self, wicket_event: CricketEvent) -> None:
        """Test generated commentary has text content."""
        engine = CommentaryEngine()
        result = engine.generate(wicket_event, BENAUD)

        assert result.text is not None


class TestBenaudTest:
    """The Benaud Test: minimal commentary for high-minimalism personas.

    Every persona implementation must pass these tests.
    The magic is in restraint - verbose AI commentary is worthless.
    """

    def test_wicket_produces_gone(self, wicket_event: CricketEvent) -> None:
        """THE BENAUD TEST: Wicket should produce 'Gone.' not a paragraph."""
        engine = CommentaryEngine()
        result = engine.generate(wicket_event, BENAUD)

        assert result.text == "Gone.", f"Expected 'Gone.' but got '{result.text}'"

    def test_boundary_four_is_minimal(self, boundary_four_event: CricketEvent) -> None:
        """Boundary four should be minimal: 'Four.' not a sentence."""
        engine = CommentaryEngine()
        result = engine.generate(boundary_four_event, BENAUD)

        assert result.text == "Four.", f"Expected 'Four.' but got '{result.text}'"

    def test_boundary_six_is_magnificent(self, boundary_six_event: CricketEvent) -> None:
        """Boundary six should be: 'Magnificent.' or similar."""
        engine = CommentaryEngine()
        result = engine.generate(boundary_six_event, BENAUD)

        assert result.text == "Magnificent.", f"Expected 'Magnificent.' but got '{result.text}'"

    def test_dot_ball_is_silence(self, dot_ball_event: CricketEvent) -> None:
        """Dot ball should be silence (empty string) for Benaud."""
        engine = CommentaryEngine()
        result = engine.generate(dot_ball_event, BENAUD)

        # Benaud's dot ball response is empty - letting the game breathe
        assert result.text == "", f"Expected silence but got '{result.text}'"

    def test_benaud_commentary_is_short(self, wicket_event: CricketEvent) -> None:
        """Benaud commentary should never exceed 20 characters."""
        engine = CommentaryEngine()
        result = engine.generate(wicket_event, BENAUD)

        assert len(result.text) <= 20, f"Too verbose: '{result.text}' ({len(result.text)} chars)"


class TestVerbosePersona:
    """Tests for verbose (low-minimalism) personas."""

    def test_verbose_wicket_is_descriptive(self, wicket_event: CricketEvent, verbose_persona: Persona) -> None:
        """Verbose personas should produce longer commentary."""
        engine = CommentaryEngine()
        result = engine.generate(wicket_event, verbose_persona)

        # Should be longer than Benaud's "Gone."
        assert len(result.text) > 10, f"Expected verbose output but got '{result.text}'"

    def test_verbose_contains_player_names(self, wicket_event: CricketEvent, verbose_persona: Persona) -> None:
        """Verbose commentary should include player names."""
        engine = CommentaryEngine()
        result = engine.generate(wicket_event, verbose_persona)

        # Should mention batter or bowler
        has_batter = "Joe Root" in result.text or "Root" in result.text
        has_bowler = "Pat Cummins" in result.text or "Cummins" in result.text
        assert has_batter or has_bowler, f"No player names in '{result.text}'"


class TestCommentaryForKeyMoments:
    """Tests for batch commentary generation."""

    def test_generate_for_key_moments(
        self,
        wicket_event: CricketEvent,
        boundary_four_event: CricketEvent,
        boundary_six_event: CricketEvent,
    ) -> None:
        """Test generating commentary for multiple events."""
        engine = CommentaryEngine()
        events = [wicket_event, boundary_four_event, boundary_six_event]

        results = engine.generate_for_key_moments(events, BENAUD)

        assert len(results) == 3
        assert all(isinstance(r, Commentary) for r in results)
        assert results[0].text == "Gone."
        assert results[1].text == "Four."
        assert results[2].text == "Magnificent."
