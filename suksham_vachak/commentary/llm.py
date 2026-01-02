"""LLM client for Claude API integration."""

import os
from dataclasses import dataclass
from enum import Enum

from anthropic import Anthropic


class ClaudeModel(Enum):
    """Available Claude models."""

    # Fast and cheap - use for development and testing
    HAIKU = "claude-3-haiku-20240307"

    # Balanced - good for production
    SONNET = "claude-sonnet-4-20250514"

    # Best quality - use for quality checks
    OPUS = "claude-opus-4-20250514"


@dataclass
class LLMResponse:
    """Response from the LLM."""

    text: str
    model: str
    input_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.input_tokens + self.output_tokens


class LLMClient:
    """Client for interacting with Claude API.

    Uses Haiku by default for speed/cost during development.
    Switch to Sonnet for production quality.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: ClaudeModel = ClaudeModel.HAIKU,
    ) -> None:
        """Initialize the LLM client.

        Args:
            api_key: Anthropic API key. If not provided, reads from ANTHROPIC_API_KEY env var.
            model: Claude model to use. Defaults to Haiku for speed/cost.
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            msg = "ANTHROPIC_API_KEY not found. Set env var or pass api_key."
            raise ValueError(msg)

        self.model = model
        self.client = Anthropic(api_key=self.api_key)

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 50,
    ) -> LLMResponse:
        """Generate a completion using Claude.

        Args:
            system_prompt: The system prompt establishing the AI's role.
            user_prompt: The user message/prompt.
            max_tokens: Maximum tokens in response. Keep low for minimal personas.

        Returns:
            LLMResponse with the generated text and token usage.
        """
        message = self.client.messages.create(
            model=self.model.value,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt},
            ],
        )

        # Extract text from response
        text = ""
        for block in message.content:
            if block.type == "text":
                text = block.text
                break

        return LLMResponse(
            text=text.strip(),
            model=self.model.value,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
        )

    def set_model(self, model: ClaudeModel) -> None:
        """Switch to a different model.

        Args:
            model: The Claude model to use.
        """
        self.model = model
