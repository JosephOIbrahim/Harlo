#!/usr/bin/env python3
"""Seed the Cognitive Twin demo database with realistic warm-up data.

Idempotent: all IDs use the 'seed_' prefix and duplicate inserts are
caught via IntegrityError or INSERT OR IGNORE.

Usage:
    python scripts/seed_demo.py
"""

from __future__ import annotations

import json
import sqlite3
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Project imports
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "python"))

from cognitive_twin.hot_store import HotStore  # noqa: E402
from cognitive_twin.injection import InjectionStore  # noqa: E402
from cognitive_twin.elenchus_v8 import ElenchusQueue  # noqa: E402
from cognitive_twin.trust import TrustLedger  # noqa: E402

DB_PATH = str(_PROJECT_ROOT / "data" / "twin.db")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_DAY = 86400
_NOW = int(time.time())


def _ts(days_ago: int) -> int:
    """Return a unix timestamp *days_ago* days in the past."""
    return _NOW - days_ago * _DAY


def _history(pairs: list[tuple[str, str]]) -> str:
    """Build a history_json string from (user, assistant) pairs."""
    msgs: list[dict] = []
    for user_msg, assistant_msg in pairs:
        msgs.append({"role": "user", "content": user_msg})
        msgs.append({"role": "assistant", "content": assistant_msg})
    return json.dumps(msgs)


