"""Verified-only consolidation into the reflex cache (Rule 12).

ONLY consolidate if gvr_state == VERIFIED or is_amygdala.
Unverified resolutions are REJECTED.

Absorbed from bridge/ in Phase 4.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Optional

from harlo.daemon.config import REFLEX_DIR


# Module-level attribute kept under the historical name so existing
# tests can `monkeypatch.setattr(consolidation, "_REFLEX_DIR", tmp)`.
# Default resolution is platform-aware via daemon.config.
_REFLEX_DIR: Path = REFLEX_DIR


def _ensure_reflex_dir() -> None:
    """Create the reflex directory if needed."""
    _REFLEX_DIR.mkdir(parents=True, exist_ok=True)


# Tags that satisfy the Rule 12 verification gate.
#   "verified"        — survived a full GVR cycle (Rule 12)
#   "amygdala_bypass" — Rule 7: SAFETY / CONSENT reflexes skip GVR by design;
#                       the tag itself records that decision rather than
#                       fabricating a "VERIFIED" claim that wasn't earned.
_CONSOLIDATABLE_STATES = frozenset({"verified", "amygdala_bypass"})


def consolidate_resolution(
    resolution: dict,
    is_amygdala: bool = False,
) -> Optional[str]:
    """Consolidate a resolution into the reflex cache.

    Rule 12: ONLY consolidate if gvr_state is in the explicit allowlist
    (``verified`` from a real GVR cycle, or ``amygdala_bypass`` from
    Rule 7).  Unverified resolutions are REJECTED and return None.

    Args:
        resolution: The resolution dict (must contain 'outcome' and 'gvr_state').
        is_amygdala: Back-compat flag — if True, the resolution is treated as
            having ``gvr_state="amygdala_bypass"`` regardless of the dict's
            actual tag.  New callers should set the tag explicitly and leave
            this False so the audit trail records the truth.

    Returns:
        Reflex hash string if consolidated, None if rejected.
    """
    gvr_state = resolution.get("gvr_state", "")
    if is_amygdala:
        # Back-compat: legacy callers that pass is_amygdala=True without
        # setting the tag.  Coerce to the canonical tag so the gate uses
        # one source of truth.
        gvr_state = "amygdala_bypass"

    # Rule 12: explicit allowlist of consolidatable states.
    if gvr_state not in _CONSOLIDATABLE_STATES:
        return None

    # Build the reflex record
    outcome = resolution.get("outcome", {})
    canonical = json.dumps(outcome, sort_keys=True)
    reflex_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    # Rule 7 reflexes are STORED as "amygdala_permanent" — the input tag
    # ("amygdala_bypass") records the GVR-skip decision; the stored tag
    # records the resulting reflex's permanence.  Both real-GVR and
    # rule-7-bypass paths converge to a single source of truth here.
    is_amygdala_path = is_amygdala or gvr_state == "amygdala_bypass"
    reflex_record = {
        "reflex_hash": reflex_hash,
        "outcome": outcome,
        "gvr_state": "amygdala_permanent" if is_amygdala_path else gvr_state,
        "merkle_root": resolution.get("merkle_root", ""),
        "consolidated_at": int(time.time()),
        "is_amygdala": is_amygdala_path,
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
