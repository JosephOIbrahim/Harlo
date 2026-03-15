"""Verified-only consolidation into the reflex cache (Rule 12).

ONLY consolidate if gvr_state == VERIFIED or is_amygdala.
Unverified resolutions are REJECTED.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Optional


# Reflex cache directory
_REFLEX_DIR = Path("data/reflexes")


def _ensure_reflex_dir() -> None:
    """Create the reflex directory if needed."""
    _REFLEX_DIR.mkdir(parents=True, exist_ok=True)


def consolidate_resolution(
    resolution: dict,
    is_amygdala: bool = False,
) -> Optional[str]:
    """Consolidate a resolution into the reflex cache.

    Rule 12: ONLY consolidate if gvr_state == VERIFIED or is_amygdala.
    Unverified resolutions are REJECTED and return None.

    Args:
        resolution: The resolution dict (must contain 'outcome' and 'gvr_state').
        is_amygdala: If True, bypass verification requirement (Rule 7).

    Returns:
        Reflex hash string if consolidated, None if rejected.
    """
    gvr_state = resolution.get("gvr_state", "")

    # Rule 12: strict verification gate
    if not is_amygdala and gvr_state != "verified":
        return None

    # Build the reflex record
    outcome = resolution.get("outcome", {})
    canonical = json.dumps(outcome, sort_keys=True)
    reflex_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    reflex_record = {
        "reflex_hash": reflex_hash,
        "outcome": outcome,
        "gvr_state": gvr_state if not is_amygdala else "amygdala_permanent",
        "merkle_root": resolution.get("merkle_root", ""),
        "consolidated_at": int(time.time()),
        "is_amygdala": is_amygdala,
    }

    # Persist
    _ensure_reflex_dir()
    path = _REFLEX_DIR / f"{reflex_hash}.json"
    path.write_text(json.dumps(reflex_record, indent=2), encoding="utf-8")

    return reflex_hash


def lookup_reflex(reflex_hash: str) -> Optional[dict]:
    """Look up a reflex by its hash."""
    path = _REFLEX_DIR / f"{reflex_hash}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_reflexes() -> list[dict]:
    """List all consolidated reflexes."""
    _ensure_reflex_dir()
    reflexes: list[dict] = []
    for path in sorted(_REFLEX_DIR.glob("*.json")):
        try:
            reflexes.append(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    return reflexes
