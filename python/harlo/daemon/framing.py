"""Length-prefixed (and legacy newline) framing for the Harlo daemon IPC.

C2 fix: the Swift ``HarloHealthBridge`` (``DaemonWriter.swift``) sends a
4-byte big-endian length prefix followed by the JSON payload, while the
original daemon read until a newline. The two framings never agreed, so
biometric ingest from the bridge never parsed (the leading binary length
bytes made ``json.loads`` fail with ``Invalid JSON``).

This module makes length-prefixed frames the canonical wire format and is
used by both the daemon (``daemon/main.py``) and the CLI client
(``cli/ipc.py``). A legacy newline-delimited request is still understood
*and answered in kind*, so any older client keeps working.

Rule 1: no polling, no ``sleep``, no background threads — pure synchronous
request/response over an already-accepted socket.
"""

from __future__ import annotations

import json
import socket
import struct
from typing import Any

# 8 MiB hard cap on a single frame — defends against a bad/huge length
# prefix turning into an unbounded allocation at the socket boundary.
MAX_FRAME_BYTES = 8 * 1024 * 1024

# Framing modes.
MODE_LENGTH = "length"  # 4-byte big-endian length prefix + payload (canonical)
MODE_LINE = "line"      # legacy: JSON + b"\n"

_LENGTH_HEADER = struct.Struct(">I")

# First byte values that indicate a legacy newline-delimited JSON message
# rather than a binary length prefix. A length prefix for any realistic
# payload (< 16 MiB) starts with 0x00; JSON starts with '{' or '[',
# optionally preceded by whitespace.
_JSON_LEADING = frozenset(b"{[ \t\r\n")


class FramingError(ValueError):
    """Raised when a frame cannot be read (bad length, oversize, truncated)."""


def encode_frame(obj: Any) -> bytes:
    """Serialize *obj* to a canonical length-prefixed frame."""
    payload = json.dumps(obj).encode("utf-8")
    if len(payload) > MAX_FRAME_BYTES:
        raise FramingError(f"frame too large: {len(payload)} bytes")
    return _LENGTH_HEADER.pack(len(payload)) + payload


def _recv_exactly(conn: socket.socket, n: int) -> bytes:
    """Read exactly *n* bytes, or fewer at a clean EOF."""
    buf = bytearray()
    while len(buf) < n:
        chunk = conn.recv(min(4096, n - len(buf)))
        if not chunk:
            break
        buf += chunk
    return bytes(buf)


def read_message(conn: socket.socket) -> tuple[Any, str]:
    """Read one request from *conn*.

    Returns ``(obj, mode)``. ``obj`` is ``None`` at clean EOF / empty
    request. The framing mode is auto-detected so the response can be
    written back in the same mode the client used.
    """
    first = _recv_exactly(conn, 1)
    if not first:
        return None, MODE_LENGTH

    if first[0] in _JSON_LEADING:
        # Legacy newline-delimited JSON.
        data = bytearray(first)
        while b"\n" not in data:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk
            if len(data) > MAX_FRAME_BYTES:
                raise FramingError("legacy frame exceeded max size")
        text = bytes(data).strip()
        if not text:
            return None, MODE_LINE
        return json.loads(text.decode("utf-8")), MODE_LINE

    # Length-prefixed frame: `first` is the high byte of a 4-byte BE length.
    rest = _recv_exactly(conn, 3)
    if len(rest) != 3:
        raise FramingError("truncated length prefix")
    (length,) = _LENGTH_HEADER.unpack(first + rest)
    if length <= 0 or length > MAX_FRAME_BYTES:
        raise FramingError(f"implausible frame length: {length}")
    payload = _recv_exactly(conn, length)
    if len(payload) != length:
        raise FramingError("truncated payload")
    return json.loads(payload.decode("utf-8")), MODE_LENGTH


def write_message(conn: socket.socket, obj: Any, mode: str = MODE_LENGTH) -> None:
    """Write a response to *conn* in the requested framing mode."""
    if mode == MODE_LINE:
        conn.sendall((json.dumps(obj) + "\n").encode("utf-8"))
    else:
        conn.sendall(encode_frame(obj))


__all__ = [
    "FramingError",
    "MAX_FRAME_BYTES",
    "MODE_LENGTH",
    "MODE_LINE",
    "encode_frame",
    "read_message",
    "write_message",
]