# ---------------------------------------------------------------------------
# Step 1: Close stale sessions
# ---------------------------------------------------------------------------
def step_1_close_stale_sessions() -> None:
    """Close any open sessions so the demo starts clean."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("UPDATE sessions SET closed = 1 WHERE closed = 0")
    conn.commit()
    count = cursor.rowcount
    conn.close()
    print(f"  Step 1: Closed {count} stale session(s).")


# ---------------------------------------------------------------------------
# Step 2: Create 6 realistic sessions
# ---------------------------------------------------------------------------
_SESSIONS = [
    {
        "session_id": "seed_sess_01",
        "domain": "technical",
        "exchange_count": 8,
        "allostatic_tokens": 2400,
        "closed": 1,
        "started_at": _ts(13),
        "last_active": _ts(13) + 3600,
        "encoder_type": "semantic",
        "history_json": _history([
            ("How does the USD-lite LIVRPS container work?",
             "LIVRPS stands for Layer-Identity-Value-Relationship-Provenance-Specialization. Each prim in the stage carries these six facets as a dataclass."),
            ("What's the hex SDR serialization about?",
             "Instead of storing 2048-int arrays (~6KB per trace), we compress to 512-char hex strings. Orders-of-magnitude improvement at scale."),
            ("How does the Merkle tree fit in?",
             "Composition stages use Merkle tree hashing for O(log n) partial-branch verification instead of full-file SHA256."),
            ("Can you explain the BrainStage __eq__ with math.isclose?",
             "Float round-trip through JSON can introduce tiny errors. math.isclose with a relative tolerance handles that gracefully."),
            ("What about the dual-mask fix for XOR?",
             "The old XOR toggle flipped already-set bits. The new approach uses (base | strengthen_mask) & ~weaken_mask for idempotent directional updates."),
            ("How does apoptosis work?",
             "twin consolidate physically DELETEs traces below epsilon and runs VACUUM. The database file size actually decreases."),
            ("What's the reconsolidation boost?",
             "User-facing retrieval gives a strength boost to contributing traces, preventing a death spiral where traces keep decaying to apoptosis."),
            ("Thanks, that's a great overview.",
             "Happy to help. These architectural decisions all serve the biological metaphor while keeping real performance constraints."),
        ]),
    },
    {
        "session_id": "seed_sess_02",
        "domain": "personal",
        "exchange_count": 5,
        "allostatic_tokens": 1200,
        "closed": 1,
        "started_at": _ts(11),
        "last_active": _ts(11) + 1800,
        "encoder_type": "semantic",
        "history_json": _history([
            ("I noticed I've been hyperfocusing on the Hebbian module for three days straight.",
             "That's a recognizable ADHD pattern — deep immersion followed by a crash. Have you scheduled any deliberate breaks?"),
            ("Not really. I just keep going until I hit a wall.",
             "The allostatic load data from your sessions shows a clear spike. Your last 5 sessions averaged 3000+ tokens."),
            ("Is that bad?",
             "Not inherently, but sustained high load without recovery correlates with lower quality output in the later sessions."),
            ("I should probably take a walk.",
             "Physical movement is one of the most effective resets. Even 15 minutes helps."),
            ("Okay, I'll try that. Thanks for the nudge.",
             "Anytime. I'll note this as a positive self-regulation moment."),
        ]),
    },
    {
        "session_id": "seed_sess_03",
        "domain": "technical",
        "exchange_count": 12,
        "allostatic_tokens": 4800,
        "closed": 1,
        "started_at": _ts(8),
        "last_active": _ts(8) + 7200,
        "encoder_type": "semantic",
        "history_json": _history([
            ("Let's work on the Elenchus v8 deferred verification.",
             "Sure. The key insight is that Observer queues claims locally and Actor verifies when connected. No local LLM needed."),
            ("How does the structural score work?",
             "It's a [0.0, 1.0] heuristic confidence from the Observer's local checks — pattern consistency, trace count, temporal coherence."),
            ("What happens when Actor resolves a claim?",
             "The claim status moves from 'pending' to 'verified' or 'rejected'. Verified claims can then be consolidated into reflexes."),
            ("And rejected ones?",
             "They're kept for audit but never consolidated. Rule 12: only VERIFIED resolutions become reflexes."),
            ("What about the 3-cycle GVR limit?",
             "Rule 13: after cycle 3, FIXABLE promotes to UNPROVABLE. The loop must terminate — it's an ADHD guard."),
            ("How does spec-gaming detection work?",
             "Rule 15: correct answer to wrong question is the dominant failure mode. The Bridge checks output answers the original intent."),
            ("Can you show me the queue_claim signature?",
             "queue_claim(claim_text, source_traces=None, structural_score=0.0, claim_id=None) -> str. Returns the claim_id."),
            ("What's the resolve signature?",
             "resolve(claim_id, verdict: bool) -> Optional[PendingClaim]. True = verified, False = rejected."),
            ("How many pending claims can we have?",
             "No hard limit in the schema, but the Actor should process them in batches. get_pending(limit=10) returns oldest first."),
            ("What about burst mode?",
             "Rule 17: burst defers, not skips. Queue unverified outputs during burst. Run GVR on burst exit."),
            ("This is solid. The deferred model is elegant.",
             "It lets us rent cloud LLM compute for verification while keeping sovereign local state."),
            ("Let's move on to the trust ledger next session.",
             "Sounds good. The trust score drives Basal Ganglia behavior gating — it'll connect well to what we just covered."),
        ]),
    },
    {
        "session_id": "seed_sess_04",
        "domain": "general",
        "exchange_count": 3,
        "allostatic_tokens": 600,
        "closed": 1,
        "started_at": _ts(5),
        "last_active": _ts(5) + 900,
        "encoder_type": "semantic",
        "history_json": _history([
            ("Quick question — what's the current trust tier?",
             "You're currently in the 'familiar' tier (0.3-0.7). This enables context and pattern surfacing."),
            ("What do I need for 'trusted'?",
             "The threshold is 0.7. Trust builds through consistent interaction, verified claims, and successful co-evolution cycles."),
            ("Got it, thanks.",
             "You're welcome. Trust is continuous, not stepped — even within the familiar tier, higher scores unlock more proactive behavior."),
        ]),
    },
    {
        "session_id": "seed_sess_05",
        "domain": "technical",
        "exchange_count": 15,
        "allostatic_tokens": 6000,
        "closed": 1,
        "started_at": _ts(3),
        "last_active": _ts(3) + 10800,
        "encoder_type": "semantic",
        "history_json": _history([
            ("Let's implement the Hebbian dual-mask system.",
             "The key change: replace XOR toggle with (base | strengthen_mask) & ~weaken_mask. Set/clear is idempotent."),
            ("Why does XOR fail?",
             "XOR flips bits. If a bit is already set and you XOR with a strengthen mask that includes it, it gets cleared instead of reinforced."),
            ("And the conflict resolution?",
             "weaken_mask wins. If a bit appears in both masks, it gets cleared. This prevents oscillation."),
            ("How do we test this?",
             "test_dual_masks.py covers: idempotent strengthen, idempotent weaken, conflict resolution, and round-trip stability."),
            ("What about Merkle isolation?",
             "Hebbian deltas go in the [V] Variant layer, not destructive SQLite mutation. This preserves the original trace."),
            ("How does reconstruction work?",
             "On retrieval, we overlay the variant layer onto the base. The reconstruction threshold must be >= apoptosis + 0.05."),
            ("What's the stability guarantee?",
             "Multiple strengthen/weaken cycles on the same trace must converge, not oscillate. The test runs 100 cycles."),
            ("How does this connect to training data?",
             "JSONL output includes cognitive_profile_features as a full float vector, not just a hash."),
            ("Where does the training data go?",
             "data/elenchus_training.jsonl — one line per verified claim with its supporting evidence and profile features."),
            ("What about the crystallization eviction?",
             "preservation_score = (obs/threshold) * depth_weight. Deep patterns survive over noise. Max 50 crystallized traces."),
            ("How does the incremental observer fit?",
             "Cursor-based processing: O(new_traces) instead of full scan. Cursor persisted in SQLite. Ghost window compliant."),
            ("What's the ghost window?",
             "A time window where recently created traces aren't yet visible to pattern detection — prevents premature crystallization."),
            ("This session is getting long. Allostatic load?",
             "You're at 6000 tokens. That's in the high zone. Consider wrapping up after the next exchange."),
            ("One more — what's the reconsolidation boost value?",
             "It's configurable but defaults to 0.1 strength units per user-facing retrieval. Gated to prevent self-bootstrapping."),
            ("Okay, I'll stop here. Good session.",
             "Agreed. You covered a lot of ground. The Hebbian system is in solid shape."),
        ]),
    },
    {
        "session_id": "seed_sess_06",
        "domain": "technical",
        "exchange_count": 6,
        "allostatic_tokens": 1800,
        "closed": 0,
        "started_at": _ts(0),
        "last_active": _NOW,
        "encoder_type": "semantic",
        "history_json": _history([
            ("Starting a new session to review the demo seed script.",
             "Good idea. The seed script should be idempotent and create realistic data across all major subsystems."),
            ("What tables need data?",
             "sessions, hot_traces, injection_traces, elenchus_pending, and trust_ledger. That covers the full stack."),
            ("Should we touch the traces table?",
             "No — that's the warm tier with SDR blobs. The seed script should only populate hot tier and metadata tables."),
            ("What about patterns?",
             "Also no. Patterns emerge from the Observer processing hot traces. The seed script just provides raw material."),
            ("How do we make it idempotent?",
             "Use deterministic IDs with a 'seed_' prefix. INSERT OR IGNORE for SQL, IntegrityError catch for store APIs."),
            ("Perfect. Let me write it up.",
             "Go for it. I'll verify the output once you're done."),
        ]),
    },
]


def step_2_create_sessions() -> None:
    """Insert 6 realistic demo sessions via raw SQL."""
    conn = sqlite3.connect(DB_PATH)
    # Ensure table exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            started_at INTEGER NOT NULL,
            last_active INTEGER NOT NULL,
            exchange_count INTEGER NOT NULL DEFAULT 0,
            domain TEXT NOT NULL DEFAULT 'general',
            encoder_type TEXT NOT NULL DEFAULT 'semantic',
            closed INTEGER NOT NULL DEFAULT 0,
            history_json TEXT NOT NULL DEFAULT '[]',
            allostatic_tokens INTEGER NOT NULL DEFAULT 0
        )
    """)
    inserted = 0
    for s in _SESSIONS:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO sessions "
                "(session_id, started_at, last_active, exchange_count, "
                "domain, encoder_type, closed, history_json, allostatic_tokens) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    s["session_id"],
                    s["started_at"],
                    s["last_active"],
                    s["exchange_count"],
                    s["domain"],
                    s["encoder_type"],
                    s["closed"],
                    s["history_json"],
                    s["allostatic_tokens"],
                ),
            )
            if conn.execute(
                "SELECT changes()"
            ).fetchone()[0] > 0:
                inserted += 1
        except sqlite3.Error as exc:
            print(f"    WARN: session {s['session_id']}: {exc}")
    conn.commit()
    conn.close()
    print(f"  Step 2: Inserted {inserted} session(s) (6 attempted, duplicates ignored).")


