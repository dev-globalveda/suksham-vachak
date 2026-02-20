# ADR-018: Agentic AI Architecture Pattern

**Date:** 2026-01-08

**Status:** Accepted

**Deciders:** Aman Misra

## Context

The system has multiple distinct capabilities: perceiving match events, reasoning about context, remembering history, tracking narratives, and generating output. These map naturally to cognitive agent concepts from AI research. The architecture needed a unifying paradigm that makes the system's intelligence legible.

## Decision

Frame the system as an **Agentic AI** with a Perceive-Reason-Remember-Plan-Act loop:

| Capability           | Component            | Function                                        |
| -------------------- | -------------------- | ----------------------------------------------- |
| **Perception**       | Parser               | Observes match events, extracts structure       |
| **Reasoning**        | Context Engine       | Calculates pressure, detects momentum shifts    |
| **Long-term Memory** | Stats Engine         | Historical matchups, phase stats, player form   |
| **Episodic Memory**  | RAG (DejaVu)         | Recalls similar moments for callbacks           |
| **Working Memory**   | Narrative Tracker    | Current storyline, subplots, recent events      |
| **Planning**         | Phase + Form Engines | Anticipates trajectory based on patterns        |
| **Personality**      | Personas             | Benaud (terse), Greig (dramatic), Doshi (Hindi) |
| **Action**           | Commentary + TTS     | Generates text and audio output                 |

This is an architectural pattern, not a framework dependency. Each component is a regular Python module — the agentic framing provides conceptual clarity, not runtime infrastructure.

### Alternatives Considered

| Option                               | Why Rejected                                                                         |
| ------------------------------------ | ------------------------------------------------------------------------------------ |
| Simple pipeline (Parser → LLM → TTS) | Misses the richness of context, memory, and narrative tracking                       |
| Microservices                        | Network overhead between components is unnecessary for a single-machine system       |
| LangChain/LangGraph agent            | Framework dependency for what's really a design pattern; our needs are more specific |
| Monolithic "do everything" function  | Unmaintainable, untestable                                                           |

## Consequences

### Positive

- Clear separation of concerns — each "capability" maps to one module
- Interview-friendly: maps directly to academic AI agent literature (ReAct, cognitive architectures)
- Makes the system's intelligence legible: "Traditional AI: 'Kohli hits four' → 'Nice shot!'. Agentic AI: same event produces 'Four. That's 85 off Anderson now — Kohli owns this matchup.'"
- Future MCP (Model Context Protocol) server decomposition maps naturally to these capabilities

### Negative

- "Agentic" is a buzzword — the system is really a well-structured pipeline with shared state
- No actual autonomous agent loop (no self-directed goal pursuit or tool selection)

### Risks

- Over-selling the "agentic" angle could create unrealistic expectations about autonomy
- The pattern adds conceptual overhead for contributors who just want to fix a bug
