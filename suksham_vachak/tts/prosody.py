"""SSML prosody control for natural-sounding commentary."""

from dataclasses import dataclass
from typing import ClassVar

from suksham_vachak.parser import EventType
from suksham_vachak.personas import Persona


@dataclass
class ProsodySettings:
    """Prosody settings for SSML generation."""

    rate: str = "medium"  # x-slow, slow, medium, fast, x-fast, or percentage
    pitch: str = "medium"  # x-low, low, medium, high, x-high, or +/-percentage
    volume: str = "medium"  # silent, x-soft, soft, medium, loud, x-loud
    pause_before_ms: int = 0  # Pause before speech in milliseconds
    pause_after_ms: int = 0  # Pause after speech in milliseconds
    emphasis: str | None = None  # strong, moderate, reduced


# Prosody rules based on event type
# These create the "drama" in commentary - pauses before big moments, etc.
EVENT_PROSODY_RULES: dict[EventType, ProsodySettings] = {
    EventType.WICKET: ProsodySettings(
        rate="slow",
        pitch="+5%",
        pause_before_ms=500,  # THE KEY: dramatic pause before "Gone."
        pause_after_ms=800,
        emphasis="strong",
    ),
    EventType.BOUNDARY_SIX: ProsodySettings(
        rate="fast",
        pitch="+15%",
        volume="loud",
        pause_before_ms=200,
        pause_after_ms=500,
    ),
    EventType.BOUNDARY_FOUR: ProsodySettings(
        rate="medium",
        pitch="+10%",
        pause_after_ms=300,
    ),
    EventType.DOT_BALL: ProsodySettings(
        rate="medium",
        pitch="-5%",
        volume="soft",
    ),
    EventType.SINGLE: ProsodySettings(
        rate="medium",
        pitch="medium",
    ),
    EventType.DOUBLE: ProsodySettings(
        rate="medium",
        pitch="medium",
    ),
    EventType.TRIPLE: ProsodySettings(
        rate="medium",
        pitch="+5%",
    ),
    EventType.WIDE: ProsodySettings(
        rate="slow",
        pitch="-5%",
    ),
    EventType.NO_BALL: ProsodySettings(
        rate="medium",
        pitch="+5%",
    ),
}

# Default prosody for events not in the rules
DEFAULT_PROSODY = ProsodySettings()