# ---------------------------------------------------------------------------
# Step 3: Create 6 injection traces
# ---------------------------------------------------------------------------
_INJECTIONS = [
    dict(trace_id="seed_inj_01", profile="microdose", s_nm=0.005, alpha=0.3,
         exchange_count=2, transition="activated", session_id="seed_sess_02"),
    dict(trace_id="seed_inj_02", profile="microdose", s_nm=0.005, alpha=0.0,
         exchange_count=5, transition="deactivated", session_id="seed_sess_02"),
    dict(trace_id="seed_inj_03", profile="perceptual", s_nm=0.015, alpha=0.7,
         exchange_count=3, transition="activated", session_id="seed_sess_03"),
    dict(trace_id="seed_inj_04", profile="perceptual", s_nm=0.015, alpha=0.0,
         exchange_count=12, transition="deactivated", session_id="seed_sess_03"),
    dict(trace_id="seed_inj_05", profile="microdose", s_nm=0.008, alpha=0.5,
         exchange_count=4, transition="activated", session_id="seed_sess_05"),
    dict(trace_id="seed_inj_06", profile="microdose", s_nm=0.008, alpha=0.0,
         exchange_count=15, transition="deactivated", session_id="seed_sess_05"),
]


def step_3_create_injections() -> None:
    """Insert 6 injection traces via InjectionStore.store()."""
    store = InjectionStore(DB_PATH)
    inserted = 0
    for inj in _INJECTIONS:
        try:
            store.store(**inj)
            inserted += 1
        except sqlite3.IntegrityError:
            pass  # Already exists — idempotent
    # Close persistent connection to avoid WAL lock in subsequent steps
    store._conn.close()
    print(f"  Step 3: Inserted {inserted} injection trace(s) (6 attempted, duplicates ignored).")


