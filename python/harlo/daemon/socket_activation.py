"""Listening-socket acquisition for the Rule-1 daemon.

Acquisition tries, in order: launchd (launch_activate_socket(3), macOS) →
systemd (LISTEN_FDS / fd 3, Linux) → dev fallback (bind the UDS path
ourselves). On macOS the old code only checked the systemd LISTEN_FDS
protocol, so it always fell through to a dev rebind that unlink+rebind the
very socket launchd was holding — Rule 1 (0W idle via OS socket
activation) was never realized on the target platform.

  - acquire_listening_socket(sock_path, launchd_name) -> (sock, owns_node)
        D69-guarded: refuses to hijack a live listener; owns_node tells
        the caller whether it may unlink the node on exit (True only in
        dev mode — under launchd/systemd the OS owns the node). This is
        the production daemon path (daemon/main.py).

Rule 1: this is pure FD acquisition — no polling, no sleep.
"""

from __future__ import annotations

import ctypes
import errno
import logging
import os
import socket
import sys

_LOGGER = logging.getLogger(__name__)

_LIBSYSTEM_PATH = "/usr/lib/libSystem.B.dylib"

# launchd socket name — MUST match the ``Sockets`` key in
# macos/launchd/com.harlo.daemon.plist.
LAUNCHD_SOCKET_NAME = "HarloCommand"


# ---------------------------------------------------------------------------
# D69-guarded API (acquire_listening_socket) — owns_node semantics.
# ---------------------------------------------------------------------------

def adopt_launchd_socket(name: str) -> list[int] | None:
    """Adopt listening fds from launchd via launch_activate_socket(3).

    Returns the list of inherited listening fds, or None when not
    applicable (non-darwin, not launchd-managed [ESRCH], name absent
    from our plist [ENOENT], or already activated [EALREADY]).

    Contract (launch(3)): the fds buffer is heap-allocated by libSystem
    and MUST be released with free(3) — we do that before returning.
    """
    if sys.platform != "darwin":
        return None
    try:
        libsystem = ctypes.CDLL(_LIBSYSTEM_PATH)
        activate = libsystem.launch_activate_socket
    except (OSError, AttributeError):
        return None  # not macOS / SDK too old — fall through

    activate.restype = ctypes.c_int
    activate.argtypes = [
        ctypes.c_char_p,                                # const char *name
        ctypes.POINTER(ctypes.POINTER(ctypes.c_int)),   # int **fds
        ctypes.POINTER(ctypes.c_size_t),                # size_t *cnt
    ]
    libsystem.free.restype = None
    libsystem.free.argtypes = [ctypes.c_void_p]

    fds_ptr = ctypes.POINTER(ctypes.c_int)()
    cnt = ctypes.c_size_t(0)
    rc = activate(name.encode("utf-8"), ctypes.byref(fds_ptr), ctypes.byref(cnt))

    if rc != 0:
        # rc IS the POSIX error code (launch_activate_socket does not
        # use errno). ESRCH = not launchd-managed (normal in dev runs).
        reason = {
            errno.ENOENT: "socket name %r not in this job's launchd.plist",
            errno.ESRCH: "process is not managed by launchd (%r)",
            errno.EALREADY: "socket %r already activated in this process",
        }.get(rc, "launch_activate_socket(%r) failed")
        _LOGGER.debug(reason + " (rc=%d)", name, rc)
        return None

    try:
        return [fds_ptr[i] for i in range(cnt.value)]
    finally:
        if fds_ptr:  # free(3) the heap buffer — man-page contract
            libsystem.free(ctypes.cast(fds_ptr, ctypes.c_void_p))


def _socket_path_has_live_listener(sock_path: str, timeout: float = 0.5) -> bool:
    """True if something is accepting on sock_path right now.

    NOTE: if launchd holds this node, the probe-connect will spawn a
    daemon activation that receives an empty payload — handle_client's
    `if not data` no-op path absorbs it. That activation is the very
    signal that we must NOT hijack the node.
    """
    probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    probe.settimeout(timeout)
    try:
        probe.connect(sock_path)
        return True
    except (ConnectionRefusedError, FileNotFoundError):
        return False  # stale node or no node — safe to (re)bind
    except OSError:
        return True   # ambiguous (EACCES, ETIMEDOUT...) — be conservative
    finally:
        probe.close()


def acquire_listening_socket(
    sock_path: str,
    launchd_name: str,
) -> tuple[socket.socket, bool]:
    """Return (listening socket, owns_node).

    owns_node=True ONLY in dev mode — the caller may unlink the node on
    exit ONLY when it owns it. Under launchd/systemd the OS owns the
    node; unlinking it breaks every subsequent activation (D69).
    """
    # 1. launchd (macOS)
    fds = adopt_launchd_socket(launchd_name)
    if fds:
        for extra in fds[1:]:
            os.close(extra)  # defensive — Unix path sockets yield 1 fd
        # fileno= adopts WITHOUT dup; the fd is already bound+listening.
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM, fileno=fds[0])
        _LOGGER.info("adopted launchd socket %r (fd=%d)", launchd_name, fds[0])
        return sock, False

    # 2. systemd (Linux) — preserved exactly as before (fd 3, dup'd)
    listen_fds = os.environ.get("LISTEN_FDS")
    if listen_fds and int(listen_fds) > 0:
        return socket.fromfd(3, socket.AF_UNIX, socket.SOCK_STREAM), False

    # 3. Dev fallback — never hijack a live listener (D69 guard)
    if os.path.exists(sock_path):
        if _socket_path_has_live_listener(sock_path):
            raise SystemExit(
                f"refusing to start: {sock_path} already has a live "
                f"listener (another daemon, or launchd holds the node). "
                f"Stop it first, or use the launchd unit."
            )
        os.unlink(sock_path)  # stale node from a crashed dev run
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(sock_path)
    sock.listen(5)
    return sock, True


__all__ = [
    "LAUNCHD_SOCKET_NAME",
    "acquire_listening_socket",
    "adopt_launchd_socket",
]
