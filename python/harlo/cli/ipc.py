"""Unix socket IPC client for communicating with the daemon.

Falls back to direct in-process execution when daemon is not running.
"""

import socket
from pathlib import Path
from typing import Optional

from ..daemon import framing
from ..daemon.config import SOCKET_PATH


def send_command(command: str, args: dict, timeout: float = 5.0) -> dict:
    """Send a command to the daemon via Unix socket.

    Falls back to direct execution if daemon is not running.
    """
    # Try socket connection first
    result = _try_socket(command, args, timeout)
    if result is not None:
        return result

    # Fallback: direct in-process execution
    return _direct_execute(command, args)


def _try_socket(command: str, args: dict, timeout: float) -> Optional[dict]:
    """Try to send command via Unix socket."""
    sock_path = str(SOCKET_PATH)
    if not Path(sock_path).exists():
        return None

    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect(sock_path)

        # Canonical length-prefixed framing (matches the daemon + the Swift
        # HealthBridge). The daemon replies in the same framing mode.
        sock.sendall(framing.encode_frame({"command": command, "args": args}))
        response, _mode = framing.read_message(sock)
        sock.close()
        return response
    except (ConnectionRefusedError, FileNotFoundError, socket.timeout, OSError):
        return None
    except framing.FramingError:
        return None


def _direct_execute(command: str, args: dict) -> dict:
    """Execute command directly in-process."""
    from ..daemon.main import run_direct
    return run_direct(command, args)
