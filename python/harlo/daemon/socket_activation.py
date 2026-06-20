"""Listening-socket acquisition for the Rule-1 daemon.

Two acquisition entry points coexist here, merged from two independent
C1/D69 fixes. Both try, in order: launchd (launch_activate_socket(3),
macOS) → systemd (LISTEN_FDS / fd 3, Linux) → dev fallback (bind the UDS
path ourselves). On macOS the old code only checked the systemd
LISTEN_FDS protocol, so it always fell through to a dev rebind that
unlink+rebind the very socket launchd was holding — Rule 1 (0W idle via
OS socket activation) was never realized on the target platform.

  - acquire_listening_socket(sock_path, launchd_name) -> (sock, owns_node)
        D69-guarded: refuses to hijack a live listener; owns_node tells
        the caller whether it may unlink the node on exit (True only in
        dev mode — under launchd/systemd the OS owns the node). This is
        the production daemon path (daemon/main.py).

  - acquire_listen_socket(sock_path) -> (sock, source)
        Returns a source label ("launchd"/"systemd"/"dev") for callers
        and tests that branch on the acquisition source.

Built for reuse: the agents harness (agents/harness.py:115-127) has the
identical LISTEN_FDS-only bug and should adopt this module in a
follow-up, passing its own socket name ("HarloAgents").

Rule 1: this is pure FD acquisition — no polling, no sleep.
"""

from __future__ import annotations

import ctypes
import ctypes.util
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


# ---------------------------------------------------------------------------
# Source-label API (acquire_listen_socket) — retained for callers and tests
# that branch on the acquisition source string.
# ponytail: deferred, test-only today (no production caller). Either adopt in
# agents/harness.py (the intended reuse — see module docstring) or delete
# acquire_listen_socket + try_launchd/systemd/bind_dev + their tests (~85
# lines). Decision tracked in issue #21.
# ---------------------------------------------------------------------------

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
    logging and tests. Prefer ``acquire_listening_socket`` for the
    production daemon path — it adds the D69 live-listener guard.
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
    "acquire_listening_socket",
    "acquire_listen_socket",
    "adopt_launchd_socket",
    "bind_dev_socket",
    "try_launchd_socket",
    "try_systemd_socket",
]
