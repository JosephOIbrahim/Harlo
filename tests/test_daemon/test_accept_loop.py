"""D69/D72 — accept loop, idle exit, and listening-socket acquisition.

Before D72 the daemon handled exactly ONE connection per activation
(plist ThrottleInterval=5 then capped ingest at ~1 batch/5s). serve()
now loops until DAEMON_IDLE_TIMEOUT_S of idle. Before D69 the dev
fallback unlinked launchd's own socket node; acquire_listening_socket
refuses to hijack a live listener.

Socket-path caveat: macOS sun_path is 104 bytes; pytest tmp_path under
/private/var/folders/... can exceed it. All AF_UNIX sockets here bind
in tempfile.mkdtemp(dir="/tmp") instead.
"""

import json
import logging
import os
import shutil
import socket
import sys
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from harlo.daemon import main as daemon_main
from harlo.daemon import socket_activation
from harlo.daemon.socket_activation import (
    acquire_listening_socket,
    adopt_launchd_socket,
)


@pytest.fixture
def short_tmp():
    """Short-path tmp dir — macOS sun_path limit forbids tmp_path."""
    d = tempfile.mkdtemp(dir="/tmp")
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


def _request(sock_path: str, payload: bytes) -> dict:
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(5)
    client.connect(sock_path)
    try:
        client.sendall(payload)
        # No SHUT_WR: newline framing lets the daemon reply without EOF,
        # and on macOS the server's response+close can land first, making
        # shutdown() raise ENOTCONN (errno 57) — a flake, not a failure.
        data = b""
        while True:
            chunk = client.recv(4096)
            if not chunk:
                break
            data += chunk
        return json.loads(data.strip())
    finally:
        client.close()


def _listener(sock_path: str) -> socket.socket:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(sock_path)
    sock.listen(5)
    return sock


class TestServe:
    def test_serve_handles_multiple_connections(self, short_tmp):
        """Pins the D72 fix — the old code died after connection 1."""
        sock_path = str(short_tmp / "twind.sock")
        sock = _listener(sock_path)
        result = {}

        def _serve():
            result["handled"] = daemon_main.serve(sock, idle_timeout=0.5)

        t = threading.Thread(target=_serve)
        t.start()
        try:
            req = (json.dumps({"command": "ping", "args": {}}) + "\n").encode()
            res1 = _request(sock_path, req)
            res2 = _request(sock_path, req)
            assert res1.get("status") == "ok"
            assert res2.get("status") == "ok"
        finally:
            t.join(timeout=10)
            sock.close()
        assert not t.is_alive()
        assert result["handled"] == 2

    def test_serve_exits_on_idle_timeout(self, short_tmp):
        """Rule 1: idle → exit, no connections handled."""
        sock_path = str(short_tmp / "idle.sock")
        sock = _listener(sock_path)
        result = {}

        def _serve():
            result["handled"] = daemon_main.serve(sock, idle_timeout=0.2)

        t = threading.Thread(target=_serve)
        t.start()
        t.join(timeout=5)
        sock.close()
        assert not t.is_alive()
        assert result["handled"] == 0

    def test_serve_survives_rude_client(self, short_tmp):
        """Repair-1 regression: a client that sends a valid request and
        closes before reading the reply (the CLI does exactly this on
        its 5s timeout — cli/ipc.py) used to BrokenPipeError out of
        serve() and kill the activation. The loop must keep accepting."""
        sock_path = str(short_tmp / "rude.sock")
        sock = _listener(sock_path)
        result = {}

        def _serve():
            result["handled"] = daemon_main.serve(sock, idle_timeout=0.5)

        t = threading.Thread(target=_serve)
        t.start()
        try:
            req = (json.dumps({"command": "ping", "args": {}}) + "\n").encode()
            rude = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            rude.settimeout(5)
            rude.connect(sock_path)
            rude.sendall(req)
            rude.close()  # abandon the connection without reading the reply
            # The loop must still be alive for the next legitimate client.
            res = _request(sock_path, req)
            assert res.get("status") == "ok"
        finally:
            t.join(timeout=10)
            sock.close()
        assert not t.is_alive()
        assert result["handled"] == 2

    def test_serve_survives_handler_oserror(self, short_tmp, caplog):
        """Deterministic exception-path pin (the rude-client repro has a
        benign race where sendall can win): handle_client raising any
        OSError is logged at WARNING and the loop keeps accepting."""
        sock_path = str(short_tmp / "epipe.sock")
        sock = _listener(sock_path)
        real_handle = daemon_main.handle_client
        calls = {"n": 0}

        def _flaky(conn):
            calls["n"] += 1
            if calls["n"] == 1:
                conn.close()
                raise BrokenPipeError(32, "Broken pipe")
            real_handle(conn)

        result = {}

        def _serve():
            result["handled"] = daemon_main.serve(sock, idle_timeout=0.5)

        with patch("harlo.daemon.main.handle_client", _flaky), \
             caplog.at_level(logging.WARNING, logger="harlo.daemon.main"):
            t = threading.Thread(target=_serve)
            t.start()
            try:
                # First connection hits the raising handler — no payload
                # needed (_flaky raises before reading; sending here
                # would race the server-side close into a client EPIPE).
                first = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                first.settimeout(5)
                first.connect(sock_path)
                first.close()
                req = (json.dumps({"command": "ping", "args": {}}) + "\n").encode()
                res = _request(sock_path, req)
                assert res.get("status") == "ok"
            finally:
                t.join(timeout=10)
                sock.close()
        assert not t.is_alive()
        assert calls["n"] == 2
        assert result["handled"] == 2
        assert "client connection error" in caplog.text

    def test_serve_preempts_running_teardown(self, short_tmp):
        """Rule 19 wiring: a new connection aborts a running teardown."""
        sock_path = str(short_tmp / "preempt.sock")
        sock = _listener(sock_path)
        mock_td = MagicMock()
        mock_td.is_running = True
        result = {}

        def _serve():
            result["handled"] = daemon_main.serve(sock, idle_timeout=0.5)

        # serve() imports get_teardown inside the function, so the
        # module attribute is the correct patch target.
        with patch("harlo.daemon.dmn_teardown.get_teardown", return_value=mock_td):
            t = threading.Thread(target=_serve)
            t.start()
            try:
                req = (json.dumps({"command": "ping", "args": {}}) + "\n").encode()
                _request(sock_path, req)
            finally:
                t.join(timeout=10)
                sock.close()
        assert result["handled"] == 1
        mock_td.abort.assert_called_once()


