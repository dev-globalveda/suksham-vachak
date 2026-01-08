"""Text-to-Speech module for Suksham Vachak.

This module provides TTS capabilities with prosody control for
natural-sounding cricket commentary.

Providers:
- Google Cloud TTS: High-quality WaveNet voices
- Azure Cognitive Services: Neural voices
- ElevenLabs: Premium voice cloning and synthesis

Example usage:
    from suksham_vachak.tts import TTSEngine, TTSConfig, AudioFormat
    from suksham_vachak.personas import BENAUD

    # Create engine with default config
    engine = TTSEngine()

    # Or with custom config
    config = TTSConfig(
        provider="google",
        audio_format=AudioFormat.MP3,
        enable_cache=True,
    )
    engine = TTSEngine(config)

    # Synthesize commentary
    segment = engine.synthesize_commentary(commentary, BENAUD)

    # Save to file
    engine.save_audio(segment, "output/commentary.mp3")
"""

from .base import (
    AudioFormat,
    TTSCredentialsError,
    TTSError,
    TTSProvider,
    TTSQuotaError,
    TTSResult,
    TTSVoiceNotFoundError,
    VoiceGender,
    VoiceInfo,
)
from .engine import AudioSegment, TTSConfig, TTSEngine, create_tts_engine
from .prosody import (
    DEFAULT_PROSODY,
    EVENT_PROSODY_RULES,
    ProsodyController,
    ProsodySettings,
    generate_ssml,
)

__all__ = [
    "DEFAULT_PROSODY",
    "EVENT_PROSODY_RULES",
    "AudioFormat",
    "AudioSegment",
    "ProsodyController",
    "ProsodySettings",
    "TTSConfig",
    "TTSCredentialsError",
    "TTSEngine",
    "TTSError",
    "TTSProvider",
    "TTSQuotaError",
    "TTSResult",
    "TTSVoiceNotFoundError",
    "VoiceGender",
    "VoiceInfo",
    "create_tts_engine",
    "generate_ssml",
]


def get_available_providers() -> list[str]:
    """Get list of available TTS providers based on installed packages.

    Returns:
        List of provider names that can be used.
    """
    providers = []

    try:
        from google.cloud import texttospeech  # noqa: F401

        providers.append("google")
    except ImportError:
        pass

    try:
        import azure.cognitiveservices.speech  # noqa: F401

        providers.append("azure")
    except ImportError:
        pass

    try:
        from elevenlabs import ElevenLabs  # noqa: F401

        providers.append("elevenlabs")
    except ImportError:
        pass

    return providers
