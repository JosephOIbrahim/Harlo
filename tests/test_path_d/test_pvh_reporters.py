"""Reporter + CLI smoke tests (hermetic; temp DB, no real corpus)."""

from __future__ import annotations

import json
from pathlib import Path

from harness.path_d.pvh.cli import main
from harness.path_d.pvh.evaluators import evaluate_session
from harness.path_d.pvh.extractor import MISSING_FIELDS, Session, SessionMeta, Window
from harness.path_d.pvh.reporters import write_evidence_artifact
from src.schemas import CognitiveObservation


def _state(burnout=1):
    return {"momentum": 0, "burnout": burnout, "energy": 2, "burst_phase": 0}


def _obs(exch):
    return CognitiveObservation(session_id="s", exchange_index=exch, observation_index=exch)


def test_cli_produces_artifacts(tmp_path, obs_db):
    db = obs_db([{"session_id": "live", "exchange_index": i} for i in range(5)])
    outdir = tmp_path / "run"
    rc = main(["--db", db, "--output", str(outdir), "--no-predictor"])
    assert rc == 0

    metrics = outdir / "pvh_metrics.json"
    evidence = outdir / "evidence_artifact.md"
    assert metrics.exists() and evidence.exists()

    payload = json.loads(metrics.read_text())
    assert payload["schema"] == "pvh_metrics/v1"
    assert len(payload["sessions"]) == 1

    text = evidence.read_text()
    for tag in ("(a)", "(b)", "(c)", "(d)"):
        assert tag in text, f"missing required v1 limitation {tag}"
    assert "no multiplier" in text.lower() or "no claim" in text.lower()


def test_metrics_overshoot_key_before_deflection(tmp_path, obs_db):
    db = obs_db([{"session_id": "s", "exchange_index": i} for i in range(4)])
    outdir = tmp_path / "run"
    main(["--db", db, "--output", str(outdir), "--no-predictor"])
    sess = json.loads((outdir / "pvh_metrics.json").read_text())["sessions"][0]
    keys = list(sess.keys())
    assert keys.index("overshoot_baseline") < keys.index("deflection")  # Commandment 5


def test_reporter_renders_leakage_confirmed(tmp_path):
    windows = tuple(
        Window(index=i, observations=(_obs(i - 2), _obs(i - 1), _obs(i)),
               actual=_state(1), predicted=_state(1))
        for i in range(2, 5)
    )
    meta = SessionMeta(obs_count=5, window_count=3, below_window_threshold=False,
                       missing_fields=MISSING_FIELDS, dropped_rows=0,
                       ordering_warnings=(), created_at_range=(None, None))
    sess = Session("s", "organic", tuple(_obs(i) for i in range(5)), windows, meta)
    result = evaluate_session(sess)
    out = tmp_path / "evidence.md"
    write_evidence_artifact([result], out)
    assert "confirmed" in out.read_text()
