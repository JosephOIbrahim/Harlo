"""Persisted modulation state — the durable bridge between the
socket-activated daemon's biometric ingest and the Motor Cortex gate.

C3 fix: ``_handle_biometric_ingest`` computes ``is_depleted`` /
``should_force_red`` from the ``AllostasisTracker``, but the Basal Ganglia
gate reads ``session_state['biometric_force_red']`` and **nothing ever
wrote it**. Because the daemon is short-lived (Rule 1), the in-process
tracker dies between activations, so the derived state must be persisted
to be visible to a later motor command.

Rule 9 / ADR-0001 (binding): ONLY *derived* scalars cross this boundary —
a boolean (``biometric_force_red``), a boolean (``is_depleted``), a
normalized float (``biometric_load``), and an optional ``cognitive_state``
enum. The raw HR / HRV sample VALUES never leave the Modulation Layer and
are never written here. ``_ALLOWED_KEYS`` enforces that structurally.

ADR-0001 constraint 4 (freshness): a frozen RED snapshot older than the
freshness window must not keep inhibiting motor — Apple Watch → Mac
latency means a stale spike cannot be trusted to drive RED.
``apply_to_session_state`` expires a stale ``biometric_force_red`` while
leaving ``is_depleted`` intact (stale samples may still indicate DEPLETED).

Rule 1: event-driven read/write of a small JSON file. No polling.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from harlo.daemon.config import DATA_DIR

MODULATION_STATE_PATH = DATA_DIR / "modulation_state.json"

# Mirrors AllostasisTracker._BIOMETRIC_RED_FRESHNESS_SEC (default 5 min).
RED_FRESHNESS_SEC = 300.0

# The ONLY keys allowed to be persisted — a structural guard against a raw
# biometric value leaking through this file (Rule 9 / ADR-0001).
_ALLOWED_KEYS = frozenset(
    {
        "is_depleted",
        "biometric_force_red",
        "biometric_load",
        "cognitive_state",
        "updated_at",
    }
)


@dataclass(frozen=True)
class ModulationState:
    """Derived modulation state. No raw biometric values, ever."""

    is_depleted: bool = False
    biometric_force_red: bool = False
    biometric_load: float = 0.0
    cognitive_state: str = "NORMAL"  # NORMAL | DEPLETED | RED
    updated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def write_modulation_state(
    state: ModulationState, path: Path | None = None
) -> None:
    """Atomically persist derived modulation state (temp file + os.replace)."""
    target = path or MODULATION_STATE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {k: v for k, v in state.to_dict().items() if k in _ALLOWED_KEYS}
    fd, tmp = tempfile.mkstemp(dir=str(target.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def read_modulation_state(path: Path | None = None) -> ModulationState:
    """Read derived modulation state. Returns defaults if absent/corrupt."""
    target = path or MODULATION_STATE_PATH
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return ModulationState()
    if not isinstance(raw, dict):
        return ModulationState()
    filtered = {k: raw[k] for k in raw if k in _ALLOWED_KEYS}
    try:
        return ModulationState(**filtered)
    except TypeError:
        return ModulationState()


def apply_to_session_state(
    session_state: dict,
    path: Path | None = None,
    now: float | None = None,
    freshness_sec: float = RED_FRESHNESS_SEC,
) -> dict:
    """Merge persisted derived modulation state into a motor ``session_state``.

    The Basal Ganglia gate consults ``session_state['biometric_force_red']``
    (Rule 28) and ``session_state['is_depleted']`` (Rule 27). This is the
    wire that makes a fresh biometric panic actually reach the gate.

    A ``biometric_force_red`` snapshot older than ``freshness_sec`` is
    expired (ADR-0001 constraint 4); ``is_depleted`` is left intact.
    """
    state = read_modulation_state(path)
    now = now if now is not None else time.time()
    merged = dict(session_state)
    merged["is_depleted"] = state.is_depleted

    force_red = state.biometric_force_red
    if force_red and state.updated_at and (now - state.updated_at) > freshness_sec:
        force_red = False  # stale RED snapshot — cannot keep inhibiting motor
    merged["biometric_force_red"] = force_red
    # NOTE: we deliberately do NOT overwrite cognitive_state to "RED" here.
    # Biometric panic inhibits motor via the dedicated biometric_force_red
    # flag (Rule 28 + ADR-0001). Escalating the whole system to RED (Rule 18
    # "RED overrides everything" — halts GVR/inquiry/injection + Recovery
    # menu) is a stronger, separate transition that biometrics must not
    # trigger on their own. The persisted ModulationState.cognitive_state
    # remains available for surfacing/UI.
    return merged


__all__ = [
    "MODULATION_STATE_PATH",
    "RED_FRESHNESS_SEC",
    "ModulationState",
    "apply_to_session_state",
    "read_modulation_state",
    "write_modulation_state",
]
