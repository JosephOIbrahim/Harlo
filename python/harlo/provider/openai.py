"""OpenAI-compatible API adapter.

Supports any OpenAI-compatible endpoint (OpenAI, Ollama, vLLM, etc.).
Falls back to a stub if the openai package is not installed.
"""

from __future__ import annotations

import os
from typing import Iterator


class OpenAIProvider:
    """OpenAI-compatible provider."""

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: str | None = None,
        base_url: str | None = None,
        max_tokens: int = 4096,
        system_prompt: str | None = None,
    ):
        """Initialize the OpenAI-compatible provider.

        Args:
            model: Model ID.
            api_key: API key. Falls back to OPENAI_API_KEY env var.
            base_url: Optional base URL for compatible endpoints.
            max_tokens: Maximum tokens in the response.
            system_prompt: Optional system prompt.
        """
        key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not key:
            raise ValueError(
                "OPENAI_API_KEY is required. "
                "Set it as an environment variable or pass api_key=."
            )

        try:
            import openai
        except ImportError:
            raise ImportError(
                "The openai package is required for OpenAIProvider. "
                "Install it with: pip install openai"
            )

        client_kwargs: dict = {"api_key": key}
        if base_url:
            client_kwargs["base_url"] = base_url

        self._client = openai.OpenAI(**client_kwargs)
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
        if self._system_prompt:
            messages.append({"role": "system", "content": self._system_prompt})
        if context:
            for msg in context:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": str(msg.get("content", "")),
                })
        messages.append({"role": "user", "content": prompt})
        return messages

    def generate(self, prompt: str, context: list[dict] | None = None) -> str:
        """Generate a complete response.

        Args:
            prompt: The user query.
            context: Optional conversation history.

        Returns:
            The full response text.
        """
        messages = self._build_messages(prompt, context)
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            max_tokens=self._max_tokens,
        )
        return response.choices[0].message.content or ""

    def stream(self, prompt: str, context: list[dict] | None = None) -> Iterator[str]:
        """Stream response tokens.

        Yields:
            Text chunks as they arrive.
        """
        messages = self._build_messages(prompt, context)
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            max_tokens=self._max_tokens,
            stream=True,
        )
        for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content
