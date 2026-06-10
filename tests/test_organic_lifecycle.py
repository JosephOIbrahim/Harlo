"""Organic memory lifecycle — TI-002 permanent closure.

    store → promote → day-scale survival → recall → verify-path reachable

The decay-survival, recall, and verify-surface segments PASS (Δ9 fixed,
ADR-0003 — decay unit is days). The PROMOTION segment is xfail: promotion is an
orphaned WIRING-GAP — no production code path invokes Observer.run_promotion_cycle,
so organically-stored hot traces never reach the warm tier (see
experiments/memory-uplift/LOG.md Cycle 6 / Δ12).

Removing the xfail on test_organic_promotion_is_wired when promotion is wired IS
the acceptance test for that fix.
"""

from __future__ import annotations

import pathlib
import sqlite3
import subprocess
import time

import pytest

from harlo import hippocampus

DAY = 86_400
REPO = pathlib.Path(__file__).resolve().parents[1]


def _backdate(db: str, trace_id: str, age_days: int, now: int) -> None:
    """Move a stored trace's created_at into the past (simulated clock)."""
    con = sqlite3.connect(db)
    con.execute(
        "UPDATE traces SET created_at = ?, last_accessed = ? WHERE id = ?",
        (now - age_days * DAY, now - age_days * DAY, trace_id),
    )
    con.commit()
    con.close()


def test_day_old_trace_survives_apoptosis(tmp_path):
    """Δ9 contract via the REAL Rust apoptosis path: a one-day-old trace
    survives; a 200-day-old one is reaped. Pre-fix (seconds) the day-old trace
    decayed to ~0 and was deleted — this is the permanent regression guard."""
    db = str(tmp_path / "twin.db")
    now = int(time.time())
    hippocampus.py_store_trace("fresh", "morning run felt strong today", db_path=db)
    hippocampus.py_store_trace("ancient", "a memory from long ago", db_path=db)
    _backdate(db, "fresh", 1, now)       # 1 day  → e^(-0.05) ≈ 0.95  (survives)
    _backdate(db, "ancient", 200, now)   # 200 d  → e^(-10)  ≈ 0      (reaped)

    hippocampus.py_microglia(0.01, db)   # now = wall clock, ε = 0.01

    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    ids = {r[0] for r in con.execute("SELECT id FROM traces")}
    con.close()
    assert "fresh" in ids, "a one-day-old trace must survive (Δ9 / ADR-0003)"
    assert "ancient" not in ids, "a 200-day-old trace should be reaped"


def test_survivor_is_recallable(tmp_path):
    """A day-old survivor is still recallable via the hot path."""
    db = str(tmp_path / "twin.db")
    now = int(time.time())
    hippocampus.py_store_trace(
        "d1", "burnout signals climb on evening pushes", db_path=db
    )
    _backdate(db, "d1", 1, now)

    result = hippocampus.py_recall("burnout evening pushes", "normal", db)
    assert result.get("traces"), f"day-old survivor not recalled: {result}"


def test_verify_path_surface_reachable():
    """The verification path exists as a surface (ElenchusQueue enumerate +
    resolve). Wiring it to organic traces is out of scope per the Cycle 6 HALT;
    this only asserts the API is reachable."""
    from harlo.elenchus_v8 import ElenchusQueue

    assert hasattr(ElenchusQueue, "get_pending")
    assert hasattr(ElenchusQueue, "pending_count")


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Promotion WIRING-GAP: no production code path calls "
        "Observer.run_promotion_cycle, so organically-stored hot traces never "
        "reach the warm tier. See experiments/memory-uplift/LOG.md Cycle 6 / "
        "Δ12. Removing this xfail when promotion is wired IS the acceptance test."
    ),
)
def test_organic_promotion_is_wired():
    """An organically-stored hot trace must reach warm through the system's OWN
    machinery — not a hand call to promote_batch. Operationalized: a production
    (non-test) caller of run_promotion_cycle must exist. Today none does."""
    hits = subprocess.run(
        ["grep", "-rn", "run_promotion_cycle", "--include=*.py", str(REPO / "python")],
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    callers = [ln for ln in hits if "def run_promotion_cycle" not in ln]
    assert callers, "no production caller invokes promotion (orphaned pipeline, Cycle 6)"
