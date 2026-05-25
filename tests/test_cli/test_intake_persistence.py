"""P1a — intake completion writes Merkle layers to STAGES_DIR.

Until this lands, `harlo intake start` echoed layers but persisted
nothing. This test runs intake end-to-end and confirms:
  - a stage file `intake-{session_id}.json` exists under STAGES_DIR;
  - it contains exactly three layers in the expected LIVRPS order;
  - every layer carries `intake_calibrated` provenance;
  - the returned merkle_root matches the rebuilt stage's root.
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

    importlib.reload(intake_mod)
    return tmp_path


def _scripted_answers() -> str:
    return "\n".join(
        [
            "connect to many",
            "specific details",
            "short bursts",
            "sharper",
            "analogies",
            "specifics first",
        ]
    ) + "\n"


def test_intake_persists_three_layers_to_stages_dir(tmp_data) -> None:
    from harlo.cli.commands.intake import intake

    runner = CliRunner()
    res = runner.invoke(intake, ["start", "--json"], input=_scripted_answers())
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)
    assert payload["status"] == "completed"

    stage_info = payload["stage"]
    stage_path = Path(stage_info["stage_path"])
    assert stage_path.exists(), stage_path

    data = json.loads(stage_path.read_text(encoding="utf-8"))
    layer_ids = [l["layer_id"] for l in data["layers"]]
    assert layer_ids == ["UserProfile", "InitialAnchorAnnotations", "CoachingContext"]

    for layer in data["layers"]:
        prov = layer["data"]["provenance"]
        assert prov["source_type"] == "intake_calibrated"

    assert data["merkle_root"] == stage_info["merkle_root"]


def test_intake_stage_id_namespaces_by_session(tmp_data) -> None:
    from harlo.cli.commands.intake import intake

    runner = CliRunner()
    res = runner.invoke(intake, ["start", "--json"], input=_scripted_answers())
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)

    expected_prefix = f"intake-{payload['session_id']}"
    assert payload["stage"]["stage_id"] == expected_prefix


def test_intake_stage_loads_back_via_merklestage(tmp_data) -> None:
    """A persisted intake stage round-trips through MerkleStage."""
    from harlo.cli.commands.intake import intake
    from harlo.composition.stage import MerkleStage

    runner = CliRunner()
    res = runner.invoke(intake, ["start", "--json"], input=_scripted_answers())
    payload = json.loads(res.output)
    stage_path = Path(payload["stage"]["stage_path"])
    raw = json.loads(stage_path.read_text(encoding="utf-8"))

    stage = MerkleStage.from_dict(raw)
    assert stage.get_merkle_root() == payload["stage"]["merkle_root"]
    assert len(stage.get_layers()) == 3
