# ADR-019: Local TTS Providers (Qwen3 + Svara) with Language-Aware Chains

**Date:** 2026-02-20

**Status:** Accepted

**Deciders:** Aman Misra

**Supersedes:** [ADR-015](ADR-015-elevenlabs-primary-tts.md)

## Context

ElevenLabs (ADR-015) provides excellent voice quality but charges per character — unsustainable for production (300+ matches/month). The system also targets Raspberry Pi edge deployment where cloud APIs add latency and require internet. Two open-source, locally-hosted TTS solutions have matured enough for production use.

## Decision

Add two local TTS providers and implement **language-aware provider chains**:

- **Qwen3-TTS** (default for English): local OpenAI-compatible server on `:7860`. Voice cloning from 3-second samples. English only.
- **Svara-TTS** (default for Hindi): local server on `:8080`. 19 Indian languages with emotion tags. Returns raw PCM audio.
- **ElevenLabs** (demoted to fallback): cloud API, last resort only.

Provider chains per language:

```
English: Qwen3-TTS → Svara-TTS → ElevenLabs
Hindi:   Svara-TTS → ElevenLabs
```

The engine automatically skips providers that don't support the requested language and falls through the chain on failure.

No new Python dependencies — `httpx` was already in `pyproject.toml`, `wave` is stdlib, `ffmpeg` (for PCM→MP3) is optional with graceful WAV fallback.

### Alternatives Considered

| Option                     | Why Rejected                                                                     |
| -------------------------- | -------------------------------------------------------------------------------- |
| Keep ElevenLabs as primary | Too expensive for production volume                                              |
| Bark (Suno)                | Lower quality, slower, no Hindi                                                  |
| Coqui XTTS                 | Heavier model, less stable                                                       |
| Piper TTS                  | Good quality but limited language support                                        |
| Single local provider      | No single provider covers both English (quality) and Hindi (19 Indian languages) |

## Consequences

### Positive

- **Zero per-character cost** for TTS — critical for production economics
- **No internet required** — full edge deployment on Pi
- Language-aware chains mean Hindi commentary automatically routes to Svara, English to Qwen3
- Graceful degradation: if local servers are down, ElevenLabs catches requests
- Emotion tags in Svara make Hindi commentary more expressive (see ADR-020)
- PCM→WAV fallback works everywhere without ffmpeg

### Negative

- Two servers to manage locally (Qwen3 on `:7860`, Svara on `:8080`)
- Qwen3 requires GPU for reasonable latency
- Svara returns raw PCM — requires conversion step (adds ~50ms for ffmpeg, more for WAV)
- Voice quality slightly below ElevenLabs (acceptable tradeoff for cost savings)

### Risks

- Both Qwen3-TTS and Svara are young open-source projects — API stability not guaranteed
- GPU requirement for Qwen3 may not be available on all Pi deployments
- ffmpeg may not be installed on minimal deployments (WAV fallback is larger)
