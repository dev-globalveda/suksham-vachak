# ADR-020: Cricket Emotion Tags for Svara TTS

**Date:** 2026-02-20

**Status:** Accepted

**Deciders:** Aman Misra

## Context

Svara TTS supports emotion-tagged speech via tags like `<happy>`, `<surprise>`, `<anger>`, `<fear>`, and `<clear>`. This capability is unique among our TTS providers and maps naturally to cricket events — a wicket should sound different from a dot ball. The question is how to map cricket events to emotions, and whether match context should influence the mapping.

## Decision

Create a dedicated **emotion mapping module** (`tts/emotion.py`) that:

1. Maps cricket `EventType` → Svara emotion tag (default mapping)
2. Applies **contextual overrides** when the match situation is tense (chasing a target with wickets falling or high required rate)
3. Injects the emotion tag as a prefix to the text before sending to Svara

### Default Mapping

| Event          | Tag          |
| -------------- | ------------ |
| WICKET         | `<surprise>` |
| SIX            | `<happy>`    |
| FOUR           | `<happy>`    |
| DOT_BALL       | `<clear>`    |
| WIDE / NO_BALL | `<anger>`    |

### Contextual Overrides (Tense Chase)

A chase is "tense" when: target exists AND (wickets >= 6 OR required rate > 8 rpo OR overs remaining <= 0).

| Event                 | Override                                  |
| --------------------- | ----------------------------------------- |
| WICKET in tense chase | `<fear>` (dread, not just surprise)       |
| SIX in tense chase    | `<surprise>` (relief/shock, not just joy) |

### Alternatives Considered

| Option                      | Why Rejected                                                |
| --------------------------- | ----------------------------------------------------------- |
| No emotion tags             | Wastes Svara's unique capability                            |
| Fixed mapping (no context)  | "A wicket is a wicket" misses the drama of a chase collapse |
| LLM-selected emotions       | Too slow; emotion must be determined before TTS call        |
| Per-persona emotion mapping | Over-engineering for v0.2.0; can be added later             |

## Consequences

### Positive

- Hindi commentary gains emotional expressiveness without LLM involvement
- Context-aware emotions: a wicket in a tight chase sounds fearful, not just surprised
- Pure functions — easily testable, no side effects
- Svara-specific — other providers ignore emotion tags (clean separation via engine)

### Negative

- Heuristic "tense chase" detection assumes T20 format (20 overs) — Test matches need different thresholds
- Only 5 emotion tags available — may not capture all commentary moods
- Emotion prefix adds a few characters to every Svara request

### Risks

- Svara's emotion tag interpretation may change across versions
- "Tense chase" heuristic may not match audience perception for all match situations
