"""Factory for creating LLM providers."""

import os
from typing import Any, Literal

from suksham_vachak.logging import get_logger

from .base import BaseLLMProvider
from .claude import ClaudeModel, ClaudeProvider
from .ollama import OllamaModel, OllamaProvider

logger = get_logger(__name__)

# Type alias for provider names
LLMProvider = Literal["claude", "ollama", "auto"]


def create_llm_provider(
    provider: LLMProvider = "auto",
    model: str | None = None,
    **kwargs: Any,
) -> BaseLLMProvider:
    """Create an LLM provider based on configuration.

    Args:
        provider: Provider to use:
            - "claude": Use Anthropic Claude API (requires ANTHROPIC_API_KEY)
            - "ollama": Use local Ollama server
            - "auto": Auto-detect based on available credentials/services

        model: Model name to use. If not specified:
            - Claude: Uses Haiku by default
            - Ollama: Uses Qwen2.5:7b by default

        **kwargs: Additional provider-specific arguments:
            - api_key: For Claude provider
            - base_url: For Ollama provider
            - timeout: For Ollama provider

    Returns:
        Configured LLM provider instance.

    Raises:
        ValueError: If provider is not available or misconfigured.

    Examples:
        # Auto-detect (tries Ollama first, falls back to Claude)
        provider = create_llm_provider()

        # Explicit Claude
        provider = create_llm_provider("claude", model="sonnet")

        # Explicit Ollama with specific model
        provider = create_llm_provider("ollama", model="llama3.1:8b")

        # Ollama on remote server
        provider = create_llm_provider("ollama", base_url="http://192.168.1.100:11434/v1")
    """
    if provider == "auto":
        return _auto_detect_provider(model, **kwargs)

    if provider == "claude":
        return _create_claude_provider(model, **kwargs)

    if provider == "ollama":
        return _create_ollama_provider(model, **kwargs)

    msg = f"Unknown provider: {provider}. Use 'claude', 'ollama', or 'auto'."
    raise ValueError(msg)


def _auto_detect_provider(model: str | None = None, **kwargs: Any) -> BaseLLMProvider:
    """Auto-detect the best available provider.

    Priority:
    1. Ollama (if server is reachable) - preferred for local/edge deployment
    2. Claude (if API key is set) - cloud fallback

    Args:
        model: Optional model name override.
        **kwargs: Additional provider arguments.

    Returns:
        Best available provider.

    Raises:
        ValueError: If no provider is available.
    """
    # Try Ollama first (local inference is preferred)
    try:
        ollama = _create_ollama_provider(model, **kwargs)
        if ollama.is_available():
            logger.info("Auto-detected Ollama provider", model=ollama.model_name)
            return ollama
    except Exception as e:
        logger.debug("Ollama not available", error=str(e))

    # Fall back to Claude
    if os.environ.get("ANTHROPIC_API_KEY"):
        logger.info("Auto-detected Claude provider (Ollama not available)")
        return _create_claude_provider(model, **kwargs)

    msg = (
        "No LLM provider available. Either:\n"
        "  1. Start Ollama: ollama serve && ollama pull qwen2.5:7b\n"
        "  2. Set ANTHROPIC_API_KEY for Claude API access"
    )
    raise ValueError(msg)


def _create_claude_provider(model: str | None = None, **kwargs: Any) -> ClaudeProvider:
    """Create a Claude provider.

    Args:
        model: Model name (haiku, sonnet, opus) or full model ID.
        **kwargs: Additional arguments (api_key).

    Returns:
        Configured ClaudeProvider.
    """
    # Map friendly names to enum
    model_map = {
        "haiku": ClaudeModel.HAIKU,
        "sonnet": ClaudeModel.SONNET,
        "opus": ClaudeModel.OPUS,
    }

    claude_model = ClaudeModel.HAIKU  # Default
    if model:
        if model.lower() in model_map:
            claude_model = model_map[model.lower()]
        else:
            # Try to find by value
            for m in ClaudeModel:
                if model in m.value:
                    claude_model = m
                    break

    return ClaudeProvider(
        model=claude_model,
        api_key=kwargs.get("api_key"),
    )


def _create_ollama_provider(model: str | None = None, **kwargs: Any) -> OllamaProvider:
    """Create an Ollama provider.

    Args:
        model: Model name (e.g., "qwen2.5:7b", "llama3.1:8b").
        **kwargs: Additional arguments (base_url, timeout).

    Returns:
        Configured OllamaProvider.
    """
    # Map friendly names to enum
    model_map = {
        "qwen": OllamaModel.QWEN2_5_7B,
        "qwen7b": OllamaModel.QWEN2_5_7B,
        "qwen3b": OllamaModel.QWEN2_5_3B,
        "llama": OllamaModel.LLAMA3_1_8B,
        "llama8b": OllamaModel.LLAMA3_1_8B,
        "llama3b": OllamaModel.LLAMA3_2_3B,
        "phi": OllamaModel.PHI3_5_MINI,
    }

    ollama_model: OllamaModel | str = OllamaModel.QWEN2_5_7B  # Default
    if model:
        ollama_model = model_map.get(model.lower(), model)

    return OllamaProvider(
        model=ollama_model,
        base_url=kwargs.get("base_url"),
        timeout=kwargs.get("timeout", 60.0),
    )
