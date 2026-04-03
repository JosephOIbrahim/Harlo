"""Cross-platform daemon launcher for the Harlo.

Usage:
    python scripts/start_daemon.py          # Foreground mode
    python scripts/start_daemon.py --bg     # Background mode (Windows: pythonw)
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    """Launch the Twin daemon."""
    from harlo.daemon.config import PID_FILE, ensure_data_dirs
    from harlo.daemon.lifecycle import is_daemon_running, write_pid_file

    ensure_data_dirs()

    if is_daemon_running():
        print(f"Daemon already running (PID file: {PID_FILE})")
        return 1

    background = "--bg" in sys.argv

    if background:
        return _start_background()
    else:
        return _start_foreground()


def _start_foreground() -> int:
    """Start daemon in foreground (blocks until exit)."""
    print("Starting Twin daemon (foreground)...")

    from harlo.daemon.main import run_socket_activated
    try:
        run_socket_activated()
    except KeyboardInterrupt:
        print("\nDaemon stopped.")
    return 0


def _start_background() -> int:
    """Start daemon as a background process."""
    # Use pythonw on Windows if available, else python with nohup-like behavior
    python = sys.executable
    script = str(Path(__file__).parent.parent / "src" / "daemon" / "main.py")

    if os.name == "nt":
        # Windows: use CREATE_NO_WINDOW flag
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE

        proc = subprocess.Popen(
            [python, script],
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        # Unix: standard daemonization
        proc = subprocess.Popen(
            [python, script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    print(f"Daemon started in background (PID: {proc.pid})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
