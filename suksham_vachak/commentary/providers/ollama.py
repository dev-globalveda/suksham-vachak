"""Ollama LLM provider for local inference.

Supports any model available in Ollama including:
- Qwen2.5 (recommended for cricket commentary)
- Llama 3.1/3.2
- Mistral
- Phi-3
- Custom fine-tuned models

Uses OpenAI-compatible API for consistency.
"""

import os
from enum import Enum

from openai import OpenAI

from suksham_vachak.logging import get_logger

from .base import BaseLLMProvider, LLMResponse

logger = get_logger(__name__)


class OllamaModel(Enum):
    """Recommended Ollama models for cricket commentary.

    These are suggestions - any Ollama model can be used via model_name parameter.
    """

    # Best for Pi 5 (16GB) - multilingual, good instruction following
    QWEN2_5_7B = "qwen2.5:7b"

    # Good balance of speed and quality
    QWEN2_5_3B = "qwen2.5:3b"

    # Alternative - strong English, larger ecosystem
    LLAMA3_1_8B = "llama3.1:8b"

    # Fastest option for Pi
    LLAMA3_2_3B = "llama3.2:3b"

    # Smallest usable model
    LLAMA3_2_1B = "llama3.2:1b"

    # Microsoft's efficient model
    PHI3_5_MINI = "phi3.5:3.8b"

    # For vision tasks (if using Qwen-VL)
    QWEN2_VL_2B = "qwen2-vl:2b"


# Default Ollama server URL
DEFAULT_OLLAMA_URL = "http://localhost:11434/v1"


class OllamaProvider(BaseLLMProvider):
    """Ollama provider for local LLM inference.

    Connects to a local Ollama server and uses the OpenAI-compatible API.
    Perfect for edge deployment on Raspberry Pi 5.

    Example:
        # Start Ollama server first:
        # $ ollama serve
        # $ ollama pull qwen2.5:7b

        provider = OllamaProvider(model=OllamaModel.QWEN2_5_7B)
        response = provider.complete(
            system_prompt="You are a cricket commentator.",
            user_prompt="Kohli hits a boundary.",
            max_tokens=50
        )
    """

    def __init__(
        self,
        model: OllamaModel | str = OllamaModel.QWEN2_5_7B,
        base_url: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        """Initialize the Ollama provider.

        Args:
            model: Ollama model to use. Can be OllamaModel enum or string.
            base_url: Ollama server URL. Defaults to http://localhost:11434/v1
                     Can also be set via OLLAMA_BASE_URL env var.
            timeout: Request timeout in seconds. Increase for slower hardware.
        """
        self._model = model.value if isinstance(model, OllamaModel) else model
        self._base_url = base_url or os.environ.get("OLLAMA_BASE_URL", DEFAULT_OLLAMA_URL)
        self._timeout = timeout

        # Use OpenAI client with Ollama's OpenAI-compatible endpoint
        self.client = OpenAI(
            base_url=self._base_url,
            api_key="ollama",  # Ollama doesn't require a real key
            timeout=timeout,
        )

        logger.info(
            "Initialized Ollama provider",
            model=self._model,
            base_url=self._base_url,
        )

    @property
    def provider_name(self) -> str:
        """Provider name."""
        return "ollama"

    @property
    def model_name(self) -> str:
        """Model name."""
        return self._model

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 50,
    ) -> LLMResponse:
        """Generate a completion using local Ollama model.

        Args:
            system_prompt: The system prompt establishing the AI's role.
            user_prompt: The user message/prompt.
            max_tokens: Maximum tokens in response.

        Returns:
            LLMResponse with the generated text and metadata.
        """
        try:
            response = self.client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.7,  # Slight creativity for commentary
            )

            text = response.choices[0].message.content or ""

            # Extract token usage (Ollama provides this)
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0

            return LLMResponse(
                text=text.strip(),
                model=self._model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                provider=self.provider_name,
            )

        except Exception as e:
            logger.exception("Ollama completion failed", model=self._model, error=str(e))
            raise

    def set_model(self, model: OllamaModel | str) -> None:
        """Switch to a different model.

        Args:
            model: The Ollama model to use.
        """
        self._model = model.value if isinstance(model, OllamaModel) else model
        logger.info("Switched Ollama model", model=self._model)

    def list_models(self) -> list[str]:
        """List available models on the Ollama server.

        Returns:
            List of model names available locally.
        """
        try:
            models = self.client.models.list()
            return [m.id for m in models.data]
        except Exception as e:
            logger.warning("Failed to list Ollama models", error=str(e))
            return []

    def is_available(self) -> bool:
        """Check if Ollama server is reachable.

        Returns:
            True if server responds, False otherwise.
        """
        try:
            self.client.models.list()
        except Exception:
            return False
        else:
            return True
