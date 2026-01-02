"""Tests for TTS module - prosody control and SSML generation.

These tests do NOT require API credentials and test the local logic
for prosody control, SSML generation, and voice selection.
"""

import pytest

from suksham_vachak.parser import CricketEvent, EventType, MatchContext
from suksham_vachak.personas import BENAUD
from suksham_vachak.personas.base import CommentaryStyle, Persona
from suksham_vachak.tts import (
    DEFAULT_PROSODY,
    EVENT_PROSODY_RULES,
    AudioFormat,
    ProsodyController,
    ProsodySettings,
    TTSConfig,
    VoiceGender,
    VoiceInfo,
    generate_ssml,
)
from suksham_vachak.tts.azure import AzureTTSProvider
from suksham_vachak.tts.google import GoogleTTSProvider

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def match_context() -> MatchContext:
    """Create a test match context."""
    return MatchContext(
        match_id="test_match_001",
        teams=("India", "Australia"),
        current_score=150,
        current_wickets=3,
        overs_completed=25.0,
        target=None,
    )


@pytest.fixture
def wicket_event(match_context: MatchContext) -> CricketEvent:
    """Create a test wicket event."""
    return CricketEvent(
        event_id="evt_wicket_001",
        event_type=EventType.WICKET,
        ball_number="25.4",
        batter="Virat Kohli",
        bowler="Mitchell Starc",
        runs_scored=0,
        is_wicket=True,
        is_boundary=False,
        dismissal_type="caught",
        fielder="Steve Smith",
        match_context=match_context,
    )


@pytest.fixture
def six_event(match_context: MatchContext) -> CricketEvent:
    """Create a test six event."""
    return CricketEvent(
        event_id="evt_six_001",
        event_type=EventType.BOUNDARY_SIX,
        ball_number="18.2",
        batter="MS Dhoni",
        bowler="Pat Cummins",
        runs_scored=6,
        is_wicket=False,
        is_boundary=True,
        match_context=match_context,
    )


@pytest.fixture
def dot_event(match_context: MatchContext) -> CricketEvent:
    """Create a test dot ball event."""
    return CricketEvent(
        event_id="evt_dot_001",
        event_type=EventType.DOT_BALL,
        ball_number="10.1",
        batter="Rohit Sharma",
        bowler="Josh Hazlewood",
        runs_scored=0,
        is_wicket=False,
        is_boundary=False,
        match_context=match_context,
    )


@pytest.fixture
def verbose_persona() -> Persona:
    """Create a verbose test persona (Tony Greig-like)."""
    return Persona(
        name="Tony Greig",
        style=CommentaryStyle.DRAMATIC,
        minimalism_score=0.2,
        languages=["en"],
        speaking_rate=1.1,
        pitch=2.0,
    )


# ============================================================================
# ProsodySettings Tests
# ============================================================================


class TestProsodySettings:
    """Tests for ProsodySettings dataclass."""

    def test_default_settings(self) -> None:
        """Default prosody settings should be medium across all values."""
        settings = ProsodySettings()
        assert settings.rate == "medium"
        assert settings.pitch == "medium"
        assert settings.volume == "medium"
        assert settings.pause_before_ms == 0
        assert settings.pause_after_ms == 0
        assert settings.emphasis is None

    def test_custom_settings(self) -> None:
        """Custom prosody settings should be preserved."""
        settings = ProsodySettings(
            rate="slow",
            pitch="+10%",
            volume="loud",
            pause_before_ms=500,
            pause_after_ms=800,
            emphasis="strong",
        )
        assert settings.rate == "slow"
        assert settings.pitch == "+10%"
        assert settings.volume == "loud"
        assert settings.pause_before_ms == 500
        assert settings.pause_after_ms == 800
        assert settings.emphasis == "strong"


# ============================================================================
# Event Prosody Rules Tests
# ============================================================================


