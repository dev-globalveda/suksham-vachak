# 🏏 Suksham Vāchak (सूक्ष्म वाचक)

[![Release](https://img.shields.io/github/v/release/dev-globalveda/suksham-vachak)](https://img.shields.io/github/v/release/dev-globalveda/suksham-vachak)
[![Build status](https://img.shields.io/github/actions/workflow/status/dev-globalveda/suksham-vachak/main.yml?branch=main)](https://github.com/dev-globalveda/suksham-vachak/actions/workflows/main.yml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/dev-globalveda/suksham-vachak/branch/main/graph/badge.svg)](https://codecov.io/gh/dev-globalveda/suksham-vachak)
[![License](https://img.shields.io/github/license/dev-globalveda/suksham-vachak)](https://img.shields.io/github/license/dev-globalveda/suksham-vachak)

**"The Subtle Commentator"** — An intelligent cricket commentary engine powered by agentic AI.

## ✨ Overview

Suksham Vāchak is a lightweight, agentic AI system designed to generate **natural, human-like cricket commentary** in real time or on replay, using structured match events as input.

It blends classical Indian philosophical precision (सूक्ष्म = subtle, fine-grained) with modern AI engineering to create a commentator that is insightful, expressive, and computationally efficient.

## 🚀 Quick Start

```bash
# Install dependencies
poetry install

# Activate pre-commit hooks
poetry run pre-commit install

# Run tests
make test
```

## 📦 Features

- **Event → Commentary Pipeline** — JSON input to contextualized commentary
- **Agentic AI (ReAct + CoT)** — Tactical insights and game state awareness
- **RAG for Cricket Memory** — Player stats, ground history, match situations
- **Runs on Raspberry Pi** — Optimized for low-power deployment
- **Modular Architecture** — FastAPI, MongoDB, React UI, Docker

## 🛠️ Tech Stack

| Layer          | Technologies                                          |
| -------------- | ----------------------------------------------------- |
| **Backend**    | Python 3.12+, FastAPI, Uvicorn, MongoDB 8.0, Pydantic |
| **AI**         | OpenAI GPT / Ollama, LangChain, ReAct, CoT, RAG       |
| **Frontend**   | React, Tailwind CSS, ElevenLabs _(future)_            |
| **Deployment** | Docker Compose, Nginx, step-ca                        |

## 📖 Modules

- [API Reference](modules.md) — Core module documentation

## 🔤 The Name

In Sanskrit:

- **Sūkṣma (सूक्ष्म)** → subtle, precise, fine-grained
- **Vācak (वाचक)** → the one who speaks / narrates

Together: **"The speaker who perceives and expresses subtle detail."**

---

_A commentator who doesn't just describe… but understands._
