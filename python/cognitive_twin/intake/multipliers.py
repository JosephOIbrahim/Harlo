"""Multiplier derivation from intake scores.

Patch 3: Continuous [0.0, 1.0] scoring with deterministic linear interpolation.
multiplier = base + (score * range)

Dimensions → Multipliers:
- associativity → surprise_threshold: [1.5, 2.5]
- detail → reconstruction_threshold: [0.15, 0.45], detail_orientation: [0.0, 1.0]
- attention → hebbian_alpha: [0.005, 0.02]
- stress → allostatic_threshold: [0.5, 1.5]
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..usd_lite.prims import (
    CognitiveProfilePrim,
    IntakeHistoryPrim,
    MultipliersPrim,
    Provenance,
    SourceType,
)
from .questionnaire import IntakeSession


# Derivation parameters: (base, range) → multiplier = base + score * range
_DERIVATION = {
    "associativity": {
        "surprise_threshold": (1.5, 1.0),   # [1.5, 2.5]
    },
    "detail": {
        "reconstruction_threshold": (0.15, 0.30),  # [0.15, 0.45]
        "detail_orientation": (0.0, 1.0),           # [0.0, 1.0]
    },
    "attention": {
        "hebbian_alpha": (0.005, 0.015),  # [0.005, 0.02]
    },
    "stress": {
        "allostatic_threshold": (0.5, 1.0),  # [0.5, 1.5]
    },
}

# Map question_id prefix to dimension
_QUESTION_DIMENSIONS = {
    "q1_assoc": "associativity",
    "q2_detail": "detail",
    "q3_attention": "attention",
    "q4_stress": "stress",
    "q5_assoc2": "associativity",
    "q6_detail2": "detail",
}


def derive_multipliers(session: IntakeSession) -> MultipliersPrim:
    """Derive multipliers from intake session scores.

    Patch 3: multiplier = base + (score * range), deterministic.
    Multiple questions per dimension are averaged.

    Returns MultipliersPrim with calibrated values.
    """
    # Average scores per dimension
    dimension_scores: dict[str, list[float]] = {}
    for qid, score in session.answers.items():
        dim = _QUESTION_DIMENSIONS.get(qid)
        if dim:
            dimension_scores.setdefault(dim, []).append(score)

    dim_avg: dict[str, float] = {}
    for dim, scores in dimension_scores.items():
        dim_avg[dim] = sum(scores) / len(scores)

    # Derive multipliers
    surprise = _derive("associativity", "surprise_threshold", dim_avg)
    reconstruction = _derive("detail", "reconstruction_threshold", dim_avg)
    detail_orient = _derive("detail", "detail_orientation", dim_avg)
    hebbian = _derive("attention", "hebbian_alpha", dim_avg)
    allostatic = _derive("stress", "allostatic_threshold", dim_avg)

    return MultipliersPrim(
        surprise_threshold=surprise,
        reconstruction_threshold=reconstruction,
        hebbian_alpha=hebbian,
        allostatic_threshold=allostatic,
        detail_orientation=detail_orient,
    )


def _derive(dimension: str, multiplier_name: str, dim_avg: dict[str, float]) -> float:
    """Compute a single multiplier using linear interpolation."""
    score = dim_avg.get(dimension, 0.5)  # Default to midpoint
    base, rng = _DERIVATION[dimension][multiplier_name]
    return base + score * rng


def build_cognitive_profile(
    session: IntakeSession,
    intake_version: str = "1.0",
) -> CognitiveProfilePrim:
    """Build a complete CognitiveProfilePrim from a completed intake session.

    Re-running updates (not appends) — returns a fresh profile.
    """
    multipliers = derive_multipliers(session)
    return CognitiveProfilePrim(
        multipliers=multipliers,
        intake_history=IntakeHistoryPrim(
            last_intake=datetime.now(timezone.utc),
            intake_version=intake_version,
            answer_embeddings=list(session.answers.values()),
        ),
    )
