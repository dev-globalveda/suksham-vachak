"""LLM client for commentary generation.

This module provides backward-compatible access to LLM providers.
For new code, prefer using the providers module directly:

    from suksham_vachak.commentary.providers import create_llm_provider

Legacy code using LLMClient will continue to work:

    from suksham_vachak.commentary.llm import LLMClient
"""

from suksham_vachak.logging import get_logger

# Re-export from providers for backward compatibility
from .providers import LLMResponse
from .providers.claude import ClaudeModel, ClaudeProvider
from .providers.factory import create_llm_provider
from .providers.ollama import OllamaModel, OllamaProvider

logger = get_logger(__name__)

# Backward compatibility alias
LLMClient = ClaudeProvider

__all__ = [
    "ClaudeModel",
    "ClaudeProvider",
    "LLMClient",
    "LLMResponse",
    "OllamaModel",
    "OllamaProvider",
    "create_llm_provider",
]