# ---------------------------------------------------------------------------
# Step 4: Queue 3 Elenchus claims
# ---------------------------------------------------------------------------
_CLAIMS = [
    dict(
        claim_id="seed_claim_01",
        claim_text=(
            "User shows a recurring pattern of deep technical sessions "
            "followed by personal reflection sessions, suggesting "
            "deliberate cognitive cycling."
        ),
        source_traces=["seed_hot_01", "seed_hot_02"],
        structural_score=0.65,
    ),
    dict(
        claim_id="seed_claim_02",
        claim_text=(
            "Allostatic load across recent sessions is trending upward "
            "\u2014 5 of last 6 sessions exceeded 1500 tokens."
        ),
        source_traces=["seed_hot_03", "seed_hot_05"],
        structural_score=0.78,
    ),
    dict(
        claim_id="seed_claim_03",
        claim_text=(
            "User's injection profile preference is shifting from "
            "perceptual to microdose."
        ),
        source_traces=["seed_inj_01", "seed_inj_03", "seed_inj_05"],
        structural_score=0.42,
    ),
]


def step_4_queue_claims() -> None:
    """Queue 3 Elenchus claims via ElenchusQueue.queue_claim()."""
    queue = ElenchusQueue(DB_PATH)
    inserted = 0
    for claim in _CLAIMS:
        try:
            queue.queue_claim(**claim)
            inserted += 1
        except sqlite3.IntegrityError:
            pass  # Already exists — idempotent
    print(f"  Step 4: Queued {inserted} claim(s) (3 attempted, duplicates ignored).")


