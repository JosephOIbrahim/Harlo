"""`harlo pulse` — HarloPulse iPhone sidecar pairing + listener (ADR-0002 v1).

Covers:
  - Token round-trip: pair writes SHA256(token) hex at 0600; the six
    displayed words derive the same key.
  - verify_auth: accept valid, reject bad mac, reject stale ts (with
    skew in the reason).
  - handle_connection over socket.socketpair(): relays auth + sample
    frames into a stubbed route callable; whitelist drops unknown
    commands without calling the router.
  - listen without pairing exits nonzero.

No threads, no network, no daemon — socketpair drives handle_connection
synchronously.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import socket
import stat
import struct
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from click.testing import CliRunner


@pytest.fixture
def tmp_data(monkeypatch, tmp_path):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setenv("HARLO_DATA_DIR", str(tmp_path / "data"))
    import importlib
    import harlo.daemon.config as cfg

    importlib.reload(cfg)
    import harlo.cli.commands.pulse as pulse_mod

    importlib.reload(pulse_mod)
    return tmp_path


def _frame_bytes(obj: dict) -> bytes:
    payload = json.dumps(obj).encode("utf-8")
    return struct.pack(">I", len(payload)) + payload


def _auth_frame(p, key: bytes, ts: str | None = None) -> dict:
    if ts is None:
        ts = datetime.now(timezone.utc).isoformat()
    nonce = "00112233aabbccdd"
    mac = hmac.new(key, p.auth_msg(ts, nonce), hashlib.sha256).hexdigest()
    return {
        "kind": "auth",
        "version": 1,
        "device": "iPhone",
        "ts": ts,
        "nonce": nonce,
        "mac": mac,
    }


def _combined_output(res) -> str:
    out = res.output
    try:
        out += res.stderr
    except (ValueError, TypeError):
        pass  # older click mixes stderr into output already
    return out


def test_pair_writes_six_word_token_file(tmp_data) -> None:
    import harlo.cli.commands.pulse as p

    runner = CliRunner()
    res = runner.invoke(p.pulse, ["pair"])
    assert res.exit_code == 0, res.output

    # The six displayed words are all from the embedded wordlist.
    words = None
    for line in res.output.splitlines():
        parts = line.split()
        if len(parts) == p.TOKEN_WORDS and all(w in p._WORDLIST for w in parts):
            words = parts
            break
    assert words is not None, f"no 6-word token line in output:\n{res.output}"

    token_file = Path(os.environ["HARLO_DATA_DIR"]) / "pulse_token.json"
    assert token_file.exists()
    assert stat.S_IMODE(os.stat(token_file).st_mode) == 0o600

    record = json.loads(token_file.read_text(encoding="utf-8"))
    # Token round-trip: stored hash == derived key of the displayed words.
    assert record["key_hash_hex"] == p.derive_key(" ".join(words)).hex()
    # The raw token never lands in the file.
    assert " ".join(words) not in token_file.read_text(encoding="utf-8")


def test_derive_key_normalizes(tmp_data) -> None:
    import harlo.cli.commands.pulse as p

    assert p.derive_key("Alpha  Bravo \t cedar") == p.derive_key("alpha bravo cedar")


def test_verify_auth_accepts_valid_frame(tmp_data) -> None:
    import harlo.cli.commands.pulse as p

    key = p.derive_key("alpha bravo cedar delta ember frost")
    ok, reason = p.verify_auth(_auth_frame(p, key), key)
    assert ok, reason


def test_verify_auth_rejects_bad_mac(tmp_data) -> None:
    import harlo.cli.commands.pulse as p

    key = p.derive_key("alpha bravo cedar delta ember frost")
    frame = _auth_frame(p, key)
    # Flip a hex digit.
    frame["mac"] = ("0" if frame["mac"][0] != "0" else "1") + frame["mac"][1:]
    ok, reason = p.verify_auth(frame, key)
    assert not ok
    assert "mac" in reason.lower()


def test_verify_auth_rejects_stale_ts(tmp_data) -> None:
    import harlo.cli.commands.pulse as p

    key = p.derive_key("alpha bravo cedar delta ember frost")
    stale = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    ok, reason = p.verify_auth(_auth_frame(p, key, ts=stale), key)
    assert not ok
    assert "skew" in reason.lower()


def test_handle_connection_relays_to_route_stub(tmp_data) -> None:
    import harlo.cli.commands.pulse as p

    key = p.derive_key("alpha bravo cedar delta ember frost")
    sample = {
        "type": "heart_rate",
        "value": 62.0,
        "unit": "count/min",
        "sampled_at": datetime.now(timezone.utc).isoformat(),
        "source": {"device": "Apple Watch Ultra", "bundle_id": "com.apple.health"},
    }
    ingest = {"command": "biometric_ingest", "args": {"samples": [sample]}}

    a, b = socket.socketpair()
    a.sendall(_frame_bytes(_auth_frame(p, key)) + _frame_bytes(ingest))
    a.shutdown(socket.SHUT_WR)

    calls: list[tuple] = []

    def stub(command, args):
        calls.append((command, args))
        return {"status": "ok", "result": {"accepted": 1}}

    summary = p.handle_connection(b, key, route=stub)

    assert summary["authed"] is True
    assert summary["frames"] == 1
    assert summary["accepted"] == 1
    assert calls == [("biometric_ingest", {"samples": [sample]})]

    # Auth ack + per-frame result ack come back on the wire.
    ack = p.read_frame(a)
    assert ack == {"status": "ok"}
    result_ack = p.read_frame(a)
    assert result_ack["result"]["accepted"] == 1
    assert p.read_frame(a) is None  # connection closed
    a.close()


def test_handle_connection_rejects_unknown_command(tmp_data) -> None:
    import harlo.cli.commands.pulse as p

    key = p.derive_key("alpha bravo cedar delta ember frost")
    a, b = socket.socketpair()
    a.sendall(
        _frame_bytes(_auth_frame(p, key))
        + _frame_bytes({"command": "store", "args": {"content": "nope"}})
    )
    a.shutdown(socket.SHUT_WR)

    calls: list[tuple] = []

    def stub(command, args):
        calls.append((command, args))
        return {"status": "ok"}

    summary = p.handle_connection(b, key, route=stub)

    # Whitelist holds: the router stub is never called.
    assert calls == []
    assert summary["authed"] is True
    assert summary["frames"] == 0

    ack = p.read_frame(a)
    assert ack == {"status": "ok"}
    assert p.read_frame(a) is None  # connection closed, no further frames
    a.close()


def test_listen_requires_pairing(tmp_data) -> None:
    import harlo.cli.commands.pulse as p

    runner = CliRunner()
    res = runner.invoke(p.pulse, ["listen", "--timeout", "1"])
    assert res.exit_code == 1
    assert "pair" in _combined_output(res).lower()


def test_listen_adopts_launchd_socket(tmp_data, monkeypatch) -> None:
    """When launchd hands us a listening fd, listen() must adopt it
    (skip bind) and announce the adoption."""
    import socket as socket_mod

    import harlo.cli.commands.pulse as p
    from click.testing import CliRunner

    _write_token(tmp_data)  # paired state

    # A real listening TCP socket stands in for launchd's fd.
    held = socket_mod.socket(socket_mod.AF_INET, socket_mod.SOCK_STREAM)
    held.bind(("127.0.0.1", 0))
    held.listen(1)
    fd = held.detach()  # ownership passes to the adopter, like launchd

    import harlo.daemon.socket_activation as sa
    monkeypatch.setattr(sa, "adopt_launchd_socket",
                        lambda name: [fd] if name == "HarloPulse" else None)

    runner = CliRunner()
    res = runner.invoke(p.pulse, ["listen", "--timeout", "1"])
    out = _combined_output(res)
    assert res.exit_code == 0, out
    assert "launchd socket" in out
