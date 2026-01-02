"""Integration tests for LLM-based commentary generation.

These tests make real API calls to Claude. They are marked as integration tests
and will be skipped if ANTHROPIC_API_KEY is not set.

Run with: pytest tests/test_llm_commentary.py -v -m integration
"""

import os

import pytest

from suksham_vachak.commentary import (
    ClaudeModel,
    CommentaryEngine,
    LLMClient,
    build_event_prompt,
    build_system_prompt,
)
from suksham_vachak.parser import CricketEvent, EventType, MatchContext, MatchFormat
from suksham_vachak.personas import BENAUD, GREIG

# Skip all tests in this module if no API key
pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set - skipping integration tests",
)


@pytest.fixture
def sample_context() -> MatchContext:
    """Create a sample match context for testing."""
    return MatchContext(
        match_id="test-match",
        teams=("India", "Australia"),
        venue="MCG",
        date="2024-01-01",
        format=MatchFormat.TEST,
        innings=1,
        current_score=245,
        current_wickets=4,
        overs_completed=67.3,
    )


@pytest.fixture
def wicket_event(sample_context: MatchContext) -> CricketEvent:
    """Create a wicket event for testing."""
    return CricketEvent(
        event_id="test-wicket-1",
        event_type=EventType.WICKET,
        ball_number="67.3",
        batter="Virat Kohli",
        bowler="Mitchell Starc",
        non_striker="Rohit Sharma",
        runs_batter=0,
        runs_extras=0,
        runs_total=0,
        is_boundary=False,
        is_wicket=True,
        match_context=sample_context,
        wicket_type="bowled",
        wicket_player="Virat Kohli",
        fielder=None,
    )


@pytest.fixture
def six_event(sample_context: MatchContext) -> CricketEvent:
    """Create a six event for testing."""
    return CricketEvent(
        event_id="test-six-1",
        event_type=EventType.BOUNDARY_SIX,
        ball_number="67.4",
        batter="Rohit Sharma",
        bowler="Mitchell Starc",
        non_striker="Virat Kohli",
        runs_batter=6,
        runs_extras=0,
        runs_total=6,
        is_boundary=True,
        is_wicket=False,
        match_context=sample_context,
    )


@pytest.fixture
def llm_client() -> LLMClient:
    """Create an LLM client using Haiku for cost efficiency."""
    return LLMClient(model=ClaudeModel.HAIKU)


@pytest.mark.integration
class TestLLMClient:
    """Tests for the LLMClient class."""

    def test_client_initialization(self, llm_client: LLMClient) -> None:
        """Test LLM client can be initialized."""
        assert llm_client.model == ClaudeModel.HAIKU

    def test_simple_completion(self, llm_client: LLMClient) -> None:
        """Test basic LLM completion works."""
        response = llm_client.complete(
            system_prompt="You are a helpful assistant. Reply in one word.",
            user_prompt="Say hello.",
            max_tokens=10,
        )

        assert response.text
        assert response.input_tokens > 0
        assert response.output_tokens > 0


@pytest.mark.integration
class TestPromptBuilding:
    """Tests for prompt building functions."""

    def test_system_prompt_for_benaud(self) -> None:
        """Test system prompt is built correctly for Benaud."""
        prompt = build_system_prompt(BENAUD)

        assert "Richie Benaud" in prompt
        assert "minimalist" in prompt.lower() or "Minimalist" in prompt
        assert "Gone." in prompt  # Should include signature phrase

    def test_system_prompt_for_greig(self) -> None:
        """Test system prompt is built correctly for Greig."""
        prompt = build_system_prompt(GREIG)

        assert "Tony Greig" in prompt
        assert "dramatic" in prompt.lower() or "Dramatic" in prompt

    def test_event_prompt_for_wicket(self, wicket_event: CricketEvent) -> None:
        """Test event prompt includes match context."""
        prompt = build_event_prompt(wicket_event, BENAUD)

        assert "India" in prompt
        assert "Australia" in prompt
        assert "WICKET" in prompt
        assert "Kohli" in prompt
        assert "Starc" in prompt


