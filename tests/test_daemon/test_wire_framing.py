"""D61 — dual wire framing on the daemon socket (canonical framing module).

The CLI sends newline-delimited JSON; HarloHealthBridge / HarloXPCRelay
send a 4-byte big-endian length prefix + payload (DaemonWriter.swift,
HarloXPCRelay/main.swift). The daemon speaks the canonical framing module
(daemon/framing.py): it auto-detects the request framing and *replies in
the same framing the client used*. The relay reads a length-prefixed
reply (readN(fd, 4) → readN(fd, n)), so replying in-kind is load-bearing,
not cosmetic — a newline reply to a length-prefixed request would make
the relay misread the JSON's first 4 bytes as a ~2 GiB length and bail.

These tests pin both framings end-to-end through handle_client over a
real socketpair, reading the reply back through the same framing reader.
"""

import json
import socket
import threading

from harlo.daemon import framing
from harlo.daemon import main as daemon_main


def _run_handle_client(server_sock):
    t = threading.Thread(target=daemon_main.handle_client, args=(server_sock,))
    t.start()
    return t


def _request_response(payload_bytes: bytes) -> dict:
    """Drive one request through handle_client and read the reply back via
    the canonical framing reader. handle_client replies in whatever
    framing the request used, so framing.read_message handles both."""
    client, server = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    t = _run_handle_client(server)
    try:
        client.sendall(payload_bytes)
        client.shutdown(socket.SHUT_WR)
        obj, _mode = framing.read_message(client)
        return obj if obj is not None else {}
    finally:
        client.close()
        t.join(timeout=5)


def test_newline_json_framing_still_works():
    """The CLI's legacy framing: JSON + trailing newline (reply in kind)."""
    req = json.dumps({"command": "ping", "args": {}}) + "\n"
    res = _request_response(req.encode())
    assert res.get("status") == "ok"


def test_length_prefixed_framing_swift_bridge():
    """DaemonWriter.swift's framing: 4-byte BE length + payload, no newline."""
    body = json.dumps({"command": "ping", "args": {}}).encode()
    frame = len(body).to_bytes(4, "big") + body
    res = _request_response(frame)
    assert res.get("status") == "ok"


def test_length_prefixed_biometric_ingest_shape():
    """The exact shape the bridge pushes reaches the router intact."""
    body = json.dumps({
        "command": "biometric_ingest",
        "args": {"samples": []},
    }).encode()
    frame = len(body).to_bytes(4, "big") + body
    res = _request_response(frame)
    # Empty batch is a valid no-op ingest, not a parse error.
    assert res.get("status") == "ok"
    assert res.get("result", {}).get("accepted") == 0


def test_zero_length_prefix_is_bounded_error():
    """A 0x00000000 prefix (length 0) is invalid. The framing reader
    rejects it as an implausible length and the daemon replies with a
    bounded error frame — never an unbounded read or attacker-sized
    allocation (any 0x00-prefixed frame has length < 16 MiB by
    construction)."""
    frame = (0).to_bytes(4, "big") + b"junk"
    res = _request_response(frame)
    assert res.get("status") == "error"


def test_huge_claimed_length_degrades_to_bounded_error():
    """A >8 MiB length prefix is rejected at the MAX_FRAME_BYTES cap —
    a bounded error reply, no attacker-sized allocation, no hang."""
    frame = (64 * 1024 * 1024).to_bytes(4, "big") + b"x"
    res = _request_response(frame)
    assert res.get("status") == "error"
