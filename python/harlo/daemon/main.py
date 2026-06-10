"""Socket-activated daemon entry point.

Rule 1: 0-WATT IDLE. Event-driven only.
Uses OS socket activation (systemd/launchd).
Daemon exits when idle. 0W between sessions.
"""

import json
import os
import socket
import sys
from pathlib import Path

from .config import SOCKET_PATH, ensure_data_dirs
from .router import route_command


_MAX_FRAME = 16 * 1024 * 1024  # 16 MiB upper bound on a single frame


def _recv_request(conn: socket.socket) -> bytes:
    """Read one request, supporting BOTH wire framings (D61).

    The CLI sends newline-delimited JSON; HarloHealthBridge sends a
    4-byte big-endian length prefix + payload (DaemonWriter.swift).
    The two are sniffable from the first byte: JSON starts with '{'
    (or whitespace/'['), while a length prefix for any sane payload
    (< 16 MiB) starts with 0x00.
    """
    head = b""
    while len(head) < 4:
        chunk = conn.recv(4 - len(head))
        if not chunk:
            return head  # short/empty — caller treats as legacy data
        head += chunk

    if head[0] == 0x00:
        # Length-prefixed frame (HealthBridge).
        length = int.from_bytes(head, "big")
        if length <= 0 or length > _MAX_FRAME:
            return b""
        data = b""
        while len(data) < length:
            chunk = conn.recv(min(65536, length - len(data)))
            if not chunk:
                break
            data += chunk
        return data

    # Legacy newline-delimited JSON (CLI).
    data = head
    for _ in range(1024):  # bounded recv loop
        if b"\n" in data:
            break
        chunk = conn.recv(4096)
        if not chunk:
            break
        data += chunk
    return data


def handle_client(conn: socket.socket):
    """Handle a single client connection."""
    data = _recv_request(conn)

    if not data:
        conn.close()
        return

    try:
        request = json.loads(data.strip())
        command = request.get("command", "")
        args = request.get("args", {})
        result = route_command(command, args)
    except json.JSONDecodeError:
        result = {"status": "error", "message": "Invalid JSON"}
    except Exception as e:
        result = {"status": "error", "message": str(e)}

    response = json.dumps(result) + "\n"
    conn.sendall(response.encode("utf-8"))
    conn.close()


def run_socket_activated():
    """Run with systemd socket activation (fd inheritance).

    On systems without socket activation, falls back to creating
    the socket directly. Exits after handling one batch of commands.
    Performs startup cleanup and installs signal handlers.
    """
    ensure_data_dirs()

    # Lifecycle: startup
    from .lifecycle import (
        write_pid_file,
        startup_cleanup,
        graceful_shutdown,
        install_signal_handlers,
    )

    write_pid_file()
    startup_cleanup()
    install_signal_handlers(shutdown_fn=graceful_shutdown)

    # Check for systemd socket activation (LISTEN_FDS)
    listen_fds = os.environ.get("LISTEN_FDS")
    if listen_fds and int(listen_fds) > 0:
        # Inherited file descriptor 3 from systemd
        sock = socket.fromfd(3, socket.AF_UNIX, socket.SOCK_STREAM)
    else:
        # Fallback: create socket directly (dev mode)
        sock_path = str(SOCKET_PATH)
        if os.path.exists(sock_path):
            os.unlink(sock_path)
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(sock_path)
        sock.listen(5)

    # Set timeout so we exit if idle (Rule 1: 0W idle)
    sock.settimeout(30.0)

    try:
        conn, _ = sock.accept()
        handle_client(conn)
    except socket.timeout:
        pass  # Idle timeout, exit cleanly
    finally:
        sock.close()
        # Clean up socket file
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink(missing_ok=True)
        # Lifecycle: shutdown
        graceful_shutdown()


def run_direct(command: str, args: dict) -> dict:
    """Run a command directly without socket IPC.

    Used by the CLI for in-process mode.
    """
    ensure_data_dirs()
    return route_command(command, args)


if __name__ == "__main__":
    run_socket_activated()
