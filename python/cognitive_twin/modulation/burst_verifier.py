"""Burst verifier stub. Placeholder for Phase 6."""

from __future__ import annotations

from typing import Any, Dict


def verify_burst(burst: Dict[str, Any]) -> bool:
    """Verify a burst payload. Phase 6 implementation.

    Args:
        burst: Burst data dict to verify.

    Returns:
        True if burst is valid (stub: always True).
    """
    return True


def reject_burst(burst: Dict[str, Any], reason: str) -> Dict[str, Any]:
    """Reject a burst with reason. Phase 6 implementation.

    Args:
        burst: The burst that failed verification.
        reason: Why it was rejected.

    Returns:
        Rejection record.
    """
    return {"rejected": True, "reason": reason, "burst_id": burst.get("id")}
