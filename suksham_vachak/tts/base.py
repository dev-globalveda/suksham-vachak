"""Base classes for Text-to-Speech providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class AudioFormat(Enum):
    """Supported audio output formats."""

    MP3 = "mp3"
    WAV = "wav"
    OGG = "ogg"


class VoiceGender(Enum):
    """Voice gender options."""

    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"


@dataclass
class VoiceInfo:
    """Information about an available TTS voice."""

    voice_id: str
    name: str
    language: str
    gender: VoiceGender
    style: str = "standard"  # e.g., "news", "conversational", "narrative"
    provider: str = "unknown"

    @property
    def display_name(self) -> str:
        """Human-readable display name."""
        return f"{self.name} ({self.language}, {self.gender.value})"


@dataclass
class TTSResult:
    """Result from TTS synthesis."""

    audio_bytes: bytes
    format: AudioFormat
    sample_rate: int
    duration_seconds: float | None = None
    voice_used: str | None = None

    @property
    def size_kb(self) -> float:
        """Audio size in kilobytes."""
        return len(self.audio_bytes) / 1024


class TTSProvider(ABC):
    """Abstract base class for TTS providers.

    Implement this class to add support for different TTS services
    like Google Cloud TTS, Azure, ElevenLabs, etc.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'google', 'azure')."""
        ...

    @property
    @abstractmethod
    def supports_ssml(self) -> bool:
        """Whether this provider supports SSML input."""
        ...

    @abstractmethod
    def synthesize(
        self,
        text: str,
        voice_id: str,
        language: str = "en-US",
        ssml: bool = False,
        audio_format: AudioFormat = AudioFormat.MP3,
    ) -> TTSResult:
        """Synthesize speech from text.

        Args:
            text: The text to synthesize, or SSML if ssml=True.
            voice_id: The voice ID to use (provider-specific).
            language: Language code (e.g., 'en-US', 'hi-IN').
            ssml: Whether the text is SSML markup.
            audio_format: Output audio format.

        Returns:
            TTSResult with audio bytes and metadata.

        Raises:
            TTSError: If synthesis fails.
        """
        ...

    @abstractmethod
    def get_available_voices(self, language: str | None = None) -> list[VoiceInfo]:
        """Get list of available voices.

        Args:
            language: Optional language filter (e.g., 'en' for all English).

        Returns:
            List of VoiceInfo objects for available voices.
        """
        ...

    def is_available(self) -> bool:
        """Check if this provider is available (credentials configured, etc.)."""
        return True


class TTSError(Exception):
    """Base exception for TTS errors."""

    pass


class TTSCredentialsError(TTSError):
    """Raised when TTS credentials are missing or invalid."""

    pass


class TTSQuotaError(TTSError):
    """Raised when TTS quota is exceeded."""

    pass


class TTSVoiceNotFoundError(TTSError):
    """Raised when requested voice is not available."""

    pass