class ProsodyController:
    """Controls SSML prosody for natural-sounding TTS output.

    Generates SSML markup with appropriate rate, pitch, volume, and pauses
    based on the event type and persona characteristics.
    """

    # Persona speaking rate modifiers (applied on top of event rules)
    PERSONA_RATE_MODIFIERS: ClassVar[dict[str, float]] = {
        # Minimalist personas speak slower, with more pauses
        "high_minimalism": 0.9,  # minimalism_score >= 0.7
        "medium_minimalism": 1.0,  # 0.3 <= minimalism_score < 0.7
        "low_minimalism": 1.1,  # minimalism_score < 0.3
    }

    def __init__(self) -> None:
        """Initialize the prosody controller."""
        pass

    def apply_prosody(
        self,
        text: str,
        persona: Persona,
        event_type: EventType,
    ) -> str:
        """Apply prosody settings to text and return SSML.

        Args:
            text: The commentary text to wrap in SSML.
            persona: The persona (affects speaking rate, pitch).
            event_type: The cricket event type (affects drama/excitement).

        Returns:
            SSML string with prosody markup.
        """
        if not text or not text.strip():
            # Empty text - return minimal SSML with just a pause
            return '<speak><break time="500ms"/></speak>'

        # Get base prosody from event type
        settings = EVENT_PROSODY_RULES.get(event_type, DEFAULT_PROSODY)

        # Adjust for persona characteristics
        adjusted_settings = self._adjust_for_persona(settings, persona)

        # Build SSML
        return self._build_ssml(text, adjusted_settings)

    def _adjust_for_persona(
        self,
        settings: ProsodySettings,
        persona: Persona,
    ) -> ProsodySettings:
        """Adjust prosody settings based on persona characteristics."""
        # Get persona's rate and pitch from their configuration
        persona_rate = persona.speaking_rate
        persona_pitch = persona.pitch

        # Determine rate modifier based on minimalism
        if persona.minimalism_score >= 0.7:
            rate_modifier = self.PERSONA_RATE_MODIFIERS["high_minimalism"]
        elif persona.minimalism_score >= 0.3:
            rate_modifier = self.PERSONA_RATE_MODIFIERS["medium_minimalism"]
        else:
            rate_modifier = self.PERSONA_RATE_MODIFIERS["low_minimalism"]

        # Combine event rate with persona rate
        # Event rate is qualitative, persona rate is a multiplier
        combined_rate = self._combine_rate(settings.rate, persona_rate * rate_modifier)

        # Combine pitch (event pitch + persona pitch offset)
        combined_pitch = self._combine_pitch(settings.pitch, persona_pitch)

        # High minimalism personas get longer pauses
        pause_multiplier = 1.5 if persona.is_minimalist else 1.0

        return ProsodySettings(
            rate=combined_rate,
            pitch=combined_pitch,
            volume=settings.volume,
            pause_before_ms=int(settings.pause_before_ms * pause_multiplier),
            pause_after_ms=int(settings.pause_after_ms * pause_multiplier),
            emphasis=settings.emphasis,
        )

    def _combine_rate(self, base_rate: str, multiplier: float) -> str:
        """Combine base rate string with a multiplier."""
        # Convert qualitative rates to percentages
        rate_values = {
            "x-slow": 50,
            "slow": 75,
            "medium": 100,
            "fast": 125,
            "x-fast": 150,
        }

        if base_rate in rate_values:
            base_pct = rate_values[base_rate]
        elif base_rate.endswith("%"):
            base_pct = int(base_rate[:-1])
        else:
            base_pct = 100

        final_pct = int(base_pct * multiplier)

        # Clamp to reasonable range
        final_pct = max(50, min(200, final_pct))

        return f"{final_pct}%"

    def _combine_pitch(self, base_pitch: str, offset: float) -> str:
        """Combine base pitch with persona offset."""
        # Convert qualitative pitches to semitone offsets
        pitch_values = {
            "x-low": -6,
            "low": -3,
            "medium": 0,
            "high": 3,
            "x-high": 6,
        }

        if base_pitch in pitch_values:
            base_st = pitch_values[base_pitch]
        elif base_pitch.startswith(("+", "-")) and base_pitch.endswith("%"):
            # Convert percentage to approximate semitones
            pct = int(base_pitch[:-1])
            base_st = pct // 5  # Rough conversion
        elif base_pitch.startswith(("+", "-")) and base_pitch.endswith("st"):
            base_st = int(base_pitch[:-2])
        else:
            base_st = 0

        final_st = base_st + offset

        # Clamp to reasonable range
        final_st = max(-12, min(12, final_st))

        if final_st >= 0:
            return f"+{final_st}st"
        else:
            return f"{final_st}st"

    def _build_ssml(self, text: str, settings: ProsodySettings) -> str:
        """Build SSML string from text and settings."""
        parts: list[str] = ["<speak>"]

        # Add pause before if specified
        if settings.pause_before_ms > 0:
            parts.append(f'<break time="{settings.pause_before_ms}ms"/>')

        # Build prosody tag
        prosody_attrs: list[str] = []
        if settings.rate != "medium":
            prosody_attrs.append(f'rate="{settings.rate}"')
        if settings.pitch != "medium":
            prosody_attrs.append(f'pitch="{settings.pitch}"')
        if settings.volume != "medium":
            prosody_attrs.append(f'volume="{settings.volume}"')

        # Wrap text in prosody and optionally emphasis
        if prosody_attrs:
            prosody_start = f"<prosody {' '.join(prosody_attrs)}>"
            prosody_end = "</prosody>"
        else:
            prosody_start = ""
            prosody_end = ""

        if settings.emphasis:
            emphasis_start = f'<emphasis level="{settings.emphasis}">'
            emphasis_end = "</emphasis>"
        else:
            emphasis_start = ""
            emphasis_end = ""

        parts.append(prosody_start)
        parts.append(emphasis_start)
        parts.append(self._escape_ssml(text))
        parts.append(emphasis_end)
        parts.append(prosody_end)

        # Add pause after if specified
        if settings.pause_after_ms > 0:
            parts.append(f'<break time="{settings.pause_after_ms}ms"/>')

        parts.append("</speak>")

        return "".join(parts)

    def _escape_ssml(self, text: str) -> str:
        """Escape special XML characters in text."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )


def generate_ssml(
    text: str,
    persona: Persona,
    event_type: EventType,
) -> str:
    """Convenience function to generate SSML for commentary.

    Args:
        text: Commentary text.
        persona: The persona generating the commentary.
        event_type: Type of cricket event.

    Returns:
        SSML string ready for TTS synthesis.
    """
    controller = ProsodyController()
    return controller.apply_prosody(text, persona, event_type)
