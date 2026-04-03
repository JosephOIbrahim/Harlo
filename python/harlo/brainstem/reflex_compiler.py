"""Reflex compiler -- compile verified resolution patterns into reflexes.

Only VERIFIED or amygdala-permanent resolutions become reflexes.
Rule 12: Verified-only consolidation.
Rule 7: Amygdala bypasses GVR but still creates permanent reflex.

Absorbed from bridge/ in Phase 4.
"""

from __future__ import annotations

import hashlib
import json
import time


def compile_to_reflex(
    pattern: dict,
    resolution: dict,
    verification_state: str,
) -> dict:
    """Compile a verified resolution pattern into a reflex.

    Raises:
        ValueError: If verification_state is not "verified" or
            "amygdala_permanent".
    """
    allowed_states = ("verified", "amygdala_permanent")
    if verification_state not in allowed_states:
        raise ValueError(
            f"Cannot compile reflex: verification_state={verification_state!r} "
            f"not in {allowed_states}. Rule 12: only VERIFIED resolutions "
            f"become reflexes."
        )

    canonical_pattern = json.dumps(pattern, sort_keys=True)
    canonical_outcome = json.dumps(
        resolution.get("outcome", {}), sort_keys=True,
    )
    combined = canonical_pattern + "|" + canonical_outcome
    reflex_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()

    is_permanent = verification_state == "amygdala_permanent"

    return {
        "reflex_hash": reflex_hash,
        "pattern": pattern,
        "outcome": resolution.get("outcome", {}),
        "verification_state": verification_state,
        "permanent": is_permanent,
        "compiled_at": int(time.time()),
        "merkle_root": resolution.get("merkle_root", ""),
    }
