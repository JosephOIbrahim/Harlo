"""Unix socket IPC client for communicating with the daemon.

Falls back to direct in-process execution when daemon is not running.
"""

import json
import socket
from pathlib import Path
from typing import Optional

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

        request = json.dumps({"command": command, "args": args}) + "\n"
        sock.sendall(request.encode("utf-8"))

        data = b""
        for _ in range(1024):  # bounded recv loop
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
            if b"\n" in data:
                break

        sock.close()
        return json.loads(data.strip())
    except (ConnectionRefusedError, FileNotFoundError, socket.timeout, OSError):
        return None


def _direct_execute(command: str, args: dict) -> dict:
    """Execute command directly in-process."""
    from ..daemon.main import run_direct
    return run_direct(command, args)
