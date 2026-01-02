# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Suksham Vāchak** (सूक्ष्म वाचक - "The Subtle Commentator") is an AI-powered cricket commentary generation platform that transforms Cricsheet ball-by-ball JSON data into natural commentary with multiple personas (Richie Benaud, Osho, Tony Greig, etc.), languages, and accessibility features.

**Status**: Early MVP stage - scaffolding complete, core implementation not yet started.

## Build Commands

```bash
# Setup
poetry install                    # Install dependencies
poetry run pre-commit install     # Setup git hooks

# Development
make check                        # Run all code quality checks (ruff, pyright, deptry)
make test                         # Run pytest with coverage
poetry run pytest tests/test_processing.py  # Run specific test file
poetry run pytest -k "test_name"  # Run tests matching pattern

# Documentation
make docs                         # Build and serve docs locally
make docs-test                    # Test documentation build

# Build
make build                        # Build wheel distribution
```

## Code Quality Tools

- **Ruff**: Linting and formatting (line-length: 120)
- **Pyright**: Type checking in strict mode
- **Deptry**: Dependency auditing
- **Pre-commit hooks**: Run automatically on commit

## Architecture

### Data Flow

```
Cricsheet JSON → Cricket Parser → Commentary Engine → TTS Engine → Audio
                                       ↓
                              (Context + Persona + LLM)
```

### Key Components (to be implemented)

| Component         | Location                       | Purpose                             |
| ----------------- | ------------------------------ | ----------------------------------- |
| Cricket Parser    | `suksham_vachak/processing.py` | Parse Cricsheet JSON to events      |
| Commentary Engine | `suksham_vachak/llm_api.py`    | LLM integration for text generation |
| TTS Engine        | `suksham_vachak/tts_engine.py` | Text-to-speech synthesis            |
| Persona Config    | `config/avatars.yaml`          | Persona style definitions           |

### Tech Stack

- **Backend**: FastAPI + Uvicorn
- **LLM**: OpenAI/Claude/Ollama (flexible)
- **TTS**: Google Cloud TTS/Azure/ElevenLabs (flexible)
- **Frontend (MVP)**: Streamlit

## Data

Sample Cricsheet data in `data/cricsheet_sample/` (20 matches). Structure:

```json
{
  "info": { "teams", "venue", "outcome", "players" },
  "innings": [{
    "team": "...",
    "overs": [{
      "over": 0,
      "deliveries": [{ "batter", "bowler", "runs", "wicket" }]
    }]
  }]
}
```

Data exploration notebook: `notebooks/cricket_data_exploration.ipynb`

## Essential Documentation

- **docs/ARCHITECTURE.md**: System design and phased MVP approach
- **docs/VISION.md**: Full vision including personas, languages, accessibility
- **docs/PROTOTYPE_BUILD_SCRIPT.md**: Day-by-day Claude CLI build instructions

## Development Guidelines

- Python 3.10+ required
- Virtual environment stored in `.venv/` (poetry.toml config)
- CI tests against Python 3.8-3.12
- Coverage reports uploaded to Codecov
