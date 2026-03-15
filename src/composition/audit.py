"""Append-only audit trail for composition resolutions.

INVARIANT: The audit log is STRICTLY append-only.
           DELETE on audit = build fail.
           No truncation, no overwrite, no deletion.

Format: JSON Lines (one JSON object per line) in data/audit.log.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Optional

from .resolver import Resolution

AUDIT_LOG = Path("data/audit.log")


def _ensure_log() -> None:
    """Create the audit log file (and parent dirs) if it does not exist."""
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    if not AUDIT_LOG.exists():
        AUDIT_LOG.touch()


def log_resolution(resolution: Resolution, stage_id: str) -> str:
    """Append a resolution record to the audit log.

    Returns the unique entry ID.

    This function only *appends*. It never deletes, truncates, or
    overwrites existing content.
    """
    _ensure_log()
    entry_id = uuid.uuid4().hex
    entry = {
        "id": entry_id,
        "timestamp": int(time.time()),
        "stage_id": stage_id,
        "merkle_root": resolution.merkle_root,
        "outcome": resolution.outcome,
        "gvr_state": resolution.gvr_state,
    }
    with AUDIT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry_id


def read_audit(entry_id: str) -> Optional[dict]:
    """Read a specific audit entry by ID."""
    _ensure_log()
    with AUDIT_LOG.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if entry.get("id") == entry_id:
                return entry
    return None


def read_audit_for_stage(stage_id: str) -> list[dict]:
    """Read all audit entries for a given stage."""
    _ensure_log()
    results: list[dict] = []
    with AUDIT_LOG.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if entry.get("stage_id") == stage_id:
                results.append(entry)
    return results
