"""Session prim updates after recall operations.

Thin orchestration layer over routing.route_recall().
"""

from __future__ import annotations

from typing import Optional

from ..usd_lite.prims import CognitiveProfilePrim, SessionPrim
from .routing import SurpriseResult, route_recall


def update_session_after_recall(
    session: SessionPrim,
    best_hamming: int,
    cognitive_profile: Optional[CognitiveProfilePrim] = None,
) -> tuple[SessionPrim, SurpriseResult]:
    """Update /Session prim after a recall operation.

    Delegates to routing.route_recall() and returns the updated session
    plus the routing decision.
    """
    result, updated_session = route_recall(
        best_hamming=best_hamming,
        session_prim=session,
        cognitive_profile=cognitive_profile,
    )
    return updated_session, result
