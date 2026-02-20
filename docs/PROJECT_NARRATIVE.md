# Suksham Vachak: Project Narrative

> _सूक्ष्म वाचक — "The Subtle Commentator"_

---

## The Vision

Cricket has 2.5 billion fans worldwide, yet 95% of matches have no commentary. Human commentators cost $500–$10,000 per match and can only cover major tournaments. Thousands of domestic matches go silent every year — a problem for fans and especially for the 285 million visually impaired people who experience cricket entirely through audio.

**Suksham Vachak** is an AI-powered commentary platform that transforms ball-by-ball match data into natural, persona-driven commentary — capturing the understated elegance of Richie Benaud, the energy of Tony Greig, or the Hindi-English flair of Susheel Doshi. It runs on an $80 Raspberry Pi, costs $0.40 per match instead of $500, and is designed for B2B distribution to streaming platforms like Hotstar, ESPN, and Willow.tv.

---

## What We've Built

### Core Infrastructure

**LLM Provider Abstraction** — A clean architecture enabling seamless switching between cloud inference (Claude API) and edge deployment (Ollama). The factory pattern auto-detects available providers, preferring local inference for cost and latency.

```
Claude API (development) ←→ Provider Interface ←→ Ollama (production/Pi)
```

**Structured Logging** — Production-grade observability using structlog with JSON-formatted output, request correlation IDs, and performance metrics.

**FastAPI Backend** — Async API layer with `/api/commentary` for generation and `/api/llm/status` for provider health checks.

### Evaluation Harness

A complete benchmarking system for comparing quantized models on edge hardware:

- **Speed metrics**: tokens/second, latency at p50/p95/p99
- **Quality metrics**: brevity score, relevance, style adherence
- **CLI tool**: `scripts/evaluate_models.py` for automated testing

This allows us to objectively compare models like `qwen2.5:7b` vs `llama3.2:3b` on the Pi before committing to a fine-tuning run.

### Documentation & Training Pipeline

**Fine-Tuning Pipeline** — Complete workflow documented for QLoRA training on cloud GPU, GGUF conversion, and deployment to Ollama:

1. Collect persona transcripts (YouTube, Cricinfo, books)
2. Format as instruction-response pairs
3. Train with QLoRA (140GB VRAM → 6GB)
4. Merge adapters, convert to GGUF
5. Quantize to Q4_K_M (14GB → 3.5GB)
6. Deploy via Ollama Modelfile

**Persona Training Workflow** — Step-by-step guide covering both LLM style training (text) and voice cloning (audio) for creating complete commentator personas.

**LLM Fine-Tuning Primer** — Educational document explaining the _why_ behind LoRA, quantization, hyperparameters, and debugging — so training becomes second nature.

### SaaS Architecture

Designed multi-tenant B2B platform with:

- REST/WebSocket/Webhook APIs for streaming integration
- Usage-based pricing tiers (Starter $99, Pro $499, Enterprise custom)
- Integration patterns for Willow.tv, ESPN, Hotstar

---

## Technical Achievements

| Metric                    | Value                     |
| ------------------------- | ------------------------- |
| Training memory reduction | 140GB → 6GB (QLoRA)       |
| Model compression         | 14GB → 3.5GB (Q4_K_M)     |
| Edge inference speed      | 6–8 tokens/second on Pi 5 |
| Cost per match            | $0.40 (vs $500 human)     |
| Cost reduction            | 99%                       |

---

## What's Next

1. ~~**Fix TTS authentication**~~ ✅ Switched to ElevenLabs, then to local TTS (Qwen3 + Svara)
2. ~~**Local TTS providers**~~ ✅ Qwen3-TTS for English, Svara-TTS for Hindi + 18 Indian languages, ElevenLabs as fallback
3. **Collect Benaud training data** — YouTube transcripts, book quotes, Cricinfo archives
4. **First fine-tuning run** — QLoRA on Qwen 7B with ~500 Benaud examples
5. **Voice cloning** — Qwen3-TTS from 3-second audio samples
6. **End-to-end demo** — JSON → Commentary → Audio on Pi 5

---

## The Bottom Line

We've built the infrastructure for production AI commentary. The provider abstraction enables cloud-to-edge deployment. The evaluation harness ensures quality. The documentation makes persona creation repeatable.

What remains is execution: collect data, train personas, ship to users.

_Every match deserves commentary. Now it can have it._
