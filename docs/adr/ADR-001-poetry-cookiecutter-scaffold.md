# ADR-001: Poetry + Cookiecutter Project Scaffold

**Date:** 2025-12-05

**Status:** Accepted

**Deciders:** Aman Misra

## Context

The project needed a professional Python project structure from day one — dependency management, virtual environments, CI/CD, documentation tooling, and build system. Manual setup would take days and risk inconsistencies.

## Decision

Use the `fpgmaas/cookiecutter-poetry` template for scaffolding and **Poetry** as the dependency manager. The template provides pre-configured Makefile, GitHub Actions CI, mkdocs, Codecov integration, and a clean package layout.

Poetry is configured with `in-project = true` (`.venv/` lives inside the project root) for IDE compatibility.

### Alternatives Considered

| Option                 | Why Rejected                                                                       |
| ---------------------- | ---------------------------------------------------------------------------------- |
| pip + requirements.txt | No lock file, no virtual env management, no extras support                         |
| pipenv                 | Slower, smaller ecosystem, no extras                                               |
| uv                     | Faster but less mature at the time; no extras support for optional deps (TTS, RAG) |
| conda                  | Overkill for a pure-Python project                                                 |

## Consequences

### Positive

- Professional project structure from minute one
- Lock file (`poetry.lock`) ensures reproducible builds
- Extras support (`--extras tts`, `--extras rag`) keeps core package lightweight
- Makefile provides consistent `make check`, `make test`, `make build` commands

### Negative

- Poetry is slower than pip/uv for dependency resolution
- Cookiecutter template includes some config that needed adjustment (e.g., CI matrix tests Python 3.8-3.12 but code requires 3.10+)

### Risks

- Poetry occasionally has compatibility issues with newer pip standards
- Template may become unmaintained
