"""Commentary generation module for Suksham Vachak."""

from .engine import Commentary, CommentaryEngine
from .llm import (
    ClaudeModel,
    ClaudeProvider,
    LLMClient,
    LLMResponse,
    OllamaModel,
    OllamaProvider,
    create_llm_provider,
)
from .prompts import build_event_prompt, build_rich_context_prompt, build_system_prompt

__all__ = [
    "ClaudeModel",
    "ClaudeProvider",
    "Commentary",
    "CommentaryEngine",
    "LLMClient",
    "LLMResponse",
    "OllamaModel",
    "OllamaProvider",
    "build_event_prompt",
    "build_rich_context_prompt",
    "build_system_prompt",
    "create_llm_provider",
]