# ---------------------------------------------------------------------------
# Step 5: Seed trust to 0.45
# ---------------------------------------------------------------------------
def step_5_seed_trust() -> None:
    """Bring trust score up to 0.45 if below 0.40."""
    tl = TrustLedger(DB_PATH)
    current = tl.get_score()
    if current < 0.40:
        new_score = tl.update(0.45 - current)
        print(f"  Step 5: Trust score updated from {current:.2f} to {new_score:.2f}.")
    else:
        print(f"  Step 5: Trust score already {current:.2f} (>= 0.40), no change.")


# ---------------------------------------------------------------------------
# Step 6: Add 5 hot traces
# ---------------------------------------------------------------------------
_HOT_TRACES = [
    dict(
        trace_id="seed_hot_01",
        message=(
            "The USD-lite LIVRPS container design is solid. Six facets per prim "
            "(Layer-Identity-Value-Relationship-Provenance-Specialization) give "
            "us a clean dataclass structure with hex SDR serialization for "
            "compact storage."
        ),
        tags=["architecture", "usd-lite", "v7"],
        domain="technical",
    ),
    dict(
        trace_id="seed_hot_02",
        message=(
            "I've been noticing my ADHD hyperfocus pattern again — three days "
            "deep in the Hebbian module without breaks. The allostatic load "
            "numbers confirm it. Need to build in deliberate recovery."
        ),
        tags=["self-reflection", "adhd", "workflow"],
        domain="personal",
    ),
    dict(
        trace_id="seed_hot_03",
        message=(
            "Elenchus v8 deferred verification is working well. Observer queues "
            "claims locally, Actor resolves when connected. No local LLM needed "
            "— we rent cloud compute for verification while keeping sovereign "
            "local state."
        ),
        tags=["elenchus", "verification", "v8"],
        domain="technical",
    ),
    dict(
        trace_id="seed_hot_04",
        message=(
            "The Hebbian dual-mask fix solved the XOR flaw. Using "
            "(base | strengthen_mask) & ~weaken_mask is idempotent and "
            "directionally correct. Conflict resolution: weaken_mask wins. "
            "100-cycle stability test passes."
        ),
        tags=["hebbian", "neuroplasticity", "bugfix"],
        domain="technical",
    ),
    dict(
        trace_id="seed_hot_05",
        message=(
            "Trust score is approaching the familiar tier threshold (0.3). "
            "Consistent interaction and verified claims are building the "
            "co-evolution relationship. Next milestone: proactive coaching "
            "at 0.7."
        ),
        tags=["trust", "co-evolution", "milestone"],
        domain="general",
    ),
]


def step_6_add_hot_traces() -> None:
    """Insert 5 hot traces via HotStore.store()."""
    hs = HotStore(DB_PATH)
    inserted = 0
    for trace in _HOT_TRACES:
        try:
            hs.store(**trace)
            inserted += 1
        except sqlite3.IntegrityError:
            pass  # Already exists — idempotent
    # Close persistent connection so later steps don't hit WAL lock
    hs._conn.close()
    print(f"  Step 6: Inserted {inserted} hot trace(s) (5 attempted, duplicates ignored).")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
def print_summary() -> None:
    """Query each table and print row counts."""
    conn = sqlite3.connect(DB_PATH)
    tables = [
        ("sessions", "SELECT COUNT(*) FROM sessions"),
        ("hot_traces", "SELECT COUNT(*) FROM hot_traces"),
        ("injection_traces", "SELECT COUNT(*) FROM injection_traces"),
        ("elenchus_pending", "SELECT COUNT(*) FROM elenchus_pending"),
        ("trust_ledger", "SELECT COUNT(*) FROM trust_ledger"),
    ]
    print("\n  Summary:")
    for name, sql in tables:
        try:
            count = conn.execute(sql).fetchone()[0]
            print(f"    {name}: {count} rows")
        except sqlite3.OperationalError:
            print(f"    {name}: table not found")
    conn.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    """Run all 6 seed steps and print a summary."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    print(f"Seeding demo database: {DB_PATH}")
    print()

    step_1_close_stale_sessions()
    step_2_create_sessions()
    step_3_create_injections()
    step_4_queue_claims()
    step_5_seed_trust()
    step_6_add_hot_traces()
    print_summary()

    print("\nDone. Database is warm.")


if __name__ == "__main__":
    main()
