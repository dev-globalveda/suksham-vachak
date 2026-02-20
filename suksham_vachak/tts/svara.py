"""Svara TTS provider — local HTTP client for Indian-language speech synthesis.

Svara supports 19 Indian languages with emotion tags. Runs as a local server
on port 8080 and returns raw PCM audio, which we convert to WAV (stdlib) or
MP3 (ffmpeg subprocess, graceful fallback to WAV).

Environment variables:
    SVARA_TTS_BASE_URL: Base URL of the Svara server (default: http://localhost:8080)
"""

from __future__ import annotations

import io
import os
import subprocess
import wave
from typing import ClassVar

import httpx

from .base import AudioFormat, TTSError, TTSProvider, TTSResult, VoiceGender, VoiceInfo

# Svara returns 16-bit mono PCM at 24kHz by default
SVARA_SAMPLE_RATE = 24000
SVARA_SAMPLE_WIDTH = 2  # 16-bit = 2 bytes
SVARA_CHANNELS = 1


def pcm_to_wav(pcm_data: bytes, sample_rate: int = SVARA_SAMPLE_RATE) -> bytes:
    """Convert raw PCM bytes to WAV format using stdlib wave module.

    Args:
        pcm_data: Raw 16-bit mono PCM audio bytes.
        sample_rate: Sample rate in Hz.

    Returns:
        WAV-formatted audio bytes.
    """
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(SVARA_CHANNELS)
        wf.setsampwidth(SVARA_SAMPLE_WIDTH)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()


