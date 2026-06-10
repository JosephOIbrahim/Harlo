"""D61 — dual wire framing on the daemon socket.

The CLI sends newline-delimited JSON; HarloHealthBridge sends a 4-byte
big-endian length prefix + payload (DaemonWriter.swift). Before D61 the
daemon only spoke newline-JSON, so 100% of bridge frames were dropped
at json.loads. These tests pin both framings end-to-end through
handle_client over a real socketpair.
"""

import json
import socket
import threading

from harlo.daemon import main as daemon_main


def _run_handle_client(server_sock):
    t = threading.Thread(target=daemon_main.handle_client, args=(server_sock,))
    t.start()
    return t


def _request_response(payload_bytes: bytes) -> dict:
    client, server = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    t = _run_handle_client(server)
    try:
        client.sendall(payload_bytes)
        client.shutdown(socket.SHUT_WR)
        data = b""
        while True:
            chunk = client.recv(4096)
            if not chunk:
                break
            data += chunk
        return json.loads(data.strip())
    finally:
        client.close()
        t.join(timeout=5)


def test_newline_json_framing_still_works():
    """The CLI's legacy framing: JSON + trailing newline."""
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


def test_zero_length_prefix_closes_cleanly():
    """A 0x00000000 prefix (length 0) is invalid — close, no response.

    Note the sniffer's safety property: any frame classified as
    length-prefixed (first byte 0x00) has length < 2^24 = 16 MiB by
    construction, so attacker-sized allocations are impossible on
    this path.
    """
    frame = (0).to_bytes(4, "big") + b"junk"
    client, server = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    t = _run_handle_client(server)
    try:
        client.sendall(frame)
        client.shutdown(socket.SHUT_WR)
        data = client.recv(4096)
        assert data == b""
    finally:
        client.close()
        t.join(timeout=5)


def test_huge_claimed_length_degrades_to_bounded_error():
    """A >16MiB 'length prefix' has a nonzero first byte, so the sniffer
    treats it as (garbage) legacy data — bounded read, JSON error reply,
    no attacker-sized allocation, no hang."""
    frame = (64 * 1024 * 1024).to_bytes(4, "big") + b"x"
    res = _request_response(frame)
    assert res.get("status") == "error"
