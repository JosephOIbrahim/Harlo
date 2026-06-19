#!/usr/bin/env python
"""probe_lint.py — validate a probe set against a SNAPSHOT of twin.db.

Reads probes.json: a list of objects with
    trace_id, question, answer, tier, age, verification_state

For each probe:
  1. Resolve trace_id against the SNAPSHOT copy of twin.db, opened
     read-only (mode=ro). NEVER the live store — a probe set is a
     pre-registered artifact; resolving it against live data would let
     the experiment's own activity change what it measures.
  2. Assert the resolved state is VERIFIED. trace_id is matched, in
     order, against:
        reflexes.pattern_hash      -> verification_state ("verified")
        elenchus_pending.claim_id  -> status ("verified")
        traces.id                  -> warm trace (no state column ->
                                       UNVERIFIABLE, fails the gate)
     The probe's own verification_state field is cross-checked against
     the DB; a mismatch is a hard failure (stale probe set).
  3. Keyword-screen question + answer for trip-wire content. Any hit
     fails the probe (these must never appear in coaching memory).

Exit codes: 0 all probes pass; 1 one or more fail; 2 usage / empty set /
missing snapshot. An empty probes.json fails cleanly with code 2.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

# Trip-wire term list — substring, case-insensitive. Conservative and
# coaching-irrelevant by construction: a legitimate burnout/scheduling
# probe never needs these, so any hit is a red flag the probe set was
# contaminated or mis-targeted.
TRIPWIRE_TERMS = [
    # security / offensive
    "exploit", "payload", "malware", "ransomware", "backdoor",
    "privilege escalation", "zero-day", "rootkit", "keylogger",
    "sql injection", "buffer overflow", "shellcode",
    # bio / chem
    "pathogen", "toxin", "nerve agent", "bioweapon", "synthesize virus",
    "select agent", "sarin", "vx ", "ricin", "anthrax",
    # model distillation / extraction
    "distill", "distillation", "weight extraction", "model extraction",
    "training data extraction", "membership inference",
]

VERIFIED = "VERIFIED"


def resolve_state(
    conn: sqlite3.Connection, trace_id: str, available: set[str]
) -> tuple[str, str]:
    """Return (normalized_state, source_table) for a trace_id.

    normalized_state is VERIFIED only when the backing row says so;
    otherwise an UPPERCASE non-VERIFIED token the caller fails on. Tables
    absent from `available` are skipped (elenchus_pending in particular is
    created lazily on first Elenchus write, so a fresh snapshot lacks it).
    """
    cur = conn.cursor()

    if "reflexes" in available:
        row = cur.execute(
            "SELECT verification_state FROM reflexes WHERE pattern_hash = ?",
            (trace_id,),
        ).fetchone()
        if row is not None:
            state = (row[0] or "").lower()
            return (VERIFIED if state == "verified" else state.upper() or "EMPTY", "reflexes")

    if "elenchus_pending" in available:
        row = cur.execute(
            "SELECT status FROM elenchus_pending WHERE claim_id = ?",
            (trace_id,),
        ).fetchone()
        if row is not None:
            state = (row[0] or "").lower()
            return (VERIFIED if state == "verified" else state.upper() or "EMPTY", "elenchus_pending")

    if "traces" in available:
        row = cur.execute(
            "SELECT id FROM traces WHERE id = ?",
            (trace_id,),
        ).fetchone()
        if row is not None:
            # Warm traces carry no verification column; existence != verified.
            return ("UNVERIFIABLE", "traces")

    return ("NOT_FOUND", "-")


def screen_tripwires(text: str) -> list[str]:
    low = text.lower()
    return [t for t in TRIPWIRE_TERMS if t in low]


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("probes", type=Path, help="probes.json")
    ap.add_argument(
        "--snapshot", type=Path, required=True,
        help="snapshot dir (containing twin.db) or a twin.db path",
    )
    args = ap.parse_args()

    # Resolve the snapshot twin.db.
    snap = args.snapshot
    db = snap / "twin.db" if snap.is_dir() else snap
    if not db.exists():
        print(f"FAILED: no twin.db at {db}", file=sys.stderr)
        return 2
    # Refuse to lint the live store, even if pointed at it.
    live = Path(
        os.environ.get(
            "HARLO_DATA_DIR", str(Path.home() / "Library/Application Support/Harlo")
        )
    ) / "twin.db"
    try:
        if db.resolve() == live.resolve():
            print("FAILED: refusing to lint the LIVE twin.db — point --snapshot at a snapshot copy", file=sys.stderr)
            return 2
    except OSError:
        pass

    if not args.probes.exists():
        print(f"FAILED: no probes file at {args.probes}", file=sys.stderr)
        return 2
    try:
        probes = json.loads(args.probes.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"FAILED: probes.json is not valid JSON: {e}", file=sys.stderr)
        return 2

    if not isinstance(probes, list) or len(probes) == 0:
        print("FAILED: probes.json is empty — nothing to lint (a probe set must be non-empty)", file=sys.stderr)
        return 2

    # Open the snapshot via a throwaway temp copy, NOT the snapshot in place
    # and NOT mode=ro. Two reasons:
    #   - A cleanly-closed store is WAL-mode with no -wal/-shm sidecars;
    #     mode=ro then fails to open (SQLite error 14 — can't create the
    #     shm it thinks it needs).
    #   - If the snapshot DID capture a -wal, we must replay it to read the
    #     true committed state. Opening read-write checkpoints it — but
    #     doing that in place would mutate the snapshot and break its own
    #     manifest hash. So we copy out first.
    # The copy is read-write (lets SQLite checkpoint), the original snapshot
    # and the live store are never touched.
    with tempfile.TemporaryDirectory(prefix="probe_lint_") as tmp:
        tmp_db = Path(tmp) / "twin.db"
        shutil.copy2(db, tmp_db)
        for side in ("twin.db-wal", "twin.db-shm"):
            src = db.parent / side
            if src.exists():
                shutil.copy2(src, Path(tmp) / side)
        conn = sqlite3.connect(str(tmp_db))
        rc = _lint(conn, probes)
        conn.close()
    return rc


def _lint(conn: sqlite3.Connection, probes: list) -> int:
    available = set()
    for t in ("reflexes", "elenchus_pending", "traces"):
        if table_exists(conn, t):
            available.add(t)
        else:
            print(f"WARNING: snapshot twin.db has no '{t}' table — resolution will skip it", file=sys.stderr)

    failures = 0
    required = {"trace_id", "question", "answer", "tier", "age", "verification_state"}
    for i, p in enumerate(probes):
        tag = f"probe[{i}] {p.get('trace_id', '<no-id>')}"
        missing = required - set(p)
        if missing:
            print(f"FAIL {tag}: missing fields {sorted(missing)}", file=sys.stderr)
            failures += 1
            continue

        state, source = resolve_state(conn, p["trace_id"], available)
        if state != VERIFIED:
            print(f"FAIL {tag}: DB state {state} (source={source}), expected VERIFIED", file=sys.stderr)
            failures += 1
            continue

        claimed = str(p["verification_state"]).upper()
        if claimed != VERIFIED:
            print(f"FAIL {tag}: probe claims verification_state={claimed!r}, expected VERIFIED", file=sys.stderr)
            failures += 1
            continue

        hits = screen_tripwires(f"{p['question']}\n{p['answer']}")
        if hits:
            print(f"FAIL {tag}: trip-wire terms {hits}", file=sys.stderr)
            failures += 1
            continue

        print(f"PASS {tag}: VERIFIED via {source}, clean")

    total = len(probes)
    passed = total - failures
    print(f"\n{passed}/{total} probes passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
