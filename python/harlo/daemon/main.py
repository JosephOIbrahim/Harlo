"""Socket-activated daemon entry point.

Rule 1: 0-WATT IDLE. Event-driven only.
Uses OS socket activation (systemd/launchd).
Daemon exits when idle. 0W between sessions.
"""

import json
import logging
import socket

from . import framing
from .config import (
    DAEMON_IDLE_TIMEOUT_S,
    DMN_BUDGET_S,
    LAUNCHD_SOCKET_NAME,
    SOCKET_PATH,
    ensure_data_dirs,
)
from .router import route_command
from .socket_activation import acquire_listening_socket

_LOGGER = logging.getLogger(__name__)


def handle_client(conn: socket.socket):
    """Handle a single client connection.

    Reads one framed request — canonical length-prefixed framing, with
    legacy newline-delimited JSON auto-detected — and replies in the same
    framing the client used (see daemon/framing.py). This is the C2 fix:
    the Swift HealthBridge and HarloXPCRelay send length-prefixed frames
    the old newline-only reader could never parse.

    Socket-level failures (peer closed early, reset) propagate as OSError
    to serve(), which logs and keeps accepting — a rude client must never
    kill the accept loop (D72). conn is ALWAYS closed here.
    """
    try:
        try:
            request, mode = framing.read_message(conn)
        except framing.FramingError as e:
            framing.write_message(conn, {"status": "error", "message": str(e)})
            return
        except (json.JSONDecodeError, UnicodeDecodeError):
            framing.write_message(conn, {"status": "error", "message": "Invalid JSON"})
            return

        if request is None:
            return

        try:
            command = request.get("command", "")
            args = request.get("args", {})
            result = route_command(command, args)
        except Exception as e:
            result = {"status": "error", "message": str(e)}

        framing.write_message(conn, result, mode)
    finally:
        conn.close()


def serve(sock: socket.socket, idle_timeout: float) -> int:
    """Accept-loop: handle connections serially until idle.

    Rule 1 compliance: this is NOT a poll loop. accept() blocks at 0%
    CPU inside the kernel; the loop is bounded by the idle timeout —
    socket.timeout flips `serving` and the process exits 0. One
    connection at a time, no threads (Rule-1 simplicity; Rule 24 spirit).
    Returns the number of connections handled (testability).
    """
    from .dmn_teardown import get_teardown

    sock.settimeout(idle_timeout)
    handled = 0
    serving = True
    while serving:                      # bounded — ends on idle timeout
        try:
            conn, _ = sock.accept()
        except socket.timeout:
            serving = False             # Rule 1: idle → exit 0
            continue
        teardown = get_teardown()
        if teardown.is_running:
            teardown.abort()            # Rule 19: human presence wins (<10ms)
        try:
            handle_client(conn)
        except OSError:
            # One misbehaving client (closed before reading the reply —
            # the CLI does exactly this on its 5s timeout, cli/ipc.py;
            # or reset mid-recv) must never kill the loop: surviving
            # the burst IS the D72 deliverable.
            _LOGGER.warning("client connection error — dropped, loop continues",
                            exc_info=True)
        handled += 1
    return handled


def run_socket_activated():
    """Acquire the listening socket (launchd → systemd → dev), serve
    until idle, then exit 0. Signature unchanged for launcher.py /
    start_daemon.py.
    """
    ensure_data_dirs()
    from .lifecycle import (
        write_pid_file, startup_cleanup, graceful_shutdown,
        idle_shutdown, install_signal_handlers,
    )

    write_pid_file()
    startup_cleanup()
    # Signal path (SIGTERM/SIGINT = bootout/system shutdown/user stop):
    # full graceful_shutdown — close ALL sessions, fire DMN (Rule S6).
    install_signal_handlers(shutdown_fn=graceful_shutdown)

    # C1/D69 fix: acquire via the correct OS protocol — launchd
    # (launch_activate_socket "HarloCommand") on macOS, systemd
    # (LISTEN_FDS) on Linux, dev bind otherwise. owns_node is True only
    # in dev mode (see socket_activation.acquire_listening_socket).
    sock, owns_node = acquire_listening_socket(str(SOCKET_PATH), LAUNCHD_SOCKET_NAME)
    try:
        serve(sock, float(DAEMON_IDLE_TIMEOUT_S))
    finally:
        # On SIGTERM during accept(), the handler runs graceful_shutdown()
        # then sys.exit(0); the SystemExit unwinds through here too. The
        # resulting double-shutdown is harmless: close_expired on
        # already-closed sessions is a no-op and remove_pid_file is
        # idempotent.
        sock.close()
        if owns_node:
            # Dev mode only. Under launchd/systemd the OS owns the node;
            # unlinking it would break the next activation (D69).
            SOCKET_PATH.unlink(missing_ok=True)
        # D73/S6: give in-flight DMN synthesis its budget, then abandon.
        try:
            from .dmn_teardown import get_teardown
            get_teardown().join_with_budget(timeout=float(DMN_BUDGET_S))
        except Exception:
            pass
        # Idle path: expire stale sessions only — active sessions
        # survive across activations (state lives in SQLite).
        idle_shutdown()


def run_direct(command: str, args: dict) -> dict:
    """Run a command directly without socket IPC.

    Used by the CLI for in-process mode.
    """
    ensure_data_dirs()
    return route_command(command, args)


if __name__ == "__main__":
    run_socket_activated()
