# 🗺️ Development Roadmap

> A-to-Z guardrails for building Suksham Vāchak — the AI Cricket Commentator.

This roadmap prioritizes getting a working prototype quickly using cloud APIs, then enhancing it in later stages.

---

## Phase 0: Setup and Environment ✅

**Status:** Complete

- **Action:** Used Cookiecutter + Manual Hybrid approach to establish the project structure and initialize Poetry.
- **Environment:** macOS, VS Code/Cursor, Python/Poetry, GitHub.
- **Outcome:** A clean, version-controlled repository with necessary folders (`suksham_vachak/`, `config/`, `data/`, `tests/`, `notebooks/`).

---

## Phase 1: The "Talking Robot" MVP

**Goal:** Prove that you can get cricket data and turn it into spoken Hindi audio.

| Step    | Task                     | Details                                                                                                                                                                                                                                                                                         |
| ------- | ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1.1** | **Data Ingestion**       | Connect to a cricket data API or use mock data. Write Python code in `suksham_vachak/processing.py` to parse events. Use [Cricsheet.org](https://cricsheet.org/) (free) for development, or paid APIs (CricAPI, CricketData.org) for live data.                                                 |
| **1.2** | **Prompt Engineering**   | Design the initial AI prompt in `notebooks/`. Iterate on: _"You are an experienced Hindi cricket commentator. Given the event '[EVENT]', describe the action in a fluent and exciting way."_                                                                                                    |
| **1.3** | **LLM API Integration**  | Use the `openai` library in `suksham_vachak/llm_api.py`. **Recommended:** Use [Foundry Local](https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-local/) for free local inference during development. Design provider-agnostic code to switch between Foundry Local, Ollama, or OpenAI. |
| **1.4** | **Text-to-Speech (TTS)** | Convert text to audio using Google Cloud TTS or Azure AI Speech. Write logic in `suksham_vachak/tts_engine.py`.                                                                                                                                                                                 |
| **1.5** | **Basic API + Output**   | Write `suksham_vachak/main.py` to orchestrate steps 1.1–1.4. Add a minimal FastAPI endpoint for future extensibility. Play audio locally using `playsound` or `pyaudio`.                                                                                                                        |

**📦 P1 Outcome:** A basic system that announces game events with a generic AI voice.

### Phase 1 Deliverables

```
suksham_vachak/
├── processing.py    # Event parsing & data ingestion
├── llm_api.py       # LLM integration (Foundry Local/OpenAI/Ollama)
├── tts_engine.py    # Text-to-speech conversion
└── main.py          # Orchestration & FastAPI app

data/
└── raw/             # Mock cricket data (Cricsheet YAML/JSON)

notebooks/
└── prompt_engineering.ipynb

config/
└── settings.toml    # API keys, model config
```

### Provider-Agnostic LLM Design

Design `llm_api.py` to work with multiple backends (all use OpenAI-compatible APIs):

```python
# suksham_vachak/llm_api.py
from enum import Enum
from openai import OpenAI

class LLMProvider(Enum):
    FOUNDRY_LOCAL = "foundry"   # Local dev (free)
    OLLAMA = "ollama"           # Edge/Raspberry Pi
    OPENAI = "openai"           # Cloud production

PROVIDER_CONFIG = {
    LLMProvider.FOUNDRY_LOCAL: {"base_url": "http://localhost:5272/v1", "api_key": "foundry"},
    LLMProvider.OLLAMA: {"base_url": "http://localhost:11434/v1", "api_key": "ollama"},
    LLMProvider.OPENAI: {"base_url": "https://api.openai.com/v1", "api_key": "YOUR_KEY"},
}

def get_client(provider: LLMProvider = LLMProvider.FOUNDRY_LOCAL) -> OpenAI:
    config = PROVIDER_CONFIG[provider]
    return OpenAI(base_url=config["base_url"], api_key=config["api_key"])
```

---

## Phase 2: Feature Enhancement & Avatars

**Goal:** Add distinct commentator personalities and better context.

| Step    | Task                     | Details                                                                                                                                                                                                                 |
| ------- | ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **2.1** | **Avatar Configuration** | Implement `config/avatars.yaml`. Create logic to dynamically swap the _system prompt_ based on selected avatar (e.g., `avatar: susheel_doshi` → Hindi poetic style, `avatar: tony_greig` → Australian energetic style). |
| **2.2** | **Voice Cloning**        | Upgrade TTS fidelity using [ElevenLabs](https://elevenlabs.io/). Map each avatar to a distinct voice profile. Ensure you have rights to use voices commercially.                                                        |
| **2.3** | **RAG Implementation**   | Add game context with Retrieval-Augmented Generation. Store match statistics/history in ChromaDB or SQLite. Retrieve relevant data _before_ calling the LLM API.                                                        |
| **2.4** | **Testing**              | Write unit tests in `tests/` to ensure data processing and API calls are robust. Mock external APIs for reliable CI.                                                                                                    |

**📦 P2 Outcome:** Context-aware commentary with character-specific voices and tones.

### Avatar Configuration Example

```yaml
# config/avatars.yaml
avatars:
  susheel_doshi:
    name: "Susheel Doshi"
    language: hi
    style: "Poetic, dramatic Hindi commentary with classical references"
    voice_id: "elevenlabs_voice_id_here"
    system_prompt: |
      You are Susheel Doshi, a legendary Hindi cricket commentator known for
      poetic descriptions and dramatic flair. Use Hindi with occasional
      Urdu/Sanskrit flourishes. Build excitement progressively.

  tony_greig:
    name: "Tony Greig"
    language: en
    style: "Energetic Australian style with technical insights"
    voice_id: "elevenlabs_voice_id_here"
    system_prompt: |
      You are an energetic cricket commentator in the style of Tony Greig.
      Provide technical insights, use cricket jargon, and build excitement
      with phrases like "That's gone all the way!"
```

---

## Phase 3: Operations & Deployment

**Goal:** Move from local Mac to scalable deployment.

| Step    | Task                     | Details                                                                                                                                     |
| ------- | ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| **3.1** | **Containerization**     | Finalize `Dockerfile` with Poetry commands. Ensure production-ready Linux container.                                                        |
| **3.2** | **Cloud Hosting**        | Select cloud provider (AWS/GCP/Azure). Set up VM instance or Kubernetes cluster.                                                            |
| **3.3** | **CI/CD Pipeline**       | Configure GitHub Actions (`.github/workflows/main.yml`) to auto-build and deploy on push to `main`.                                         |
| **3.4** | **Monitoring & Logging** | Integrate logging (ELK stack or cloud-native). Track errors, API costs, latency, AI response quality.                                       |
| **3.5** | **Edge Deployment**      | Deploy to Raspberry Pi using Docker Compose. Use Foundry Local or Ollama for local LLM inference. Configure Nginx + step-ca for LAN access. |

**📦 P3 Outcome:** An automatically deployed, scalable, and monitored application.

### Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Cloud / Edge                         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Nginx     │───▶│  FastAPI    │───▶│  MongoDB    │     │
│  │  (reverse   │    │  (main.py)  │    │  (events &  │     │
│  │   proxy)    │    │             │    │  history)   │     │
│  └─────────────┘    └──────┬──────┘    └─────────────┘     │
│                            │                                │
│                     ┌──────▼──────┐                        │
│                     │ Agent Layer │                        │
│                     │ (LLM + RAG) │                        │
│                     └──────┬──────┘                        │
│                            │                                │
│                     ┌──────▼──────┐                        │
│                     │ TTS Engine  │                        │
│                     │ (ElevenLabs)│                        │
│                     └─────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 4: Polish & Production

| Step    | Task                     | Details                                                                                                   |
| ------- | ------------------------ | --------------------------------------------------------------------------------------------------------- |
| **4.1** | **Latency Optimization** | Fine-tune data polling frequency. Explore model quantization for edge deployment.                         |
| **4.2** | **UI/UX Development**    | Build React frontend for avatar selection, live commentary display, and voice playback.                   |
| **4.3** | **Security Audit**       | Check for prompt injection vulnerabilities. Secure API keys with environment variables / secret managers. |
| **4.4** | **Beta Release**         | Launch closed beta to gather feedback on commentary quality and sync issues.                              |

**📦 P4 Outcome:** Production-ready application with polished UX and security.

---

## 📊 Progress Tracker

| Phase             | Status         | Target   |
| ----------------- | -------------- | -------- |
| Phase 0: Setup    | ✅ Complete    | —        |
| Phase 1: MVP      | 🔲 Not Started | Week 1-2 |
| Phase 2: Features | 🔲 Not Started | Week 3-4 |
| Phase 3: DevOps   | 🔲 Not Started | Week 5-6 |
| Phase 4: Polish   | 🔲 Not Started | Week 7-8 |

---

## 🔗 Resources

- **Cricket Data:** [Cricsheet.org](https://cricsheet.org/) (free ball-by-ball data)
- **LLM APIs:** [OpenAI](https://platform.openai.com/), [Google AI](https://ai.google.dev/)
- **Local LLM:** [Foundry Local](https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-local/) (recommended), [Ollama](https://ollama.ai/)
- **TTS:** [ElevenLabs](https://elevenlabs.io/), [Google Cloud TTS](https://cloud.google.com/text-to-speech)
- **Vector DB:** [ChromaDB](https://www.trychroma.com/)

### Installing Foundry Local

```bash
# macOS
brew tap microsoft/foundrylocal
brew install foundrylocal

# Windows
winget install Microsoft.FoundryLocal

# Verify installation
foundry --version
```

---

_Last updated: December 2024_
