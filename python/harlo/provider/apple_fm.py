"""Apple Foundation Models provider — on-device reasoning for Harlo.

macOS 27 ("Golden Gate", WWDC 2026) ships an official Python SDK
(``pip install apple-fm-sdk``) over the same on-device model that powers
Apple Intelligence: on-device inference, guided generation, and tool
calling, plus a Private Cloud Compute (PCC) reasoning tier.

For Harlo this is the **local-first reasoning provider**: it keeps
sensitive cognition (sincerity classification, intent / spec-gaming
judging) on the machine instead of a cloud round-trip — no API key, no
trace egress. It mirrors the ``ClaudeProvider`` interface
(``generate`` / ``stream`` / ``model_name``) so it drops into the existing
provider abstraction.

The SDK is an OPTIONAL dependency: the import is lazy and a clear error is
raised if it is unavailable, so the rest of Harlo runs without it (same
posture as ``provider/openai.py``).

NOTE: the exact ``apple_fm`` SDK surface is still settling (beta as of
2026-06). The thin adapter below targets the documented
``LanguageModelSession`` shape and degrades gracefully; verify against the
installed SDK before relying on it in production.
"""

from __future__ import annotations

from typing import Iterator


def is_available() -> bool:
    """True if the apple-fm-sdk is importable on this host."""
    try:
        import apple_fm  # type: ignore  # noqa: F401

        return True
    except Exception:
        return False


class AppleFoundationModelsProvider:
    """On-device provider via Apple's Foundation Models Python SDK."""

    def __init__(
        self,
        model: str = "system",
        system_prompt: str | None = None,
        max_tokens: int = 1024,
        reasoning: str | None = None,
    ) -> None:
        """Initialize the provider.

        Args:
            model: ``"system"`` (on-device) or ``"pcc"`` (Private Cloud Compute).
            system_prompt: Optional instructions prepended to every request.
            max_tokens: Response length cap (the on-device window is small).
            reasoning: Optional PCC reasoning level (e.g. ``"light"``/``"deep"``).
        """
        self._model = model
        self._system_prompt = system_prompt
        self._max_tokens = max_tokens
        self._reasoning = reasoning
        self._session = self._make_session()

    def _make_session(self):
        try:
            import apple_fm  # type: ignore
        except ImportError as exc:  # pragma: no cover - env-dependent
            raise RuntimeError(
                "apple-fm-sdk is not installed. On macOS 26+/27 run "
                "`pip install apple-fm-sdk` to enable on-device reasoning."
            ) from exc
        return apple_fm.LanguageModelSession(
            model=self._model,
            instructions=self._system_prompt,
        )

    @property
    def model_name(self) -> str:
        return f"apple-fm:{self._model}"

    def generate(self, prompt: str, context: list[dict] | None = None) -> str:
        """Generate a complete on-device response."""
        full = _join_context(prompt, context)
        resp = self._session.respond(full, max_tokens=self._max_tokens)
        return getattr(resp, "content", str(resp))

    def stream(
        self, prompt: str, context: list[dict] | None = None
    ) -> Iterator[str]:
        """Stream response chunks from the on-device model."""
        full = _join_context(prompt, context)
        for chunk in self._session.stream(full):
            yield getattr(chunk, "content", str(chunk))


def _join_context(prompt: str, context: list[dict] | None) -> str:
    if not context:
        return prompt
    lines = [
        f"{m.get('role', 'user')}: {m.get('content', '')}" for m in context
    ]
    lines.append(f"user: {prompt}")
    return "\n".join(lines)


__all__ = ["AppleFoundationModelsProvider", "is_available"]
