"""Google Cloud Text-to-Speech provider."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from google.cloud import texttospeech

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


class GoogleTTSProvider(TTSProvider):
    """Google Cloud Text-to-Speech provider.

    Uses WaveNet voices for high-quality, natural-sounding speech.
    Supports SSML for prosody control (rate, pitch, volume, pauses).

    Voice recommendations for cricket commentary:
    - en-AU-Wavenet-B: Australian male (Benaud-style)
    - en-GB-Wavenet-B: British male (Greig-style)
    - en-IN-Wavenet-C: Indian English male (Bhogle-style)
    - hi-IN-Wavenet-A: Hindi male (Doshi-style)
    - ta-IN-Wavenet-A: Tamil male
    """

    # Recommended voices for cricket commentary personas
    RECOMMENDED_VOICES: ClassVar[dict[str, str]] = {
        # English voices
        "benaud": "en-AU-Wavenet-B",  # Australian male, measured
        "greig": "en-GB-Wavenet-B",  # British male, energetic
        "bhogle": "en-IN-Wavenet-C",  # Indian English male
        # Hindi voices
        "doshi": "hi-IN-Wavenet-B",  # Hindi male (A is female!)
        "hindi_female": "hi-IN-Wavenet-D",  # Hindi female
        # Tamil voices
        "tamil_male": "ta-IN-Wavenet-B",  # Tamil male
        "tamil_female": "ta-IN-Wavenet-A",  # Tamil female
        # Default fallbacks
        "en_default": "en-US-Wavenet-D",  # American male
        "hi_default": "hi-IN-Wavenet-A",  # Hindi male
    }

    # Audio format mappings
    FORMAT_MAP: ClassVar[dict[AudioFormat, str]] = {
        AudioFormat.MP3: "MP3",
        AudioFormat.WAV: "LINEAR16",
        AudioFormat.OGG: "OGG_OPUS",
    }

    def __init__(self, credentials_path: str | None = None) -> None:
        """Initialize Google TTS provider.

        Args:
            credentials_path: Path to Google Cloud credentials JSON file.
                            If not provided, uses GOOGLE_APPLICATION_CREDENTIALS env var.
        """
        self._credentials_path = credentials_path or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        self._client: texttospeech.TextToSpeechClient | None = None

    @property
    def name(self) -> str:
        """Provider name."""
        return "google"

    @property
    def supports_ssml(self) -> bool:
        """Google TTS supports SSML."""
        return True

    def _get_client(self) -> texttospeech.TextToSpeechClient:
        """Get or create the TTS client."""
        if self._client is None:
            try:
                from google.cloud import texttospeech
            except ImportError as e:
                msg = "google-cloud-texttospeech not installed. Run: pip install google-cloud-texttospeech"
                raise TTSError(msg) from e

            if self._credentials_path:
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self._credentials_path

            # Note: google-cloud library auto-detects Application Default Credentials (ADC)
            # from gcloud auth application-default login, so explicit env var not required

            try:
                self._client = texttospeech.TextToSpeechClient()
            except Exception as e:
                msg = f"Failed to create Google TTS client: {e}"
                raise TTSCredentialsError(msg) from e

        return self._client

    def is_available(self) -> bool:
        """Check if Google TTS is available."""
        try:
            self._get_client()
            return True
        except (TTSCredentialsError, TTSError):
            return False

    def synthesize(
        self,
        text: str,
        voice_id: str,
        language: str = "en-US",
        ssml: bool = False,
        audio_format: AudioFormat = AudioFormat.MP3,
    ) -> TTSResult:
        """Synthesize speech using Google Cloud TTS.

        Args:
            text: Text or SSML to synthesize.
            voice_id: Google voice ID (e.g., 'en-AU-Wavenet-B').
            language: Language code (e.g., 'en-US', 'hi-IN').
            ssml: Whether text is SSML markup.
            audio_format: Output format (MP3, WAV, OGG).

        Returns:
            TTSResult with audio bytes.
        """
        from google.cloud import texttospeech

        client = self._get_client()

        # Build synthesis input
        if ssml:
            synthesis_input = texttospeech.SynthesisInput(ssml=text)
        else:
            synthesis_input = texttospeech.SynthesisInput(text=text)

        # Build voice selection
        voice = texttospeech.VoiceSelectionParams(
            language_code=language,
            name=voice_id,
        )

        # Build audio config
        audio_encoding = getattr(
            texttospeech.AudioEncoding,
            self.FORMAT_MAP.get(audio_format, "MP3"),
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=audio_encoding,
            sample_rate_hertz=24000 if audio_format == AudioFormat.WAV else None,
        )

        try:
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config,
            )
        except Exception as e:
            error_str = str(e).lower()
            if "voice" in error_str and "not found" in error_str:
                msg = f"Voice '{voice_id}' not found for language '{language}'"
                raise TTSVoiceNotFoundError(msg) from e
            msg = f"Google TTS synthesis failed: {e}"
            raise TTSError(msg) from e

        # Calculate approximate duration (rough estimate)
        # More accurate would require parsing the audio
        word_count = len(text.split())
        duration_estimate = word_count * 0.4  # ~0.4 seconds per word

        return TTSResult(
            audio_bytes=response.audio_content,
            format=audio_format,
            sample_rate=24000,
            duration_seconds=duration_estimate,
            voice_used=voice_id,
        )

    def get_available_voices(self, language: str | None = None) -> list[VoiceInfo]:
        """Get list of available Google TTS voices.

        Args:
            language: Optional language filter (e.g., 'en' for all English).

        Returns:
            List of VoiceInfo objects.
        """
        from google.cloud import texttospeech

        client = self._get_client()

        try:
            response = client.list_voices(language_code=language or "")
        except Exception as e:
            msg = f"Failed to list voices: {e}"
            raise TTSError(msg) from e

        voices = []
        for voice in response.voices:
            # Get the primary language code
            lang_code = voice.language_codes[0] if voice.language_codes else "unknown"

            # Filter by language if specified
            if language and not lang_code.startswith(language):
                continue

            # Determine gender
            if voice.ssml_gender == texttospeech.SsmlVoiceGender.MALE:
                gender = VoiceGender.MALE
            elif voice.ssml_gender == texttospeech.SsmlVoiceGender.FEMALE:
                gender = VoiceGender.FEMALE
            else:
                gender = VoiceGender.NEUTRAL

            # Determine style based on voice name
            style = "standard"
            if "Wavenet" in voice.name:
                style = "wavenet"
            elif "Neural" in voice.name:
                style = "neural"
            elif "Studio" in voice.name:
                style = "studio"

            voices.append(
                VoiceInfo(
                    voice_id=voice.name,
                    name=voice.name,
                    language=lang_code,
                    gender=gender,
                    style=style,
                    provider="google",
                )
            )

        return voices

    @classmethod
    def get_voice_for_persona(cls, persona_name: str, language: str = "en") -> str:
        """Get recommended voice ID for a persona and language.

        Args:
            persona_name: Persona name (e.g., 'Richie Benaud').
            language: Target language code (e.g., 'en', 'hi').

        Returns:
            Voice ID string appropriate for the persona style in the target language.
        """
        # If Hindi is requested, use Hindi voice regardless of persona
        if language.startswith("hi"):
            return cls.RECOMMENDED_VOICES["doshi"]  # hi-IN-Wavenet-B (male)

        # For English, select voice based on persona's accent/style
        name_lower = persona_name.lower()

        if "benaud" in name_lower:
            return cls.RECOMMENDED_VOICES["benaud"]  # Australian
        elif "greig" in name_lower:
            return cls.RECOMMENDED_VOICES["greig"]  # British
        elif "bhogle" in name_lower or "harsha" in name_lower:
            return cls.RECOMMENDED_VOICES["bhogle"]  # Indian English
        elif "doshi" in name_lower or "sushil" in name_lower:
            return cls.RECOMMENDED_VOICES["bhogle"]  # Indian English for Doshi in English

        # Default
        return cls.RECOMMENDED_VOICES["en_default"]
