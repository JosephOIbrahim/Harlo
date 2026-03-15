"""Tests for daemon lifecycle management.

Tests:
- PID file creation/cleanup
- Startup cleanup (expire stale sessions)
- Graceful shutdown (close sessions, fire DMN)
- Health check
- Signal handling
- is_daemon_running detection
- Router health command
"""

import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.daemon.lifecycle import (
    write_pid_file,
    read_pid_file,
    remove_pid_file,
    is_daemon_running,
    startup_cleanup,
    graceful_shutdown,
    get_health,
    install_signal_handlers,
)


@pytest.fixture
def tmp_pid_file(tmp_path):
    """Override PID_FILE to a temp path."""
    pid_path = tmp_path / "test.pid"
    with patch("src.daemon.lifecycle.PID_FILE", pid_path):
        yield pid_path


@pytest.fixture
def db_path():
    """Provide a temporary database path."""
    path = tempfile.mktemp(suffix=".db")
    yield path
    if os.path.exists(path):
        os.unlink(path)


# ─────────────────────────────────────────────────────────────────────
# PID File
# ─────────────────────────────────────────────────────────────────────

class TestPIDFile:
    """Test PID file management."""

    def test_write_pid_creates_file(self, tmp_pid_file):
        """write_pid_file() should create the PID file."""
        write_pid_file()
        assert tmp_pid_file.exists()

    def test_write_pid_contains_current_pid(self, tmp_pid_file):
        """PID file should contain the current process PID."""
        write_pid_file()
        content = tmp_pid_file.read_text().strip()
        assert int(content) == os.getpid()

    def test_read_pid_returns_pid(self, tmp_pid_file):
        """read_pid_file() should return the written PID."""
        write_pid_file()
        assert read_pid_file() == os.getpid()

    def test_read_pid_returns_none_when_missing(self, tmp_pid_file):
        """read_pid_file() should return None when file doesn't exist."""
        assert read_pid_file() is None

    def test_remove_pid_deletes_file(self, tmp_pid_file):
        """remove_pid_file() should delete the PID file."""
        write_pid_file()
        assert tmp_pid_file.exists()
        remove_pid_file()
        assert not tmp_pid_file.exists()

    def test_remove_pid_idempotent(self, tmp_pid_file):
        """remove_pid_file() should not fail when file doesn't exist."""
        remove_pid_file()  # Should not raise
        remove_pid_file()  # Still should not raise

    def test_is_daemon_running_current_process(self, tmp_pid_file):
        """is_daemon_running() should return True for the current process."""
        write_pid_file()
        assert is_daemon_running() is True

    def test_is_daemon_running_no_file(self, tmp_pid_file):
        """is_daemon_running() should return False when no PID file."""
        assert is_daemon_running() is False

    def test_is_daemon_running_stale_pid(self, tmp_pid_file):
        """is_daemon_running() should return False for a dead PID and clean up."""
        tmp_pid_file.write_text("999999999")  # Very unlikely to be running
        assert is_daemon_running() is False
        assert not tmp_pid_file.exists()  # Cleaned up stale file


# ─────────────────────────────────────────────────────────────────────
# Startup Cleanup
# ─────────────────────────────────────────────────────────────────────

class TestStartupCleanup:
    """Test startup cleanup behavior."""

    def test_startup_cleanup_returns_report(self):
        """startup_cleanup() should return a report dict."""
        with patch("src.daemon.lifecycle.DB_PATH", Path(tempfile.mktemp(suffix=".db"))):
            report = startup_cleanup()
            assert "expired_sessions" in report
            assert "recovered_dmn" in report
            assert "pid" in report
            assert report["pid"] == os.getpid()

    def test_startup_expires_stale_sessions(self, db_path):
        """startup_cleanup() should expire old sessions."""
        # Create a stale session
        from src.session import SessionManager
        mgr = SessionManager(db_path=db_path, timeout_s=60)
        old = mgr.create(now=1000)

        with patch("src.daemon.lifecycle.DB_PATH", Path(db_path)):
            with patch("src.daemon.lifecycle.SESSION_TIMEOUT_S", 60):
                report = startup_cleanup()

        # The old session should have been expired
        assert old.session_id in report["expired_sessions"]

    def test_startup_cleanup_handles_missing_db(self):
        """startup_cleanup() should not fail on fresh database."""
        with patch("src.daemon.lifecycle.DB_PATH", Path("/nonexistent/path.db")):
            report = startup_cleanup()
            assert report["expired_sessions"] == []

    def test_startup_recovers_dmn_temp(self, tmp_path):
        """startup_cleanup() should recover DMN partial results."""
        import json
        temp_file = tmp_path / "twin_dmn_partial.json"
        temp_file.write_text(json.dumps({"partial": True}))

        mock_teardown = MagicMock()
        mock_teardown.recover_temp.return_value = {"partial": True}

        with patch("src.daemon.lifecycle.DB_PATH", Path(tempfile.mktemp(suffix=".db"))):
            with patch("src.daemon.dmn_teardown.get_teardown", return_value=mock_teardown):
                report = startup_cleanup()
                assert report["recovered_dmn"] == {"partial": True}


# ─────────────────────────────────────────────────────────────────────
# Graceful Shutdown
# ─────────────────────────────────────────────────────────────────────

