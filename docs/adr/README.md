# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for Suksham Vachak.

ADRs document significant architectural and engineering decisions made during the project's lifecycle. They provide context for future contributors about _why_ things are the way they are.

## Index

| ADR                                                | Title                                                          | Status                | Date       |
| -------------------------------------------------- | -------------------------------------------------------------- | --------------------- | ---------- |
| [ADR-001](ADR-001-poetry-cookiecutter-scaffold.md) | Poetry + Cookiecutter Project Scaffold                         | Accepted              | 2025-12-05 |
| [ADR-002](ADR-002-ruff-pyright-precommit.md)       | Ruff, Pyright Strict, and Pre-commit for Code Quality          | Accepted              | 2025-12-05 |
| [ADR-003](ADR-003-cricsheet-data-source.md)        | Cricsheet as Sole Data Source with Iterator Parsing            | Accepted              | 2025-12-31 |
| [ADR-004](ADR-004-persona-driven-commentary.md)    | Persona-Driven Commentary with Minimalism Score                | Accepted              | 2025-12-31 |
| [ADR-005](ADR-005-hindi-transcreation.md)          | Hindi as Transcreation, Not Translation                        | Accepted              | 2025-12-31 |
| [ADR-006](ADR-006-fastapi-dataclasses.md)          | FastAPI for API, Dataclasses for Domain Models                 | Accepted              | 2026-01-02 |
| [ADR-007](ADR-007-nextjs-frontend.md)              | Next.js + Tailwind Over Streamlit                              | Accepted              | 2026-01-03 |
| [ADR-008](ADR-008-context-pressure-model.md)       | Context Builder with Multi-Factor Pressure Model               | Accepted              | 2026-01-05 |
| [ADR-009](ADR-009-commentary-fallback-chain.md)    | Three-Layer Commentary Fallback Chain                          | Accepted              | 2026-01-05 |
| [ADR-010](ADR-010-ollama-claude-auto-detection.md) | Ollama + Claude Auto-Detection for LLM                         | Accepted              | 2026-01-08 |
| [ADR-011](ADR-011-sqlite-stats-no-orm.md)          | SQLite for Stats Engine, No ORM                                | Accepted              | 2026-01-06 |
| [ADR-012](ADR-012-chromadb-voyage-rag.md)          | ChromaDB + Voyage for RAG                                      | Accepted              | 2026-01-05 |
| [ADR-013](ADR-013-structlog-correlation-ids.md)    | structlog with Correlation IDs                                 | Accepted              | 2026-01-08 |
| [ADR-014](ADR-014-tts-provider-abstraction.md)     | TTS Provider Abstraction (Strategy Pattern)                    | Accepted              | 2026-01-08 |
| [ADR-015](ADR-015-elevenlabs-primary-tts.md)       | ElevenLabs as Primary TTS                                      | Superseded by ADR-019 | 2026-01-08 |
| [ADR-016](ADR-016-docker-raspberry-pi.md)          | Docker Deployment Targeting Raspberry Pi 5                     | Accepted              | 2026-01-05 |
| [ADR-017](ADR-017-toon-serialization.md)           | TOON Serialization for LLM Token Savings                       | Accepted              | 2026-02-11 |
| [ADR-018](ADR-018-agentic-architecture.md)         | Agentic AI Architecture Pattern                                | Accepted              | 2026-01-08 |
| [ADR-019](ADR-019-local-tts-providers.md)          | Local TTS Providers (Qwen3 + Svara) with Language-Aware Chains | Accepted              | 2026-02-20 |
| [ADR-020](ADR-020-emotion-tags-svara.md)           | Cricket Emotion Tags for Svara TTS                             | Accepted              | 2026-02-20 |

## Convention

- ADRs are numbered sequentially (ADR-001, ADR-002, ...)
- Statuses: `Proposed`, `Accepted`, `Deprecated`, `Superseded by [ADR-XXX]`
- Once accepted, ADRs are immutable. New decisions supersede old ones via new ADRs.
- Deciders default to "Aman Misra" unless otherwise noted.
