"""P1b — `harlo audit --layers --provenance ...` surfaces intake layers.

The intake CLI persists three INTAKE_CALIBRATED layers to a MerkleStage
under STAGES_DIR. This test:

  1. Runs intake end-to-end so the stage file exists.
  2. Invokes `harlo audit --layers --provenance intake_calibrated`.
  3. Asserts the response lists the freshly persisted stage with
     exactly the three expected layers, in order.

Direct in-process execution path — the daemon's not running in tests,
so the IPC client falls back to `run_direct`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner


@pytest.fixture
def tmp_data(monkeypatch, tmp_path):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setenv("HARLO_DATA_DIR", str(tmp_path / "data"))
    import importlib
    import harlo.daemon.config as cfg

    importlib.reload(cfg)
    import harlo.cli.commands.intake as intake_mod
    import harlo.cli.commands.audit as audit_mod

    importlib.reload(intake_mod)
    importlib.reload(audit_mod)
    return tmp_path


def _run_intake() -> str:
    from harlo.cli.commands.intake import intake

    runner = CliRunner()
    answers = "\n".join(
        [
            "connect to many",
            "specific details",
            "short bursts",
            "sharper",
            "analogies",
            "specifics first",
        ]
    ) + "\n"
    res = runner.invoke(intake, ["start", "--json"], input=answers)
    assert res.exit_code == 0, res.output
    return res.output


def test_audit_layers_lists_intake_stage(tmp_data) -> None:
    from harlo.cli.commands.audit import audit

    intake_payload = json.loads(_run_intake())
    expected_stage_id = intake_payload["stage"]["stage_id"]

    runner = CliRunner()
    res = runner.invoke(
        audit,
        ["--layers", "--provenance", "intake_calibrated", "--json"],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)

    stage_ids = [s["stage_id"] for s in data["stages"]]
    assert expected_stage_id in stage_ids

    stage = next(s for s in data["stages"] if s["stage_id"] == expected_stage_id)
    layer_ids = [l["layer_id"] for l in stage["layers"]]
    assert layer_ids == ["UserProfile", "InitialAnchorAnnotations", "CoachingContext"]
    assert data["layer_count"] >= 3


def test_audit_layers_filters_out_unmatched_provenance(tmp_data) -> None:
    from harlo.cli.commands.audit import audit

    _run_intake()

    runner = CliRunner()
    # No layer in this codebase has source_type=user_direct, so the
    # provenance filter should yield zero matches.
    res = runner.invoke(
        audit,
        ["--layers", "--provenance", "user_direct", "--json"],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["stages"] == []
    assert data["layer_count"] == 0


def test_audit_layers_without_provenance_lists_all(tmp_data) -> None:
    from harlo.cli.commands.audit import audit

    intake_payload = json.loads(_run_intake())
    expected_stage_id = intake_payload["stage"]["stage_id"]

    runner = CliRunner()
    res = runner.invoke(audit, ["--layers", "--json"])
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    stage_ids = [s["stage_id"] for s in data["stages"]]
    assert expected_stage_id in stage_ids


def test_audit_without_layers_flag_still_requires_id(tmp_data) -> None:
    from harlo.cli.commands.audit import audit

    runner = CliRunner()
    res = runner.invoke(audit, ["--json"])
    # SystemExit(2) → click exit code 2.
    assert res.exit_code != 0
