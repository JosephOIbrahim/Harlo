"""P1c — `harlo doctor` operator readiness command.

Runs the doctor on a clean install and asserts:
  - Exits 0 by default.
  - --json emits a valid report with the expected sections.
  - Compliance section reports clean (no violations) for the production
    invariants from CLAUDE.md.
  - Schemas section reports all three schemas present and parseable.
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner


@pytest.fixture
def tmp_data(monkeypatch, tmp_path):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setenv("HARLO_DATA_DIR", str(tmp_path / "data"))
    import importlib
    import harlo.daemon.config as cfg

    importlib.reload(cfg)
    import harlo.cli.commands.doctor as doctor_mod

    importlib.reload(doctor_mod)
    return tmp_path


def test_doctor_runs_clean(tmp_data) -> None:
    from harlo.cli.commands.doctor import doctor

    runner = CliRunner()
    res = runner.invoke(doctor, [])
    assert res.exit_code == 0, res.output
    assert "Harlo" in res.output
    assert "Data dir" in res.output
    assert "Compliance" in res.output


def test_doctor_json_has_expected_sections(tmp_data) -> None:
    from harlo.cli.commands.doctor import doctor

    runner = CliRunner()
    res = runner.invoke(doctor, ["--json"])
    assert res.exit_code == 0, res.output
    report = json.loads(res.output)

    for key in ("harlo_version", "data_dir", "daemon", "compliance", "schemas", "biometric"):
        assert key in report, f"missing section: {key}"

    # data_dir.path follows HARLO_DATA_DIR override.
    assert str(tmp_data) in report["data_dir"]["path"]


def test_doctor_strict_passes_on_clean_baseline(tmp_data) -> None:
    """The current branch is supposed to be compliance-clean. The doctor
    in --strict mode should exit 0; if it doesn't, surface the offending
    findings in the assertion."""
    from harlo.cli.commands.doctor import doctor

    runner = CliRunner()
    res = runner.invoke(doctor, ["--json", "--strict"])
    if res.exit_code != 0:
        # Re-parse without --strict so we can show what failed.
        plain = runner.invoke(doctor, ["--json"])
        report = json.loads(plain.output)
        violations = [
            f for f in report["compliance"]["findings"]
            if f["status"] == "violation"
        ]
        pytest.fail(
            f"doctor --strict failed; violations:\n"
            + json.dumps(violations, indent=2)
        )


def test_doctor_compliance_section_lists_known_invariants(tmp_data) -> None:
    from harlo.cli.commands.doctor import doctor

    runner = CliRunner()
    res = runner.invoke(doctor, ["--json"])
    report = json.loads(res.output)
    labels = {f["label"] for f in report["compliance"]["findings"]}

    expected = {
        "sleep_calls",
        "while_true",
        "float32",
        "cosine",
        "delete_audit",
        "biometric_in_elenchus_or_bridge",
    }
    assert expected.issubset(labels), labels


def test_doctor_schemas_all_parseable(tmp_data) -> None:
    from harlo.cli.commands.doctor import doctor

    runner = CliRunner()
    res = runner.invoke(doctor, ["--json"])
    report = json.loads(res.output)

    for name, info in report["schemas"].items():
        assert info["exists"], f"{name} missing at {info['path']}"
        assert info["parseable"], f"{name} unparseable"
