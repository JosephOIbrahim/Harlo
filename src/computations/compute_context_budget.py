"""Pure function: compute context budget level with hysteresis.

Commandment 9: Context budget uses hysteresis.
Promote Payload→Reference at >4.2x, demote at <3.8x.
"""

from __future__ import annotations

from src.schemas import (
    ContextLevel,
    CognitiveObservation,
    StateBlock,
)


def compute_context_budget(
    authored: CognitiveObservation,
    prev_state: StateBlock,
    token_ratio: float,
    promote_threshold: float = 4.2,
    demote_threshold: float = 3.8,
) -> ContextLevel:
    """Compute context budget level with hysteresis.

    token_ratio: current context tokens / reference token budget.
    Hysteresis prevents oscillation near the boundary.
    """
    prev_level = prev_state.context

    if prev_level == ContextLevel.PAYLOAD:
        # Currently payload: promote to reference if ratio exceeds promote threshold
        if token_ratio > promote_threshold:
            return ContextLevel.REFERENCE
        return ContextLevel.PAYLOAD

    # Currently reference: demote to payload if ratio drops below demote threshold
    if token_ratio < demote_threshold:
        return ContextLevel.PAYLOAD
    return ContextLevel.REFERENCE
