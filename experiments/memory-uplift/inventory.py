#!/usr/bin/env python
"""inventory.py — Cycle 4 probe-candidate inventory against a SNAPSHOT.

Read-only, never the live store. Same temp-copy-and-checkpoint open as
probe_lint.py (a cleanly-closed WAL db has no sidecars; mode=ro fails;
and a captured -wal must replay without mutating the snapshot).

Definition of a probe candidate (consistent with probe_lint.py, the P2
verifier, AND with the SPEC's Hot/Warm-tier + decay-age requirements):

    a Hot or Warm trace whose content is Elenchus-VERIFIED.

Neither hot_traces (FTS5) nor warm `traces` (SDR) carries a verification
column — confirmed against schema. The only VERIFIED-bearing tables are
reflexes.verification_state and elenchus_pending.status. A trace becomes
probe-eligible when its trace_id appears in the `source_traces` of a
VERIFIED elenchus_pending claim. (reflexes are compiled responses keyed by
pattern_hash, not tier-able memory traces — counted separately, not pooled.)

TIER criterion: table residency.
    Hot  = row in hot_traces  (FTS5-resident, recent)
    Warm = row in `traces`    (SDR-resident, decay-aged)

AGE bins (Warm, via read-side lazy decay — decay.rs):
    strength = initial * e^(-lambda * dt) + sum(boost_i * e^(-lambda * dt_i))
    now = snapshot capture time (twin.db mtime — the frozen universe).
    fresh          : strength > 0.5 * initial
    mid            : 1.2*epsilon < strength <= 0.5 * initial
    near-apoptosis : strength <= 1.2 * epsilon   (within ~20% of the
                     epsilon=0.01 deletion floor, or already below it)
Hot traces have no decay fields; aged by wall-clock recency, never
near-apoptosis (they are evicted/promoted, not decayed).

TRIP-WIRE screen: drop any candidate whose text touches cybersecurity,
bio/chem, or distillation content. Counts reported, never contents.

Output: probe_candidates.json. Kill: pool < 12 -> KILL CONDITION FIRED.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

EPSILON = 0.01          # daemon/config.py DEFAULT_EPSILON
KILL_FLOOR = 12         # SPEC falsification condition
NEAR_APOPTOSIS_FACTOR = 1.2

# Same conservative, coaching-irrelevant list probe_lint.py screens with.
TRIPWIRE_TERMS = [
    "exploit", "payload", "malware", "ransomware", "backdoor",
    "privilege escalation", "zero-day", "rootkit", "keylogger",
    "sql injection", "buffer overflow", "shellcode", "credential",
    "api key", "secret key", "token scope", "mcp attack", "attack surface",
    "pathogen", "toxin", "nerve agent", "bioweapon", "synthesize virus",
    "select agent", "sarin", "ricin", "anthrax",
    "distill", "distillation", "weight extraction", "model extraction",
    "training data extraction", "membership inference",
]


def screen(text: str) -> list[str]:
    low = (text or "").lower()
    return [t for t in TRIPWIRE_TERMS if t in low]


def table_exists(conn, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def columns(conn, table: str) -> list[str]:
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]


def warm_strength(initial, lam, created_at, boosts_json, now) -> float:
    try:
        boosts = json.loads(boosts_json or "[]")
    except json.JSONDecodeError:
        boosts = []
    dt = max(0.0, now - created_at)
    s = initial * math.exp(-lam * dt)
    for b in boosts:
        bdt = max(0.0, now - b.get("timestamp", now))
        s += b.get("amount", 0.0) * math.exp(-lam * bdt)
    return s


def age_bin_warm(strength: float, initial: float) -> str:
    if strength <= NEAR_APOPTOSIS_FACTOR * EPSILON:
        return "near-apoptosis"
    if strength > 0.5 * initial:
        return "fresh"
    return "mid"


def main() -> int:
    here = Path(__file__).resolve().parent
    snap_arg = sys.argv[1] if len(sys.argv) > 1 else None
    if snap_arg is None:
        snaps = sorted((here / "snapshots").glob("*/manifest.sha256"))
        if not snaps:
            print("FAILED: no snapshot with a manifest under snapshots/", file=sys.stderr)
            return 2
        snap = snaps[-1].parent
    else:
        snap = Path(snap_arg)
    db = snap / "twin.db" if snap.is_dir() else snap
    if not db.exists():
        print(f"FAILED: no twin.db at {db}", file=sys.stderr)
        return 2

    live = Path(os.environ.get(
        "HARLO_DATA_DIR", str(Path.home() / "Library/Application Support/Harlo")
    )) / "twin.db"
    try:
        if db.resolve() == live.resolve():
            print("FAILED: refusing to inventory the LIVE twin.db", file=sys.stderr)
            return 2
    except OSError:
        pass

    now = db.stat().st_mtime  # frozen-universe clock
    snapshot_id = snap.name if snap.is_dir() else snap.parent.name

    with tempfile.TemporaryDirectory(prefix="inventory_") as tmp:
        tmp_db = Path(tmp) / "twin.db"
        shutil.copy2(db, tmp_db)
        for side in ("twin.db-wal", "twin.db-shm"):
            s = db.parent / side
            if s.exists():
                shutil.copy2(s, Path(tmp) / side)
        conn = sqlite3.connect(str(tmp_db))
        result = inventory(conn, now, snapshot_id)
        conn.close()

    out = here / "probe_candidates.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    # ---- console summary ------------------------------------------------
    s = result["summary"]
    print(f"\nSnapshot: {snapshot_id}   now(frozen)={int(now)}")
    print(f"Store: hot_traces={s['store']['hot_traces']} "
          f"warm_traces={s['store']['warm_traces']} "
          f"reflexes_total={s['store']['reflexes_total']} "
          f"reflexes_verified={s['store']['reflexes_verified']} "
          f"elenchus_pending={s['store']['elenchus_pending']} "
          f"elenchus_verified={s['store']['elenchus_verified']}")
    print(f"VERIFIED probe-eligible traces (pre-screen): {s['verified_eligible']}")
    print(f"Trip-wire screened out: {s['screened_out']}")
    print(f"Surviving probe pool: {s['pool']}")
    print("\ntier × age_bin:")
    grid = s["grid"]
    bins = ["fresh", "mid", "near-apoptosis"]
    print(f"  {'tier':<6} " + " ".join(f"{b:>14}" for b in bins))
    for tier in ("Hot", "Warm"):
        print(f"  {tier:<6} " + " ".join(f"{grid[tier][b]:>14}" for b in bins))
    if result["kill"]["fired"]:
        print(f"\n*** KILL CONDITION FIRED: pool {s['pool']} < {KILL_FLOOR} ***")
        print(f"    {result['kill']['reason']}")
    return 0


def inventory(conn, now: float, snapshot_id: str) -> dict:
    # Full schema dump — makes the conclusion self-documenting.
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    schema = {}
    for t in tables:
        try:
            n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        except sqlite3.OperationalError:
            n = None
        schema[t] = {"rows": n, "columns": columns(conn, t)}

    # VERIFIED sources.
    reflexes_total = reflexes_verified = 0
    if table_exists(conn, "reflexes"):
        reflexes_total = conn.execute("SELECT COUNT(*) FROM reflexes").fetchone()[0]
        reflexes_verified = conn.execute(
            "SELECT COUNT(*) FROM reflexes WHERE verification_state='verified'").fetchone()[0]

    verified_source_trace_ids: set[str] = set()
    elenchus_pending = elenchus_verified = 0
    if table_exists(conn, "elenchus_pending"):
        elenchus_pending = conn.execute(
            "SELECT COUNT(*) FROM elenchus_pending WHERE status='pending'").fetchone()[0]
        rows = conn.execute(
            "SELECT source_traces FROM elenchus_pending WHERE status='verified'").fetchall()
        elenchus_verified = len(rows)
        for (src,) in rows:
            try:
                for tid in json.loads(src or "[]"):
                    verified_source_trace_ids.add(str(tid))
            except json.JSONDecodeError:
                pass

    # Hot + Warm trace inventories (documentation + candidate resolution).
    hot = {}
    if table_exists(conn, "hot_traces"):
        for tid, msg, ts in conn.execute(
                "SELECT trace_id, message, timestamp FROM hot_traces"):
            hot[str(tid)] = {"text": msg, "tier": "Hot", "stored_at": ts}
    warm = {}
    if table_exists(conn, "traces"):
        for tid, msg, init, lam, created, boosts in conn.execute(
                "SELECT id, message, initial_strength, decay_lambda, "
                "created_at, boosts_json FROM traces"):
            strength = warm_strength(init, lam, created, boosts, now)
            warm[str(tid)] = {
                "text": msg, "tier": "Warm", "stored_at": created,
                "strength": round(strength, 6),
                "age_bin": age_bin_warm(strength, init),
            }

    # Probe pool = verified-linked Hot/Warm traces, trip-wire screened.
    eligible = []
    for tid in sorted(verified_source_trace_ids):
        rec = warm.get(tid) or hot.get(tid)
        if rec is None:
            continue  # verified claim cites a trace not present in this snapshot
        eligible.append((tid, rec))

    pool = []
    screened_out = 0
    for tid, rec in eligible:
        if screen(rec["text"]):
            screened_out += 1
            continue
        pool.append({
            "trace_id": tid,
            "text": rec["text"],
            "tier": rec["tier"],
            "age_bin": rec.get("age_bin", "fresh"),  # Hot defaults fresh
            "strength": rec.get("strength"),
            "stored_at": rec["stored_at"],
        })

    grid = {"Hot": {"fresh": 0, "mid": 0, "near-apoptosis": 0},
            "Warm": {"fresh": 0, "mid": 0, "near-apoptosis": 0}}
    for p in pool:
        grid[p["tier"]][p["age_bin"]] += 1

    fired = len(pool) < KILL_FLOOR
    if fired:
        if not verified_source_trace_ids and reflexes_verified == 0:
            reason = ("No Elenchus-verified material in the snapshot: "
                      f"reflexes_verified={reflexes_verified}, "
                      f"elenchus_verified={elenchus_verified}, "
                      "elenchus_pending table "
                      + ("present" if table_exists(conn, "elenchus_pending") else "ABSENT")
                      + ". hot_traces/warm traces carry no verification column, "
                      "so no probe-eligible VERIFIED trace can exist.")
        else:
            reason = (f"Verified-linked, trip-wire-clean pool ({len(pool)}) "
                      f"is below the floor ({KILL_FLOOR}).")

    return {
        "snapshot_id": snapshot_id,
        "now_frozen": int(now),
        "definition": "Hot/Warm trace whose trace_id is in source_traces of a VERIFIED elenchus_pending claim",
        "tier_criterion": "table residency: hot_traces=Hot, traces=Warm",
        "epsilon": EPSILON,
        "kill_floor": KILL_FLOOR,
        "schema": schema,
        "pool": pool,
        "kill": {"fired": fired, "reason": reason if fired else None},
        "summary": {
            "store": {
                "hot_traces": len(hot),
                "warm_traces": len(warm),
                "reflexes_total": reflexes_total,
                "reflexes_verified": reflexes_verified,
                "elenchus_pending": elenchus_pending,
                "elenchus_verified": elenchus_verified,
            },
            "verified_eligible": len(eligible),
            "screened_out": screened_out,
            "pool": len(pool),
            "grid": grid,
        },
    }


if __name__ == "__main__":
    raise SystemExit(main())
