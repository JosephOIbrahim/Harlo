"""Listen-socket acquisition for the Harlo daemon.

C1 fix: the daemon checked the **systemd** ``LISTEN_FDS`` / ``fromfd(3)``
protocol, but the macOS plist uses **launchd** socket activation, which
hands the listening socket over via the ``launch_activate_socket(
"HarloCommand", ...)`` C API — NOT ``LISTEN_FDS``. On macOS the old code
therefore always fell through to a dev rebind that ``unlink``s and
re-``bind``s the very socket launchd is holding, so Rule 1 (0W idle via OS
socket activation) was never actually realized on the target platform.

``acquire_listen_socket()`` now tries, in order:

  1. **launchd** (``launch_activate_socket``) — the correct macOS path.
  2. **systemd** (``LISTEN_FDS`` / fd 3) — Linux.
  3. **dev fallback** — bind the UDS path directly.

Every step is defensive: any failure falls through to the next, so the
daemon always comes up. Rule 1: this is pure FD acquisition — no polling.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import os
import socket
import sys

# launchd socket name — MUST match the ``Sockets`` key in
# macos/launchd/com.harlo.daemon.plist.
LAUNCHD_SOCKET_NAME = "HarloCommand"


def try_launchd_socket(name: str = LAUNCHD_SOCKET_NAME) -> socket.socket | None:
    """Return the launchd-activated listening socket, or ``None``.

    Wraps ``int launch_activate_socket(const char *name, int **fds,
    size_t *cnt)`` from libSystem (Darwin only). Returns ``None`` on any
    non-Darwin host, missing symbol, non-zero status, or zero fds — never
    raises.
    """
    if sys.platform != "darwin":
        return None
    try:
        libc = ctypes.CDLL(
            ctypes.util.find_library("System") or "/usr/lib/libSystem.B.dylib"
        )
        fn = libc.launch_activate_socket
    except (OSError, AttributeError):
        return None

    fn.restype = ctypes.c_int
    fn.argtypes = [
        ctypes.c_char_p,
        ctypes.POINTER(ctypes.POINTER(ctypes.c_int)),
        ctypes.POINTER(ctypes.c_size_t),
    ]
    fds_ptr = ctypes.POINTER(ctypes.c_int)()
    count = ctypes.c_size_t(0)
    try:
        rc = fn(name.encode("utf-8"), ctypes.byref(fds_ptr), ctypes.byref(count))
    except Exception:
        return None
    if rc != 0 or count.value < 1:
        return None

    try:
        fd = fds_ptr[0]
        sock = socket.fromfd(fd, socket.AF_UNIX, socket.SOCK_STREAM)
    except Exception:
        return None
    finally:
        # launch_activate_socket malloc's the fd array; free it.
        try:
            libc.free.argtypes = [ctypes.c_void_p]
            libc.free(ctypes.cast(fds_ptr, ctypes.c_void_p))
        except Exception:
            pass
    return sock


def try_systemd_socket() -> socket.socket | None:
    """Return the systemd-activated socket (fd 3), or ``None``."""
    listen_fds = os.environ.get("LISTEN_FDS")
    if listen_fds and listen_fds.isdigit() and int(listen_fds) > 0:
        return socket.fromfd(3, socket.AF_UNIX, socket.SOCK_STREAM)
    return None


def bind_dev_socket(sock_path: str, backlog: int = 5) -> socket.socket:
    """Dev fallback: bind the UDS path directly."""
    if os.path.exists(sock_path):
        os.unlink(sock_path)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(sock_path)
    sock.listen(backlog)
    return sock


def acquire_listen_socket(sock_path: str) -> tuple[socket.socket, str]:
    """Acquire the listening socket. Returns ``(sock, source)``.

    ``source`` is one of ``"launchd"`` / ``"systemd"`` / ``"dev"`` for
    logging and tests.
    """
    sock = try_launchd_socket()
    if sock is not None:
        return sock, "launchd"
    sock = try_systemd_socket()
    if sock is not None:
        return sock, "systemd"
    return bind_dev_socket(sock_path), "dev"


__all__ = [
    "LAUNCHD_SOCKET_NAME",
    "acquire_listen_socket",
    "bind_dev_socket",
    "try_launchd_socket",
    "try_systemd_socket",
]
