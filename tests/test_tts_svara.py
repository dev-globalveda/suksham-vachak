"""Tests for Svara TTS provider (mocked HTTP + PCM conversion)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from suksham_vachak.tts.base import AudioFormat, TTSError
from suksham_vachak.tts.svara import (
    SVARA_SAMPLE_RATE,
    SvaraTTSProvider,
    pcm_to_mp3,
    pcm_to_wav,
)


def _make_pcm(num_samples: int = 2400, sample_rate: int = SVARA_SAMPLE_RATE) -> bytes:
    """Generate dummy 16-bit mono PCM data (silence)."""
    return b"\x00\x00" * num_samples


class TestPcmToWav:
    """Tests for PCM → WAV conversion."""

    def test_wav_has_riff_header(self) -> None:
        pcm = _make_pcm(1000)
        wav = pcm_to_wav(pcm)
        assert wav[:4] == b"RIFF"
        assert wav[8:12] == b"WAVE"

    def test_wav_size_larger_than_pcm(self) -> None:
        pcm = _make_pcm(1000)
        wav = pcm_to_wav(pcm)
        # WAV adds 44-byte header
        assert len(wav) > len(pcm)

    def test_wav_empty_pcm(self) -> None:
        wav = pcm_to_wav(b"")
        # Should still produce a valid WAV header
        assert wav[:4] == b"RIFF"


class TestPcmToMp3:
    """Tests for PCM → MP3 conversion."""

    def test_returns_none_when_ffmpeg_missing(self) -> None:
        with patch("suksham_vachak.tts.svara.subprocess.run", side_effect=FileNotFoundError):
            result = pcm_to_mp3(_make_pcm())
            assert result is None

    def test_returns_mp3_bytes_on_success(self) -> None:
        fake_mp3 = b"\xff\xfb\x90\x00" + b"\x00" * 100  # Fake MP3 frame header
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = fake_mp3

        with patch("suksham_vachak.tts.svara.subprocess.run", return_value=mock_result):
            result = pcm_to_mp3(_make_pcm())
            assert result == fake_mp3

    def test_returns_none_on_ffmpeg_failure(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = b""

        with patch("suksham_vachak.tts.svara.subprocess.run", return_value=mock_result):
            result = pcm_to_mp3(_make_pcm())
            assert result is None


class TestSvaraTTSProvider:
    """Tests for the SvaraTTSProvider class."""

    def test_name(self) -> None:
        provider = SvaraTTSProvider(base_url="http://test:8080")
        assert provider.name == "svara"

    def test_does_not_support_ssml(self) -> None:
        provider = SvaraTTSProvider(base_url="http://test:8080")
        assert provider.supports_ssml is False

    def test_supports_hindi(self) -> None:
        provider = SvaraTTSProvider()
        assert provider.supports_language("hi") is True
        assert provider.supports_language("hi-IN") is True

    def test_supports_english(self) -> None:
        provider = SvaraTTSProvider()
        assert provider.supports_language("en") is True

    def test_supports_tamil(self) -> None:
        provider = SvaraTTSProvider()
        assert provider.supports_language("ta") is True

    def test_does_not_support_french(self) -> None:
        provider = SvaraTTSProvider()
        assert provider.supports_language("fr") is False

    def test_is_available_when_server_responds(self) -> None:
        provider = SvaraTTSProvider(base_url="http://test:8080")
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(httpx.Client, "get", return_value=mock_response):
            assert provider.is_available() is True

    def test_is_not_available_when_server_down(self) -> None:
        provider = SvaraTTSProvider(base_url="http://test:8080")

        with patch.object(httpx.Client, "get", side_effect=httpx.ConnectError("refused")):
            assert provider.is_available() is False

    def test_synthesize_returns_wav_when_no_ffmpeg(self) -> None:
        provider = SvaraTTSProvider(base_url="http://test:8080")
        pcm_data = _make_pcm(2400)

        mock_response = MagicMock()
        mock_response.content = pcm_data
        mock_response.headers = {"x-sample-rate": "24000"}
        mock_response.raise_for_status = MagicMock()

        with (
            patch.object(httpx.Client, "post", return_value=mock_response),
            patch("suksham_vachak.tts.svara.pcm_to_mp3", return_value=None),
        ):
            result = provider.synthesize(
                text="शानदार!", voice_id="hi_male", language="hi-IN", audio_format=AudioFormat.MP3
            )
            # Falls back to WAV when ffmpeg unavailable
            assert result.format == AudioFormat.WAV
            assert result.audio_bytes[:4] == b"RIFF"
            assert result.sample_rate == 24000
            assert result.duration_seconds > 0

    def test_synthesize_returns_mp3_when_ffmpeg_available(self) -> None:
        provider = SvaraTTSProvider(base_url="http://test:8080")
        pcm_data = _make_pcm(2400)
        fake_mp3 = b"\xff\xfb" + b"\x00" * 100

        mock_response = MagicMock()
        mock_response.content = pcm_data
        mock_response.headers = {"x-sample-rate": "24000"}
        mock_response.raise_for_status = MagicMock()

        with (
            patch.object(httpx.Client, "post", return_value=mock_response),
            patch("suksham_vachak.tts.svara.pcm_to_mp3", return_value=fake_mp3),
        ):
            result = provider.synthesize(
                text="शानदार!", voice_id="hi_male", language="hi-IN", audio_format=AudioFormat.MP3
            )
            assert result.format == AudioFormat.MP3
            assert result.audio_bytes == fake_mp3

    def test_synthesize_wav_format(self) -> None:
        provider = SvaraTTSProvider(base_url="http://test:8080")
        pcm_data = _make_pcm(2400)

        mock_response = MagicMock()
        mock_response.content = pcm_data
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock()

        with patch.object(httpx.Client, "post", return_value=mock_response):
            result = provider.synthesize(text="Test", voice_id="en_male", language="en", audio_format=AudioFormat.WAV)
            assert result.format == AudioFormat.WAV

    def test_synthesize_http_error_raises(self) -> None:
        provider = SvaraTTSProvider(base_url="http://test:8080")

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=mock_response
        )

        with (
            patch.object(httpx.Client, "post", return_value=mock_response),
            pytest.raises(TTSError, match="Svara synthesis failed"),
        ):
            provider.synthesize(text="test", voice_id="hi_male", language="hi")

    def test_synthesize_connection_error_raises(self) -> None:
        provider = SvaraTTSProvider(base_url="http://test:8080")

        with (
            patch.object(httpx.Client, "post", side_effect=httpx.ConnectError("refused")),
            pytest.raises(TTSError, match="Svara server unreachable"),
        ):
            provider.synthesize(text="test", voice_id="hi_male", language="hi")

    def test_synthesize_empty_response_raises(self) -> None:
        provider = SvaraTTSProvider(base_url="http://test:8080")

        mock_response = MagicMock()
        mock_response.content = b""
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock()

        with (
            patch.object(httpx.Client, "post", return_value=mock_response),
            pytest.raises(TTSError, match="empty audio"),
        ):
            provider.synthesize(text="test", voice_id="hi_male", language="hi")


class TestSvaraVoiceMapping:
    """Tests for Svara voice selection."""

    def test_doshi_gets_hindi_male(self) -> None:
        voice = SvaraTTSProvider.get_voice_for_persona("Sushil Doshi", "hi")
        assert voice == "hi_male"

    def test_benaud_gets_english_male(self) -> None:
        voice = SvaraTTSProvider.get_voice_for_persona("Richie Benaud", "en")
        assert voice == "en_male"

    def test_unknown_persona_gets_default(self) -> None:
        voice = SvaraTTSProvider.get_voice_for_persona("Unknown", "hi")
        assert voice == "hi_male"

    def test_get_available_voices_hindi(self) -> None:
        provider = SvaraTTSProvider()
        voices = provider.get_available_voices(language="hi")
        assert len(voices) == 2  # male and female
        assert all(v.language == "hi" for v in voices)

    def test_get_available_voices_all(self) -> None:
        provider = SvaraTTSProvider()
        voices = provider.get_available_voices()
        # 19 languages x 2 genders
        assert len(voices) == 38
