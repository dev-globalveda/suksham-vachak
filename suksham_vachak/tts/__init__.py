"""Text-to-Speech module for Suksham Vachak.

This module provides TTS capabilities with prosody control for
natural-sounding cricket commentary.

Providers (in priority order):
- Qwen3-TTS: Local, high-quality English synthesis (default for English)
- Svara-TTS: Local, 19 Indian languages with emotion tags (default for Hindi)
- ElevenLabs: Premium cloud-based voice cloning (demo/fallback)
- Google Cloud TTS: High-quality WaveNet voices
- Azure Cognitive Services: Neural voices

Example usage:
    from suksham_vachak.tts import TTSEngine, TTSConfig, AudioFormat
    from suksham_vachak.personas import BENAUD

    # Create engine with default config (language-aware provider chains)
    engine = create_tts_engine()

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
    """Get list of available TTS providers based on installed packages and running servers.

    Returns:
        List of provider names that can be used.
    """
    providers = []

    # Local providers (always importable — they use httpx which is a dependency)
    # Actual availability depends on whether the servers are running
    try:
        from .qwen3 import Qwen3TTSProvider  # noqa: F401

        providers.append("qwen3")
    except ImportError:
        pass

    try:
        from .svara import SvaraTTSProvider  # noqa: F401

        providers.append("svara")
    except ImportError:
        pass

    # Cloud providers (require optional SDK installs)
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
