"""Cricket event to Svara TTS emotion tag mapping.

Maps cricket EventTypes to Svara emotion tags for expressive Hindi/Indian language TTS.
Supports contextual overrides for high-pressure match situations.
"""

from __future__ import annotations

from suksham_vachak.parser import EventType

# Svara emotion tags
EMOTION_HAPPY = "<happy>"
EMOTION_SURPRISE = "<surprise>"
EMOTION_ANGER = "<anger>"
EMOTION_FEAR = "<fear>"
EMOTION_CLEAR = "<clear>"

# Default event → emotion mapping
EVENT_EMOTION_MAP: dict[EventType, str] = {
    EventType.WICKET: EMOTION_SURPRISE,
    EventType.BOUNDARY_SIX: EMOTION_HAPPY,
    EventType.BOUNDARY_FOUR: EMOTION_HAPPY,
    EventType.DOT_BALL: EMOTION_CLEAR,
    EventType.SINGLE: EMOTION_CLEAR,
    EventType.DOUBLE: EMOTION_CLEAR,
    EventType.TRIPLE: EMOTION_CLEAR,
    EventType.WIDE: EMOTION_ANGER,
    EventType.NO_BALL: EMOTION_ANGER,
    EventType.BYE: EMOTION_CLEAR,
    EventType.LEG_BYE: EMOTION_CLEAR,
}

DEFAULT_EMOTION = EMOTION_CLEAR


def is_tense_chase(target: int | None, current_score: int, current_wickets: int, overs_completed: float) -> bool:
    """Determine if the match situation is a tense chase.

    A chase is tense when the batting team is chasing a target and either:
    - Required run rate is high (>8 rpo) with wickets in hand
    - Many wickets have fallen (>=6) regardless of rate

    Args:
        target: The target score (None if first innings).
        current_score: Current batting team score.
        current_wickets: Number of wickets fallen.
        overs_completed: Overs completed (e.g., 15.3).

    Returns:
        True if the match is in a tense chase situation.
    """
    if target is None:
        return False

    runs_needed = target - current_score
    if runs_needed <= 0:
        return False

    # Many wickets down in a chase is always tense
    if current_wickets >= 6:
        return True

    # High required run rate with wickets in hand
    overs_remaining = 20.0 - overs_completed  # Assume T20 for simplicity
    if overs_remaining <= 0:
        return True

    required_rate = runs_needed / overs_remaining
    return required_rate > 8.0


def get_emotion_tag(
    event_type: EventType,
    target: int | None = None,
    current_score: int = 0,
    current_wickets: int = 0,
    overs_completed: float = 0.0,
) -> str:
    """Get the Svara emotion tag for a cricket event.

    Uses contextual overrides for high-pressure situations:
    - WICKET in tense chase → <fear> instead of <surprise>
    - SIX in tight chase → <surprise> instead of <happy>

    Args:
        event_type: The type of cricket event.
        target: Chase target (None if first innings).
        current_score: Current score.
        current_wickets: Wickets fallen.
        overs_completed: Overs completed.

    Returns:
        Svara emotion tag string (e.g., '<happy>').
    """
    tense = is_tense_chase(target, current_score, current_wickets, overs_completed)

    if tense:
        if event_type == EventType.WICKET:
            return EMOTION_FEAR
        if event_type == EventType.BOUNDARY_SIX:
            return EMOTION_SURPRISE

    return EVENT_EMOTION_MAP.get(event_type, DEFAULT_EMOTION)


def inject_emotion(text: str, emotion_tag: str) -> str:
    """Prepend an emotion tag to text for Svara TTS.

    Args:
        text: The commentary text.
        emotion_tag: The Svara emotion tag (e.g., '<happy>').

    Returns:
        Text with emotion tag prepended.
    """
    return f"{emotion_tag} {text}"
