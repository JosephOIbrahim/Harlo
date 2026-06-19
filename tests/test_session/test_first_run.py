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
    so the module-level constants pick up the new env.

    Also redirects _LEGACY_DATA away from PROJECT_ROOT/data so dev
    machines (which may have a real ./data/ from earlier dogfooding)
    don't trigger the migration path and skew fresh_install assertions.

    Cleans up after itself: reloads the modules a second time without
    HARLO_DATA_DIR so subsequent tests in the session see the real
    DATA_DIR. Without this, tests like
    test_schedule/test_e2e_mcp_bridge.py inherit a tmp DATA_DIR pointing
    at a directory pytest has already torn down.
    """
    monkeypatch.setenv("HARLO_DATA_DIR", str(tmp_path))
    import importlib
    import harlo.daemon.config as cfg
    importlib.reload(cfg)
    import harlo.session.first_run as first_run
    importlib.reload(first_run)
    monkeypatch.setattr(first_run, "_LEGACY_DATA", tmp_path / "no-legacy")
    try:
        yield tmp_path, first_run
    finally:
        monkeypatch.delenv("HARLO_DATA_DIR", raising=False)
        importlib.reload(cfg)
        importlib.reload(first_run)


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

    def test_migration_overwrites_engine_stubs(self, monkeypatch, tmp_path):
        """Regression: engine bootstrap may write a stub schedule.usda
        into DATA_DIR/stages/ before first_run migration runs. The old
        `if target.exists(): continue` skip prevented the legacy
        schedule.usda from migrating, leaving the empty stub in place.

        Repro: pre-create stages/schedule.usda at DATA_DIR (as the
        engine would). Legacy holds a real schedule.usda. Run first_run.
        Expect target to hold legacy content, not the stub.
        """
        legacy = tmp_path / "legacy_data"
        dest = tmp_path / "data"
        # Legacy holds real content.
        (legacy / "stages").mkdir(parents=True)
        (legacy / "stages" / "schedule.usda").write_text(
            "real-schedule-content\n", encoding="utf-8"
        )
        # Engine has already written a stub into DATA_DIR/stages/.
        (dest / "stages").mkdir(parents=True)
        (dest / "stages" / "schedule.usda").write_text(
            "stub-skeleton\n", encoding="utf-8"
        )

        monkeypatch.setenv("HARLO_DATA_DIR", str(dest))
        import importlib
        import harlo.daemon.config as cfg
        importlib.reload(cfg)
        import harlo.session.first_run as first_run
        importlib.reload(first_run)
        monkeypatch.setattr(first_run, "_LEGACY_DATA", legacy)

        first_run.run_first_run()

        assert (dest / "stages" / "schedule.usda").read_text() == (
            "real-schedule-content\n"
        ), "engine stub should have been overwritten by legacy migration"


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

    def test_no_tty_returns_false_without_stamping(self, isolated_data_dir):
        """D55: a silent (no-TTY) launch must NOT permanently suppress
        the onboarding offer. The marker stays absent so the next
        interactive launch still prompts."""
        tmp_path, first_run = isolated_data_dir
        out = io.StringIO()
        with patch.object(sys, "platform", "darwin"), \
             patch.object(sys.stdin, "isatty", return_value=False):
            result = first_run.prompt_install_launchd(out=out)
        assert result is False
        marker = tmp_path / ".launchd_offered"
        assert not marker.exists()

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


class TestLegacyObservationMerge:
    """D56/B2 — one-shot merge of the pre-D56 repo-tree observation buffer."""

    def _make_buffer(self, path, rows):
        import sqlite3
        conn = sqlite3.connect(str(path))
        conn.execute(
            """CREATE TABLE observation_buffer (
                obs_id TEXT PRIMARY KEY,
                observation_json TEXT NOT NULL,
                priority REAL NOT NULL DEFAULT 0.0,
                partition TEXT NOT NULL DEFAULT 'organic',
                surprise_score REAL NOT NULL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"""
        )
        conn.executemany(
            "INSERT INTO observation_buffer (obs_id, observation_json) VALUES (?, ?)",
            rows,
        )
        conn.commit()
        conn.close()

    def test_merge_is_lossless_and_idempotent(self, isolated_data_dir, monkeypatch):
        import sqlite3
        tmp_path, first_run = isolated_data_dir
        legacy_dir = tmp_path / "legacy_repo_data"
        legacy_dir.mkdir()
        monkeypatch.setattr(first_run, "_LEGACY_DATA", legacy_dir)

        # Fork: 2 shared rows, 1 unique per side.
        self._make_buffer(legacy_dir / "observations.db",
                          [("a", "{}"), ("b", "{}"), ("legacy-only", "{}")])
        self._make_buffer(tmp_path / "observations.db",
                          [("a", "{}"), ("b", "{}"), ("datadir-only", "{}")])

        merged = first_run._merge_legacy_observations()
        assert merged == 1  # only legacy-only is new

        conn = sqlite3.connect(str(tmp_path / "observations.db"))
        ids = {r[0] for r in conn.execute(
            "SELECT obs_id FROM observation_buffer").fetchall()}
        conn.close()
        assert ids == {"a", "b", "legacy-only", "datadir-only"}

        # Idempotent: marker stamped, second call is a no-op.
        assert (tmp_path / ".obs_merge_v1").exists()
        assert first_run._merge_legacy_observations() == 0

    def test_no_legacy_db_stamps_and_skips(self, isolated_data_dir, monkeypatch):
        tmp_path, first_run = isolated_data_dir
        legacy_dir = tmp_path / "legacy_repo_data"
        legacy_dir.mkdir()
        monkeypatch.setattr(first_run, "_LEGACY_DATA", legacy_dir)
        assert first_run._merge_legacy_observations() == 0
        assert (tmp_path / ".obs_merge_v1").exists()
