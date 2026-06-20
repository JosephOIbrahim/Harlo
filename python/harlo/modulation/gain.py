"""Gain equation with structural anchors.

Rule 10: ANCHORS (SAFETY/CONSENT/KNOWLEDGE/CONSTITUTIONAL) = gain 1.0 ALWAYS.
"""

from __future__ import annotations

# Structural anchors. These ALWAYS produce gain = 1.0. Non-negotiable.
ANCHORS = frozenset(["SAFETY", "CONSENT", "KNOWLEDGE", "CONSTITUTIONAL"])


def compute_gain(s_nm: float, d: float, phase: str) -> float:
    """Compute modulation gain.

    Args:
        s_nm: Spectral nanometer value (modulation depth).
        d: Distance / relevance metric.
        phase: Current processing phase or anchor name.

    Returns:
        Gain multiplier. 1.0 for anchors (STRUCTURAL), otherwise 1.0 + s_nm * d.
    """
    if phase in ANCHORS:
        return 1.0  # STRUCTURAL - Rule 10
    return 1.0 + s_nm * d
