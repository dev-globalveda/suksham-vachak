# ADR-003: Cricsheet as Sole Data Source with Iterator Parsing

**Date:** 2025-12-31

**Status:** Accepted

**Deciders:** Aman Misra

## Context

The commentary engine needs ball-by-ball match data. Options range from paid APIs (ESPNcricinfo, CricAPI) to free open datasets. For an MVP targeting offline/edge deployment, we needed a free, well-structured, comprehensive source that works without network access.

## Decision

Use **Cricsheet** (cricsheet.org) ball-by-ball JSON as the sole data source. 17,020 matches available. 20 sample matches committed to the repository for development; full dataset downloaded separately.

The parser uses a **generator/iterator pattern** — `parse_innings()` yields `CricketEvent` objects one ball at a time rather than loading all events into memory.

### Alternatives Considered

| Option                    | Why Rejected                                               |
| ------------------------- | ---------------------------------------------------------- |
| ESPNcricinfo API          | Paid, rate-limited, requires network                       |
| CricAPI / CricketData.org | Paid APIs, not suitable for offline edge deployment        |
| Synthetic/mock data       | Lacks the richness needed for realistic commentary testing |
| Cricsheet YAML format     | JSON format is faster to parse and matches our stack       |

## Consequences

### Positive

- Free, open-source, no API keys required
- 17K matches provides exhaustive test coverage across formats (T20, ODI, Test)
- Works completely offline — critical for Raspberry Pi deployment
- Iterator pattern keeps memory constant regardless of match length

### Negative

- No live data — only historical matches (live feed integration is a future phase)
- Sequential access only — finding a specific ball requires iterating from the start of the innings
- Cricsheet player names are inconsistent (e.g., "V Kohli" vs "Virat Kohli"), requiring normalization

### Risks

- Cricsheet format could change without notice (no SLA)
- 17K matches is ~2GB uncompressed; full dataset management needs care
