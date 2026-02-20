# ADR-010: Ollama + Claude Auto-Detection for LLM

**Date:** 2026-01-08

**Status:** Accepted

**Deciders:** Aman Misra

## Context

The system needs LLM inference for commentary generation. Cloud APIs (Claude, GPT-4) provide quality but cost money and require internet. Local inference (Ollama) is free and fast but requires a capable machine. The system should work in both environments without manual configuration.

## Decision

- **Ollama** as the preferred local LLM runtime (OpenAI-compatible API)
- **Claude Haiku** as the default cloud model (cheapest, fastest; Sonnet/Opus available via explicit selection)
- **Auto-detection** via factory pattern: `create_llm_provider("auto")` pings Ollama first, falls back to Claude if `ANTHROPIC_API_KEY` is set
- Default Ollama model: **Qwen2.5 7B** (Q4_K_M quantization, ~5GB RAM, 6-8 tok/s on Pi 5)
- Uses the standard `openai` Python library for Ollama (OpenAI-compatible endpoint at `localhost:11434/v1`)

### Alternatives Considered

| Option             | Why Rejected                                                                                        |
| ------------------ | --------------------------------------------------------------------------------------------------- |
| GPT-4 / OpenAI     | "Claude follows persona instructions more reliably. GPT tends to be verbose regardless of prompts." |
| llama.cpp directly | No model management, harder to use than Ollama                                                      |
| vLLM               | Heavier, GPU-focused, not ideal for Pi                                                              |
| Foundry Local      | Originally recommended in roadmap but Ollama proved simpler                                         |
| langchain          | Unnecessary abstraction for direct API calls                                                        |

## Consequences

### Positive

- Zero-configuration: system auto-detects the best available provider
- Local Ollama is free and has no API latency
- `openai` library works for Ollama, OpenAI, and any compatible server — one dependency for all
- Claude Haiku is sufficient for short commentary (1-20 words per event)

### Negative

- Auto-detection adds a health-check round-trip on startup
- Ollama requires a separate install and model download (`ollama pull qwen2.5:7b`)
- Quality gap between Ollama/Qwen2.5 and Claude for complex commentary

### Risks

- Ollama API compatibility may drift from OpenAI spec over time
- Qwen2.5 7B Hindi output quality is significantly below Claude's
