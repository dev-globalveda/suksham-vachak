"""Tests for Qwen3-TTS provider (mocked HTTP)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from suksham_vachak.tts.base import AudioFormat, TTSError
from suksham_vachak.tts.qwen3 import Qwen3TTSProvider


class TestQwen3TTSProvider:
    """Tests for the Qwen3TTSProvider class."""

    def test_name(self) -> None:
        provider = Qwen3TTSProvider(base_url="http://test:7860")
        assert provider.name == "qwen3"

    def test_does_not_support_ssml(self) -> None:
        provider = Qwen3TTSProvider(base_url="http://test:7860")
        assert provider.supports_ssml is False

    def test_supports_english(self) -> None:
        provider = Qwen3TTSProvider()
        assert provider.supports_language("en") is True
        assert provider.supports_language("en-US") is True
        assert provider.supports_language("en-AU") is True

    def test_does_not_support_hindi(self) -> None:
        provider = Qwen3TTSProvider()
        assert provider.supports_language("hi") is False

    def test_does_not_support_tamil(self) -> None:
        provider = Qwen3TTSProvider()
        assert provider.supports_language("ta") is False

    def test_is_available_when_server_responds(self) -> None:
        provider = Qwen3TTSProvider(base_url="http://test:7860")
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(httpx.Client, "get", return_value=mock_response):
            assert provider.is_available() is True

    def test_is_not_available_when_server_down(self) -> None:
        provider = Qwen3TTSProvider(base_url="http://test:7860")

        with patch.object(httpx.Client, "get", side_effect=httpx.ConnectError("refused")):
            assert provider.is_available() is False

    def test_synthesize_returns_audio(self) -> None:
        provider = Qwen3TTSProvider(base_url="http://test:7860")
        fake_mp3 = b"\xff\xfb\x90\x00" + b"\x00" * 200

        mock_response = MagicMock()
        mock_response.content = fake_mp3
        mock_response.headers = {"x-sample-rate": "24000"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(httpx.Client, "post", return_value=mock_response) as mock_post:
            result = provider.synthesize(
                text="Gone! What a delivery!",
                voice_id="Ryan",
                language="en-AU",
                audio_format=AudioFormat.MP3,
            )

            assert result.format == AudioFormat.MP3
            assert result.audio_bytes == fake_mp3
            assert result.sample_rate == 24000
            assert result.voice_used == "Ryan"
            assert result.duration_seconds > 0

            # Verify the payload sent to server
            call_args = mock_post.call_args
            payload = call_args.kwargs.get("json") or call_args[1].get("json")
            assert payload["input"] == "Gone! What a delivery!"
            assert payload["voice"] == "Ryan"
            assert payload["response_format"] == "mp3"

    def test_synthesize_wav_format(self) -> None:
        provider = Qwen3TTSProvider(base_url="http://test:7860")
        fake_wav = b"RIFF" + b"\x00" * 200

        mock_response = MagicMock()
        mock_response.content = fake_wav
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock()

        with patch.object(httpx.Client, "post", return_value=mock_response):
            result = provider.synthesize(
                text="Four!",
                voice_id="Aiden",
                language="en",
                audio_format=AudioFormat.WAV,
            )
            assert result.format == AudioFormat.WAV

    def test_synthesize_http_error_raises(self) -> None:
        provider = Qwen3TTSProvider(base_url="http://test:7860")

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=mock_response
        )

        with (
            patch.object(httpx.Client, "post", return_value=mock_response),
            pytest.raises(TTSError, match="Qwen3-TTS synthesis failed"),
        ):
            provider.synthesize(text="test", voice_id="Ryan", language="en")

    def test_synthesize_connection_error_raises(self) -> None:
        provider = Qwen3TTSProvider(base_url="http://test:7860")

        with (
            patch.object(httpx.Client, "post", side_effect=httpx.ConnectError("refused")),
            pytest.raises(TTSError, match="Qwen3-TTS server unreachable"),
        ):
            provider.synthesize(text="test", voice_id="Ryan", language="en")

    def test_synthesize_empty_response_raises(self) -> None:
        provider = Qwen3TTSProvider(base_url="http://test:7860")

        mock_response = MagicMock()
        mock_response.content = b""
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock()

        with (
            patch.object(httpx.Client, "post", return_value=mock_response),
            pytest.raises(TTSError, match="empty audio"),
        ):
            provider.synthesize(text="test", voice_id="Ryan", language="en")


class TestQwen3VoiceMapping:
    """Tests for Qwen3 voice selection."""

    def test_benaud_gets_ryan(self) -> None:
        voice = Qwen3TTSProvider.get_voice_for_persona("Richie Benaud", "en")
        assert voice == "Ryan"

    def test_greig_gets_aiden(self) -> None:
        voice = Qwen3TTSProvider.get_voice_for_persona("Tony Greig", "en")
        assert voice == "Aiden"

    def test_unknown_persona_gets_default(self) -> None:
        voice = Qwen3TTSProvider.get_voice_for_persona("Unknown Commentator", "en")
        assert voice == "Ryan"

    def test_get_available_voices_english(self) -> None:
        provider = Qwen3TTSProvider()
        voices = provider.get_available_voices(language="en")
        assert len(voices) == 2
        assert all(v.provider == "qwen3" for v in voices)

    def test_get_available_voices_hindi_empty(self) -> None:
        provider = Qwen3TTSProvider()
        voices = provider.get_available_voices(language="hi")
        assert len(voices) == 0

    def test_get_available_voices_no_filter(self) -> None:
        provider = Qwen3TTSProvider()
        voices = provider.get_available_voices()
        assert len(voices) == 2
