# ADR-012: ChromaDB + Voyage for RAG

**Date:** 2026-01-05

**Status:** Accepted

**Deciders:** Aman Misra

## Context

The commentary engine benefits from "Deja Vu" callbacks — referencing similar historical moments. This requires vector similarity search over past match events. The system needs an embedding provider and a vector store that can run on resource-constrained hardware.

## Decision

- **ChromaDB** for vector storage (lightweight, embedded, Python-native)
- **Voyage API** for text embeddings (`voyage-lite-02-instruct` for edge deployment)
- **Curated moment boost**: hand-picked iconic moments (Dhoni's WC2011 six, Stokes at Headingley) receive a 1.5x relevance multiplier

The RAG module is **optional** — installed via `poetry install --extras rag`. System works without it (just no historical parallels). Import guarded with try/except.

### Alternatives Considered

| Option                        | Why Rejected                                         |
| ----------------------------- | ---------------------------------------------------- |
| Pinecone                      | Cloud-only, costs money, requires network            |
| Weaviate                      | Heavier, requires separate server                    |
| FAISS                         | Low-level, no persistence built-in                   |
| pgvector                      | Requires PostgreSQL (see ADR-011)                    |
| OpenAI embeddings             | More expensive, less retrieval-optimized than Voyage |
| sentence-transformers (local) | Viable but adds heavy PyTorch dependency             |

## Consequences

### Positive

- ChromaDB runs embedded — no external server, Pi-friendly
- Voyage embeddings are optimized for retrieval (better than generic OpenAI embeddings)
- Curated moment boost ensures the most impactful historical parallels surface
- Optional dependency means core system stays lightweight

### Negative

- Voyage API requires network access and API key
- ChromaDB performance may degrade with very large collections (10K+ moments)
- 1.5x curated boost is a hard-coded heuristic

### Risks

- Voyage API could change pricing or deprecate models
- ChromaDB is a young project — API stability not guaranteed
