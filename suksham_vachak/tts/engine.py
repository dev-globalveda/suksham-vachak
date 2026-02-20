"""TTS Engine - Main orchestrator for text-to-speech synthesis."""

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from suksham_vachak.commentary import Commentary
from suksham_vachak.logging import get_logger
from suksham_vachak.parser import EventType
from suksham_vachak.personas import Persona

from .base import AudioFormat, TTSError, TTSProvider, TTSResult
from .prosody import ProsodyController

logger = get_logger(__name__)


@dataclass
class AudioSegment:
    """A single audio segment with metadata."""

    audio_bytes: bytes
    format: AudioFormat
    duration_seconds: float
    event_type: EventType
    persona_name: str
    text: str
    voice_id: str
    cache_key: str | None = None


@dataclass
class TTSConfig:
    """Configuration for TTS Engine."""

    # Provider settings
    provider: str = "qwen3"  # Primary: "qwen3", "svara", "elevenlabs", "google", "azure"
    fallback_provider: str | None = "svara"  # Fallback if primary fails

    # Language-aware provider chains: language → ordered list of providers to try
    # If set, overrides provider/fallback_provider for the given language
    language_providers: dict[str, list[str]] = field(
        default_factory=lambda: {
            "en": ["qwen3", "svara", "elevenlabs"],
            "hi": ["svara", "elevenlabs"],
        }
    )

    # Audio settings
    audio_format: AudioFormat = AudioFormat.MP3
    sample_rate: int = 24000

    # Cache settings
    enable_cache: bool = True
    cache_dir: str = ".tts_cache"

    # Voice mapping (persona name -> voice ID)
    # If not specified, uses provider's default mapping
    voice_mapping: dict[str, str] = field(default_factory=lambda: {})


