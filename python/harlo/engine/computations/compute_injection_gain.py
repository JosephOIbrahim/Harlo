"""Pure function: compute injection gain.

Commandment 6: Anchor gain = 1.0 ALWAYS. Separate function.
No code path from injection params to anchor output.
"""

from __future__ import annotations

import math

from src.schemas import (
    CognitiveObservation,
    InjectionPhase,
    InjectionProfile,
)

# Anchor domains — always gain 1.0 (Commandment 6)
ANCHOR_DOMAINS = frozenset({"SAFETY", "CONSENT", "KNOWLEDGE", "CONSTITUTIONAL"})


def compute_anchor_gain(domain: str) -> float:
    """Anchor gain is ALWAYS 1.0. No exceptions. No code path from injection.

    Commandment 6: Separate function. Returns 1.0 unconditionally.
    """
    return 1.0


def compute_injection_gain(
    authored: CognitiveObservation,
    domain: str = "",
) -> float:
    """Compute injection modulation gain for a domain.

    Returns alpha-modulated gain based on injection profile and phase.
    Anchors ALWAYS return 1.0 via separate function (Commandment 6).
    """
    # Anchors bypass injection entirely
    if domain.upper() in ANCHOR_DOMAINS:
        return compute_anchor_gain(domain)

    injection = authored.injection

    if injection.profile == InjectionProfile.NONE:
        return 1.0

    if injection.phase == InjectionPhase.BASELINE:
        return 1.0

    alpha = injection.alpha

    # Profile-specific gain curves
    if injection.profile == InjectionProfile.MICRODOSE:
        # Subtle: 1.0 + 0.15 * alpha (max 1.15)
        return 1.0 + 0.15 * alpha

    if injection.profile == InjectionProfile.PERCEPTUAL:
        # Moderate: 1.0 + 0.3 * alpha (max 1.3)
        return 1.0 + 0.3 * alpha

    if injection.profile == InjectionProfile.CLASSICAL:
        # Strong: exponential curve, can dissolve structure
        # 1.0 + 0.8 * alpha^2 (max 1.8)
        return 1.0 + 0.8 * alpha * alpha

    if injection.profile == InjectionProfile.MDMA:
        # Empathogenic: bell curve peaking at alpha=0.7
        # 1.0 + 0.5 * sin(pi * alpha)
        return 1.0 + 0.5 * math.sin(math.pi * alpha)

    return 1.0
