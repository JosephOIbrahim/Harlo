"""Metacognitive routing — surprise Z-score and dual-process escalation.

Patch 1: Z-score formulation with max(std_dev, 1.0) cold-start floor.
Dual-process: System 1 (fast hamming) → System 2 (deliberative LIVRPS)
when surprise exceeds threshold.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from ..usd_lite.prims import (
    CognitiveProfilePrim,
    RetrievalPath,
    SessionPrim,
)

ROLLING_WINDOW = 100
DEFAULT_SURPRISE_THRESHOLD = 2.0
_STD_FLOOR = 1.0


@dataclass
class SurpriseResult:
    """Result of surprise computation after a recall."""
    z_score: float
    rolling_mean: float
    rolling_std: float
    escalate: bool
    retrieval_path: RetrievalPath


def compute_surprise(
    best_hamming: int,
    rolling_mean: float,
    rolling_std: float,
    history_count: int,
    threshold: float = DEFAULT_SURPRISE_THRESHOLD,
) -> SurpriseResult:
    """Compute surprise Z-score and routing decision.

    Formula: z_score = (best_hamming - rolling_mean) / max(rolling_std, 1.0)
    Escalation: z_score > threshold → SYSTEM_2, else SYSTEM_1.
    """
    floored_std = max(rolling_std, _STD_FLOOR)
    z_score = (best_hamming - rolling_mean) / floored_std
    escalate = z_score > threshold
    return SurpriseResult(
        z_score=z_score,
        rolling_mean=rolling_mean,
        rolling_std=rolling_std,
        escalate=escalate,
        retrieval_path=RetrievalPath.SYSTEM_2 if escalate else RetrievalPath.SYSTEM_1,
    )


def update_rolling_stats(
    current_mean: float,
    current_std: float,
    history_count: int,
    new_hamming: int,
) -> tuple[float, float, int]:
    """Update rolling mean and std dev with a new hamming distance.

    Uses Welford's online algorithm for numerically stable updates.
    Capped at ROLLING_WINDOW (100) values.

    Returns: (new_mean, new_std, new_count)
    """
    n = min(history_count + 1, ROLLING_WINDOW)

    if history_count == 0:
        return float(new_hamming), 0.0, 1

    # Welford's online update (approximated for rolling window)
    delta = new_hamming - current_mean
    new_mean = current_mean + delta / n

    # Update variance: use running estimate
    # For a rolling window, we approximate by blending
    if history_count < 2:
        new_std = abs(delta) / 2.0
    else:
        # Reconstruct M2 from std and count, then update
        old_var = current_std * current_std
        old_m2 = old_var * min(history_count, ROLLING_WINDOW)
        delta2 = new_hamming - new_mean
        new_m2 = old_m2 + delta * delta2
        new_var = new_m2 / n
        new_std = math.sqrt(max(new_var, 0.0))

    return new_mean, new_std, n


def get_surprise_threshold(
    cognitive_profile: Optional[CognitiveProfilePrim],
) -> float:
    """Read surprise threshold from cognitive profile.

    If profile exists and has multipliers: return surprise_threshold.
    Otherwise: return DEFAULT_SURPRISE_THRESHOLD (2.0).
    """
    if cognitive_profile is not None:
        return cognitive_profile.multipliers.surprise_threshold
    return DEFAULT_SURPRISE_THRESHOLD


def route_recall(
    best_hamming: int,
    session_prim: SessionPrim,
    cognitive_profile: Optional[CognitiveProfilePrim] = None,
) -> tuple[SurpriseResult, SessionPrim]:
    """Full routing pipeline: compute surprise, update session, return decision.

    1. Get threshold from profile (or default 2.0)
    2. Update rolling stats with new hamming value
    3. Compute surprise Z-score
    4. Build updated SessionPrim
    5. Return (SurpriseResult, updated SessionPrim)
    """
    threshold = get_surprise_threshold(cognitive_profile)

    # Update rolling stats
    new_mean, new_std, new_count = update_rolling_stats(
        session_prim.surprise_rolling_mean,
        session_prim.surprise_rolling_std,
        session_prim.exchange_count,
        best_hamming,
    )

    # Compute surprise on updated stats
    result = compute_surprise(
        best_hamming=best_hamming,
        rolling_mean=new_mean,
        rolling_std=new_std,
        history_count=new_count,
        threshold=threshold,
    )

    # Update session prim
    updated_session = SessionPrim(
        current_session_id=session_prim.current_session_id,
        exchange_count=new_count,
        surprise_rolling_mean=new_mean,
        surprise_rolling_std=new_std,
        last_query_surprise=result.z_score,
        last_retrieval_path=result.retrieval_path,
    )

    return result, updated_session
