"""Claude API adapter using the Anthropic SDK.

Reads API key from ANTHROPIC_API_KEY environment variable.
"""

from __future__ import annotations

import os
from typing import Iterator

import anthropic


class ClaudeProvider:
    """Claude provider via the Anthropic SDK."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: str | None = None,
        max_tokens: int = 4096,
        system_prompt: str | None = None,
    ):
        """Initialize the Claude provider.

        Args:
            model: Anthropic model ID.
            api_key: API key. Falls back to ANTHROPIC_API_KEY env var.
            max_tokens: Maximum tokens in the response.
            system_prompt: Optional system prompt prepended to every request.
        """
        key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            raise ValueError(
                "ANTHROPIC_API_KEY is required. "
                "Set it as an environment variable or pass api_key=."
            )
        self._client = anthropic.Anthropic(api_key=key)
        self._model = model
        self._max_tokens = max_tokens
        self._system_prompt = system_prompt

    @property
    def model_name(self) -> str:
        return self._model

    def _build_messages(
        self, prompt: str, context: list[dict] | None = None
    ) -> list[dict]:
        """Build the messages list for the API call."""
        messages = []
        if context:
            for msg in context:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": str(msg.get("content", "")),
                })
        messages.append({"role": "user", "content": prompt})
        return messages

    def generate(self, prompt: str, context: list[dict] | None = None) -> str:
        """Generate a complete response via Claude API.

        Args:
            prompt: The user query.
            context: Optional conversation history.

        Returns:
            The full response text.
        """
        messages = self._build_messages(prompt, context)
        kwargs: dict = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": messages,
        }
        if self._system_prompt:
            kwargs["system"] = self._system_prompt

        response = self._client.messages.create(**kwargs)

        # Extract text from content blocks
        parts = []
        for block in response.content:
            if block.type == "text":
                parts.append(block.text)
        return "".join(parts)

    def stream(self, prompt: str, context: list[dict] | None = None) -> Iterator[str]:
        """Stream response tokens from Claude API.

        Yields:
            Text chunks as they arrive.
        """
        messages = self._build_messages(prompt, context)
        kwargs: dict = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": messages,
        }
        if self._system_prompt:
            kwargs["system"] = self._system_prompt

        with self._client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                yield text
