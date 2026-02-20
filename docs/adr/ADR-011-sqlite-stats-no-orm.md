# ADR-011: SQLite for Stats Engine, No ORM

**Date:** 2026-01-06

**Status:** Accepted

**Deciders:** Aman Misra

## Context

The stats engine needs to store player matchup data (head-to-head records, phase stats, player form) and serve aggregation queries efficiently. The system must run on a Raspberry Pi with limited resources.

## Decision

Use **SQLite** with raw SQL queries (no ORM). Schema includes indexed columns for batter+bowler pairs, match phases, and dates. The `stats/` module provides `StatsDB`, `PhaseEngine`, and `FormEngine` classes.

Player names are normalized via a dedicated `normalize.py` module to handle Cricsheet's inconsistent formatting (e.g., "V Kohli" → canonical ID `v_kohli`).

### Alternatives Considered

| Option         | Why Rejected                                                                        |
| -------------- | ----------------------------------------------------------------------------------- |
| PostgreSQL     | Requires separate server process; overkill for read-heavy workloads on Pi           |
| Redis          | In-memory only; stats data must persist across restarts                             |
| DuckDB         | Better for analytics but less mature and heavier                                    |
| SQLAlchemy ORM | Unnecessary abstraction for stats aggregation queries; adds complexity and overhead |
| Raw JSON files | No indexing, O(n) scan for every query                                              |

## Consequences

### Positive

- Zero-dependency, embedded database — no server process
- Perfect for Raspberry Pi (low memory, low disk)
- Raw SQL is simpler and faster for aggregation queries (GROUP BY, COUNT, AVG)
- Indexed columns provide fast lookups by batter+bowler pair
- Player name normalization ensures reliable matchup queries

### Negative

- No ORM means manual SQL query construction (risk of SQL injection if not careful)
- Schema migrations must be handled manually
- Single-writer limitation (acceptable for this workload)

### Risks

- SQLite write performance degrades under concurrent load (not a concern for single-user MVP)
- Name normalization may produce collisions for players with similar names
