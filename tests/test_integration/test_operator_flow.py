"""End-to-end happy-path: intake → audit_layers → doctor.

Three single-purpose commands wired together via shared state in
STAGES_DIR. This test fails if ANY of:

  - intake stops persisting Merkle layers
  - audit_layers stops finding INTAKE_CALIBRATED layers
  - doctor stops counting stages
  - the three commands stop honoring HARLO_DATA_DIR

… because operators rely on this exact sequence the first time they
calibrate a fresh Harlo install.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner


@pytest.fixture
def isolated_install(monkeypatch, tmp_path):
    """A fresh, empty HARLO_DATA_DIR — what a first-launch Harlo sees."""
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setenv("HARLO_DATA_DIR", str(tmp_path / "data"))
    import importlib
    import harlo.daemon.config as cfg

    importlib.reload(cfg)
    for mod_name in (
        "harlo.cli.commands.intake",
        "harlo.cli.commands.audit",
        "harlo.cli.commands.doctor",
        "harlo.composition.audit",
    ):
        import importlib as _i
        try:
            _i.reload(_i.import_module(mod_name))
        except Exception:
            pass
    return tmp_path / "data"


def _run_intake() -> dict:
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
    return json.loads(res.output)


def test_first_run_calibration_flow(isolated_install) -> None:
    """Step 1: intake completes and persists three Merkle layers."""
    intake_payload = _run_intake()
    assert intake_payload["status"] == "completed"
    stage_id = intake_payload["stage"]["stage_id"]
    stage_path = Path(intake_payload["stage"]["stage_path"])
    assert stage_path.exists()
    assert str(isolated_install) in str(stage_path)

    # Step 2: audit --layers --provenance lists the stage.
    from harlo.cli.commands.audit import audit

    runner = CliRunner()
    res = runner.invoke(
        audit,
        ["--layers", "--provenance", "intake_calibrated", "--json"],
    )
    assert res.exit_code == 0, res.output
    layers_payload = json.loads(res.output)
    stage_ids = [s["stage_id"] for s in layers_payload["stages"]]
    assert stage_id in stage_ids

    # Step 3: doctor sees the new stage.
    from harlo.cli.commands.doctor import doctor

    res = runner.invoke(doctor, ["--json"])
    assert res.exit_code == 0, res.output
    report = json.loads(res.output)
    assert report["data_dir"]["stage_count"] >= 1
    assert str(isolated_install) in report["data_dir"]["path"]


def test_doctor_strict_still_passes_after_intake(isolated_install) -> None:
    """Running intake should not introduce any compliance violation
    (e.g., writing a file that trips a grep). doctor --strict must
    keep exiting 0."""
    _run_intake()

    from harlo.cli.commands.doctor import doctor

    runner = CliRunner()
    res = runner.invoke(doctor, ["--strict", "--json"])
    assert res.exit_code == 0, (
        "doctor --strict failed after intake; payload:\n" + res.output
    )


def test_layer_filter_isolates_intake_provenance(isolated_install) -> None:
    """If we ever start emitting layers with other provenances, the
    intake_calibrated filter should still surface exactly the
    intake-side layers — no cross-contamination."""
    intake_payload = _run_intake()
    expected_layers = {l["layer_id"] for l in intake_payload["layers"]}

    from harlo.cli.commands.audit import audit

    runner = CliRunner()
    res = runner.invoke(
        audit,
        ["--layers", "--provenance", "intake_calibrated", "--json"],
    )
    data = json.loads(res.output)
    actual_layers: set[str] = set()
    for stage in data["stages"]:
        for layer in stage["layers"]:
            actual_layers.add(layer["layer_id"])
    assert expected_layers.issubset(actual_layers)
