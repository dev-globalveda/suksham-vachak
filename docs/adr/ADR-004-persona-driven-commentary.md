# ADR-004: Persona-Driven Commentary with Minimalism Score

**Date:** 2025-12-31

**Status:** Accepted

**Deciders:** Aman Misra

## Context

Generic AI commentary sounds bland. Real cricket commentary is defined by distinct voices — Benaud's silences, Greig's theatrics, Doshi's Hindi passion. The system needed a mechanism to enforce dramatically different output styles from the same LLM.

## Decision

Design **three distinct commentator personas** with a single controlling parameter: the **minimalism score** (0.0-1.0).

| Persona       | Minimalism | Behavior                                    |
| ------------- | ---------- | ------------------------------------------- |
| Richie Benaud | 0.95       | 1-3 words ("Gone."), silence on dot balls   |
| Tony Greig    | 0.20       | 5-20 words, dramatic, every ball is theatre |
| Sushil Doshi  | 0.60       | Expressive Hindi, punchy                    |

The minimalism score controls: word limits per event type, template selection (minimal vs verbose), LLM max_tokens budget, SSML pause durations, and even whether a dot ball produces output at all.

Word-limit enforcement is **belt-and-suspenders**: the LLM prompt specifies per-event word budgets AND the engine programmatically truncates any output exceeding the limit.

### Alternatives Considered

| Option                                           | Why Rejected                                                        |
| ------------------------------------------------ | ------------------------------------------------------------------- |
| Single "good commentary" model                   | No personality, no differentiation                                  |
| Style sliders (verbosity, excitement, formality) | Too many knobs; minimalism score captures the essential dimension   |
| Per-persona LLM fine-tuning only                 | LLMs are probabilistic — prompt-only control fails ~10% of the time |
| Separate engine per persona                      | Code duplication, hard to maintain                                  |

## Consequences

### Positive

- New personas = new dataclass instance with a different number. Extremely easy to extend.
- Silence ("") is a valid output — matches real commentator behavior
- Belt-and-suspenders enforcement means Benaud's "Gone." stays "Gone." regardless of LLM verbosity
- Demo "wow factor" — same ball described by three completely different voices

### Negative

- Minimalism score is a single axis — doesn't capture all dimensions (analytical vs dramatic, serious vs humorous)
- Word-limit truncation can cut mid-sentence (engine adds a period, but grammar may suffer)

### Risks

- Adding personas beyond the English/Hindi axis requires new language-specific templates and voice mappings
