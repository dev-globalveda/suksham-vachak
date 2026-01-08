"""ElevenLabs Text-to-Speech provider.

Provides high-quality voice synthesis with voice cloning capabilities.
Ideal for creating distinct commentator voices.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from elevenlabs.client import ElevenLabs

from .base import (
    AudioFormat,
    TTSCredentialsError,
    TTSError,
    TTSProvider,
    TTSResult,
    TTSVoiceNotFoundError,
    VoiceGender,
    VoiceInfo,
)


class ElevenLabsTTSProvider(TTSProvider):
    """ElevenLabs Text-to-Speech provider.

    Uses ElevenLabs API for high-quality, natural-sounding speech synthesis.
    Supports voice cloning for custom commentator voices.

    Voice recommendations for cricket commentary:
    - Use pre-made voices for prototyping
    - Clone actual commentator voices for production (with rights)

    Models:
    - eleven_multilingual_v2: Best quality, supports 29 languages
    - eleven_turbo_v2_5: Faster, English-optimized
    - eleven_flash_v2_5: Lowest latency for real-time

    Environment variables:
    - ELEVENLABS_API_KEY: Your ElevenLabs API key
    """

    # Pre-made voice IDs for cricket commentary (these are public voices)
    # Users should replace with their own cloned voices for production
    RECOMMENDED_VOICES: ClassVar[dict[str, str]] = {
        # English voices (pre-made)
        "benaud": "pNInz6obpgDQGcFmaJgB",  # Adam - deep, mature male
        "greig": "ErXwobaYiN019PkySvjV",  # Antoni - energetic male
        "bhogle": "VR6AewLTigWG4xSOukaG",  # Arnold - articulate male
        # Hindi/multilingual
        "doshi": "pNInz6obpgDQGcFmaJgB",  # Adam (use multilingual model)
        # Defaults
        "en_default": "pNInz6obpgDQGcFmaJgB",  # Adam
        "hi_default": "pNInz6obpgDQGcFmaJgB",  # Adam with multilingual
    }

    # Model selection
    MODELS: ClassVar[dict[str, str]] = {
        "quality": "eleven_multilingual_v2",  # Best quality
        "fast": "eleven_turbo_v2_5",  # Faster, English
        "realtime": "eleven_flash_v2_5",  # Lowest latency
    }

    # Audio format mappings
    FORMAT_MAP: ClassVar[dict[AudioFormat, str]] = {
        AudioFormat.MP3: "mp3_44100_128",
        AudioFormat.WAV: "pcm_44100",
        AudioFormat.OGG: "mp3_44100_128",  # ElevenLabs doesn't support OGG directly
    }

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "quality",
    ) -> None:
        """Initialize ElevenLabs TTS provider.

        Args:
            api_key: ElevenLabs API key. If not provided, uses ELEVENLABS_API_KEY env var.
            model: Model quality preset ('quality', 'fast', 'realtime').
        """
        self._api_key = api_key or os.environ.get("ELEVENLABS_API_KEY")
        self._model_id = self.MODELS.get(model, self.MODELS["quality"])
        self._client: ElevenLabs | None = None

    @property
    def name(self) -> str:
        """Provider name."""
        return "elevenlabs"

    @property
    def supports_ssml(self) -> bool:
        """ElevenLabs supports limited SSML (breaks only)."""
        return False  # We'll strip SSML and use plain text

    def _get_client(self) -> ElevenLabs:
        """Get or create the ElevenLabs client."""
        if self._client is None:
            try:
                from elevenlabs.client import ElevenLabs
            except ImportError as e:
                msg = "elevenlabs not installed. Run: pip install elevenlabs"
                raise TTSError(msg) from e

            if not self._api_key:
                msg = "ELEVENLABS_API_KEY not set. Get your key at https://elevenlabs.io"
                raise TTSCredentialsError(msg)

            try:
                self._client = ElevenLabs(api_key=self._api_key)
            except Exception as e:
                msg = f"Failed to create ElevenLabs client: {e}"
                raise TTSCredentialsError(msg) from e

        return self._client

    def is_available(self) -> bool:
        """Check if ElevenLabs is available."""
        try:
            self._get_client()
            return True
        except (TTSCredentialsError, TTSError):
            return False

    def _strip_ssml(self, text: str) -> str:
        """Strip SSML tags and return plain text.

        ElevenLabs doesn't support full SSML, so we extract the text content.
        """
        import re

        # Remove <speak> tags
        text = re.sub(r"</?speak>", "", text)
        # Remove <prosody> tags but keep content
        text = re.sub(r"<prosody[^>]*>", "", text)
        text = re.sub(r"</prosody>", "", text)
        # Convert <break> to pause marker (ElevenLabs uses ... for pauses)
        text = re.sub(r'<break[^>]*time="(\d+)ms"[^>]*/>', r" ... ", text)
        text = re.sub(r"<break[^>]*/?>", " ... ", text)
        # Remove any other XML tags
        text = re.sub(r"<[^>]+>", "", text)
        # Clean up whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def synthesize(
        self,
        text: str,
        voice_id: str,
        language: str = "en-US",
        ssml: bool = False,
        audio_format: AudioFormat = AudioFormat.MP3,
    ) -> TTSResult:
        """Synthesize speech using ElevenLabs.

        Args:
            text: Text or SSML to synthesize.
            voice_id: ElevenLabs voice ID.
            language: Language code (used for model selection).
            ssml: Whether text is SSML markup (will be stripped).
            audio_format: Output format (MP3 recommended).

        Returns:
            TTSResult with audio bytes.
        """
        client = self._get_client()

        # Strip SSML if present (ElevenLabs doesn't support it)
        if ssml or text.strip().startswith("<speak"):
            text = self._strip_ssml(text)

        # Select model based on language
        model_id = self._model_id
        if language.startswith("hi") or language.startswith("ta"):
            # Use multilingual model for non-English
            model_id = self.MODELS["quality"]

        # Get output format
        output_format = self.FORMAT_MAP.get(audio_format, "mp3_44100_128")

        try:
            # Generate audio
            audio_generator = client.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                model_id=model_id,
                output_format=output_format,
            )

            # Collect audio bytes from generator
            audio_bytes = b"".join(audio_generator)

        except Exception as e:
            error_str = str(e).lower()
            if "voice" in error_str and ("not found" in error_str or "invalid" in error_str):
                msg = f"Voice '{voice_id}' not found. Check your ElevenLabs voice library."
                raise TTSVoiceNotFoundError(msg) from e
            if "unauthorized" in error_str or "api key" in error_str:
                msg = "Invalid ElevenLabs API key"
                raise TTSCredentialsError(msg) from e
            msg = f"ElevenLabs synthesis failed: {e}"
            raise TTSError(msg) from e

        # Estimate duration (rough)
        word_count = len(text.split())
        duration_estimate = word_count * 0.4

        return TTSResult(
            audio_bytes=audio_bytes,
            format=audio_format,
            sample_rate=44100,
            duration_seconds=duration_estimate,
            voice_used=voice_id,
        )

    def get_available_voices(self, language: str | None = None) -> list[VoiceInfo]:
        """Get list of available ElevenLabs voices.

        Args:
            language: Optional language filter (not directly supported by API).

        Returns:
            List of VoiceInfo objects.
        """
        client = self._get_client()

        try:
            response = client.voices.get_all()
        except Exception as e:
            msg = f"Failed to list voices: {e}"
            raise TTSError(msg) from e

        voices = []
        for voice in response.voices:
            # ElevenLabs voices don't have strict language codes
            # Most support multiple languages with multilingual model
            lang = "en"
            if voice.labels:
                # Check for language hints in labels
                labels_str = str(voice.labels).lower()
                if "hindi" in labels_str:
                    lang = "hi"
                elif "spanish" in labels_str:
                    lang = "es"

            # Filter by language if specified
            if language and not lang.startswith(language[:2]):
                continue

            # Determine gender from labels
            gender = VoiceGender.NEUTRAL
            if voice.labels:
                labels_str = str(voice.labels).lower()
                if "male" in labels_str:
                    gender = VoiceGender.MALE
                elif "female" in labels_str:
                    gender = VoiceGender.FEMALE

            voices.append(
                VoiceInfo(
                    voice_id=voice.voice_id,
                    name=voice.name or voice.voice_id,
                    language=lang,
                    gender=gender,
                    style=voice.labels.get("use_case", "general") if voice.labels else "general",
                    provider="elevenlabs",
                )
            )

        return voices

    def clone_voice(
        self,
        name: str,
        audio_files: list[str],
        description: str | None = None,
    ) -> str:
        """Clone a voice from audio samples.

        Args:
            name: Name for the cloned voice.
            audio_files: List of paths to audio files (1-25 files, clear speech).
            description: Optional description of the voice.

        Returns:
            Voice ID of the cloned voice.
        """
        client = self._get_client()

        try:
            # Open audio files
            files = []
            for path in audio_files:
                files.append(open(path, "rb"))  # noqa: SIM115

            try:
                voice = client.clone(
                    name=name,
                    description=description or f"Cloned voice: {name}",
                    files=files,
                )
                return voice.voice_id
            finally:
                # Close all files
                for f in files:
                    f.close()

        except Exception as e:
            msg = f"Voice cloning failed: {e}"
            raise TTSError(msg) from e

    @classmethod
    def get_voice_for_persona(cls, persona_name: str, language: str = "en") -> str:
        """Get recommended voice ID for a persona.

        Args:
            persona_name: Persona name (e.g., 'Richie Benaud').
            language: Target language code (e.g., 'en', 'hi').

        Returns:
            Voice ID string appropriate for the persona.
        """
        name_lower = persona_name.lower()

        # Hindi language uses multilingual model with same voices
        if language.startswith("hi"):
            return cls.RECOMMENDED_VOICES["doshi"]

        if "benaud" in name_lower:
            return cls.RECOMMENDED_VOICES["benaud"]
        elif "greig" in name_lower:
            return cls.RECOMMENDED_VOICES["greig"]
        elif "bhogle" in name_lower or "harsha" in name_lower:
            return cls.RECOMMENDED_VOICES["bhogle"]
        elif "doshi" in name_lower or "sushil" in name_lower:
            return cls.RECOMMENDED_VOICES["doshi"]

        return cls.RECOMMENDED_VOICES["en_default"]
