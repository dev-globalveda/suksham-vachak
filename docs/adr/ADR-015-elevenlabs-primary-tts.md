# ADR-015: ElevenLabs as Primary TTS

**Date:** 2026-01-08

**Status:** Superseded by [ADR-019](ADR-019-local-tts-providers.md)

**Deciders:** Aman Misra

## Context

The original TTS implementation used Google Cloud TTS and Azure Speech. While functional, both produced robotic-sounding voices that didn't match the gravitas expected from cricket commentary personas. ElevenLabs offered significantly more natural speech synthesis with multilingual support.

## Decision

Switch to **ElevenLabs** as the primary TTS provider. Use pre-made voices mapped to personas:

| Persona | Voice               | Rationale                        |
| ------- | ------------------- | -------------------------------- |
| Benaud  | Adam (deep, mature) | Matches Benaud's measured tone   |
| Greig   | Antoni (energetic)  | Matches Greig's theatrical style |
| Doshi   | Adam (multilingual) | Best available Hindi voice       |

Model: `eleven_multilingual_v2` for Hindi, `eleven_turbo_v2_5` for English.

Google TTS retained as fallback.

### Alternatives Considered

| Option                 | Why Rejected                                      |
| ---------------------- | ------------------------------------------------- |
| Google Cloud TTS       | More robotic; kept as fallback                    |
| Azure Speech           | Better than Google but still noticeably synthetic |
| Amazon Polly           | Limited voice quality for this use case           |
| Local TTS (Bark, XTTS) | Not mature enough at the time (Jan 2026)          |

## Consequences

### Positive

- Dramatically better voice quality — commentary sounds human
- Multilingual support (Hindi via multilingual v2 model)
- Voice cloning capability for future authentic persona voices

### Negative

- **Per-character API costs** — expensive at scale ($0.30/1K characters)
- Requires internet access and API key
- No SSML support — prosody control via SSML is stripped

### Risks

- Cost becomes prohibitive at production volume (300+ matches/month)
- API dependency is a single point of failure for audio

---

_This decision was superseded by [ADR-019](ADR-019-local-tts-providers.md) in v0.2.0, which moved to local TTS (Qwen3 + Svara) as primary with ElevenLabs demoted to fallback._
