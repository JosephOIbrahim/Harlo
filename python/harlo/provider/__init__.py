"""LLM Provider abstraction — pluggable adapters for language model backends.

Provides a Protocol-based interface so the Twin can generate text via
any LLM backend (Claude, OpenAI-compatible, etc.) without coupling to
a specific API.

Usage:
    from harlo.provider import get_provider
    provider = get_provider("claude")
    response = provider.generate("What is memory?", context=[...])
"""

from __future__ import annotations

import os
from typing import Iterator, Protocol, runtime_checkable


@runtime_checkable
class Provider(Protocol):
    """Protocol for LLM provider adapters.

    Every provider must implement generate(), stream(), and expose
    its model_name.
    """

    @property
    def model_name(self) -> str:
        """Return the model identifier string."""
        ...

    def generate(self, prompt: str, context: list[dict] | None = None) -> str:
        """Generate a complete response.

        Args:
            prompt: The user prompt / query.
            context: Optional list of message dicts (role/content pairs)
                     prepended as conversation history.

        Returns:
            The full generated text.
        """
        ...

    def stream(self, prompt: str, context: list[dict] | None = None) -> Iterator[str]:
        """Stream response tokens incrementally.

        Args:
            prompt: The user prompt / query.
            context: Optional list of message dicts.

        Yields:
            Text chunks as they arrive.
        """
        ...


def get_provider(name: str = "claude", **kwargs) -> Provider:
    """Factory: instantiate a provider by name.

    Args:
        name: Provider name — "claude" or "openai".
        **kwargs: Forwarded to the provider constructor.

    Returns:
        A Provider instance.

    Raises:
        ValueError: If the provider name is unknown.
        ImportError: If the required SDK is not installed.
    """
    if name == "claude":
        from .claude import ClaudeProvider
        return ClaudeProvider(**kwargs)
    elif name == "openai":
        from .openai import OpenAIProvider
        return OpenAIProvider(**kwargs)
    else:
        raise ValueError(f"Unknown provider: {name!r}. Use 'claude' or 'openai'.")
