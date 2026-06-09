"""Path C persistence layer — real OpenUSD canonical storage.

Imports pxr only here. If [substrate] extra is not installed, the
module import fails with a clear error pointing to the install command.
Runtime tier (parent harlo.usd_lite package) does NOT import this module
and stays pxr-free per Constitution Law 3.
"""
from __future__ import annotations

try:
    from pxr import Sdf, Usd, Plug  # noqa: F401
except ImportError as exc:
    raise ImportError(
        "harlo.usd_lite.persistence requires the [substrate] extra. "
        "Install via: pip install -e .[substrate]  (or "
        "pip install \"usd-core>=24.05\" if the editable build "
        "fails on a .pyd file lock — see harness/path_c/substrate_pin.md)."
    ) from exc

from .writer import write
from .reader import read


def persist_current_brain(db_path: str, stage_dir) -> dict:
    """Assemble the current cognitive state and write it to a real .usda.

    Explicit persist entrypoint for the USD-proof trial verifier. Reads
    in-process state (SessionManager + Hot Tier traces), assembles a BrainStage
    via the existing brainstem.stage_builder, and writes via writer.write.
    The v9 cognitive engine's init path is NOT modified — persistence stays
    an operation invoked at known times, not a side-effect of engine init
    (architect amendment 1).

    Decision tier (MotorPrim) is deferred — the v9 engine doesn't produce a
    MotorPrim in any minimal flow; fabricating one to satisfy the verifier
    would be hallucinated completion (architect amendment 2).

    Args:
        db_path: Path to twin.db (SessionManager + Hot Tier live there).
        stage_dir: Directory to write runtime.usda under (created if absent).

    Returns:
        dict with: ``path`` (str), ``tier_counts`` (dict[str, int] for
        session/entity/decision), ``decision_deferred`` (bool),
        ``decision_deferred_reason`` (str).
    """
    # Lazy imports: keep module-level imports pxr-only per the layer's
    # Constitution Law 3 — runtime tier must not pull pxr through us.
    from pathlib import Path
    import sqlite3

    from harlo.session.manager import SessionManager
    from harlo.brainstem.stage_builder import full_stage

    stage_dir = Path(stage_dir)
    stage_dir.mkdir(parents=True, exist_ok=True)

    # --- Session tier --------------------------------------------------------
    # Ensure SessionManager has an active session. The verifier path runs in
    # a fresh spawn where the v9 engine's "live" session isn't mirrored into
    # SessionManager, so persist creates one if absent. The session is real,
    # not fabricated — domain="trial-verifier" makes the provenance auditable.
    sm = SessionManager(db_path)
    active = sm.list_active()
    if not active:
        sm.create(domain="trial-verifier")
        active = sm.list_active()
    session_dict = active[0].to_dict() if active else None

    # --- Entity tier ---------------------------------------------------------
    # Read from hot_traces (twin_store's destination). Promotion to Warm is
    # async; we don't wait for it. The SDR field is placeholder (zero vector)
    # because Hot Tier doesn't encode; that's fine for P1's structural check.
    traces_for_recall: list[dict] = []
    try:
        conn = sqlite3.connect(db_path)
        try:
            try:
                rows = conn.execute(
                    "SELECT trace_id, message FROM hot_traces "
                    "ORDER BY rowid DESC LIMIT 50"
                ).fetchall()
            except sqlite3.OperationalError:
                rows = []  # hot_traces table not yet created
            for trace_id, message in rows:
                traces_for_recall.append({
                    "trace_id": trace_id,
                    "content_hash": (message or "")[:16],
                    "strength": 1.0,
                    "sdr": [0] * 2048,
                })
        finally:
            conn.close()
    except sqlite3.Error:
        pass  # no twin.db yet — empty entity tier

    recall_result = {"traces": traces_for_recall} if traces_for_recall else None

    # --- Decision tier -------------------------------------------------------
    # DEFERRED (amendment 2). No fabrication.

    brain = full_stage(session=session_dict, recall_result=recall_result)

    path = stage_dir / "runtime.usda"
    write(brain, str(path))

    return {
        "path": str(path),
        "tier_counts": {
            "session": 1 if session_dict else 0,
            "entity": len(traces_for_recall),
            "decision": 0,
        },
        "decision_deferred": True,
        "decision_deferred_reason": (
            "no minimal-flow MotorPrim production in v9 engine — needs a "
            "motor-system wire-up cycle (separate decision)"
        ),
    }


__all__ = ["write", "read", "persist_current_brain"]
