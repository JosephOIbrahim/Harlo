"""Gain equation with structural anchors.

Rule 10: ANCHORS (SAFETY/CONSENT/KNOWLEDGE/CONSTITUTIONAL) = gain 1.0 ALWAYS.
"""

from __future__ import annotations

from typing import Any, Dict

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


def apply_modulation(clean: dict, profile: Any) -> dict:
    """Apply modulation to clean output. Clean is always recoverable.

    output = clean + alpha * delta

    Args:
        clean: The unmodulated (clean) output dict.
        profile: Profile instance with s_nm and other parameters.

    Returns:
        Modulated output dict. Original clean dict is NOT mutated.
    """
    # Copy so clean is always recoverable
    output: Dict[str, Any] = dict(clean)

    s_nm = getattr(profile, "s_nm", 0.0)

    # If s_nm is 0, no modulation needed
    if s_nm == 0.0:
        return output

    # Apply gain per field, respecting anchors
    for key, value in clean.items():
        gain = compute_gain(s_nm, 1.0, key)
        if gain != 1.0 and isinstance(value, (int, float)):
            output[key] = value * gain

    return output
