# ADR-017: TOON Serialization for LLM Token Savings

**Date:** 2026-02-11

**Status:** Accepted

**Deciders:** Aman Misra

## Context

Every LLM API call costs per token. The system sends rich match context (match state, batter stats, bowler stats, pressure levels, narrative) to the LLM with every commentary request. JSON serialization of this context consumes significant tokens due to verbose keys, quotes, and brackets.

## Decision

Use **TOON (Token-Oriented Object Notation)** — a custom serialization format designed for LLM consumption. TOON uses short keys, no quotes, indentation-based nesting, and array length prefixes.

```
# JSON: 145 tokens
{"match": {"teams": ["India", "Australia"], "score": "145/3", ...}}

# TOON: ~85 tokens
M
  teams [2] India, Australia
  score 145/3
```

Enabled by default (`use_toon=True` in CommentaryEngine). The system prompt includes a TOON schema explanation so the LLM understands the format. A **custom encoder** was written because the `toon-format` library's encoder was not yet implemented.

Token savings: ~40% on match context, ~42% on batter context. At scale (300 matches/month on Claude Sonnet): ~$5.18/month savings.

### Alternatives Considered

| Option               | Why Rejected                                                 |
| -------------------- | ------------------------------------------------------------ |
| JSON (standard)      | 40-50% more tokens for the same information                  |
| YAML                 | Marginally better than JSON but still verbose                |
| MessagePack / binary | LLMs can't read binary formats                               |
| Just send less data  | Context richness directly correlates with commentary quality |

## Consequences

### Positive

- ~50% token savings per LLM call — compounds across thousands of match events
- LLMs understand TOON equally well as JSON (verified empirically)
- Custom encoder handles cricket-specific fields (chase context only when chasing, hat-trick only when relevant)
- Can be disabled per-request (`use_toon=False`) for debugging

### Negative

- Custom serialization format requires documentation and maintenance
- System prompt must explain TOON schema — adds fixed token overhead (~50 tokens)
- Cache key must include TOON flag (different prompts for same event depending on format)
- `toon-format` library dependency added even though we use our own encoder

### Risks

- Future LLMs may handle TOON differently (though the format is designed to be intuitive)
- If TOON library's encoder ships, we'll need to decide whether to migrate or keep custom encoder
