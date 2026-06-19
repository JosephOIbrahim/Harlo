"""C1 — listen-socket acquisition (launchd / systemd / dev).

These run on any platform: they assert the selection logic and the dev
fallback, and that the launchd probe never raises when no socket is
registered (the common case off-launchd).
"""

from __future__ import annotations

import os
import socket

import pytest

from harlo.daemon import socket_activation as sa


@pytest.fixture()
def short_sock_path():
    # AF_UNIX sun_path is capped at ~104 bytes on macOS; pytest's tmp_path is
    # too long, so use a short, unique /tmp path and clean it up.
    p = f"/tmp/h{os.getpid()}.sock"
    if os.path.exists(p):
        os.unlink(p)
    yield p
    if os.path.exists(p):
        os.unlink(p)


def test_systemd_socket_none_without_env(monkeypatch):
    monkeypatch.delenv("LISTEN_FDS", raising=False)
    assert sa.try_systemd_socket() is None


def test_launchd_probe_returns_none_and_never_raises():
    # Not running under launchd with this (bogus) registered name, so the
    # probe must return None gracefully on every platform.
    assert sa.try_launchd_socket("HarloCommand_not_registered_xyz") is None


def test_bind_dev_socket_creates_path(short_sock_path):
    s = sa.bind_dev_socket(short_sock_path)
    try:
        assert os.path.exists(short_sock_path)
        assert s.family == socket.AF_UNIX
    finally:
        s.close()


def test_acquire_falls_back_to_dev(short_sock_path, monkeypatch):
    monkeypatch.delenv("LISTEN_FDS", raising=False)
    monkeypatch.setattr(sa, "try_launchd_socket", lambda *a, **k: None)
    s, source = sa.acquire_listen_socket(short_sock_path)
    try:
        assert source == "dev"
        assert os.path.exists(short_sock_path)
    finally:
        s.close()


def test_acquire_prefers_launchd_when_available(tmp_path, monkeypatch):
    fake = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    monkeypatch.setattr(sa, "try_launchd_socket", lambda *a, **k: fake)
    try:
        s, source = sa.acquire_listen_socket(str(tmp_path / "unused.sock"))
        assert source == "launchd"
        assert s is fake
    finally:
        fake.close()