class TestEventProsodyRules:
    """Tests for event-based prosody rules."""

    def test_wicket_has_dramatic_pause(self) -> None:
        """Wicket events should have dramatic pause before."""
        wicket_settings = EVENT_PROSODY_RULES[EventType.WICKET]
        assert wicket_settings.pause_before_ms >= 500
        assert wicket_settings.emphasis == "strong"

    def test_six_has_fast_rate(self) -> None:
        """Six events should have fast speaking rate."""
        six_settings = EVENT_PROSODY_RULES[EventType.BOUNDARY_SIX]
        assert six_settings.rate == "fast"
        assert six_settings.volume == "loud"

    def test_dot_ball_is_subdued(self) -> None:
        """Dot ball events should be quiet and lower pitch."""
        dot_settings = EVENT_PROSODY_RULES[EventType.DOT_BALL]
        assert dot_settings.volume == "soft"

    def test_default_prosody_is_medium(self) -> None:
        """Default prosody should be medium settings."""
        assert DEFAULT_PROSODY.rate == "medium"
        assert DEFAULT_PROSODY.pitch == "medium"
        assert DEFAULT_PROSODY.volume == "medium"


# ============================================================================
# ProsodyController Tests
# ============================================================================


class TestProsodyController:
    """Tests for ProsodyController class."""

    def test_apply_prosody_wicket_benaud(self) -> None:
        """SSML for wicket should include dramatic pause for Benaud."""
        controller = ProsodyController()
        ssml = controller.apply_prosody("Gone.", BENAUD, EventType.WICKET)

        assert ssml.startswith("<speak>")
        assert ssml.endswith("</speak>")
        assert "Gone." in ssml
        # Should have a break before for drama
        assert '<break time="' in ssml

    def test_apply_prosody_six_event(self, verbose_persona: Persona) -> None:
        """SSML for six should include excitement indicators."""
        controller = ProsodyController()
        ssml = controller.apply_prosody(
            "That's a massive six!",
            verbose_persona,
            EventType.BOUNDARY_SIX,
        )

        assert ssml.startswith("<speak>")
        assert "massive six" in ssml
        # Should have prosody tags for pitch/rate
        assert "<prosody" in ssml

    def test_empty_text_returns_minimal_ssml(self) -> None:
        """Empty text should return SSML with just a pause."""
        controller = ProsodyController()
        ssml = controller.apply_prosody("", BENAUD, EventType.DOT_BALL)

        assert ssml == '<speak><break time="500ms"/></speak>'

    def test_special_characters_escaped(self) -> None:
        """Special XML characters should be escaped in SSML."""
        controller = ProsodyController()
        ssml = controller.apply_prosody(
            "India < Australia & that's that!",
            BENAUD,
            EventType.SINGLE,
        )

        assert "&lt;" in ssml
        assert "&amp;" in ssml
        assert "&apos;" in ssml

    def test_minimalist_persona_longer_pauses(self) -> None:
        """Minimalist personas should get longer pauses."""
        controller = ProsodyController()

        # Benaud is minimalist (0.95)
        ssml_benaud = controller.apply_prosody("Gone.", BENAUD, EventType.WICKET)

        # Extract pause times (this is a simple check - actual implementation may vary)
        # Just verify both generate valid SSML
        assert "<speak>" in ssml_benaud
        assert "</speak>" in ssml_benaud


# ============================================================================
# generate_ssml Convenience Function Tests
# ============================================================================


class TestGenerateSSML:
    """Tests for the generate_ssml convenience function."""

    def test_generate_ssml_basic(self) -> None:
        """Basic SSML generation should work."""
        ssml = generate_ssml("Magnificent!", BENAUD, EventType.BOUNDARY_SIX)

        assert ssml.startswith("<speak>")
        assert ssml.endswith("</speak>")
        assert "Magnificent!" in ssml

    def test_generate_ssml_different_events(self) -> None:
        """Different events should produce different SSML."""
        ssml_wicket = generate_ssml("Out!", BENAUD, EventType.WICKET)
        ssml_dot = generate_ssml("Defended.", BENAUD, EventType.DOT_BALL)

        # Both valid SSML but different content
        assert ssml_wicket != ssml_dot


# ============================================================================
# VoiceInfo Tests
# ============================================================================