@pytest.mark.integration
class TestBenaudLLMGeneration:
    """Integration tests for Benaud persona with LLM.

    THE BENAUD TEST: Commentary should be minimal.
    """

    def test_wicket_is_brief(self, wicket_event: CricketEvent, llm_client: LLMClient) -> None:
        """Benaud + WICKET should produce <= 5 words."""
        engine = CommentaryEngine(use_llm=True, llm_client=llm_client)
        result = engine.generate(wicket_event, BENAUD)

        word_count = len(result.text.split()) if result.text else 0
        assert word_count <= 5, f"Too verbose ({word_count} words): '{result.text}'"
        assert result.used_llm is True

    def test_six_is_brief(self, six_event: CricketEvent, llm_client: LLMClient) -> None:
        """Benaud + SIX should produce <= 5 words."""
        engine = CommentaryEngine(use_llm=True, llm_client=llm_client)
        result = engine.generate(six_event, BENAUD)

        word_count = len(result.text.split()) if result.text else 0
        assert word_count <= 5, f"Too verbose ({word_count} words): '{result.text}'"


@pytest.mark.integration
class TestGreigLLMGeneration:
    """Integration tests for Greig persona with LLM.

    Greig should be more expressive and dramatic.
    """

    def test_six_is_enthusiastic(self, six_event: CricketEvent, llm_client: LLMClient) -> None:
        """Greig + SIX should be more verbose than Benaud."""
        engine = CommentaryEngine(use_llm=True, llm_client=llm_client)
        result = engine.generate(six_event, GREIG)

        word_count = len(result.text.split()) if result.text else 0
        # Greig should use more words (but still reasonable)
        assert word_count >= 3, f"Too brief for Greig ({word_count} words): '{result.text}'"
        assert word_count <= 25, f"Too verbose ({word_count} words): '{result.text}'"


@pytest.mark.integration
class TestDifferentPersonasSameEvent:
    """Test that different personas produce different styles for the same event."""

    def test_wicket_different_styles(self, wicket_event: CricketEvent, llm_client: LLMClient) -> None:
        """Same wicket event should produce different commentary for different personas."""
        engine = CommentaryEngine(use_llm=True, llm_client=llm_client)

        benaud_result = engine.generate(wicket_event, BENAUD)
        greig_result = engine.generate(wicket_event, GREIG)

        # Benaud should be shorter
        benaud_words = len(benaud_result.text.split()) if benaud_result.text else 0
        greig_words = len(greig_result.text.split()) if greig_result.text else 0

        assert benaud_words < greig_words, (
            f"Benaud ({benaud_words} words) should be more brief than Greig ({greig_words} words). "
            f"Benaud: '{benaud_result.text}' | Greig: '{greig_result.text}'"
        )


@pytest.mark.integration
class TestTokenUsage:
    """Test token usage tracking."""

    def test_tracks_token_usage(self, wicket_event: CricketEvent, llm_client: LLMClient) -> None:
        """Commentary should track token usage."""
        engine = CommentaryEngine(use_llm=True, llm_client=llm_client)
        result = engine.generate(wicket_event, BENAUD)

        assert result.llm_response is not None
        assert result.llm_response.input_tokens > 0
        assert result.llm_response.output_tokens > 0
        assert result.llm_response.total_tokens > 0


@pytest.mark.integration
class TestFallbackBehavior:
    """Test fallback to templates when LLM is disabled."""

    def test_template_fallback(self, wicket_event: CricketEvent) -> None:
        """When use_llm=False, should use templates."""
        engine = CommentaryEngine(use_llm=False)
        result = engine.generate(wicket_event, BENAUD)

        assert result.used_llm is False
        assert result.llm_response is None
        # Benaud's template response for wicket is "Gone."
        assert result.text == "Gone."
