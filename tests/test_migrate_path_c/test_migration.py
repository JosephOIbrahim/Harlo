"""Migration script tests.

Per Phase 4 design §3 + §4. Crucible Gate 4 verifies criteria 1-2
(round-trip fidelity, idempotence) plus 1,164 baseline preservation.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def _import_persistence_or_skip():
    try:
        from harlo.usd_lite.persistence import read, write  # noqa: F401
    except ImportError as exc:
        pytest.skip(f"persistence layer unavailable: {exc}")


HEBBIAN_SEEDED = Path(__file__).resolve().parents[2] / "data" / "hebbian_seeded.usda"


def test_migrate_hebbian_seeded(tmp_path):
    """Crucible Gate 4 criterion 1: round-trip without data loss."""
    _import_persistence_or_skip()
    from harlo.migrate_path_c import migrate
    from harlo.usd_lite.persistence import read
    from harlo.usd_lite.serializer import parse

    if not HEBBIAN_SEEDED.exists():
        pytest.skip(f"reference fixture absent: {HEBBIAN_SEEDED}")

    output = tmp_path / "hebbian_seeded.migrated.usda"
    report = migrate(str(HEBBIAN_SEEDED), str(output))

    assert report.error is None, f"migration error: {report.error}"
    assert report.exit_code == 0
    assert report.input_format == "old"
    assert output.exists()

    # Round-trip equality: parse old format, read new format, compare
    original_stage = parse(HEBBIAN_SEEDED.read_text(encoding="utf-8"))
    migrated_stage = read(str(output))
    assert original_stage == migrated_stage


def test_migrate_idempotent(tmp_path):
    """Crucible Gate 4 criterion 2: running on the new format is a no-op."""
    _import_persistence_or_skip()
    from harlo.migrate_path_c import migrate
    from harlo.usd_lite.persistence import write
    from harlo.usd_lite.stage import BrainStage

    # Produce a new-format file directly.
    new_format_path = tmp_path / "new_format.usda"
    write(BrainStage(), str(new_format_path))

    report = migrate(str(new_format_path), str(tmp_path / "second_pass.usda"))
    assert report.error is None
    assert report.exit_code == 0
    assert report.input_format == "new"
    assert report.prims_migrated == {}
    # Idempotence: no second-pass output written
    assert not (tmp_path / "second_pass.usda").exists()


def test_migrate_unknown_format(tmp_path):
    """Unrecognized input → exit code 1, no output written."""
    from harlo.migrate_path_c import migrate

    bogus = tmp_path / "bogus.txt"
    bogus.write_text("this is not a usda file at all\n")

    report = migrate(str(bogus), str(tmp_path / "out.usda"))
    assert report.input_format == "unknown"
    assert report.exit_code == 1
    assert report.error is not None


def test_migrate_dry_run(tmp_path):
    """Dry run reports prim counts but does not write the output file."""
    _import_persistence_or_skip()
    from harlo.migrate_path_c import migrate

    if not HEBBIAN_SEEDED.exists():
        pytest.skip(f"reference fixture absent: {HEBBIAN_SEEDED}")

    output = tmp_path / "dry_run_output.usda"
    report = migrate(str(HEBBIAN_SEEDED), str(output), dry_run=True)

    assert report.error is None
    assert report.dry_run is True
    assert report.input_format == "old"
    assert sum(report.prims_migrated.values()) > 0
    assert not output.exists(), "dry_run should not write output"


def test_migrate_cli_smoke(tmp_path):
    """Smoke test: `python -m harlo.migrate_path_c ...` invocation."""
    _import_persistence_or_skip()

    if not HEBBIAN_SEEDED.exists():
        pytest.skip(f"reference fixture absent: {HEBBIAN_SEEDED}")

    output = tmp_path / "cli_output.usda"
    report_json = tmp_path / "cli_report.json"

    result = subprocess.run(
        [
            sys.executable, "-m", "harlo.migrate_path_c",
            str(HEBBIAN_SEEDED),
            "--output", str(output),
            "--report", str(report_json),
        ],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, (
        f"CLI invocation failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert output.exists()
    assert report_json.exists()

    report = json.loads(report_json.read_text())
    assert report["input_format"] == "old"
    assert report["error"] is None
    assert sum(report["prims_migrated"].values()) > 0


def test_migrate_report_structure(tmp_path):
    """MigrationReport.to_dict() exposes the expected keys."""
    from harlo.migrate_path_c import migrate

    bogus = tmp_path / "missing.usda"
    report = migrate(str(bogus), str(tmp_path / "out.usda"))
    d = report.to_dict()
    assert "input_path" in d
    assert "output_path" in d
    assert "input_format" in d
    assert "prims_migrated" in d
    assert "codec_conversions" in d
    assert "dry_run" in d
    assert "error" in d
    assert "exit_code" in d
