"""C2 — daemon IPC framing.

Proves the daemon now understands the Swift HealthBridge's length-prefixed
frames (which the old newline-only reader could never parse) while staying
backward-compatible with legacy newline-delimited clients.
"""

from __future__ import annotations

import json
import socket
import struct

import pytest

from harlo.daemon import framing
from harlo.daemon.main import handle_client


def _roundtrip_request(raw: bytes):
    a, b = socket.socketpair()
    try:
        a.sendall(raw)
        a.close()
        return framing.read_message(b)
    finally:
        b.close()


def test_encode_frame_is_length_prefixed():
    raw = framing.encode_frame({"command": "ping", "args": {}})
    assert raw[:4] == struct.pack(">I", len(raw) - 4)


def test_length_prefixed_roundtrip():
    obj = {"command": "ping", "args": {}}
    got, mode = _roundtrip_request(framing.encode_frame(obj))
    assert got == obj
    assert mode == framing.MODE_LENGTH


def test_legacy_newline_roundtrip():
    raw = (json.dumps({"command": "ping", "args": {}}) + "\n").encode("utf-8")
    got, mode = _roundtrip_request(raw)
    assert got["command"] == "ping"
    assert mode == framing.MODE_LINE


def test_swift_style_biometric_frame_parses():
    # Mirrors DaemonWriter.swift exactly: 4-byte BE length + JSON, NO newline.
    payload = json.dumps(
        {"command": "biometric_ingest", "args": {"samples": []}}
    ).encode("utf-8")
    frame = struct.pack(">I", len(payload)) + payload
    got, mode = _roundtrip_request(frame)
    assert got["command"] == "biometric_ingest"
    assert mode == framing.MODE_LENGTH


def test_oversize_length_prefix_rejected():
    a, b = socket.socketpair()
    try:
        a.sendall(struct.pack(">I", framing.MAX_FRAME_BYTES + 1) + b"x")
        a.close()
        with pytest.raises(framing.FramingError):
            framing.read_message(b)
    finally:
        b.close()


def test_empty_request_is_none():
    a, b = socket.socketpair()
    try:
        a.close()  # immediate EOF
        got, _mode = framing.read_message(b)
    finally:
        b.close()
    assert got is None


def test_handle_client_ping_length_framed():
    srv, cli = socket.socketpair()
    try:
        cli.sendall(framing.encode_frame({"command": "ping", "args": {}}))
        handle_client(srv)  # reads request, writes response, closes srv
        resp, mode = framing.read_message(cli)
    finally:
        cli.close()
    assert resp["status"] == "ok"
    assert resp.get("pong") is True
    assert mode == framing.MODE_LENGTH


def test_handle_client_legacy_line_framed_replies_in_kind():
    srv, cli = socket.socketpair()
    try:
        cli.sendall((json.dumps({"command": "ping", "args": {}}) + "\n").encode())
        handle_client(srv)
        resp, mode = framing.read_message(cli)
    finally:
        cli.close()
    assert resp["status"] == "ok"
    assert mode == framing.MODE_LINE
