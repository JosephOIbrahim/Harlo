"""Tests for session.first_run — fresh install, migration, and the
new launchd install offer (Phase 5A).

The launchd offer is only active on macOS; the test suite runs on
both Linux (CI/dev) and macOS, so the cross-platform paths must
short-circuit cleanly.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def isolated_data_dir(monkeypatch, tmp_path):
    """Point DATA_DIR at a tmp tree and reload the relevant modules
    so the module-level constants pick up the new env."""
    monkeypatch.setenv("HARLO_DATA_DIR", str(tmp_path))
    import importlib
    import harlo.daemon.config as cfg
    importlib.reload(cfg)
    import harlo.session.first_run as first_run
    importlib.reload(first_run)
    return tmp_path, first_run


class TestFirstRun:
    def test_fresh_install_creates_marker(self, isolated_data_dir):
        tmp_path, first_run = isolated_data_dir
        assert not first_run.already_completed()
        r = first_run.run_first_run()
        assert r.fresh_install is True
        assert r.migrated_from is None
        assert first_run.already_completed()

    def test_idempotent(self, isolated_data_dir):
        _, first_run = isolated_data_dir
        first_run.run_first_run()
        r2 = first_run.run_first_run()
        assert r2.migrated_paths == ()


class TestLaunchdPrompt:
    def test_non_macos_returns_false(self, isolated_data_dir):
        _, first_run = isolated_data_dir
        with patch.object(sys, "platform", "linux"):
            result = first_run.prompt_install_launchd()
        assert result is False

    def test_marker_blocks_second_call(self, isolated_data_dir):
        tmp_path, first_run = isolated_data_dir
        # Pre-stamp the marker; the function should short-circuit.
        marker = tmp_path / ".launchd_offered"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("already-asked\n", encoding="utf-8")
        with patch.object(sys, "platform", "darwin"):
            assert first_run.prompt_install_launchd() is False

    def test_no_tty_stamps_marker_and_returns_false(self, isolated_data_dir):
        tmp_path, first_run = isolated_data_dir
        out = io.StringIO()
        with patch.object(sys, "platform", "darwin"), \
             patch.object(sys.stdin, "isatty", return_value=False):
            result = first_run.prompt_install_launchd(out=out)
        assert result is False
        marker = tmp_path / ".launchd_offered"
        assert marker.exists()
        assert "no-tty" in marker.read_text()

    def test_auto_accept_false_records_decline(self, isolated_data_dir):
        tmp_path, first_run = isolated_data_dir
        out = io.StringIO()
        with patch.object(sys, "platform", "darwin"):
            result = first_run.prompt_install_launchd(auto_accept=False, out=out)
        assert result is False
        marker = tmp_path / ".launchd_offered"
        assert marker.exists()
        assert "declined" in marker.read_text()

    def test_auto_accept_true_runs_installer(self, isolated_data_dir, monkeypatch):
        tmp_path, first_run = isolated_data_dir
        # Make _find_install_script return a known path that we can
        # verify subprocess.run got called against.
        fake_script = tmp_path / "fake_install.py"
        fake_script.write_text("# stub\n", encoding="utf-8")
        monkeypatch.setattr(first_run, "_find_install_script", lambda: fake_script)
        recorded = {}

        def fake_run(cmd, check):
            recorded["cmd"] = cmd
            recorded["check"] = check
            class _R:
                returncode = 0
            return _R()

        monkeypatch.setattr(first_run.subprocess, "run", fake_run)
        with patch.object(sys, "platform", "darwin"):
            result = first_run.prompt_install_launchd(auto_accept=True)
        assert result is True
        assert recorded["cmd"][1] == str(fake_script)
        assert "install" in recorded["cmd"]
        assert "--all" in recorded["cmd"]
        marker = tmp_path / ".launchd_offered"
        assert "installed" in marker.read_text()

    def test_missing_install_script_skips_gracefully(self, isolated_data_dir, monkeypatch):
        tmp_path, first_run = isolated_data_dir
        monkeypatch.setattr(first_run, "_find_install_script", lambda: None)
        with patch.object(sys, "platform", "darwin"):
            result = first_run.prompt_install_launchd(auto_accept=True)
        assert result is False
        marker = tmp_path / ".launchd_offered"
        assert "missing-script" in marker.read_text()

    def test_failed_install_records_failure(self, isolated_data_dir, monkeypatch):
        tmp_path, first_run = isolated_data_dir
        fake_script = tmp_path / "fake_install.py"
        fake_script.write_text("# stub\n", encoding="utf-8")
        monkeypatch.setattr(first_run, "_find_install_script", lambda: fake_script)

        def fake_run(cmd, check):
            import subprocess
            raise subprocess.CalledProcessError(returncode=42, cmd=cmd)

        monkeypatch.setattr(first_run.subprocess, "run", fake_run)
        with patch.object(sys, "platform", "darwin"):
            result = first_run.prompt_install_launchd(auto_accept=True)
        assert result is False
        marker = tmp_path / ".launchd_offered"
        assert "failed: 42" in marker.read_text()
