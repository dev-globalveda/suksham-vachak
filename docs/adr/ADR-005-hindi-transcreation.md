# ADR-005: Hindi as Transcreation, Not Translation

**Date:** 2025-12-31

**Status:** Accepted

**Deciders:** Aman Misra

## Context

600M+ regional language speakers in India are underserved by English-only cricket commentary. The system needs Hindi support, but how? Machine translation produces stilted, unnatural output. Real Hindi commentators don't translate English — they think and emote in Hindi natively.

## Decision

Hindi is implemented as a **native-language persona** (Sushil Doshi), not as translation of English output. The LLM generates Hindi directly, guided by Hindi-specific persona prompts, templates, and emotion keys. Benaud's "Gone." becomes Doshi's "गया।" — not "वह आउट हो गया है।" (literal translation).

Each language gets its own persona with native-language:

- Templates and fallback phrases
- Emotion-specific vocabulary (Hindi phrases for wickets, sixes, etc.)
- TTS voice mapping (Hindi-specific voices)

### Alternatives Considered

| Option                                  | Why Rejected                                                         |
| --------------------------------------- | -------------------------------------------------------------------- |
| Machine translation (Google Translate)  | Stilted, loses emotion and style                                     |
| LLM-based translation of English output | Still filtered through English thinking; loses Hindi idiom           |
| Single multilingual persona             | Real commentators have one primary language; mixing feels artificial |

## Consequences

### Positive

- Hindi commentary sounds native, not translated
- Preserves persona minimalism (Doshi's "गया।" matches Benaud's "Gone." in spirit)
- Architecture extends naturally to other Indian languages (Tamil, Telugu, etc.)
- Aligns with Svara TTS emotion tags — Hindi text with native emotional expression

### Negative

- Each new language requires a dedicated persona (more work per language)
- Hindi template quality depends on the prompt engineer's Hindi fluency
- LLM Hindi output quality varies by model (Claude > most open-source models for Hindi)

### Risks

- Script mixing (Hindi text with English cricket terms) needs careful handling
- Hindi text evaluation is harder to automate than English
