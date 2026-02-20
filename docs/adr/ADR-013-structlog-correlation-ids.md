# ADR-013: structlog with Correlation IDs

**Date:** 2026-01-08

**Status:** Accepted

**Deciders:** Aman Misra

## Context

Production observability requires structured, queryable logs. Python's stdlib logging is text-based and hard to parse at scale. The system also needs request-level tracing across components (parser → context → LLM → TTS).

## Decision

- **structlog** for structured logging with JSON output in production and pretty console in development
- **Dual-mode configuration**: `LOG_ENV=production` produces JSON (for log aggregation), otherwise pretty console output
- **Correlation ID middleware**: custom FastAPI middleware propagates `X-Correlation-ID` header through all logs in a request, using Python `contextvars`
- Short 8-character UUID for correlation IDs (readable in logs)
- Per-module logger via `get_logger(__name__)`

### Alternatives Considered

| Option             | Why Rejected                                                    |
| ------------------ | --------------------------------------------------------------- |
| stdlib logging     | Text-based, hard to parse, no built-in structured output        |
| loguru             | Nice API but less control over output format, smaller ecosystem |
| python-json-logger | JSON output only — no pretty console mode for development       |
| OpenTelemetry      | Full tracing framework is overkill for MVP; can be added later  |

## Consequences

### Positive

- Every log entry includes structured context (match_id, persona, provider, etc.)
- Correlation IDs enable end-to-end request tracing without external APM tools
- Dual-mode means developers see readable logs, production sees parseable JSON
- Context binding (`.bind(match_id=...)`) flows through all function calls

### Negative

- structlog has a learning curve compared to stdlib logging
- JSON logs are verbose (larger log files in production)

### Risks

- `contextvars`-based correlation IDs may not propagate correctly in some async patterns
