"""Azure Cognitive Services Text-to-Speech provider."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    import azure.cognitiveservices.speech as speechsdk

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


class AzureTTSProvider(TTSProvider):
    """Azure Cognitive Services Text-to-Speech provider.

    Uses Azure Neural voices for high-quality, natural-sounding speech.
    Supports SSML for prosody control (rate, pitch, volume, pauses).

    Voice recommendations for cricket commentary:
    - en-AU-WilliamNeural: Australian male (Benaud-style)
    - en-GB-RyanNeural: British male (Greig-style)
    - en-IN-PrabhatNeural: Indian English male (Bhogle-style)
    - hi-IN-MadhurNeural: Hindi male (Doshi-style)
    - ta-IN-ValluvarNeural: Tamil male
    """

    # Recommended voices for cricket commentary personas
    RECOMMENDED_VOICES: ClassVar[dict[str, str]] = {
        # English voices
        "benaud": "en-AU-WilliamNeural",  # Australian male, measured
        "greig": "en-GB-RyanNeural",  # British male, energetic
        "bhogle": "en-IN-PrabhatNeural",  # Indian English male
        # Hindi voices
        "doshi": "hi-IN-MadhurNeural",  # Hindi male
        "hindi_female": "hi-IN-SwaraNeural",  # Hindi female
        # Tamil voices
        "tamil_male": "ta-IN-ValluvarNeural",  # Tamil male
        "tamil_female": "ta-IN-PallaviNeural",  # Tamil female
        # Default fallbacks
        "en_default": "en-US-GuyNeural",  # American male
        "hi_default": "hi-IN-MadhurNeural",  # Hindi male
    }

    # Audio format mappings
    FORMAT_MAP: ClassVar[dict[AudioFormat, str]] = {
        AudioFormat.MP3: "audio-24khz-48kbitrate-mono-mp3",
        AudioFormat.WAV: "riff-24khz-16bit-mono-pcm",
        AudioFormat.OGG: "ogg-24khz-16bit-mono-opus",
    }

    def __init__(
        self,
        subscription_key: str | None = None,
        region: str | None = None,
    ) -> None:
        """Initialize Azure TTS provider.

        Args:
            subscription_key: Azure Speech Services subscription key.
                            If not provided, uses AZURE_SPEECH_KEY env var.
            region: Azure region (e.g., 'eastus', 'westeurope').
                   If not provided, uses AZURE_SPEECH_REGION env var.
        """
        self._subscription_key = subscription_key or os.environ.get("AZURE_SPEECH_KEY")
        self._region = region or os.environ.get("AZURE_SPEECH_REGION", "eastus")
        self._synthesizer: speechsdk.SpeechSynthesizer | None = None

    @property
    def name(self) -> str:
        """Provider name."""
        return "azure"

    @property
    def supports_ssml(self) -> bool:
        """Azure TTS supports SSML."""
        return True

    def _get_synthesizer(
        self,
        audio_format: AudioFormat = AudioFormat.MP3,
    ) -> speechsdk.SpeechSynthesizer:
        """Get or create the speech synthesizer."""
        try:
            import azure.cognitiveservices.speech as speechsdk
        except ImportError as e:
            msg = "azure-cognitiveservices-speech not installed. Run: pip install azure-cognitiveservices-speech"
            raise TTSError(msg) from e

        if not self._subscription_key:
            msg = "AZURE_SPEECH_KEY not set. Provide subscription_key or set env var."
            raise TTSCredentialsError(msg)

        try:
            # Configure speech settings
            speech_config = speechsdk.SpeechConfig(
                subscription=self._subscription_key,
                region=self._region,
            )

            # Set output format
            output_format = getattr(
                speechsdk.SpeechSynthesisOutputFormat,
                self.FORMAT_MAP.get(audio_format, self.FORMAT_MAP[AudioFormat.MP3]).replace("-", "_"),
                speechsdk.SpeechSynthesisOutputFormat.Audio24Khz48KBitRateMonoMp3,
            )
            speech_config.set_speech_synthesis_output_format(output_format)

            # Create synthesizer without audio output (we want bytes)
            self._synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=speech_config,
                audio_config=None,  # No audio output, get bytes instead
            )

        except Exception as e:
            msg = f"Failed to create Azure TTS synthesizer: {e}"
            raise TTSCredentialsError(msg) from e

        return self._synthesizer

    def is_available(self) -> bool:
        """Check if Azure TTS is available."""
        try:
            import azure.cognitiveservices.speech as speechsdk  # noqa: F401

            return bool(self._subscription_key)
        except ImportError:
            return False

    def synthesize(
        self,
        text: str,
        voice_id: str,
        language: str = "en-US",
        ssml: bool = False,
        audio_format: AudioFormat = AudioFormat.MP3,
    ) -> TTSResult:
        """Synthesize speech using Azure Cognitive Services TTS.

        Args:
            text: Text or SSML to synthesize.
            voice_id: Azure voice ID (e.g., 'en-AU-WilliamNeural').
            language: Language code (e.g., 'en-US', 'hi-IN').
            ssml: Whether text is SSML markup.
            audio_format: Output format (MP3, WAV, OGG).

        Returns:
            TTSResult with audio bytes.
        """
        try:
            import azure.cognitiveservices.speech as speechsdk
        except ImportError as e:
            msg = "azure-cognitiveservices-speech not installed. Run: pip install azure-cognitiveservices-speech"
            raise TTSError(msg) from e

        synthesizer = self._get_synthesizer(audio_format)

        try:
            if ssml:
                # Text is already SSML
                result = synthesizer.speak_ssml_async(text).get()
            else:
                # Wrap plain text in minimal SSML with voice selection
                ssml_text = self._wrap_in_ssml(text, voice_id, language)
                result = synthesizer.speak_ssml_async(ssml_text).get()

            # Check result
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                audio_data = result.audio_data

                # Calculate approximate duration
                word_count = len(text.split())
                duration_estimate = word_count * 0.4  # ~0.4 seconds per word

                return TTSResult(
                    audio_bytes=audio_data,
                    format=audio_format,
                    sample_rate=24000,
                    duration_seconds=duration_estimate,
                    voice_used=voice_id,
                )

            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                if cancellation_details.reason == speechsdk.CancellationReason.Error:
                    error_str = str(cancellation_details.error_details).lower()
                    if "voice" in error_str and "not found" in error_str:
                        msg = f"Voice '{voice_id}' not found for language '{language}'"
                        raise TTSVoiceNotFoundError(msg)
                    msg = f"Azure TTS synthesis failed: {cancellation_details.error_details}"
                    raise TTSError(msg)
                msg = f"Azure TTS synthesis canceled: {cancellation_details.reason}"
                raise TTSError(msg)

            else:
                msg = f"Azure TTS synthesis failed with reason: {result.reason}"
                raise TTSError(msg)

        except (TTSError, TTSVoiceNotFoundError):
            raise
        except Exception as e:
            msg = f"Azure TTS synthesis failed: {e}"
            raise TTSError(msg) from e

    def _wrap_in_ssml(self, text: str, voice_id: str, language: str) -> str:
        """Wrap plain text in SSML with voice selection."""
        escaped_text = self._escape_ssml(text)
        return f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{language}">
    <voice name="{voice_id}">
        {escaped_text}
    </voice>
</speak>"""

    def _escape_ssml(self, text: str) -> str:
        """Escape special XML characters in text."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

    def get_available_voices(self, language: str | None = None) -> list[VoiceInfo]:
        """Get list of available Azure TTS voices.

        Args:
            language: Optional language filter (e.g., 'en' for all English).

        Returns:
            List of VoiceInfo objects.
        """
        try:
            import azure.cognitiveservices.speech as speechsdk
        except ImportError as e:
            msg = "azure-cognitiveservices-speech not installed. Run: pip install azure-cognitiveservices-speech"
            raise TTSError(msg) from e

        if not self._subscription_key:
            msg = "AZURE_SPEECH_KEY not set. Provide subscription_key or set env var."
            raise TTSCredentialsError(msg)

        try:
            speech_config = speechsdk.SpeechConfig(
                subscription=self._subscription_key,
                region=self._region,
            )
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=speech_config,
                audio_config=None,
            )

            result = synthesizer.get_voices_async(language or "").get()

            if result.reason == speechsdk.ResultReason.VoicesListRetrieved:
                voices = []
                for voice in result.voices:
                    # Filter by language if specified
                    if language and not voice.locale.startswith(language):
                        continue

                    # Determine gender
                    if voice.gender == speechsdk.SynthesisVoiceGender.Male:
                        gender = VoiceGender.MALE
                    elif voice.gender == speechsdk.SynthesisVoiceGender.Female:
                        gender = VoiceGender.FEMALE
                    else:
                        gender = VoiceGender.NEUTRAL

                    # Determine style based on voice name
                    style = "neural" if "Neural" in voice.short_name else "standard"

                    voices.append(
                        VoiceInfo(
                            voice_id=voice.short_name,
                            name=voice.local_name,
                            language=voice.locale,
                            gender=gender,
                            style=style,
                            provider="azure",
                        )
                    )

                return voices

            else:
                msg = f"Failed to list Azure voices: {result.reason}"
                raise TTSError(msg)

        except (TTSError, TTSCredentialsError):
            raise
        except Exception as e:
            msg = f"Failed to list voices: {e}"
            raise TTSError(msg) from e

    @classmethod
    def get_voice_for_persona(cls, persona_name: str, language: str = "en") -> str:
        """Get recommended voice ID for a persona.

        Args:
            persona_name: Persona name (e.g., 'Richie Benaud').
            language: Language code (e.g., 'en', 'hi').

        Returns:
            Voice ID string.
        """
        # Normalize persona name
        name_lower = persona_name.lower()

        if "benaud" in name_lower:
            return cls.RECOMMENDED_VOICES["benaud"]
        elif "greig" in name_lower:
            return cls.RECOMMENDED_VOICES["greig"]
        elif "bhogle" in name_lower or "harsha" in name_lower:
            return cls.RECOMMENDED_VOICES["bhogle"]
        elif "doshi" in name_lower or "sushil" in name_lower:
            return cls.RECOMMENDED_VOICES["doshi"]

        # Default based on language
        if language.startswith("hi"):
            return cls.RECOMMENDED_VOICES["hi_default"]
        else:
            return cls.RECOMMENDED_VOICES["en_default"]
