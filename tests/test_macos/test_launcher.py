"""Tests for macos/launcher.py — the bundle's single entry point.

The launcher is the linchpin of the macOS install: launchd plists,
the menu-bar app, and the MCP server all hand control to this file.
A broken dispatcher means the .app silently fails. These tests pin
the dispatch contract.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# macos/ is not a package — add the dir to sys.path for tests.
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "macos"))

import launcher  # noqa: E402


class TestDetectMode:
    def test_no_mode_flag(self):
        mode, residual = launcher._detect_mode([])
        assert mode is None
        assert residual == []

    def test_daemon_flag(self):
        mode, residual = launcher._detect_mode(["--daemon"])
        assert mode == "--daemon"
        assert residual == []

    def test_agents_flag(self):
        mode, residual = launcher._detect_mode(["--agents"])
        assert mode == "--agents"
        assert residual == []

    def test_mcp_flag(self):
        mode, residual = launcher._detect_mode(["--mcp"])
        assert mode == "--mcp"
        assert residual == []

    def test_mode_flag_among_others(self):
        mode, residual = launcher._detect_mode(["recall", "--daemon", "--json"])
        assert mode == "--daemon"
        assert residual == ["recall", "--json"]

    def test_only_first_mode_flag_consumed(self):
        # If launchd somehow passes both, we honor --daemon (the
        # first in _MODE_FLAGS iteration order doesn't matter since
        # `in` checks each independently; assert only one is removed).
        mode, residual = launcher._detect_mode(["--daemon", "--agents"])
        assert mode in {"--daemon", "--agents"}
        # At least one residual flag remains.
        remaining_mode_flags = [f for f in residual if f in launcher._MODE_FLAGS]
        assert len(remaining_mode_flags) == 1

    def test_cli_args_passthrough(self):
        mode, residual = launcher._detect_mode(["intake", "start", "--json"])
        assert mode is None
        assert residual == ["intake", "start", "--json"]


class TestDispatch:
    def test_daemon_path_invokes_run_socket_activated(self):
        with patch("harlo.daemon.main.run_socket_activated") as m:
            code = launcher.main(["--daemon"])
        assert code == 0
        m.assert_called_once_with()

    def test_mcp_path_invokes_mcp_main(self):
        with patch("harlo.mcp_server.main") as m:
            code = launcher.main(["--mcp"])
        assert code == 0
        m.assert_called_once_with()

    def test_agents_path_appends_socket_activated_flag(self):
        with patch("agents.harness.main", return_value=0) as m:
            code = launcher.main(["--agents"])
        assert code == 0
        called_args = m.call_args.args[0]
        assert "--socket-activated" in called_args

    def test_agents_path_does_not_duplicate_flag(self):
        with patch("agents.harness.main", return_value=0) as m:
            launcher.main(["--agents", "--socket-activated"])
        called_args = m.call_args.args[0]
        # No duplicate
        assert called_args.count("--socket-activated") == 1

    def test_cli_path_runs_first_run_and_cli(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HARLO_DATA_DIR", str(tmp_path))
        import importlib
        import harlo.daemon.config as cfg

        importlib.reload(cfg)
        import harlo.session.first_run as first_run

        importlib.reload(first_run)

        calls = {"first_run": 0, "prompt": 0, "cli": 0}

        def fake_run_first_run():
            calls["first_run"] += 1
            return first_run.FirstRunResult(
                fresh_install=True, migrated_from=None, migrated_paths=()
            )

        def fake_prompt(**kwargs):
            calls["prompt"] += 1
            return False

        def fake_cli_main():
            calls["cli"] += 1

        with patch("harlo.session.first_run.run_first_run", fake_run_first_run), \
             patch("harlo.session.first_run.prompt_install_launchd", fake_prompt), \
             patch("harlo.cli.main.main", fake_cli_main):
            launcher.main([])
        assert calls == {"first_run": 1, "prompt": 1, "cli": 1}

    def test_finder_launch_shows_dialog_not_cli(self, monkeypatch, tmp_path):
        """D55: a LaunchServices (double-click) launch shows feedback and
        returns — it does not fall through to Click with no TTY, and it
        does not trigger the launchd prompt."""
        monkeypatch.setenv("HARLO_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("__CFBundleIdentifier", "com.josephibrahim.harlo")
        import importlib
        import harlo.daemon.config as cfg

        importlib.reload(cfg)
        import harlo.session.first_run as first_run

        importlib.reload(first_run)

        calls = {"dialog": 0, "cli": 0, "prompt": 0}

        def fake_run_first_run():
            return first_run.FirstRunResult(
                fresh_install=True, migrated_from=None, migrated_paths=()
            )

        with patch("harlo.session.first_run.run_first_run", fake_run_first_run), \
             patch("harlo.session.first_run.prompt_install_launchd",
                   lambda **k: calls.__setitem__("prompt", calls["prompt"] + 1)), \
             patch.object(launcher, "_show_finder_dialog",
                          lambda: calls.__setitem__("dialog", calls["dialog"] + 1)), \
             patch("harlo.cli.main.main",
                   lambda: calls.__setitem__("cli", calls["cli"] + 1)), \
             patch.object(launcher.sys.stdin, "isatty", return_value=False):
            rc = launcher.main([])
        assert rc == 0
        assert calls == {"dialog": 1, "cli": 0, "prompt": 0}

    def test_cli_path_prompts_even_when_not_fresh(self, monkeypatch, tmp_path):
        """D55: the launchd offer is no longer gated on fresh_install —
        a silent Finder first launch consumes the one-shot flag, so the
        prompt must run on every interactive launch (it short-circuits
        internally via .launchd_offered)."""
        monkeypatch.setenv("HARLO_DATA_DIR", str(tmp_path))
        import importlib
        import harlo.daemon.config as cfg

        importlib.reload(cfg)
        import harlo.session.first_run as first_run

        importlib.reload(first_run)
        # Mark first-run already complete
        (tmp_path / ".first_run_complete").write_text("ok\n", encoding="utf-8")

        prompt_called = []
        with patch(
            "harlo.session.first_run.prompt_install_launchd",
            lambda **k: prompt_called.append(1),
        ), patch("harlo.cli.main.main", lambda: None):
            launcher.main([])
        assert prompt_called == [1]  # offer survives a consumed first-run
