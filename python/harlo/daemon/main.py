"""Socket-activated daemon entry point.

Rule 1: 0-WATT IDLE. Event-driven only.
Uses OS socket activation (systemd/launchd).
Daemon exits when idle. 0W between sessions.
"""

import json
import socket

from . import framing
from .config import DAEMON_IDLE_TIMEOUT_S, SOCKET_PATH, ensure_data_dirs
from .router import route_command
from .socket_activation import acquire_listen_socket


def handle_client(conn: socket.socket):
    """Handle a single client connection.

    Reads one framed request — canonical length-prefixed framing, with
    legacy newline-delimited JSON auto-detected — and replies in the same
    framing the client used (see daemon/framing.py). This is the C2 fix:
    the Swift HealthBridge sends length-prefixed frames that the old
    newline-only reader could never parse.
    """
    try:
        request, mode = framing.read_message(conn)
    except framing.FramingError as e:
        framing.write_message(conn, {"status": "error", "message": str(e)})
        conn.close()
        return
    except (json.JSONDecodeError, UnicodeDecodeError):
        framing.write_message(conn, {"status": "error", "message": "Invalid JSON"})
        conn.close()
        return

    if request is None:
        conn.close()
        return

    try:
        command = request.get("command", "")
        args = request.get("args", {})
        result = route_command(command, args)
    except Exception as e:
        result = {"status": "error", "message": str(e)}

    framing.write_message(conn, result, mode)
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

    # C1 fix: acquire the listening socket via the correct OS protocol —
    # launchd (launch_activate_socket "HarloCommand") on macOS, systemd
    # (LISTEN_FDS) on Linux, dev bind otherwise. See socket_activation.py.
    sock, source = acquire_listen_socket(str(SOCKET_PATH))

    # Set timeout so we exit if idle (Rule 1: 0W idle)
    sock.settimeout(float(DAEMON_IDLE_TIMEOUT_S))

    try:
        conn, _ = sock.accept()
        handle_client(conn)
    except socket.timeout:
        pass  # Idle timeout, exit cleanly
    finally:
        sock.close()
        # Only remove a socket file WE created (dev mode). Under launchd
        # the socket is owned by launchd and must NOT be unlinked, or the
        # next activation breaks.
        if source == "dev" and SOCKET_PATH.exists():
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