class TestRunSocketActivated:
    def test_run_socket_activated_idle_path_uses_idle_shutdown(
        self, short_tmp, monkeypatch
    ):
        """D72: the idle exit preserves sessions — idle_shutdown(), not
        graceful_shutdown() (which stays wired to the signal path only)."""
        monkeypatch.delenv("LISTEN_FDS", raising=False)
        sock_path = short_tmp / "run.sock"
        idle_mock = MagicMock(return_value={})
        graceful_mock = MagicMock(return_value={})

        # main resolves lifecycle functions at call time via in-function
        # import, so the lifecycle module attributes are the patch targets.
        with patch("harlo.daemon.main.ensure_data_dirs"), \
             patch("harlo.daemon.main.DAEMON_IDLE_TIMEOUT_S", 0.2), \
             patch("harlo.daemon.main.SOCKET_PATH", sock_path), \
             patch("harlo.daemon.config.SOCKET_PATH", sock_path), \
             patch("harlo.daemon.lifecycle.write_pid_file"), \
             patch("harlo.daemon.lifecycle.startup_cleanup"), \
             patch("harlo.daemon.lifecycle.install_signal_handlers"), \
             patch("harlo.daemon.lifecycle.idle_shutdown", idle_mock), \
             patch("harlo.daemon.lifecycle.graceful_shutdown", graceful_mock):
            daemon_main.run_socket_activated()

        idle_mock.assert_called_once()
        graceful_mock.assert_not_called()
        # owns_node=True in dev mode — the node was unlinked on exit.
        assert not sock_path.exists()


class TestAcquireListeningSocket:
    def test_dev_mode_refuses_to_hijack_live_listener(self, short_tmp, monkeypatch):
        """D69 guard: never unlink a node something is accepting on."""
        monkeypatch.delenv("LISTEN_FDS", raising=False)
        sock_path = str(short_tmp / "live.sock")
        listener = _listener(sock_path)
        try:
            with pytest.raises(SystemExit):
                acquire_listening_socket(sock_path, "HarloCommand")
            # The original listener still owns the node — proves no unlink.
            probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            probe.settimeout(1.0)
            probe.connect(sock_path)
            probe.close()
        finally:
            listener.close()

    def test_dev_mode_cleans_stale_node(self, short_tmp, monkeypatch):
        """A node with no listener (crashed dev run) is unlinked + rebound."""
        monkeypatch.delenv("LISTEN_FDS", raising=False)
        sock_path = str(short_tmp / "stale.sock")
        stale = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        stale.bind(sock_path)
        stale.close()  # node remains on disk, nothing listening
        assert os.path.exists(sock_path)

        sock, owns_node = acquire_listening_socket(sock_path, "HarloCommand")
        try:
            assert owns_node is True
            sock.settimeout(5)
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.settimeout(5)
            client.connect(sock_path)
            conn, _ = sock.accept()
            conn.close()
            client.close()
        finally:
            sock.close()

    @pytest.mark.skipif(sys.platform != "darwin", reason="launchd is macOS-only")
    def test_adopt_launchd_socket_not_managed_returns_none(self):
        """pytest is not launchd-managed — the REAL libSystem call runs
        and the ESRCH branch returns None."""
        assert adopt_launchd_socket("HarloCommand") is None

    def test_acquire_adopts_launchd_fds_without_dup(self, short_tmp, monkeypatch):
        """Adoption-path logic with the ctypes call monkeypatched (the
        success branch cannot run outside launchd): fd[0] is wrapped via
        fileno= (no dup), extras are closed, owns_node=False."""
        sock_path = str(short_tmp / "adopt.sock")
        backing = _listener(sock_path)
        fd0 = backing.detach()  # raw bound+listening fd, as launchd hands over
        extra_r, extra_w = os.pipe()  # stand-in second fd
        os.close(extra_w)

        monkeypatch.setattr(
            socket_activation, "adopt_launchd_socket",
            lambda name: [fd0, extra_r] if name == "HarloCommand" else None,
        )
        sock, owns_node = socket_activation.acquire_listening_socket(
            sock_path, "HarloCommand"
        )
        try:
            assert owns_node is False
            assert sock.fileno() == fd0  # fileno= adoption, not a dup
            with pytest.raises(OSError):
                os.fstat(extra_r)  # extras closed defensively
            # The adopted socket actually accepts.
            sock.settimeout(5)
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.settimeout(5)
            client.connect(sock_path)
            conn, _ = sock.accept()
            conn.close()
            client.close()
        finally:
            sock.close()
