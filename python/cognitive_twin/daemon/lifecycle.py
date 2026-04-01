"""Daemon lifecycle management — startup, shutdown, PID, health.

Handles:
- PID file creation/cleanup
- Startup session cleanup (expire stale sessions from previous run)
- Graceful shutdown (close active sessions, fire DMN teardown)
- Health check data
- Signal handling for clean exit
"""

from __future__ import annotations

import os
import signal
import sys
import time
from pathlib import Path
from typing import Optional

from .config import (
    DB_PATH,
    PID_FILE,
    SESSION_TIMEOUT_S,
    ensure_data_dirs,
)


def write_pid_file() -> None:
    """Write the current process PID to the PID file."""
    ensure_data_dirs()
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")


def read_pid_file() -> Optional[int]:
    """Read the PID from the PID file, or None if not found."""
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return None


def remove_pid_file() -> None:
    """Remove the PID file if it exists."""
    PID_FILE.unlink(missing_ok=True)


def is_daemon_running() -> bool:
    """Check if a daemon process is already running based on PID file."""
    pid = read_pid_file()
    if pid is None:
        return False
    try:
        # On Windows, os.kill with signal 0 checks if process exists
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        # PID file is stale — process not running
        remove_pid_file()
        return False


def startup_cleanup() -> dict:
    """Run startup cleanup: expire stale sessions, recover DMN temp files.

    Returns a report dict with cleanup results.
    """
    ensure_data_dirs()
    report = {
        "expired_sessions": [],
        "recovered_dmn": None,
        "pid": os.getpid(),
    }

    # 1. Expire stale sessions from previous run
    try:
        from ..session import SessionManager
        mgr = SessionManager(db_path=str(DB_PATH), timeout_s=SESSION_TIMEOUT_S)
        expired = mgr.close_expired()
        report["expired_sessions"] = expired
    except Exception:
        pass  # Session table may not exist yet

    # 2. Recover DMN partial results from temp file
    try:
        from .dmn_teardown import get_teardown
        teardown = get_teardown()
        recovered = teardown.recover_temp()
        if recovered:
            report["recovered_dmn"] = recovered
    except Exception:
        pass

    return report


def graceful_shutdown() -> dict:
    """Close all active sessions and fire DMN teardown for each.

    Returns a report dict with shutdown results.
    """
    report = {
        "closed_sessions": [],
        "dmn_triggered": 0,
    }

    try:
        from ..session import SessionManager
        mgr = SessionManager(db_path=str(DB_PATH), timeout_s=SESSION_TIMEOUT_S)
        active = mgr.list_active()

        for session in active:
            mgr.close(session.session_id, trigger_dmn=True)
            report["closed_sessions"].append(session.session_id)
            report["dmn_triggered"] += 1
    except Exception:
        pass  # Best effort — don't crash on shutdown

    remove_pid_file()
    return report


def get_health() -> dict:
    """Return daemon health status."""
    pid = os.getpid()
    uptime_available = True

    session_count = 0
    try:
        from ..session import SessionManager
        mgr = SessionManager(db_path=str(DB_PATH), timeout_s=SESSION_TIMEOUT_S)
        session_count = len(mgr.list_active())
    except Exception:
        pass

    return {
        "status": "healthy",
        "pid": pid,
        "pid_file": str(PID_FILE),
        "pid_file_exists": PID_FILE.exists(),
        "db_path": str(DB_PATH),
        "db_exists": DB_PATH.exists(),
        "active_sessions": session_count,
        "timestamp": int(time.time()),
    }


def install_signal_handlers(shutdown_fn=None) -> None:
    """Install signal handlers for graceful shutdown.

    Args:
        shutdown_fn: Optional callable to run on shutdown signal.
                     Defaults to graceful_shutdown.
    """
    fn = shutdown_fn or graceful_shutdown

    def _handler(signum, frame):
        """Signal handler that runs graceful shutdown."""
        fn()
        sys.exit(0)

    # SIGTERM is the standard graceful shutdown signal
    signal.signal(signal.SIGTERM, _handler)

    # SIGINT (Ctrl+C) also gets graceful shutdown
    signal.signal(signal.SIGINT, _handler)
