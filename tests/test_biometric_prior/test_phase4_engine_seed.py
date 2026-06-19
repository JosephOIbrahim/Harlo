"""Phase 4 deep seed — the v9 engine's RESOLVED energy for a new session's first
exchange comes from today's biometric_prior (not the MEDIUM baseline), and the
session then transitions from the seed.

Gated by BIOMETRICS_ENABLED; once per session; no-op when disabled or absent;
never breaks the exchange.
"""

from __future__ import annotations

import harlo.biometric_prior.readpath as readpath
from harlo.engine.cognitive_engine import CognitiveEngine
from harlo.engine.schemas import Energy


def _engine():
    return CognitiveEngine(in_memory=True, prediction_enabled=False, observation_logging=False)


def _exchange(eng, session_id, msg="hi"):
    eng.process_exchange("twin_recall", {"message": msg}, session_id=session_id, current_time_iso=None)
    return eng._observations[-1].state.energy  # the RESOLVED, post-DAG energy


def test_resolved_energy_seeded_when_enabled(monkeypatch):
    monkeypatch.setenv("BIOMETRICS_ENABLED", "1")
    monkeypatch.setattr(readpath, "seed_block", lambda *a, **k: {"energy": "LOW", "directive_mode": False})
    assert _exchange(_engine(), "sess-A") == Energy.LOW


def test_seed_once_per_session_then_transitions(monkeypatch):
    monkeypatch.setenv("BIOMETRICS_ENABLED", "1")
    box = {"v": {"energy": "HIGH"}}
    monkeypatch.setattr(readpath, "seed_block", lambda *a, **k: box["v"])
    eng = _engine()
    assert _exchange(eng, "sess-A") == Energy.HIGH   # first exchange → seeded HIGH
    box["v"] = {"energy": "LOW"}                       # prior "changes" mid-session
    assert _exchange(eng, "sess-A") == Energy.HIGH   # NOT re-seeded → transitions from HIGH
    assert _exchange(eng, "sess-B") == Energy.LOW    # new session → seeded again (no leak)


def test_no_seed_when_kill_switch_off(monkeypatch):
    monkeypatch.delenv("BIOMETRICS_ENABLED", raising=False)
    monkeypatch.setattr(readpath, "seed_block", lambda *a, **k: {"energy": "LOW"})
    assert _exchange(_engine(), "sess-A") == Energy.MEDIUM


def test_no_seed_when_no_prior_today(monkeypatch):
    monkeypatch.setenv("BIOMETRICS_ENABLED", "1")
    monkeypatch.setattr(readpath, "seed_block", lambda *a, **k: None)
    assert _exchange(_engine(), "sess-A") == Energy.MEDIUM


def test_seed_failure_never_breaks_exchange(monkeypatch):
    monkeypatch.setenv("BIOMETRICS_ENABLED", "1")

    def boom(*a, **k):
        raise RuntimeError("buffer exploded")

    monkeypatch.setattr(readpath, "seed_block", boom)
    assert _exchange(_engine(), "sess-A") == Energy.MEDIUM
