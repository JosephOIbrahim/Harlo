"""D60 — persistent modulation state.

The AllostasisTracker's verdicts previously died with the short-lived
daemon process. These tests pin: write/read round-trip, staleness
clamping (stale data must never inhibit), absent-table behavior, and
the ingest handler actually persisting.
"""

import time

from harlo.modulation.state_store import (
    STALE_AFTER_SEC,
    read_modulation_state,
    write_modulation_state,
)


def test_round_trip(tmp_path):
    db = str(tmp_path / "twin.db")
    write_modulation_state(
        db, biometric_load=0.72, depleted=True, force_red=False,
        samples_accepted=5,
    )
    state = read_modulation_state(db)
    assert state is not None
    assert state["biometric_load"] == 0.72
    assert state["depleted"] is True
    assert state["force_red"] is False
    assert state["samples_accepted"] == 5
    assert state["stale"] is False


def test_single_row_upsert(tmp_path):
    db = str(tmp_path / "twin.db")
    write_modulation_state(db, biometric_load=0.1, depleted=False,
                           force_red=False, samples_accepted=1)
    write_modulation_state(db, biometric_load=0.9, depleted=True,
                           force_red=True, samples_accepted=2)
    state = read_modulation_state(db)
    assert state["biometric_load"] == 0.9
    assert state["force_red"] is True


def test_stale_verdict_never_inhibits(tmp_path):
    """ADR-0001 principle: stale data cannot drive RED/DEPLETED."""
    db = str(tmp_path / "twin.db")
    old = time.time() - STALE_AFTER_SEC - 60
    write_modulation_state(db, biometric_load=0.95, depleted=True,
                           force_red=True, samples_accepted=9, now=old)
    state = read_modulation_state(db)
    assert state["stale"] is True
    assert state["depleted"] is False
    assert state["force_red"] is False
    # Load is still reported for observability.
    assert state["biometric_load"] == 0.95


def test_absent_table_returns_none(tmp_path):
    db = str(tmp_path / "empty.db")
    # No write ever happened — no table, no row, no error.
    assert read_modulation_state(db) is None


def test_ingest_handler_persists(tmp_path, monkeypatch):
    """_handle_biometric_ingest writes the verdict to the state store."""
    import harlo.daemon.config as cfg
    monkeypatch.setattr(cfg, "DB_PATH", tmp_path / "twin.db")

    from harlo.daemon.router import _handle_biometric_ingest

    sample = {
        "type": "heart_rate",
        "value": 62.0,
        "unit": "count/min",
        "sampled_at": "2026-06-10T08:00:00Z",
        "source": {"device": "Apple Watch Series 10"},
    }
    res = _handle_biometric_ingest({"samples": [sample]})
    assert res["status"] == "ok"
    assert res["result"]["accepted"] == 1

    state = read_modulation_state(str(tmp_path / "twin.db"))
    assert state is not None
    assert state["samples_accepted"] == 1