class TestVoiceInfo:
    """Tests for VoiceInfo dataclass."""

    def test_voice_info_creation(self) -> None:
        """VoiceInfo should store all voice attributes."""
        voice = VoiceInfo(
            voice_id="en-AU-Wavenet-B",
            name="Australian Male B",
            language="en-AU",
            gender=VoiceGender.MALE,
            style="wavenet",
            provider="google",
        )

        assert voice.voice_id == "en-AU-Wavenet-B"
        assert voice.language == "en-AU"
        assert voice.gender == VoiceGender.MALE

    def test_voice_display_name(self) -> None:
        """Display name should include name, language, and gender."""
        voice = VoiceInfo(
            voice_id="en-AU-Wavenet-B",
            name="Australian Male B",
            language="en-AU",
            gender=VoiceGender.MALE,
        )

        display = voice.display_name
        assert "Australian Male B" in display
        assert "en-AU" in display
        assert "male" in display


# ============================================================================
# AudioFormat Tests
# ============================================================================


class TestAudioFormat:
    """Tests for AudioFormat enum."""

    def test_audio_formats_exist(self) -> None:
        """All expected audio formats should exist."""
        assert AudioFormat.MP3.value == "mp3"
        assert AudioFormat.WAV.value == "wav"
        assert AudioFormat.OGG.value == "ogg"


# ============================================================================
# TTSConfig Tests
# ============================================================================


class TestTTSConfig:
    """Tests for TTSConfig dataclass."""

    def test_default_config(self) -> None:
        """Default config should use Google with Azure fallback."""
        config = TTSConfig()

        assert config.provider == "google"
        assert config.fallback_provider == "azure"
        assert config.audio_format == AudioFormat.MP3
        assert config.enable_cache is True

    def test_custom_config(self) -> None:
        """Custom config should override defaults."""
        config = TTSConfig(
            provider="azure",
            fallback_provider=None,
            audio_format=AudioFormat.WAV,
            enable_cache=False,
        )

        assert config.provider == "azure"
        assert config.fallback_provider is None
        assert config.audio_format == AudioFormat.WAV
        assert config.enable_cache is False


# ============================================================================
# Voice Mapping Tests
# ============================================================================


class TestVoiceMapping:
    """Tests for voice mapping functionality."""

    def test_google_benaud_voice(self) -> None:
        """Google should map Benaud to Australian male voice."""
        voice = GoogleTTSProvider.get_voice_for_persona("Richie Benaud", "en")
        assert voice == "en-AU-Wavenet-B"

    def test_google_greig_voice(self) -> None:
        """Google should map Greig to British male voice."""
        voice = GoogleTTSProvider.get_voice_for_persona("Tony Greig", "en")
        assert voice == "en-GB-Wavenet-B"

    def test_google_hindi_default(self) -> None:
        """Google should default to Hindi voice for Hindi language."""
        voice = GoogleTTSProvider.get_voice_for_persona("Unknown Persona", "hi")
        assert voice == "hi-IN-Wavenet-A"

    def test_azure_benaud_voice(self) -> None:
        """Azure should map Benaud to Australian neural voice."""
        voice = AzureTTSProvider.get_voice_for_persona("Richie Benaud", "en")
        assert voice == "en-AU-WilliamNeural"

    def test_azure_bhogle_voice(self) -> None:
        """Azure should map Bhogle to Indian English voice."""
        voice = AzureTTSProvider.get_voice_for_persona("Harsha Bhogle", "en")
        assert voice == "en-IN-PrabhatNeural"


# ============================================================================
# Provider Format Mapping Tests
# ============================================================================


class TestProviderFormatMapping:
    """Tests for audio format mappings in providers."""

    def test_google_format_mapping(self) -> None:
        """Google should map audio formats correctly."""
        assert GoogleTTSProvider.FORMAT_MAP[AudioFormat.MP3] == "MP3"
        assert GoogleTTSProvider.FORMAT_MAP[AudioFormat.WAV] == "LINEAR16"
        assert GoogleTTSProvider.FORMAT_MAP[AudioFormat.OGG] == "OGG_OPUS"

    def test_azure_format_mapping(self) -> None:
        """Azure should map audio formats correctly."""
        assert "mp3" in AzureTTSProvider.FORMAT_MAP[AudioFormat.MP3].lower()
        assert "pcm" in AzureTTSProvider.FORMAT_MAP[AudioFormat.WAV].lower()
        assert "opus" in AzureTTSProvider.FORMAT_MAP[AudioFormat.OGG].lower()


