"""Base persona definitions for commentary generation."""

from dataclasses import dataclass, field
from enum import Enum


class CommentaryStyle(Enum):
    """Commentary style categories."""

    MINIMALIST = "minimalist"
    ANALYTICAL = "analytical"
    DRAMATIC = "dramatic"
    PHILOSOPHICAL = "philosophical"
    TECHNICAL = "technical"


@dataclass
class Persona:
    """A commentary persona with distinct style and voice.

    The minimalism_score is key: 0.0 = verbose paragraphs, 1.0 = "Gone."
    This controls how much the persona says - higher scores mean fewer words.
    """

    name: str
    style: CommentaryStyle
    vocabulary: list[str] = field(default_factory=lambda: [])
    cultural_context: str = ""
    emotion_range: dict[str, str] = field(default_factory=lambda: {})
    signature_phrases: list[str] = field(default_factory=lambda: [])
    minimalism_score: float = 0.5  # 0.0 = verbose, 1.0 = "Gone."
    languages: list[str] = field(default_factory=lambda: ["en"])

    # TTS configuration (for future use)
    voice_id: str | None = None
    speaking_rate: float = 1.0
    pitch: float = 0.0

    def get_phrase_for_emotion(self, emotion: str) -> str | None:
        """Get a signature phrase for a given emotion."""
        return self.emotion_range.get(emotion)

    @property
    def is_minimalist(self) -> bool:
        """Whether this persona favors minimal commentary."""
        return self.minimalism_score >= 0.7
