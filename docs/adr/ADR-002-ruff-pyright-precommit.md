# ADR-002: Ruff, Pyright Strict, and Pre-commit for Code Quality

**Date:** 2025-12-05

**Status:** Accepted

**Deciders:** Aman Misra

## Context

Python code quality requires linting, formatting, and type checking. The traditional stack (flake8 + black + isort + mypy) uses four separate tools with overlapping config. We needed a fast, modern alternative that fits into a pre-commit workflow.

## Decision

- **Ruff** for both linting and formatting (replaces flake8 + black + isort)
- **Pyright in strict mode** for type checking (replaces mypy)
- **Pre-commit hooks** with Ruff, Prettier (Markdown/JSON/YAML), and standard hooks (trailing whitespace, end-of-file, TOML/YAML validation)
- Line length: **120 characters** (wider than PEP8's 79, matches modern display widths)

### Alternatives Considered

| Option                 | Why Rejected                                                  |
| ---------------------- | ------------------------------------------------------------- |
| flake8 + black + isort | Three tools to maintain; 10-100x slower than Ruff             |
| pylint                 | Too opinionated, slow, many false positives                   |
| mypy                   | Less strict by default, worse editor integration than Pyright |
| No type checking       | Unacceptable for a multi-module project                       |

## Consequences

### Positive

- Single tool (Ruff) replaces three, with 10-100x speed improvement
- Pyright strict mode catches bugs that mypy basic mode misses
- Pre-commit catches issues before they reach CI
- 120-char lines reduce artificial line breaks in modern code

### Negative

- Pyright strict mode is demanding — every parameter needs type annotations
- Prettier reformatting during commit can cause a chicken-and-egg problem (files modified by hook → commit fails → must re-stage). Workaround: run `pre-commit run --all-files` before `git add`.

### Risks

- Ruff is relatively new; some flake8 plugins not yet ported
- Pyright strict produces many errors in codebases using dynamic patterns (e.g., ORM results)
