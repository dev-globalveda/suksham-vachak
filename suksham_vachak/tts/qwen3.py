"""Qwen3-TTS provider — HTTP client to an OpenAI-compatible local TTS server.

Qwen3-TTS provides high-quality English voice synthesis with voice cloning.
Runs as a local server (e.g., via vllm or a custom wrapper) exposing the
OpenAI-compatible `/v1/audio/speech` endpoint.

Environment variables:
    QWEN3_TTS_BASE_URL: Base URL of the Qwen3-TTS server (default: http://localhost:7860)
"""

from __future__ import annotations

import os
from typing import ClassVar

import httpx

from .base import AudioFormat, TTSError, TTSProvider, TTSResult, VoiceGender, VoiceInfo


class Qwen3TTSProvider(TTSProvider):
    """Qwen3-TTS provider for high-quality English speech synthesis.

    Connects to a local OpenAI-compatible TTS server. Supports voice cloning
    and multiple speaker presets.

    The server exposes POST /v1/audio/speech with:
    - model: model name (ignored by most local servers)
    - input: text to synthesize
    - voice: voice preset name
    - response_format: 'mp3', 'wav', 'opus'
    """

    # English-only provider
    SUPPORTED_LANGUAGES: ClassVar[set[str]] = {"en"}

    # Voice presets available on the server
    PERSONA_VOICES: ClassVar[dict[str, str]] = {
        "Richie Benaud": "Ryan",
        "Tony Greig": "Aiden",
        "Harsha Bhogle": "Ryan",
    }

    DEFAULT_VOICE = "Ryan"

    # Map our AudioFormat to OpenAI API format strings
    FORMAT_MAP: ClassVar[dict[AudioFormat, str]] = {
        AudioFormat.MP3: "mp3",
        AudioFormat.WAV: "wav",
        AudioFormat.OGG: "opus",
    }

    def __init__(self, base_url: str | None = None, timeout: float = 30.0) -> None:
        self._base_url = (base_url or os.environ.get("QWEN3_TTS_BASE_URL", "http://localhost:7860")).rstrip("/")
        self._timeout = timeout
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(base_url=self._base_url, timeout=self._timeout)
        return self._client

    @property
    def name(self) -> str:
        return "qwen3"

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
        language: str = "en-US",
        ssml: bool = False,
        audio_format: AudioFormat = AudioFormat.MP3,
    ) -> TTSResult:
        """Synthesize speech using Qwen3-TTS OpenAI-compatible endpoint.

        Args:
            text: Text to synthesize.
            voice_id: Voice preset name (e.g., 'Ryan', 'Aiden').
            language: Language code (only 'en' variants supported).
            ssml: Ignored (Qwen3-TTS doesn't support SSML).
            audio_format: Output format.

        Returns:
            TTSResult with audio bytes.
        """
        client = self._get_client()

        response_format = self.FORMAT_MAP.get(audio_format, "mp3")

        payload = {
            "model": "qwen3-tts",
            "input": text,
            "voice": voice_id,
            "response_format": response_format,
        }

        try:
            resp = client.post("/v1/audio/speech", json=payload)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            msg = f"Qwen3-TTS synthesis failed (HTTP {e.response.status_code}): {e.response.text}"
            raise TTSError(msg) from e
        except httpx.HTTPError as e:
            msg = f"Qwen3-TTS server unreachable: {e}"
            raise TTSError(msg) from e

        audio_bytes = resp.content
        if not audio_bytes:
            msg = "Qwen3-TTS returned empty audio"
            raise TTSError(msg)

        # Sample rate from headers or default (most servers use 24kHz)
        sample_rate = int(resp.headers.get("x-sample-rate", "24000"))

        # Estimate duration from text
        word_count = len(text.split())
        duration_estimate = word_count * 0.4

        return TTSResult(
            audio_bytes=audio_bytes,
            format=audio_format,
            sample_rate=sample_rate,
            duration_seconds=duration_estimate,
            voice_used=voice_id,
        )

    def get_available_voices(self, language: str | None = None) -> list[VoiceInfo]:
        if language and not language.split("-")[0].lower().startswith("en"):
            return []

        return [
            VoiceInfo(
                voice_id="Ryan",
                name="Ryan (Deep, Mature)",
                language="en",
                gender=VoiceGender.MALE,
                style="narrative",
                provider="qwen3",
            ),
            VoiceInfo(
                voice_id="Aiden",
                name="Aiden (Energetic)",
                language="en",
                gender=VoiceGender.MALE,
                style="dramatic",
                provider="qwen3",
            ),
        ]

    @classmethod
    def get_voice_for_persona(cls, persona_name: str, language: str = "en") -> str:
        return cls.PERSONA_VOICES.get(persona_name, cls.DEFAULT_VOICE)
