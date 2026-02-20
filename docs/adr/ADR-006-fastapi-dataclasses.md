# ADR-006: FastAPI for API, Dataclasses for Domain Models

**Date:** 2026-01-02

**Status:** Accepted

**Deciders:** Aman Misra

## Context

The system needs an HTTP API layer for the frontend and future integrations. Domain objects (CricketEvent, Persona, RichContext, etc.) need structured representation. The choice of web framework and data modeling approach affects the entire codebase.

## Decision

- **FastAPI + Uvicorn** as the backend framework (async by default, auto-generated OpenAPI docs, Pydantic validation)
- **Python dataclasses** for domain models (CricketEvent, Persona, BatterContext, etc.)
- **Pydantic BaseModel** reserved exclusively for API request/response schemas

This creates a clean boundary: domain logic uses stdlib dataclasses (framework-agnostic), while the API layer uses Pydantic (validation, serialization).

### Alternatives Considered

| Option                  | Why Rejected                                                                  |
| ----------------------- | ----------------------------------------------------------------------------- |
| Flask                   | Synchronous by default, no built-in validation, no auto-docs                  |
| Django                  | Overkill for an API-only backend, heavy ORM we don't need                     |
| Pydantic for everything | Ties domain logic to a framework; dataclasses are simpler for internal models |
| attrs                   | Additional dependency for marginal benefit over stdlib dataclasses            |

## Consequences

### Positive

- FastAPI provides async endpoints, auto-generated OpenAPI docs, and Pydantic validation for free
- Domain models are framework-agnostic — can be used in CLI tools, scripts, tests without FastAPI
- Clean separation: API layer handles validation/serialization, domain layer handles logic
- Fastest Python web framework (on par with Node.js for I/O-bound workloads)

### Negative

- Two modeling patterns in one codebase (dataclass vs Pydantic) requires discipline
- FastAPI's dependency injection is underused (most dependencies are manual)

### Risks

- FastAPI ecosystem is younger than Flask/Django — some middleware/plugins may be missing
