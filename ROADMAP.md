# Development Roadmap

> A-to-Z guardrails for building Suksham Vachak — the AI Cricket Commentator.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Suksham Vachak Pipeline                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │   Parser     │───▶│   Context    │───▶│  Commentary  │              │
│  │  (Cricsheet) │    │   Builder    │    │   Engine     │              │
│  └──────────────┘    └──────┬───────┘    └──────┬───────┘              │
│                             │                    │                       │
│              ┌──────────────┼──────────────┐    │                       │
│              ▼              ▼              ▼    ▼                       │
│       ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐       │
│       │  Stats   │   │   RAG    │   │ Narrative│   │   TTS    │       │
│       │  Engine  │   │ (DejaVu) │   │  Tracker │   │  Engine  │       │
│       └──────────┘   └──────────┘   └──────────┘   └──────────┘       │
│            │                                             │              │
│       ┌────┴────┐                                       │              │
│       ▼         ▼                                       ▼              │
│  ┌─────────┐ ┌─────────┐                         ┌──────────┐         │
│  │ Matchups│ │ Phase/  │                         │  Audio   │         │
│  │         │ │  Form   │                         │  Output  │         │
│  └─────────┘ └─────────┘                         └──────────┘         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Foundation (Complete)

### 1.1 Parser Layer

- [x] Cricsheet JSON parser with full event typing
- [x] Match info extraction (teams, venue, format, toss)
- [x] Ball-by-ball event stream with context
- [x] Key moment detection (wickets, boundaries, milestones)

### 1.2 Commentary Engine

- [x] Multi-persona system (Benaud, Greig, Bhogle)
- [x] Template-based generation for consistency
- [x] LLM integration (Anthropic Claude) for key moments
- [x] Persona traits: minimalist vs verbose, emotion range

### 1.3 TTS Engine

- [x] SSML prosody generation
- [x] Event-based prosody rules (wicket = dramatic pause, six = fast rate)
- [x] Provider abstraction (Google Cloud TTS, Azure Speech)
- [x] Voice mapping per persona

**Deliverables:**

```
suksham_vachak/
├── parser/           # Cricsheet parsing
│   ├── cricsheet.py  # Main parser
│   └── events.py     # Event types & models
├── commentary/       # Commentary generation
│   ├── engine.py     # Template + LLM hybrid
│   └── personas.py   # Benaud, Greig, Bhogle
└── tts/              # Text-to-speech
    ├── prosody.py    # SSML generation
    └── providers.py  # Google/Azure abstraction
```

---

## Phase 2: Intelligence Layer (Complete)

### 2.1 Context Engine

- [x] Match phase detection (powerplay, middle, death, sessions)
- [x] Pressure calculation with weighted factors
- [x] Momentum tracking (batting/bowling team advantage)
- [x] Narrative subplot detection (comeback, collapse, milestone chase)

### 2.2 RAG System (DejaVu)

- [x] ChromaDB vector store for historical moments
- [x] Moment embedding with match context
- [x] Similarity retrieval for callback commentary
- [x] Integration with ContextBuilder

### 2.3 Stats Engine

- [x] SQLite database for player statistics
- [x] Head-to-head matchup queries
- [x] Phase-based performance (powerplay SR, death economy)
- [x] Recent form with trend detection (improving/declining/stable)
- [x] CLI tools for stats queries

**Deliverables:**

```
suksham_vachak/
├── context/          # Match context
│   ├── models.py     # NarrativeState, pressure, momentum
│   ├── builder.py    # ContextBuilder orchestration
│   └── pressure.py   # Pressure calculation
├── rag/              # Retrieval-Augmented Generation
│   ├── dejavu.py     # ChromaDB retriever
│   └── models.py     # CricketMoment, RetrievedMoment
└── stats/            # Statistics engine
    ├── db.py         # SQLite layer
    ├── matchups.py   # Head-to-head queries
    ├── phases.py     # Phase performance
    ├── form.py       # Recent form & trends
    └── cli.py        # Command-line interface
```

---

## Phase 3: Enhancement (In Progress)

### 3.1 Forecasting Engine

- [ ] Win probability model (match state features)
- [ ] Run rate projections (current vs required)
- [ ] Wicket probability (phase + matchup based)
- [ ] Integration with commentary context

### 3.2 Live Data Integration

- [ ] Real-time cricket API connection
- [ ] Event streaming with WebSocket
- [ ] Score synchronization
- [ ] Delay compensation for broadcast sync

### 3.3 Voice Enhancement

- [ ] ElevenLabs voice cloning integration
- [ ] Custom voice profiles per persona
- [ ] Emotion-aware voice modulation
- [ ] Multi-language support (Hindi, Tamil, Telugu)

---

## Phase 4: Production (Planned)

### 4.1 API & Deployment

- [ ] FastAPI REST endpoints
- [ ] WebSocket for live streaming
- [ ] Docker containerization
- [ ] Cloud deployment (AWS/GCP)

### 4.2 Frontend

- [ ] React web application
- [ ] Avatar/persona selection UI
- [ ] Live commentary display
- [ ] Audio player with visualization

### 4.3 Edge Deployment

- [ ] Raspberry Pi optimization
- [ ] Local LLM inference (Ollama/Foundry)
- [ ] Offline mode with cached stats
- [ ] LAN streaming capability

---

## Progress Tracker

| Phase | Component         | Status      |
| ----- | ----------------- | ----------- |
| 1.1   | Parser            | Complete    |
| 1.2   | Commentary Engine | Complete    |
| 1.3   | TTS Engine        | Complete    |
| 2.1   | Context Engine    | Complete    |
| 2.2   | RAG (DejaVu)      | Complete    |
| 2.3   | Stats Engine      | Complete    |
| 3.1   | Forecasting       | Not Started |
| 3.2   | Live Data         | Not Started |
| 3.3   | Voice Enhancement | Not Started |
| 4.1   | API & Deployment  | Not Started |
| 4.2   | Frontend          | Not Started |
| 4.3   | Edge Deployment   | Not Started |

---

## CLI Quick Reference

```bash
# Stats queries
python -m suksham_vachak.stats.cli matchup "V Kohli" "JM Anderson"
python -m suksham_vachak.stats.cli phase "DA Warner" powerplay --format ODI
python -m suksham_vachak.stats.cli form "MA Starc" --bowler

# Data ingestion
python -m suksham_vachak.stats.cli ingest
python -m suksham_vachak.stats.cli clear

# RAG indexing
python -m suksham_vachak.rag.cli index
python -m suksham_vachak.rag.cli search "dramatic wicket"

# Demo
python demo_llm_commentary.py --rag --stats
```

---

## Resources

- **Cricket Data:** [Cricsheet.org](https://cricsheet.org/) (free ball-by-ball)
- **LLM:** [Anthropic Claude](https://anthropic.com/), [OpenAI](https://openai.com/)
- **TTS:** [Google Cloud TTS](https://cloud.google.com/text-to-speech), [Azure Speech](https://azure.microsoft.com/en-us/products/ai-services/text-to-speech), [ElevenLabs](https://elevenlabs.io/)
- **Vector DB:** [ChromaDB](https://www.trychroma.com/)
- **Local LLM:** [Ollama](https://ollama.ai/), [Foundry Local](https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-local/)

---

_Last updated: January 2025_
