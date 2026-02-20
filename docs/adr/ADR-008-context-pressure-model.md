# ADR-008: Context Builder with Multi-Factor Pressure Model

**Date:** 2026-01-05

**Status:** Accepted

**Deciders:** Aman Misra

## Context

Great commentary isn't about describing what happened — it's about understanding what it _means_. A wicket in the 3rd over is routine; a wicket in the 19th over of a chase is devastating. The system needs situational awareness to guide LLM generation.

## Decision

Build a **ContextBuilder** that processes every ball from 0.1 to the target ball, accumulating state. The builder produces a **RichContext** object containing:

- **Pressure score** (0.0-1.0): composite of phase base, chase pressure, wicket clusters, new batter vulnerability, and dot ball tension
- **Momentum state**: batting_dominant, bowling_dominant, balanced, or momentum_shift
- **Narrative arcs**: current storyline, subplots, milestones approaching
- **Batter/bowler context**: individual stats, recent form, matchup history

Five pressure levels: CALM (0.0-0.2), BUILDING (0.2-0.4), TENSE (0.4-0.6), INTENSE (0.6-0.8), CRITICAL (0.8-1.0).

### Alternatives Considered

| Option                         | Why Rejected                                                   |
| ------------------------------ | -------------------------------------------------------------- |
| Current-ball-only analysis     | Misses context entirely (no running totals, no momentum)       |
| Pre-computed stats per ball    | Would require preprocessing all matches; can't handle new data |
| ML-based excitement prediction | Needs training data we don't have; less interpretable          |
| Binary high/low pressure       | Too coarse; loses nuance between "building" and "critical"     |

## Consequences

### Positive

- Commentary adapts to match situation — same shot described differently at 10/0 vs 180/8
- Interpretable and tunable — each pressure factor has clear max contribution
- ContextBuilder is the single source of truth for match state
- Feeds directly into LLM prompt via TOON serialization

### Negative

- O(n) per request — must iterate through all balls up to the target
- Test matches (1000+ balls per innings) would need optimization
- Pressure model is heuristic, not data-driven — could be calibrated against real excitement metrics

### Risks

- Pressure weights are hand-tuned; may not match audience perception of "tense moments"
- Different match formats (T20 vs Test) may need different pressure curves
