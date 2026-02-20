# 🏏 Suksham Vāchak (सूक्ष्म वाचक)

[![Release](https://img.shields.io/github/v/release/dev-globalveda/suksham-vachak)](https://img.shields.io/github/v/release/dev-globalveda/suksham-vachak)
[![Build status](https://img.shields.io/github/actions/workflow/status/dev-globalveda/suksham-vachak/main.yml?branch=main)](https://github.com/dev-globalveda/suksham-vachak/actions/workflows/main.yml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/dev-globalveda/suksham-vachak/branch/main/graph/badge.svg)](https://codecov.io/gh/dev-globalveda/suksham-vachak)
[![License](https://img.shields.io/github/license/dev-globalveda/suksham-vachak)](https://img.shields.io/github/license/dev-globalveda/suksham-vachak)

**"The Subtle Commentator"** — An intelligent cricket commentary engine powered by agentic AI.

> _A commentator who doesn't just describe… but understands._

## ✨ What is Suksham Vāchak?

Suksham Vāchak is a lightweight, agentic AI system designed to generate **natural, human-like cricket commentary** in real time or on replay, using structured match events as input.

It blends classical Indian philosophical precision (सूक्ष्म = subtle, fine-grained) with modern AI engineering to create a commentator that is insightful, expressive, and computationally efficient.

At its heart, Suksham Vāchak is:

- 🤖 A **GenAI-powered reasoning agent**
- 🎙️ A **commentary generator** with domain awareness
- 📦 A **small-footprint, containerized service** that can run even on a Raspberry Pi
- 💡 Built on the belief that _intelligence ≠ big infrastructure_ — subtle design and smart reasoning outperform brute force

## 🧠 Agentic AI Architecture

Suksham Vachak implements the **Agentic AI paradigm** — not just a model that responds, but a system that perceives, reasons, remembers, and acts.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         THE AGENTIC LOOP                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│    PERCEIVE         REASON           REMEMBER          ACT              │
│    ┌───────┐       ┌───────┐        ┌───────┐       ┌───────┐          │
│    │Parser │──────▶│Context│◀──────▶│ Stats │──────▶│Comment│          │
│    │       │       │Engine │        │ + RAG │       │Engine │          │
│    └───────┘       └───────┘        └───────┘       └───────┘          │
│        │               │                │               │               │
│    Cricsheet       Pressure          Matchups       "Four."            │
│    JSON            Momentum          History        + Audio            │
│    Events          Narrative         Parallels                         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

| Capability           | Component         | What It Does                                             |
| -------------------- | ----------------- | -------------------------------------------------------- |
| **Perception**       | Parser            | Observes match events, extracts structure                |
| **Reasoning**        | Context Engine    | Calculates pressure, detects momentum shifts             |
| **Long-term Memory** | Stats Engine      | Historical matchups, phase stats, player form            |
| **Episodic Memory**  | RAG (DejaVu)      | Recalls similar moments for callbacks                    |
| **Working Memory**   | Narrative Tracker | Current storyline, subplots, recent events               |
| **Planning**         | Phase + Form      | Anticipates trajectory based on patterns                 |
| **Personality**      | Personas          | Benaud (terse), Greig (dramatic), Bhogle (analytical)    |
| **Tool Use**         | LLM + TTS         | Claude/Ollama for text, Qwen3/Svara/ElevenLabs for voice |

**Why Agentic?** Traditional AI: `"Kohli hits four"` → `"Nice shot!"`. Agentic AI: Same event produces `"Four. That's 85 off Anderson now — Kohli owns this matchup."` because it _remembers_, _reasons_, and _understands context_.

> 📖 Deep dive: [docs/AGENTIC.md](docs/AGENTIC.md)

## 🌍 What Does It Do?

Takes **structured cricket event data** (ball-by-ball JSON feeds) and converts them into:

### 1. Natural Language Commentary

- _"Bumrah angles it in… beats the inside edge! Excellent variation."_
- Emotion, pacing, and context-aware phrasing
- Adaptation to game situations (powerplay, slog overs, milestones)

### 2. Analytical Reasoning

- Explains _why_ something happened
- Uses agentic reasoning (ReAct, CoT) for tactical insights
- Suggests momentum shifts, pressure scenarios, bowler strategies

### 3. Multi-Modal Output

- 🔊 Voice commentary via local TTS (Qwen3 for English, Svara for Hindi + 18 Indian languages) with ElevenLabs cloud fallback
- 🎭 Emotion-tagged Hindi speech — cricket events auto-mapped to expressive voice tags
- 📊 Optional real-time web dashboard _(Roadmap)_
- 📝 Export to logs, transcriptions, or score summaries

## 🎯 Who Is It For?

| Audience                             | Use Case                                                                                       |
| ------------------------------------ | ---------------------------------------------------------------------------------------------- |
| **Cricket Enthusiasts & Developers** | Build cricket apps, scoreboards, dashboards, or playful commentary systems                     |
| **AI & MLOps Learners**              | Learn model grounding, LLM reasoning loops, FastAPI, event-driven design, RAG, MongoDB, Docker |
| **You — the Architect**              | Fuse cloud architecture, GenAI engineering, Python backend design, and container orchestration |

## 🚀 Key Features

| Feature                         | Description                                                                                       |
| ------------------------------- | ------------------------------------------------------------------------------------------------- |
| **Event → Commentary Pipeline** | JSON input (`over`, `ball`, `runs`, `bowler`, `batsman`, `shot_type`) → contextualized commentary |
| **Agentic AI (ReAct + CoT)**    | Understands game state, evaluates pressure, generates tactical insights, maintains continuity     |
| **RAG for Cricket Memory**      | Lookups for player stats, ground history, strike rates, similar match situations                  |
| **Runs on Raspberry Pi**        | Optimized for low power, small model footprints, containerized deployment                         |
| **Modular Architecture**        | FastAPI backend, MongoDB 8.0, Agent Layer, React UI, Docker, DevContainer                         |

## 🛠️ Tech Stack

### Backend

- Python 3.12+
- FastAPI + Uvicorn
- MongoDB 8.0 (Docker)
- Pydantic for schemas
- LangChain / Microsoft Agent Framework

### AI / Reasoning

- OpenAI GPT models _or_ Local LLMs via Ollama/Umbrel
- Prompt Engineering, Chain-of-Thought, ReAct Agent Loop, RAG

### Frontend _(MVP)_

- React (Vite)
- Tailwind CSS
- Qwen3-TTS / Svara-TTS (local) with ElevenLabs fallback

### Deployment

- Docker Compose
- Nginx reverse proxy
- Local certificates via `step-ca`
- LAN / Cloudflare Tunnel

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/dev-globalveda/suksham-vachak.git
cd suksham-vachak

# Install dependencies
poetry install

# Activate pre-commit hooks
poetry run pre-commit install
```

## 🧪 Development

```bash
# Run tests
make test

# Run code quality checks
make check

# Serve documentation locally
make docs
```

## 📖 Documentation

- **GitHub**: <https://github.com/dev-globalveda/suksham-vachak/>
- **Docs**: <https://dev-globalveda.github.io/suksham-vachak/>

## 🔤 Why the Name?

In Sanskrit:

- **Sūkṣma (सूक्ष्म)** → subtle, precise, fine-grained
- **Vācak (वाचक)** → the one who speaks / narrates

Together: **"The speaker who perceives and expresses subtle detail."**

This captures the soul of the system — a commentator who doesn't just describe… but understands.

## 📄 License

This project is licensed under the terms of the [MIT License](LICENSE).

---

_Built with ❤️ for cricket and AI_
