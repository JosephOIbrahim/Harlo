"""Cross-platform daemon stopper for the Harlo.

Reads the PID file, sends graceful shutdown signal, and waits for exit.

Usage:
    python scripts/stop_daemon.py
"""

from __future__ import annotations

import os
import signal
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    """Stop the Twin daemon gracefully."""
    from harlo.daemon.lifecycle import read_pid_file, remove_pid_file, is_daemon_running

    pid = read_pid_file()
    if pid is None:
        print("No PID file found. Daemon may not be running.")
        return 1

    if not is_daemon_running():
        print(f"PID {pid} is not running. Cleaning up stale PID file.")
        remove_pid_file()
        return 0

    print(f"Stopping daemon (PID: {pid})...")

    try:
        if os.name == "nt":
            # Windows: terminate the process
            os.kill(pid, signal.SIGTERM)
        else:
            # Unix: send SIGTERM for graceful shutdown
            os.kill(pid, signal.SIGTERM)
    except (OSError, ProcessLookupError) as e:
        print(f"Error sending signal: {e}")
        remove_pid_file()
        return 1

    # Wait briefly for process to exit
    for _ in range(10):
        try:
            os.kill(pid, 0)
            time.sleep(0.5)
        except (OSError, ProcessLookupError):
            print("Daemon stopped.")
            remove_pid_file()
            return 0

    print(f"Warning: Daemon (PID {pid}) did not exit within 5 seconds.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