class TTSEngine:
    """Main TTS engine that orchestrates speech synthesis.

    Combines prosody control, provider selection, and caching to
    generate natural-sounding audio from commentary.
    """

    # Default voice mappings per provider
    DEFAULT_VOICE_MAPPINGS: ClassVar[dict[str, dict[str, str]]] = {
        "qwen3": {
            "Richie Benaud": "Ryan",
            "Tony Greig": "Aiden",
            "Harsha Bhogle": "Ryan",
        },
        "svara": {
            "Richie Benaud": "en_male",
            "Tony Greig": "en_male",
            "Harsha Bhogle": "en_male",
            "Sushil Doshi": "hi_male",
        },
        "google": {
            "Richie Benaud": "en-AU-Wavenet-B",
            "Tony Greig": "en-GB-Wavenet-B",
            "Harsha Bhogle": "en-IN-Wavenet-C",
            "Sushil Doshi": "hi-IN-Wavenet-A",
        },
        "azure": {
            "Richie Benaud": "en-AU-WilliamNeural",
            "Tony Greig": "en-GB-RyanNeural",
            "Harsha Bhogle": "en-IN-PrabhatNeural",
            "Sushil Doshi": "hi-IN-MadhurNeural",
        },
        "elevenlabs": {
            "Richie Benaud": "pNInz6obpgDQGcFmaJgB",  # Adam - deep, mature
            "Tony Greig": "ErXwobaYiN019PkySvjV",  # Antoni - energetic
            "Harsha Bhogle": "VR6AewLTigWG4xSOukaG",  # Arnold - articulate
            "Sushil Doshi": "pNInz6obpgDQGcFmaJgB",  # Adam (multilingual)
        },
    }

    def __init__(self, config: TTSConfig | None = None) -> None:
        """Initialize TTS Engine.

        Args:
            config: TTS configuration. If None, uses defaults.
        """
        self.config = config or TTSConfig()
        self._prosody_controller = ProsodyController()
        self._providers: dict[str, TTSProvider] = {}
        self._cache_dir: Path | None = None

        if self.config.enable_cache:
            self._cache_dir = Path(self.config.cache_dir)
            self._cache_dir.mkdir(parents=True, exist_ok=True)

    def __enter__(self) -> "TTSEngine":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager, optionally clearing cache."""
        # Clear providers (they may hold connections)
        self._providers.clear()

    def __repr__(self) -> str:
        """Concise representation for debugging."""
        cache_status = f"cache={self._cache_dir}" if self._cache_dir else "no-cache"
        return f"TTSEngine(provider={self.config.provider}, {cache_status})"

    def _get_provider(self, provider_name: str) -> TTSProvider:
        """Get or create a TTS provider instance."""
        if provider_name not in self._providers:
            if provider_name == "qwen3":
                from .qwen3 import Qwen3TTSProvider

                self._providers[provider_name] = Qwen3TTSProvider()
            elif provider_name == "svara":
                from .svara import SvaraTTSProvider

                self._providers[provider_name] = SvaraTTSProvider()
            elif provider_name == "google":
                from .google import GoogleTTSProvider

                self._providers[provider_name] = GoogleTTSProvider()
            elif provider_name == "azure":
                from .azure import AzureTTSProvider

                self._providers[provider_name] = AzureTTSProvider()
            elif provider_name == "elevenlabs":
                from .elevenlabs import ElevenLabsTTSProvider

                self._providers[provider_name] = ElevenLabsTTSProvider()
            else:
                msg = f"Unknown TTS provider: {provider_name}"
                raise TTSError(msg)

        return self._providers[provider_name]

    def _get_provider_chain(self, language: str) -> list[str]:
        """Get the ordered list of providers to try for a language.

        Uses language_providers config if the language has a chain defined,
        otherwise falls back to the default provider + fallback_provider.

        Args:
            language: Language code (e.g., 'en', 'hi').

        Returns:
            Ordered list of provider names to try.
        """
        lang_code = language.split("-")[0].lower()

        # Check for language-specific chain
        if lang_code in self.config.language_providers:
            return list(self.config.language_providers[lang_code])

        # Fall back to default provider chain
        chain = [self.config.provider]
        if self.config.fallback_provider:
            chain.append(self.config.fallback_provider)
        return chain

    def _get_voice_id(self, persona: Persona, provider_name: str) -> str:
        """Get voice ID for a persona from config or defaults."""
        # Check custom voice mapping first
        if persona.name in self.config.voice_mapping:
            return self.config.voice_mapping[persona.name]

        # Check provider-specific defaults
        provider_defaults = self.DEFAULT_VOICE_MAPPINGS.get(provider_name, {})
        if persona.name in provider_defaults:
            return provider_defaults[persona.name]

        # Use provider's own mapping method
        provider = self._get_provider(provider_name)
        if hasattr(provider, "get_voice_for_persona"):
            language = persona.languages[0] if persona.languages else "en"
            return provider.get_voice_for_persona(persona.name, language)  # type: ignore[union-attr]

        # Ultimate fallback
        if provider_name == "qwen3":
            return "Ryan"
        elif provider_name == "svara":
            language = persona.languages[0] if persona.languages else "en"
            lang_code = language.split("-")[0].lower()
            return f"{lang_code}_male"
        elif provider_name == "google":
            return "en-US-Wavenet-D"
        elif provider_name == "elevenlabs":
            return "pNInz6obpgDQGcFmaJgB"  # Adam
        else:
            return "en-US-GuyNeural"

    def _get_cache_key(
        self,
        text: str,
        voice_id: str,
        event_type: EventType,
        persona_name: str,
    ) -> str:
        """Generate a cache key for audio."""
        # Include all parameters that affect the output
        key_data = f"{text}|{voice_id}|{event_type.value}|{persona_name}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    def _get_cached_audio(self, cache_key: str) -> bytes | None:
        """Get cached audio if available."""
        if not self._cache_dir:
            return None

        cache_file = self._cache_dir / f"{cache_key}.{self.config.audio_format.value}"
        if cache_file.exists():
            return cache_file.read_bytes()
        return None

    def _cache_audio(self, cache_key: str, audio_bytes: bytes) -> None:
        """Cache audio bytes."""
        if not self._cache_dir:
            return

        cache_file = self._cache_dir / f"{cache_key}.{self.config.audio_format.value}"
        cache_file.write_bytes(audio_bytes)

    def synthesize_commentary(
        self,
        commentary: Commentary,
        persona: Persona,
        use_ssml: bool = True,
    ) -> AudioSegment:
        """Synthesize speech for a single commentary.

        Uses language-aware provider chains to select the best TTS provider.
        For Svara, injects emotion tags based on the cricket event type.

        Args:
            commentary: The commentary to synthesize.
            persona: The persona who generated the commentary.
            use_ssml: Whether to apply prosody via SSML.

        Returns:
            AudioSegment with synthesized audio.
        """
        text = commentary.text
        event_type = commentary.event.event_type

        # Get primary language from persona
        language = persona.languages[0] if persona.languages else "en"

        # Build language-aware provider chain
        providers_to_try = self._get_provider_chain(language)

        # Get voice ID for the first provider (may change per provider below)
        first_provider = providers_to_try[0] if providers_to_try else self.config.provider
        voice_id = self._get_voice_id(persona, first_provider)

        # Generate cache key
        cache_key = self._get_cache_key(text, voice_id, event_type, persona.name)

        # Check cache first
        cached_audio = self._get_cached_audio(cache_key)
        if cached_audio:
            word_count = len(text.split())
            duration = word_count * 0.4

            return AudioSegment(
                audio_bytes=cached_audio,
                format=self.config.audio_format,
                duration_seconds=duration,
                event_type=event_type,
                persona_name=persona.name,
                text=text,
                voice_id=voice_id,
                cache_key=cache_key,
            )

        # Prepare SSML text (for providers that support it)
        if use_ssml:
            ssml_text = self._prosody_controller.apply_prosody(text, persona, event_type)
        else:
            ssml_text = text

        # Prepare Svara emotion text (for Svara provider)
        match_ctx = commentary.event.match_context
        svara_text = self._prepare_svara_text(text, event_type, match_ctx)

        # Try providers in chain order
        result: TTSResult | None = None
        last_error: Exception | None = None

        for provider_name in providers_to_try:
            try:
                provider = self._get_provider(provider_name)

                # Skip providers that don't support this language
                if not provider.supports_language(language):
                    logger.debug("provider_skip_language", provider=provider_name, language=language)
                    continue

                # Get voice ID for this provider
                voice_id = self._get_voice_id(persona, provider_name)

                # Choose the right text variant for this provider
                if provider_name == "svara":
                    synth_text = svara_text
                    is_ssml = False
                elif use_ssml and provider.supports_ssml:
                    synth_text = ssml_text
                    is_ssml = True
                else:
                    synth_text = text
                    is_ssml = False

                result = provider.synthesize(
                    text=synth_text,
                    voice_id=voice_id,
                    language=language,
                    ssml=is_ssml,
                    audio_format=self.config.audio_format,
                )
                logger.info("tts_synthesis_success", provider=provider_name, language=language)
                break

            except TTSError as e:
                last_error = e
                logger.warning("tts_provider_failed", provider=provider_name, error=str(e))
                continue

        if result is None:
            msg = f"All TTS providers failed. Last error: {last_error}"
            raise TTSError(msg)

        # Cache the result
        self._cache_audio(cache_key, result.audio_bytes)

        return AudioSegment(
            audio_bytes=result.audio_bytes,
            format=result.format,
            duration_seconds=result.duration_seconds or 0.0,
            event_type=event_type,
            persona_name=persona.name,
            text=text,
            voice_id=voice_id,
            cache_key=cache_key,
        )

    def _prepare_svara_text(self, text: str, event_type: EventType, match_ctx: object) -> str:
        """Prepare text with Svara emotion tags based on event context.

        Args:
            text: Plain commentary text.
            event_type: The cricket event type.
            match_ctx: Match context with target, score, wickets, overs.

        Returns:
            Text with Svara emotion tag prepended.
        """
        from .emotion import get_emotion_tag, inject_emotion

        # Extract match context fields safely
        target = getattr(match_ctx, "target", None)
        current_score = getattr(match_ctx, "current_score", 0)
        current_wickets = getattr(match_ctx, "current_wickets", 0)
        overs_completed = getattr(match_ctx, "overs_completed", 0.0)

        emotion_tag = get_emotion_tag(
            event_type,
            target=target,
            current_score=current_score,
            current_wickets=current_wickets,
            overs_completed=overs_completed,
        )
        return inject_emotion(text, emotion_tag)

    def synthesize_batch(
        self,
        commentaries: list[Commentary],
        persona: Persona,
        use_ssml: bool = True,
    ) -> list[AudioSegment]:
        """Synthesize speech for multiple commentaries.

        Args:
            commentaries: List of commentaries to synthesize.
            persona: The persona who generated the commentaries.
            use_ssml: Whether to apply prosody via SSML.

        Returns:
            List of AudioSegments in same order as input.
        """
        return [self.synthesize_commentary(commentary, persona, use_ssml) for commentary in commentaries]

    def save_audio(
        self,
        segment: AudioSegment,
        output_path: str | Path,
    ) -> Path:
        """Save an audio segment to a file.

        Args:
            segment: The audio segment to save.
            output_path: Output file path. Extension will be adjusted
                        to match the audio format.

        Returns:
            Path to the saved file.
        """
        output_path = Path(output_path)

        # Ensure correct extension
        expected_ext = f".{segment.format.value}"
        if output_path.suffix != expected_ext:
            output_path = output_path.with_suffix(expected_ext)

        # Create parent directories
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write audio
        output_path.write_bytes(segment.audio_bytes)

        return output_path

    def concatenate_segments(
        self,
        segments: list[AudioSegment],
        output_path: str | Path,
        gap_ms: int = 500,
    ) -> Path:
        """Concatenate multiple audio segments into one file.

        Note: This is a basic implementation. For production,
        consider using pydub or ffmpeg for proper audio handling.

        Args:
            segments: List of audio segments to concatenate.
            output_path: Output file path.
            gap_ms: Gap between segments in milliseconds.

        Returns:
            Path to the concatenated file.
        """
        if not segments:
            msg = "No segments to concatenate"
            raise TTSError(msg)

        # For MP3, we can do simple concatenation (not ideal but works)
        # For production, use pydub: AudioSegment.from_mp3() + silence
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("wb") as f:
            for segment in segments:
                f.write(segment.audio_bytes)
                # Note: This doesn't add actual silence gaps for MP3
                # Use pydub for proper audio manipulation

        return output_path

    def clear_cache(self) -> int:
        """Clear the audio cache.

        Returns:
            Number of files deleted.
        """
        if not self._cache_dir or not self._cache_dir.exists():
            return 0

        count = 0
        for cache_file in self._cache_dir.glob("*"):
            if cache_file.is_file():
                cache_file.unlink()
                count += 1

        return count

    def get_cache_stats(self) -> dict[str, int | float]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats (files, size_mb).
        """
        if not self._cache_dir or not self._cache_dir.exists():
            return {"files": 0, "size_mb": 0.0}

        files = list(self._cache_dir.glob("*"))
        total_size = sum(f.stat().st_size for f in files if f.is_file())

        return {
            "files": len(files),
            "size_mb": round(total_size / (1024 * 1024), 2),
        }


