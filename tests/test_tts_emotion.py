"""Tests for cricket event → Svara emotion tag mapping."""

from suksham_vachak.parser import EventType
from suksham_vachak.tts.emotion import (
    DEFAULT_EMOTION,
    EMOTION_ANGER,
    EMOTION_CLEAR,
    EMOTION_FEAR,
    EMOTION_HAPPY,
    EMOTION_SURPRISE,
    get_emotion_tag,
    inject_emotion,
    is_tense_chase,
)


class TestDefaultEmotionMapping:
    """Tests for default event → emotion mapping (no match context)."""

    def test_wicket_is_surprise(self) -> None:
        assert get_emotion_tag(EventType.WICKET) == EMOTION_SURPRISE

    def test_six_is_happy(self) -> None:
        assert get_emotion_tag(EventType.BOUNDARY_SIX) == EMOTION_HAPPY

    def test_four_is_happy(self) -> None:
        assert get_emotion_tag(EventType.BOUNDARY_FOUR) == EMOTION_HAPPY

    def test_dot_ball_is_clear(self) -> None:
        assert get_emotion_tag(EventType.DOT_BALL) == EMOTION_CLEAR

    def test_wide_is_anger(self) -> None:
        assert get_emotion_tag(EventType.WIDE) == EMOTION_ANGER

    def test_no_ball_is_anger(self) -> None:
        assert get_emotion_tag(EventType.NO_BALL) == EMOTION_ANGER

    def test_single_is_clear(self) -> None:
        assert get_emotion_tag(EventType.SINGLE) == EMOTION_CLEAR

    def test_bye_is_clear(self) -> None:
        assert get_emotion_tag(EventType.BYE) == EMOTION_CLEAR


class TestContextualOverrides:
    """Tests for emotion overrides in tense match situations."""

    def test_wicket_in_tense_chase_is_fear(self) -> None:
        # Chasing 180, at 100/6, over 15 → tense (many wickets down)
        result = get_emotion_tag(
            EventType.WICKET,
            target=180,
            current_score=100,
            current_wickets=6,
            overs_completed=15.0,
        )
        assert result == EMOTION_FEAR

    def test_six_in_tense_chase_is_surprise(self) -> None:
        # Chasing 200, at 120/7, over 15 → tense
        result = get_emotion_tag(
            EventType.BOUNDARY_SIX,
            target=200,
            current_score=120,
            current_wickets=7,
            overs_completed=15.0,
        )
        assert result == EMOTION_SURPRISE

    def test_four_in_tense_chase_stays_happy(self) -> None:
        # FOUR doesn't have a contextual override
        result = get_emotion_tag(
            EventType.BOUNDARY_FOUR,
            target=200,
            current_score=120,
            current_wickets=7,
            overs_completed=15.0,
        )
        assert result == EMOTION_HAPPY

    def test_wicket_in_easy_chase_stays_surprise(self) -> None:
        # Chasing 150, at 140/2, over 15 → easy
        result = get_emotion_tag(
            EventType.WICKET,
            target=150,
            current_score=140,
            current_wickets=2,
            overs_completed=15.0,
        )
        assert result == EMOTION_SURPRISE


class TestIsTenseChase:
    """Tests for the is_tense_chase helper."""

    def test_first_innings_not_tense(self) -> None:
        assert is_tense_chase(target=None, current_score=100, current_wickets=3, overs_completed=10.0) is False

    def test_target_already_reached(self) -> None:
        assert is_tense_chase(target=150, current_score=160, current_wickets=3, overs_completed=18.0) is False

    def test_many_wickets_is_tense(self) -> None:
        assert is_tense_chase(target=180, current_score=100, current_wickets=6, overs_completed=12.0) is True

    def test_high_required_rate_is_tense(self) -> None:
        # Need 50 off 5 overs = 10 rpo
        assert is_tense_chase(target=200, current_score=150, current_wickets=3, overs_completed=15.0) is True

    def test_comfortable_chase_not_tense(self) -> None:
        # Need 20 off 5 overs = 4 rpo
        assert is_tense_chase(target=170, current_score=150, current_wickets=2, overs_completed=15.0) is False

    def test_last_over_always_tense(self) -> None:
        # Overs remaining <= 0
        assert is_tense_chase(target=180, current_score=170, current_wickets=3, overs_completed=20.0) is True


class TestInjectEmotion:
    """Tests for emotion tag injection."""

    def test_inject_happy(self) -> None:
        result = inject_emotion("What a shot!", EMOTION_HAPPY)
        assert result == "<happy> What a shot!"

    def test_inject_surprise(self) -> None:
        result = inject_emotion("He's gone!", EMOTION_SURPRISE)
        assert result == "<surprise> He's gone!"

    def test_inject_preserves_text(self) -> None:
        text = "शानदार छक्का!"
        result = inject_emotion(text, EMOTION_HAPPY)
        assert text in result

    def test_default_emotion_value(self) -> None:
        assert DEFAULT_EMOTION == EMOTION_CLEAR