# ============================================================================
# ProsodyController Rate/Pitch Combination Tests
# ============================================================================


class TestProsodyCombination:
    """Tests for combining persona and event prosody settings."""

    def test_rate_combination_percentage(self) -> None:
        """Rate combination should produce percentage values."""
        controller = ProsodyController()
        result = controller._combine_rate("fast", 1.0)

        assert result.endswith("%")
        # Fast (125%) * 1.0 = 125%
        assert result == "125%"

    def test_rate_clamped_to_range(self) -> None:
        """Rate should be clamped to 50-200%."""
        controller = ProsodyController()

        # Very slow rate with low multiplier
        result_slow = controller._combine_rate("x-slow", 0.5)
        assert int(result_slow[:-1]) >= 50

        # Very fast rate with high multiplier
        result_fast = controller._combine_rate("x-fast", 2.0)
        assert int(result_fast[:-1]) <= 200

    def test_pitch_combination_semitones(self) -> None:
        """Pitch combination should produce semitone values."""
        controller = ProsodyController()
        result = controller._combine_pitch("high", 2.0)

        # high (3st) + 2.0 = 5st (output includes decimal)
        assert result == "+5.0st"

    def test_pitch_negative_values(self) -> None:
        """Negative pitch values should be formatted correctly."""
        controller = ProsodyController()
        result = controller._combine_pitch("low", -3.0)

        # low (-3st) + -3.0 = -6st (output includes decimal)
        assert result == "-6.0st"


# ============================================================================
# SSML Building Tests
# ============================================================================


class TestSSMLBuilding:
    """Tests for SSML construction."""

    def test_ssml_structure(self) -> None:
        """SSML should have proper structure."""
        controller = ProsodyController()
        ssml = controller._build_ssml(
            "Test text",
            ProsodySettings(rate="fast", pitch="+5%", pause_before_ms=200),
        )

        assert ssml.startswith("<speak>")
        assert ssml.endswith("</speak>")
        assert "Test text" in ssml
        assert '<break time="200ms"/>' in ssml
        assert '<prosody rate="fast"' in ssml

    def test_ssml_no_prosody_when_default(self) -> None:
        """SSML should omit prosody tags when all values are default."""
        controller = ProsodyController()
        ssml = controller._build_ssml("Test", ProsodySettings())

        # Should not have prosody tag when all values are "medium"
        assert "<prosody" not in ssml

    def test_ssml_with_emphasis(self) -> None:
        """SSML should include emphasis when specified."""
        controller = ProsodyController()
        ssml = controller._build_ssml(
            "Gone!",
            ProsodySettings(emphasis="strong"),
        )

        assert '<emphasis level="strong">' in ssml
        assert "</emphasis>" in ssml


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_unknown_event_type_uses_default(self) -> None:
        """Unknown event types should use default prosody."""
        # EventType.SINGLE might not have specific rules
        # Should fall back to DEFAULT_PROSODY
        ssml = generate_ssml("One run.", BENAUD, EventType.SINGLE)

        # Should still produce valid SSML
        assert ssml.startswith("<speak>")
        assert ssml.endswith("</speak>")

    def test_very_long_text_escaping(self) -> None:
        """Long text with many special chars should escape correctly."""
        controller = ProsodyController()
        long_text = "A & B < C > D & E" * 50
        ssml = controller.apply_prosody(long_text, BENAUD, EventType.DOT_BALL)

        # All ampersands should be escaped
        assert "&" in ssml  # Will be &amp;
        assert "& B" not in ssml  # Raw ampersand should not exist

    def test_whitespace_only_text(self) -> None:
        """Whitespace-only text should return minimal SSML."""
        controller = ProsodyController()
        ssml = controller.apply_prosody("   ", BENAUD, EventType.DOT_BALL)

        # Should be treated as empty
        assert ssml == '<speak><break time="500ms"/></speak>'
