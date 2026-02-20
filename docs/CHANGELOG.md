# Changelog

All notable changes to Suksham Vachak will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

_Nothing yet._

---

## [0.2.0] - 2026-02-20 — "Deshi Awaaz" (देशी आवाज़)

> _"Local Voice"_ — Self-hosted TTS replaces cloud dependency. Hindi gets a native voice engine, English gets voice cloning. ElevenLabs becomes the safety net, not the lifeline.

### Added

- **Qwen3-TTS provider** (`suksham_vachak/tts/qwen3.py`) — HTTP client to local OpenAI-compatible server on `:7860`. Default for English personas (Benaud, Greig). Supports voice cloning from 3-second samples.
- **Svara-TTS provider** (`suksham_vachak/tts/svara.py`) — HTTP client to local server on `:8080`. Default for Hindi (Doshi). Supports 19 Indian languages with emotion-tagged speech. PCM-to-WAV via stdlib, PCM-to-MP3 via ffmpeg (graceful fallback).
- **Emotion tag mapping** (`suksham_vachak/tts/emotion.py`) — Cricket EventType to Svara emotion tags (`<happy>`, `<surprise>`, `<anger>`, `<fear>`, `<clear>`). Contextual overrides for tense chase situations (wicket in chase = `<fear>`, six in tight finish = `<surprise>`).
- **Language-aware provider chains** — TTSEngine now routes by language:
  - English: `Qwen3 -> Svara -> ElevenLabs`
  - Hindi: `Svara -> ElevenLabs`
- **`supports_language()` on TTSProvider ABC** — Non-breaking addition. Providers declare which languages they handle. Engine skips unsupported providers automatically.
- **`_get_provider_chain(language)`** on TTSEngine — Returns ordered provider list for a language, configurable via `TTSConfig.language_providers`.
- **New environment variables**: `QWEN3_TTS_BASE_URL`, `SVARA_TTS_BASE_URL`
- **65 new tests** across 3 test files (`test_tts_qwen3.py`, `test_tts_svara.py`, `test_tts_emotion.py`) — all mocked, no server dependencies
- **CHANGELOG.md** — This file. Release cycle starts here.

### Changed

- **Default TTS provider**: `elevenlabs` -> `qwen3` (env: `TTS_PROVIDER`)
- **Default fallback provider**: `google` -> `svara` (env: `TTS_FALLBACK_PROVIDER`)
- **`TTSConfig`** now includes `language_providers` dict for per-language provider chains
- **`synthesize_commentary()`** — Now iterates language-aware chain, injects Svara emotion tags automatically, logs provider selection
- **`routes.py`** — Commentary endpoint uses TTSEngine with provider chain instead of hardcoded ElevenLabs
- **`__init__.py`** — `get_available_providers()` includes qwen3 and svara
- **ARCHITECTURE.md** — "Technology Radar" section replaced with full "TTS Provider Architecture" documentation

### Fixed

- Commentary endpoint no longer crashes when ElevenLabs API key is missing — gracefully falls through provider chain

### No New Dependencies

- `httpx` was already in `pyproject.toml`
- `wave` is Python stdlib
- `ffmpeg` is an optional system tool (graceful WAV fallback if missing)

---

## [0.1.0] - 2026-01-22 — "Pehli Awaaz" (पहली आवाज़)

> _"First Voice"_ — The prototype speaks. End-to-end pipeline from Cricsheet JSON to persona-driven audio commentary.

### Added

- **Cricsheet parser** — Ball-by-ball JSON parsing for 17,020 matches
- **Context engine** — Pressure levels, momentum shifts, narrative tracking, batter milestones
- **Commentary engine** — LLM-based generation with persona-enforced word limits and style constraints
- **3 personas**: Richie Benaud (minimalist), Tony Greig (dramatic), Sushil Doshi (Hindi)
- **TOON serialization** — Token-Oriented Object Notation for ~50% LLM token savings
- **ElevenLabs TTS** — Cloud TTS with persona-mapped voices and prosody control (SSML)
- **Ollama integration** — Local LLM inference with auto-detection and Claude API fallback
- **Template fallback** — Commentary generation works offline without any LLM
- **Stats engine** — SQLite-backed player matchups, phase analysis, form tracking
- **RAG engine** — Historical parallels via ChromaDB for "Deja Vu" callbacks
- **FastAPI backend** — `/api/commentary`, `/api/matches`, `/api/personas`, `/api/health`
- **Raspberry Pi deployment** — Edge deployment script for local inference
- **Structured logging** — Production-grade observability with structlog
- **Full test suite** — 177 tests covering parser, context, commentary, TTS, stats, RAG

---

## Release Naming Convention

Releases are named in Hindi/Urdu, reflecting the project's roots in Indian cricket commentary:

| Version | Codename                 | Meaning       |
| ------- | ------------------------ | ------------- |
| 0.1.0   | Pehli Awaaz (पहली आवाज़) | "First Voice" |
| 0.2.0   | Deshi Awaaz (देशी आवाज़) | "Local Voice" |

---

[Unreleased]: https://github.com/dev-globalveda/suksham-vachak/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/dev-globalveda/suksham-vachak/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/dev-globalveda/suksham-vachak/releases/tag/v0.1.0
