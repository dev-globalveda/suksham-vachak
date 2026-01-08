"""Base class for LLM providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Response from an LLM provider."""

    text: str
    model: str
    input_tokens: int
    output_tokens: int
    provider: str = "unknown"

    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.input_tokens + self.output_tokens

    def __repr__(self) -> str:
        """Concise representation for debugging."""
        return (
            f"LLMResponse(provider={self.provider}, model={self.model}, "
            f"tokens={self.total_tokens}, text={self.text[:50]}...)"
        )


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers.

    Implementations:
    - ClaudeProvider: Anthropic Claude API
    - OllamaProvider: Local Ollama server (Qwen, Llama, etc.)
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g., 'claude', 'ollama')."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the model being used."""
        ...

    @abstractmethod
    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 50,
    ) -> LLMResponse:
        """Generate a completion.

        Args:
            system_prompt: The system prompt establishing the AI's role.
            user_prompt: The user message/prompt.
            max_tokens: Maximum tokens in response.

        Returns:
            LLMResponse with generated text and metadata.
        """
        ...

    def __repr__(self) -> str:
        """Concise representation for debugging."""
        return f"{self.__class__.__name__}(model={self.model_name})"
