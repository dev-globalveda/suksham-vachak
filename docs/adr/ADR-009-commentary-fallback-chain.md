# ADR-009: Three-Layer Commentary Fallback Chain

**Date:** 2026-01-05

**Status:** Accepted

**Deciders:** Aman Misra

## Context

The system targets edge deployment (Raspberry Pi) where LLM inference may be unavailable, slow, or produce poor results. An AI commentary system that fails when the AI is down is useless. The system must always produce some output.

## Decision

Implement a **three-layer fallback chain** for commentary generation:

1. **LLM generation** (best quality) — Claude API or local Ollama
2. **Persona signature phrases** — hand-crafted per-persona responses per event type
3. **Template-based generation** — parameterized templates with batter/bowler names

The engine selects MINIMAL_TEMPLATES (for personas with minimalism > 0.7) or VERBOSE_TEMPLATES based on the persona's minimalism score. Word-limit enforcement truncates output and adds a period if the LLM exceeds its budget.

Additionally, the LLM provider itself has a fallback: `create_llm_provider("auto")` tries Ollama first, falls back to Claude.

### Alternatives Considered

| Option                         | Why Rejected                                              |
| ------------------------------ | --------------------------------------------------------- |
| LLM-only (fail if unavailable) | Unacceptable for edge deployment; single point of failure |
| Templates-only                 | Misses the entire point of AI commentary                  |
| Cache previous LLM outputs     | Doesn't work for novel match situations                   |

## Consequences

### Positive

- System **never fails** — even fully offline, templates produce coherent output
- Quality degrades gracefully: LLM → signature → template
- Belt-and-suspenders word limits ensure persona consistency even when LLM is verbose
- Enables meaningful offline demos without API keys

### Negative

- Template commentary is generic and repetitive
- Three layers of fallback add code complexity
- Word-limit truncation can cut mid-sentence

### Risks

- Users may not realize when they're getting template output vs LLM output (quality difference is noticeable but not flagged in the UI)
