# ADR-014: TTS Provider Abstraction (Strategy Pattern)

**Date:** 2026-01-08

**Status:** Accepted

**Deciders:** Aman Misra

## Context

Multiple TTS providers are needed — some for English, some for Hindi, some cloud-based, some local. The engine must switch providers without changing calling code. Each provider has unique APIs, voice IDs, format quirks, and capabilities (SSML support, language support).

## Decision

Implement the **Strategy pattern** via an abstract base class `TTSProvider` with:

- `name` (property): provider identifier
- `supports_ssml` (property): whether SSML prosody tags work
- `supports_language(lang)`: whether a language is handled
- `synthesize(text, voice_id, language, ssml, audio_format)` → `TTSResult`
- `get_available_voices(language)` → `list[VoiceInfo]`
- `is_available()`: health check

`TTSEngine` orchestrates providers via `_get_provider(name)` with lazy initialization. Voice mapping is per-provider via `DEFAULT_VOICE_MAPPINGS` class variable and per-provider `get_voice_for_persona()` class methods.

Audio is cached by SHA256 hash of `(text, voice_id, event_type, persona_name)` in a file-based `.tts_cache/` directory.

### Alternatives Considered

| Option                                     | Why Rejected                                                                     |
| ------------------------------------------ | -------------------------------------------------------------------------------- |
| Direct API calls per provider              | No swapping, no fallback, duplicated error handling                              |
| Adapter pattern                            | Too indirect; Strategy is cleaner for "same interface, different implementation" |
| No abstraction                             | Impossible to support 5 providers cleanly                                        |
| DI framework (inject, dependency-injector) | Overkill; lazy dict-based instantiation is simpler                               |

## Consequences

### Positive

- Adding a new provider = one new file implementing `TTSProvider`, one registration in `_get_provider()`
- TTSEngine doesn't know which provider it's using — clean separation
- Provider-specific quirks (ElevenLabs strips SSML, Svara uses emotion tags, Qwen3 uses OpenAI endpoint) are encapsulated
- File-based cache with SHA256 keys prevents redundant synthesis

### Negative

- `get_voice_for_persona()` is a classmethod on each provider rather than a separate registry — slightly scattered
- Cache has no TTL — files accumulate until `clear_cache()` is called

### Risks

- Provider API changes require updates to individual provider files (but that's the point of encapsulation)