def create_tts_engine(
    provider: str | None = None,
    fallback_provider: str | None = None,
    cache_enabled: bool = True,
    cache_dir: str = ".tts_cache",
) -> TTSEngine:
    """Convenience function to create a TTS engine.

    Provider selection priority:
    1. Explicit parameter
    2. TTS_PROVIDER environment variable
    3. Default: 'qwen3' (local, free, high-quality English)

    The engine uses language-aware provider chains:
    - English: qwen3 → svara → elevenlabs
    - Hindi: svara → elevenlabs

    Args:
        provider: Primary TTS provider ('qwen3', 'svara', 'elevenlabs', 'google', 'azure').
        fallback_provider: Fallback provider if primary fails.
        cache_enabled: Whether to enable audio caching.
        cache_dir: Directory for cached audio files.

    Returns:
        Configured TTSEngine instance.
    """
    # Read from env vars if not specified
    if provider is None:
        provider = os.environ.get("TTS_PROVIDER", "qwen3")
    if fallback_provider is None:
        fallback_provider = os.environ.get("TTS_FALLBACK_PROVIDER", "svara")

    logger.info(
        "creating_tts_engine",
        provider=provider,
        fallback_provider=fallback_provider,
        cache_enabled=cache_enabled,
    )

    config = TTSConfig(
        provider=provider,
        fallback_provider=fallback_provider,
        enable_cache=cache_enabled,
        cache_dir=cache_dir,
    )
    return TTSEngine(config)
