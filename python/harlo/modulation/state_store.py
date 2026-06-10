"""Persistent modulation state — D60 (CTO review).

The AllostasisTracker is a process-local in-memory deque; with a
socket-activated, short-lived daemon its DEPLETED/force_red verdicts
died with the process and never reached the coach or MCP surface
(Rule 9 "High = DEPLETED" and Rule 28 were unenforceable end-to-end).

This store persists the tracker's DERIVED verdicts — never raw
samples — to a single-row table in twin.db so any process (coach,
status, future Basal Ganglia wiring) can read the latest modulation
state. Rule 9 holds: raw biometric values stay in memory and die with
the tracker; only load/depleted/force_red/sample-counts cross here.

Single row, last-writer-wins: modulation state is a "current verdict",
not a time series.
"""

from __future__ import annotations

import sqlite3
import time

_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS modulation_state (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        biometric_load REAL NOT NULL DEFAULT 0.0,
        depleted INTEGER NOT NULL DEFAULT 0,
        force_red INTEGER NOT NULL DEFAULT 0,
        samples_accepted INTEGER NOT NULL DEFAULT 0,
        updated_at REAL NOT NULL
    )
"""

# Verdicts older than this are stale — a dead bridge must not pin the
# coach in DEPLETED forever. Mirrors ADR-0001's freshness philosophy
# (samples have a 5-min RED window; the derived verdict gets a longer
# but still bounded shelf life).
STALE_AFTER_SEC = 30 * 60.0


def write_modulation_state(
    db_path: str,
    *,
    biometric_load: float,
    depleted: bool,
    force_red: bool,
    samples_accepted: int,
    now: float | None = None,
) -> None:
    """Persist the tracker's current derived verdict (UPSERT row id=1)."""
    ts = now if now is not None else time.time()
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(_TABLE_SQL)
        conn.execute(
            """INSERT INTO modulation_state
               (id, biometric_load, depleted, force_red, samples_accepted, updated_at)
               VALUES (1, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 biometric_load = excluded.biometric_load,
                 depleted = excluded.depleted,
                 force_red = excluded.force_red,
                 samples_accepted = excluded.samples_accepted,
                 updated_at = excluded.updated_at""",
            (float(biometric_load), int(depleted), int(force_red),
             int(samples_accepted), ts),
        )
        conn.commit()
    finally:
        conn.close()


def read_modulation_state(db_path: str, *, now: float | None = None) -> dict | None:
    """Read the latest modulation verdict, or None when absent/stale.

    Staleness: past STALE_AFTER_SEC the verdict is reported with
    depleted/force_red forced False (stale data must never inhibit —
    same principle as ADR-0001's freshness window) and `stale: True`
    so consumers can surface "bridge silent since …" if they care.
    """
    ts = now if now is not None else time.time()
    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.Error:
        return None
    try:
        try:
            row = conn.execute(
                """SELECT biometric_load, depleted, force_red,
                          samples_accepted, updated_at
                   FROM modulation_state WHERE id = 1"""
            ).fetchone()
        except sqlite3.OperationalError:
            return None  # table never created — no bridge has pushed
        if row is None:
            return None
        load, depleted, force_red, accepted, updated_at = row
        stale = (ts - updated_at) > STALE_AFTER_SEC
        return {
            "biometric_load": float(load),
            "depleted": bool(depleted) and not stale,
            "force_red": bool(force_red) and not stale,
            "samples_accepted": int(accepted),
            "updated_at": float(updated_at),
            "age_seconds": max(0.0, ts - updated_at),
            "stale": stale,
        }
    finally:
        conn.close()


__all__ = ["read_modulation_state", "write_modulation_state", "STALE_AFTER_SEC"]