class TestGracefulShutdown:
    """Test graceful shutdown behavior."""

    def test_graceful_shutdown_returns_report(self, db_path, tmp_pid_file):
        """graceful_shutdown() should return a report dict."""
        write_pid_file()
        with patch("src.daemon.lifecycle.DB_PATH", Path(db_path)):
            report = graceful_shutdown()
            assert "closed_sessions" in report
            assert "dmn_triggered" in report

    def test_graceful_shutdown_closes_active_sessions(self, db_path, tmp_pid_file):
        """graceful_shutdown() should close all active sessions."""
        from src.session import SessionManager
        mgr = SessionManager(db_path=db_path, timeout_s=1800)
        s1 = mgr.create()
        s2 = mgr.create()

        write_pid_file()
        with patch("src.daemon.lifecycle.DB_PATH", Path(db_path)):
            report = graceful_shutdown()

        assert s1.session_id in report["closed_sessions"]
        assert s2.session_id in report["closed_sessions"]

        # Verify sessions are actually closed in DB
        loaded_s1 = mgr.get(s1.session_id)
        loaded_s2 = mgr.get(s2.session_id)
        assert loaded_s1.closed is True
        assert loaded_s2.closed is True

    def test_graceful_shutdown_removes_pid_file(self, db_path, tmp_pid_file):
        """graceful_shutdown() should remove the PID file."""
        write_pid_file()
        assert tmp_pid_file.exists()

        with patch("src.daemon.lifecycle.DB_PATH", Path(db_path)):
            graceful_shutdown()

        assert not tmp_pid_file.exists()

    def test_graceful_shutdown_handles_no_sessions(self, db_path, tmp_pid_file):
        """graceful_shutdown() should work fine with no active sessions."""
        write_pid_file()
        with patch("src.daemon.lifecycle.DB_PATH", Path(db_path)):
            report = graceful_shutdown()
            assert report["closed_sessions"] == []
            assert report["dmn_triggered"] == 0


# ─────────────────────────────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────────────────────────────

class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_returns_status(self):
        """get_health() should return a health dict."""
        with patch("src.daemon.lifecycle.DB_PATH", Path(tempfile.mktemp(suffix=".db"))):
            health = get_health()
            assert health["status"] == "healthy"
            assert health["pid"] == os.getpid()
            assert "timestamp" in health
            assert "active_sessions" in health

    def test_health_reports_db_existence(self, db_path):
        """get_health() should report whether DB exists."""
        with patch("src.daemon.lifecycle.DB_PATH", Path(db_path)):
            health = get_health()
            assert "db_exists" in health

    def test_health_reports_pid_file(self, tmp_pid_file):
        """get_health() should report PID file status."""
        with patch("src.daemon.lifecycle.DB_PATH", Path(tempfile.mktemp(suffix=".db"))):
            health = get_health()
            assert "pid_file_exists" in health

    def test_health_counts_active_sessions(self, db_path):
        """get_health() should count active sessions."""
        from src.session import SessionManager
        mgr = SessionManager(db_path=db_path, timeout_s=1800)
        mgr.create()
        mgr.create()

        with patch("src.daemon.lifecycle.DB_PATH", Path(db_path)):
            health = get_health()
            assert health["active_sessions"] == 2


# ─────────────────────────────────────────────────────────────────────
# Router Integration
# ─────────────────────────────────────────────────────────────────────

class TestRouterIntegration:
    """Test daemon commands through the router."""

    def test_router_health_command(self):
        """Router should handle health command."""
        from src.daemon.router import route_command
        result = route_command("health", {})
        assert result["status"] == "ok"
        assert result["result"]["status"] == "healthy"
        assert result["result"]["pid"] == os.getpid()

    def test_router_health_has_session_count(self):
        """Health command should include active session count."""
        from src.daemon.router import route_command
        result = route_command("health", {})
        assert "active_sessions" in result["result"]


# ─────────────────────────────────────────────────────────────────────
# Signal Handling
# ─────────────────────────────────────────────────────────────────────

class TestSignalHandling:
    """Test signal handler installation."""

    def test_install_signal_handlers(self):
        """install_signal_handlers() should not raise."""
        mock_fn = MagicMock()
        install_signal_handlers(shutdown_fn=mock_fn)
        # Just verify it doesn't crash — actual signal testing is OS-dependent


# ─────────────────────────────────────────────────────────────────────
# Scripts
# ─────────────────────────────────────────────────────────────────────

class TestScripts:
    """Test that startup/stop scripts exist and are importable."""

    def test_start_script_exists(self):
        """start_daemon.py should exist."""
        path = Path(__file__).parent.parent.parent / "scripts" / "start_daemon.py"
        assert path.exists()

    def test_stop_script_exists(self):
        """stop_daemon.py should exist."""
        path = Path(__file__).parent.parent.parent / "scripts" / "stop_daemon.py"
        assert path.exists()


# ─────────────────────────────────────────────────────────────────────
# Compliance
# ─────────────────────────────────────────────────────────────────────

class TestCompliance:
    """Verify no rules violated."""

    def test_no_sleep_in_lifecycle(self):
        """Rule 1: No sleep() in lifecycle code."""
        import inspect
        from src.daemon import lifecycle
        source = inspect.getsource(lifecycle)
        assert "sleep(" not in source

    def test_no_while_true_in_lifecycle(self):
        """Rule 1: No while True in lifecycle code."""
        import inspect
        from src.daemon import lifecycle
        source = inspect.getsource(lifecycle)
        assert "while True" not in source