def pcm_to_mp3(pcm_data: bytes, sample_rate: int = SVARA_SAMPLE_RATE) -> bytes | None:
    """Convert raw PCM bytes to MP3 using ffmpeg subprocess.

    Returns None if ffmpeg is not available (caller should fall back to WAV).

    Args:
        pcm_data: Raw 16-bit mono PCM audio bytes.
        sample_rate: Sample rate in Hz.

    Returns:
        MP3 audio bytes, or None if ffmpeg is unavailable.
    """
    try:
        result = subprocess.run(  # noqa: S603
            [  # noqa: S607
                "ffmpeg",
                "-f",
                "s16le",
                "-ar",
                str(sample_rate),
                "-ac",
                str(SVARA_CHANNELS),
                "-i",
                "pipe:0",
                "-codec:a",
                "libmp3lame",
                "-b:a",
                "128k",
                "-f",
                "mp3",
                "pipe:1",
            ],
            input=pcm_data,
            capture_output=True,
            timeout=30,
            check=False,
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
    except FileNotFoundError:
        # ffmpeg not installed
        pass
    except subprocess.TimeoutExpired:
        pass
    return None


class SvaraTTSProvider(TTSProvider):
    """Svara TTS provider for Indian-language speech synthesis.

    Connects to a local Svara server via HTTP. Supports 19 Indian languages
    and emotion tags for expressive speech.

    Voice IDs follow the pattern: {language_code}_{gender}
    e.g., 'hi_male', 'hi_female', 'en_male', 'ta_female'
    """

    SUPPORTED_LANGUAGES: ClassVar[set[str]] = {
        "hi",
        "en",
        "ta",
        "te",
        "bn",
        "mr",
        "gu",
        "kn",
        "ml",
        "pa",
        "or",
        "as",
        "ur",
        "sd",
        "ne",
        "si",
        "kok",
        "doi",
        "mai",
    }

    # Voice mappings for personas
    PERSONA_VOICES: ClassVar[dict[str, dict[str, str]]] = {
        "Richie Benaud": {"en": "en_male"},
        "Tony Greig": {"en": "en_male"},
        "Harsha Bhogle": {"en": "en_male", "hi": "hi_male"},
        "Sushil Doshi": {"hi": "hi_male"},
    }

    DEFAULT_VOICES: ClassVar[dict[str, str]] = {
        "en": "en_male",
        "hi": "hi_male",
    }

    def __init__(self, base_url: str | None = None, timeout: float = 30.0) -> None:
        self._base_url = (base_url or os.environ.get("SVARA_TTS_BASE_URL", "http://localhost:8080")).rstrip("/")
        self._timeout = timeout
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(base_url=self._base_url, timeout=self._timeout)
        return self._client

    @property
    def name(self) -> str:
        return "svara"

    @property
    def supports_ssml(self) -> bool:
        return False

    def supports_language(self, language: str) -> bool:
        lang_code = language.split("-")[0].lower()
        return lang_code in self.SUPPORTED_LANGUAGES

    def is_available(self) -> bool:
        try:
            client = self._get_client()
            resp = client.get("/health", timeout=5.0)
            return resp.status_code == 200
        except (httpx.HTTPError, Exception):
            return False

    def synthesize(
        self,
        text: str,
        voice_id: str,
        language: str = "hi-IN",
        ssml: bool = False,
        audio_format: AudioFormat = AudioFormat.MP3,
    ) -> TTSResult:
        """Synthesize speech using Svara.

        Svara returns raw PCM audio. We convert to the requested format.

        Args:
            text: Text to synthesize (may include Svara emotion tags).
            voice_id: Voice ID (e.g., 'hi_male', 'en_female').
            language: Language code (e.g., 'hi-IN', 'en-IN').
            ssml: Ignored (Svara doesn't support SSML).
            audio_format: Output format (MP3 or WAV).

        Returns:
            TTSResult with audio bytes.
        """
        client = self._get_client()
        lang_code = language.split("-")[0].lower()

        payload = {
            "text": text,
            "voice_id": voice_id,
            "language": lang_code,
        }

        try:
            resp = client.post("/synthesize", json=payload)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            msg = f"Svara synthesis failed (HTTP {e.response.status_code}): {e.response.text}"
            raise TTSError(msg) from e
        except httpx.HTTPError as e:
            msg = f"Svara server unreachable: {e}"
            raise TTSError(msg) from e

        pcm_data = resp.content
        if not pcm_data:
            msg = "Svara returned empty audio"
            raise TTSError(msg)

        # Determine sample rate from response headers or use default
        sample_rate = int(resp.headers.get("x-sample-rate", str(SVARA_SAMPLE_RATE)))

        # Convert PCM to requested format
        if audio_format == AudioFormat.MP3:
            mp3_data = pcm_to_mp3(pcm_data, sample_rate)
            if mp3_data is not None:
                audio_bytes = mp3_data
                result_format = AudioFormat.MP3
            else:
                # Fallback to WAV if ffmpeg unavailable
                audio_bytes = pcm_to_wav(pcm_data, sample_rate)
                result_format = AudioFormat.WAV
        else:
            audio_bytes = pcm_to_wav(pcm_data, sample_rate)
            result_format = AudioFormat.WAV

        # Estimate duration from PCM data
        num_samples = len(pcm_data) // SVARA_SAMPLE_WIDTH
        duration = num_samples / sample_rate

        return TTSResult(
            audio_bytes=audio_bytes,
            format=result_format,
            sample_rate=sample_rate,
            duration_seconds=duration,
            voice_used=voice_id,
        )

    def get_available_voices(self, language: str | None = None) -> list[VoiceInfo]:
        voices = []
        languages = [language.split("-")[0].lower()] if language else list(self.SUPPORTED_LANGUAGES)

        for lang in languages:
            if lang not in self.SUPPORTED_LANGUAGES:
                continue
            for gender in ["male", "female"]:
                voice_id = f"{lang}_{gender}"
                voices.append(
                    VoiceInfo(
                        voice_id=voice_id,
                        name=f"Svara {lang.upper()} {gender.title()}",
                        language=lang,
                        gender=VoiceGender.MALE if gender == "male" else VoiceGender.FEMALE,
                        style="expressive",
                        provider="svara",
                    )
                )
        return voices

    @classmethod
    def get_voice_for_persona(cls, persona_name: str, language: str = "hi") -> str:
        lang_code = language.split("-")[0].lower()
        persona_map = cls.PERSONA_VOICES.get(persona_name, {})
        if lang_code in persona_map:
            return persona_map[lang_code]
        return cls.DEFAULT_VOICES.get(lang_code, "hi_male")
