"""Pattern detection stub."""

from __future__ import annotations

from typing import List

# Valid patterns
_PATTERNS = {"adhd", "analytical", "creative", "depleted", "default"}


def detect_pattern(messages: List[dict]) -> str:
    """Detect conversational pattern from message history.

    Args:
        messages: List of message dicts (stub - structure TBD).

    Returns:
        One of: "adhd", "analytical", "creative", "depleted", "default".
    """
    # Stub: full implementation in later phase
    if not messages:
        return "default"

    # Simple heuristics as placeholder
    def _msg_len(m):
        if isinstance(m, dict):
            return len(str(m.get("content", "")))
        return len(str(m))

    total_len = sum(_msg_len(m) for m in messages)
    count = len(messages)

    if count == 0:
        return "default"

    avg_len = total_len / count

    # Very short rapid messages -> adhd pattern
    if avg_len < 20 and count > 5:
        return "adhd"

    # Long structured messages -> analytical
    if avg_len > 200:
        return "analytical"

    return "default"
