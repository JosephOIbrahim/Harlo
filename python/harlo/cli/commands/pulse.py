"""harlo pulse — pair with and receive from the HarloPulse iPhone sidecar.

ADR-0002 v1: the iPhone is the biometric signal source (D67 — HealthKit
data does not exist on any Mac through macOS 27). HarloPulse pushes the
EXACT existing DaemonWriter payload over LAN TCP, 4-byte big-endian
length-prefixed JSON frames (D61 framing, byte-identical).

This is the first sanctioned network listener in Harlo (ADR-0002
point 3). Blast radius is contained by:

  - Command whitelist: ONLY ``biometric_ingest`` is routable from the
    network. A frame naming any other router command drops the
    connection and never touches the router.
  - HMAC-SHA256 auth frame (key = SHA256 of the 6-word pairing token)
    verified with ``hmac.compare_digest`` plus a freshness window.
  - 1 MiB frame cap and bounded idle deadline; the listener exits on
    idle (no daemon, no KeepAlive, no forever-loop — Rule 1 spirit).

Rule 9 containment: raw samples NEVER touch disk Mac-side. The path is
socket bytes -> json.loads -> route_command("biometric_ingest", args)
-> biometric_barrier -> in-memory AllostasisTracker. The only things
that hit disk are pulse_token.json (token HASH only — no biometric
data) and the D60 derived verdict written inside the existing
``_handle_biometric_ingest`` handler.

Note: ``route_command`` runs in THIS process, not the daemon, so the
D60 ``write_modulation_state`` persistence inside the handler runs here
too (it is process-agnostic and writes twin.db). If the daemon is
simultaneously live there is a small SQLite write-contention window;
WAL/busy-timeout defaults make this benign.

Security note: pulse_token.json stores SHA256(token), which IS the HMAC
key — key-equivalent material. It is written 0600-from-the-first-byte
(D50/D80 pattern) and is the same trust class as the daemon socket
itself: anyone who can read it can authenticate as the phone.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import socket
import subprocess
import struct
import time
from datetime import datetime, timezone
from pathlib import Path

import click

PROTO = "harlo-pulse-v1"
DEFAULT_PORT = 48653
MAX_FRAME = 1 << 20  # 1 MiB frame cap (DoS guard)
AUTH_WINDOW_S = 300  # auth ts freshness, mirrors Rule 9 freshness philosophy
TOKEN_WORDS = 6

# 256 unique lowercase 3-6 letter words (EFF-short-list-style subset).
# 6 words x 8 bits = 48 bits of pairing entropy.
_WORDLIST: tuple[str, ...] = (
    "able", "acid", "acorn", "actor", "adobe", "adopt", "agile", "aging",
    "alarm", "album", "alert", "alias", "alibi", "alien", "alley", "aloft",
    "alpha", "amber", "ample", "anchor", "angle", "ankle", "annex", "apple",
    "apron", "arch", "arena", "argon", "armor", "aroma", "arrow", "aspen",
    "asset", "atlas", "atom", "attic", "audio", "auger", "autumn", "avid",
    "awake", "axiom", "axis", "bacon", "badge", "bagel", "baker", "balsa",
    "bamboo", "banjo", "barge", "basil", "baton", "beacon", "beagle", "bean",
    "bear", "beech", "belt", "bench", "berry", "bicep", "birch", "bison",
    "blade", "blank", "blaze", "blend", "bloom", "bluff", "board", "bolt",
    "bonus", "booth", "bound", "brace", "braid", "brain", "brand", "brass",
    "brave", "bread", "brick", "brief", "brisk", "broad", "bronze", "brook",
    "broom", "brush", "buck", "buggy", "bugle", "bulb", "bunch", "bunny",
    "burlap", "cabin", "cable", "cactus", "camel", "canal", "candy", "canoe",
    "canvas", "cape", "cargo", "carrot", "cedar", "cello", "chalk", "charm",
    "chess", "chief", "chili", "chime", "cider", "cigar", "civic", "clamp",
    "clash", "clay", "cleat", "cliff", "climb", "cloak", "clover", "coast",
    "cobalt", "cocoa", "comet", "conch", "coral", "cork", "couch", "cove",
    "crane", "crate", "creek", "crepe", "crisp", "crown", "cube", "cumin",
    "cycle", "daisy", "dandy", "dart", "deck", "decoy", "delta", "denim",
    "depot", "derby", "dice", "diary", "dime", "dingo", "diver", "dock",
    "dodge", "dome", "donor", "dough", "dove", "dozen", "draft", "drape",
    "drift", "drill", "drum", "dune", "dusk", "eagle", "easel", "echo",
    "edge", "eject", "elbow", "elder", "elk", "elm", "ember", "emblem",
    "empty", "engine", "envoy", "epoxy", "equal", "essay", "etch", "evoke",
    "exit", "fable", "falcon", "fancy", "fang", "fawn", "fence", "fern",
    "ferry", "fiber", "flame", "flank", "flask", "fleece", "fleet", "flint",
    "flora", "flute", "foam", "foggy", "forge", "fossil", "fresh", "frost",
    "fruit", "fudge", "fungus", "gala", "galaxy", "garlic", "gauge", "gecko",
    "geyser", "ginger", "glade", "gleam", "glide", "globe", "glove", "gloss",
    "gold", "goose", "gorge", "gourd", "grain", "grape", "gravel", "green",
    "grove", "guard", "guava", "guitar", "gulf", "gusto", "habit", "harbor",
    "hatch", "hazel", "heron", "hippo", "holly", "honey", "hutch", "husk",
)


def normalize_token(token: str) -> str:
    """Lowercase, split on whitespace, single-space join."""
    return " ".join(token.lower().split())


def generate_token() -> str:
    """Six words from the 256-word list = 48 bits of entropy."""
    return " ".join(secrets.choice(_WORDLIST) for _ in range(TOKEN_WORDS))


def derive_key(token: str) -> bytes:
    """HMAC key = SHA256 digest of the normalized token (32 bytes)."""
    return hashlib.sha256(normalize_token(token).encode("utf-8")).digest()


def auth_msg(ts: str, nonce: str) -> bytes:
    """The exact bytes both sides MAC: 'harlo-pulse-v1|<ts>|<nonce>'."""
    return f"{PROTO}|{ts}|{nonce}".encode("utf-8")


def verify_auth(frame: dict, key: bytes, now=None) -> tuple[bool, str]:
    """Verify an auth frame: kind/version, HMAC, freshness.

    Returns (ok, reason). On rejection the reason includes the computed
    clock skew where applicable, so badly skewed phone/Mac clocks are
    debuggable instead of mysterious.
    """
    if frame.get("kind") != "auth":
        return False, "first frame must have kind='auth'"
    if frame.get("version") != 1:
        return False, f"unsupported auth version {frame.get('version')!r}"
    ts = frame.get("ts")
    nonce = frame.get("nonce")
    mac = frame.get("mac")
    if not (isinstance(ts, str) and isinstance(nonce, str) and isinstance(mac, str)):
        return False, "auth frame missing ts/nonce/mac"

    expected = hmac.new(key, auth_msg(ts, nonce), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected.encode("ascii"), mac.encode("utf-8", "replace")):
        return False, "bad mac (wrong pairing token? re-run: harlo pulse pair)"

    if now is None:
        now = datetime.now(timezone.utc)
    try:
        sent = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return False, f"unparseable auth ts {ts!r}"
    if sent.tzinfo is None:
        sent = sent.replace(tzinfo=timezone.utc)
    skew = abs((now - sent).total_seconds())
    if skew > AUTH_WINDOW_S:
        return False, (
            f"stale auth: computed clock skew {skew:.0f}s exceeds the "
            f"{AUTH_WINDOW_S}s freshness window (check phone/Mac clocks)"
        )
    return True, "ok"


def _recv_exact(sock, n: int) -> bytes | None:
    """Read exactly n bytes. None on clean EOF at a frame boundary;
    ValueError if the connection dies mid-read."""
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            if buf:
                raise ValueError("connection truncated mid-frame")
            return None
        buf += chunk
    return buf


def read_frame(sock) -> dict | None:
    """Read one D61 frame (4-byte BE length + UTF-8 JSON).

    Returns None on clean EOF; raises ValueError on oversize or
    truncated frames.
    """
    head = _recv_exact(sock, 4)
    if head is None:
        return None
    (length,) = struct.unpack(">I", head)
    if length > MAX_FRAME:
        raise ValueError(f"frame of {length} bytes exceeds {MAX_FRAME} byte cap")
    body = _recv_exact(sock, length)
    if body is None:
        raise ValueError("connection truncated mid-frame")
    return json.loads(body.decode("utf-8"))


def write_frame(sock, obj: dict) -> None:
    """Write one D61 frame: 4-byte BE length prefix + UTF-8 JSON."""
    payload = json.dumps(obj).encode("utf-8")
    sock.sendall(struct.pack(">I", len(payload)) + payload)


def handle_connection(conn, key: bytes, route=None) -> dict:
    """Drive one phone session: auth frame -> ack -> sample frames.

    ``route`` defaults to the daemon router's ``route_command`` (lazy
    import so tests can inject a stub without a daemon). Closes ``conn``
    before returning.

    Whitelist (the ADR-0002 containment): any frame whose command is
    not ``biometric_ingest`` drops the connection without touching the
    router.
    """
    if route is None:
        from harlo.daemon.router import route_command as route

    summary: dict = {
        "authed": False,
        "frames": 0,
        "accepted": 0,
        "device": None,
        "last_result": None,
        "auth_error": None,
    }
    try:
        auth = read_frame(conn)
        if auth is None:
            return summary
        ok, reason = verify_auth(auth, key)
        if not ok:
            summary["auth_error"] = reason
            write_frame(conn, {"status": "error", "message": reason})
            return summary
        summary["authed"] = True
        summary["device"] = auth.get("device") or "unknown"
        write_frame(conn, {"status": "ok"})

        frame = read_frame(conn)
        while frame is not None:
            command = frame.get("command")
            if command != "biometric_ingest":
                # Whitelist violation: warn + close. The router is
                # never called — this is what keeps the listener from
                # being "the router exposed to the LAN".
                click.echo(
                    f"pulse: dropping connection — non-whitelisted command {command!r}",
                    err=True,
                )
                break
            result = route("biometric_ingest", frame.get("args") or {})
            summary["frames"] += 1
            summary["last_result"] = result
            if isinstance(result, dict):
                summary["accepted"] += (result.get("result") or {}).get("accepted") or 0
            # Per-frame ack: the route_command result dict (derived
            # verdict only — contains no raw samples).
            write_frame(conn, result)
            frame = read_frame(conn)
    except (ValueError, OSError):
        # Oversize/truncated frame, bad JSON, or per-connection timeout:
        # drop the connection. Nothing partial reaches the router.
        pass
    finally:
        conn.close()
    return summary


def _token_path() -> Path:
    # Lazy import so the test fixture's importlib.reload(config)
    # pattern (HARLO_DATA_DIR override) is honored at call time.
    from harlo.daemon.config import DATA_DIR

    return Path(DATA_DIR) / "pulse_token.json"


def _host_candidates() -> list[str]:
    """LAN IPv4 FIRST, then the real Bonjour name.

    Field lesson (2026-06-10): socket.gethostname() can return a
    generic 'Mac', whose '.local' form resolves to NOTHING — the phone
    fails with NWError -65554 NoSuchRecord before any packet is sent
    (which also means iOS's Local Network permission prompt never
    fires, compounding the confusion). The numeric IP involves no
    resolver at all, so it leads. The mDNS name comes from scutil's
    LocalHostName — the name Bonjour actually advertises — never from
    gethostname().
    """
    candidates: list[str] = []
    # UDP-connect trick: routes a socket without sending any packet,
    # then reads the local address the OS picked.
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("198.51.100.1", 9))
            ip = probe.getsockname()[0]
            if ip and ip != "0.0.0.0":
                candidates.append(ip)
        finally:
            probe.close()
    except OSError:
        pass
    # Bonjour name (macOS): scutil --get LocalHostName + ".local".
    try:
        out = subprocess.run(
            ["scutil", "--get", "LocalHostName"],
            capture_output=True, text=True, timeout=5,
        )
        name = out.stdout.strip()
        if out.returncode == 0 and name:
            candidates.append(f"{name}.local")
    except (OSError, subprocess.SubprocessError):
        pass
    # Last-resort fallback when both probes fail (non-mac dev boxes).
    if not candidates:
        hostname = socket.gethostname()
        candidates.append(hostname if hostname.endswith(".local")
                          else hostname.split(".")[0] + ".local")
    deduped: list[str] = []
    for c in candidates:
        if c not in deduped:
            deduped.append(c)
    return deduped


@click.group()
def pulse():
    """Pair with and receive from the HarloPulse iPhone sidecar (ADR-0002)."""
    pass


@pulse.command("pair")
@click.option("--port", default=DEFAULT_PORT, type=int, help="TCP port the listener will use.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def pulse_pair(port: int, as_json: bool):
    """Generate a 6-word pairing token and store its hash.

    The token itself is only DISPLAYED — never written anywhere. Only
    SHA256(token) lands in pulse_token.json (0600). Re-pairing
    overwrites the file, which revokes the old token.
    """
    token = generate_token()
    key_hex = derive_key(token).hex()
    path = _token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "v": 1,
        "key_hash_hex": key_hex,
        "port": port,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    # 0600 from the first byte (D50/D80 pattern, router.py export) —
    # create-then-chmod would leave key material world-readable for the
    # gap; the trailing chmod tightens pre-existing wider files.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(record, indent=2))
    os.chmod(path, 0o600)

    hosts = _host_candidates()
    if as_json:
        click.echo(json.dumps({
            "token": token,
            "hosts": hosts,
            "port": port,
            "token_file": str(path),
        }, indent=2))
        return
    click.echo("Pairing token (enter in HarloPulse on your iPhone):")
    click.echo("")
    click.echo(f"    {token}")
    click.echo("")
    click.echo("Host (try in order):")
    for h in hosts:
        click.echo(f"    {h}")
    click.echo(f"Port: {port}")
    click.echo("")
    click.echo("Next: enter the words + host + port in HarloPulse, then run:")
    click.echo("    harlo pulse listen")


@pulse.command("listen")
@click.option("--timeout", default=300, type=int, help="Idle seconds before the listener exits.")
@click.option("--bind", default="0.0.0.0", help="Interface to bind (use a LAN IP for tighter scoping).")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def pulse_listen(timeout: int, bind: str, as_json: bool):
    """Accept pushes from the paired phone until idle, then exit.

    Hands off and exits on the idle deadline (ADR-0002 constraint 1 /
    Rule 1 spirit — no daemon, no KeepAlive). Each accepted connection
    resets the idle clock.
    """
    path = _token_path()
    if not path.exists():
        msg = "Not paired. Run: harlo pulse pair"
        if as_json:
            click.echo(json.dumps({"error": msg}))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        key = bytes.fromhex(record["key_hash_hex"])
        port = int(record.get("port") or DEFAULT_PORT)
    except (ValueError, KeyError, OSError) as exc:
        msg = f"Corrupt pairing file {path}: {exc}. Re-run: harlo pulse pair"
        if as_json:
            click.echo(json.dumps({"error": msg}))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    # TODO(ADR-0002 v1): Bonjour advertisement deferred — would need
    # zeroconf (new dep, disallowed) or a launchd/dnssd integration;
    # the phone uses manual host:port entry until then (its NWBrowser
    # path is dormant).
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        srv.bind((bind, port))
    except OSError as exc:
        srv.close()
        msg = f"Cannot bind {bind}:{port}: {exc}"
        if as_json:
            click.echo(json.dumps({"error": msg}))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)
    srv.listen(1)
    srv.settimeout(1.0)

    if not as_json:
        click.echo(f"Listening on {bind}:{port} (idle timeout {timeout}s)...")

    sessions: list[dict] = []
    # Deadline-bounded accept loop — never a forever-loop (Rule 1).
    deadline = time.monotonic() + timeout
    try:
        while time.monotonic() < deadline:
            try:
                conn, addr = srv.accept()
            except socket.timeout:
                continue
            # Human presence resets the idle clock.
            deadline = time.monotonic() + timeout
            conn.settimeout(10.0)
            summary = handle_connection(conn, key)
            sessions.append(summary)
            if not as_json:
                _echo_session(summary, addr)
    finally:
        srv.close()

    if as_json:
        click.echo(json.dumps({"sessions": sessions}, indent=2))
    else:
        click.echo(f"Idle deadline reached. {len(sessions)} session(s) handled.")


def _echo_session(summary: dict, addr) -> None:
    """One line per session: device, frames, accepted, derived verdict
    (the user-visible payoff of D60)."""
    if not summary["authed"]:
        click.echo(f"  {addr[0]}: auth rejected — {summary.get('auth_error')}")
        return
    last = summary.get("last_result") or {}
    res = (last.get("result") or {}) if isinstance(last, dict) else {}
    click.echo(
        f"  {summary['device']} ({addr[0]}): frames={summary['frames']} "
        f"accepted={summary['accepted']} depleted={res.get('depleted')} "
        f"force_red={res.get('force_red')} biometric_load={res.get('biometric_load')}"
    )


@pulse.command("unpair")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def pulse_unpair(as_json: bool):
    """Revoke the pairing (ADR-0002 constraint 3: explicit, revocable)."""
    path = _token_path()
    if path.exists():
        path.unlink()
        if as_json:
            click.echo(json.dumps({"revoked": True}))
        else:
            click.echo("Pairing revoked. The phone can no longer authenticate.")
    else:
        if as_json:
            click.echo(json.dumps({"revoked": False, "message": "not paired"}))
        else:
            click.echo("Not paired — nothing to revoke.")
