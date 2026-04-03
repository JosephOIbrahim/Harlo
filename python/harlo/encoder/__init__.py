"""Encoder module — lexical (Rust) and semantic (Python) encoding paths.

Both encoders produce 2048-bit SDR bitvectors (256 bytes).
Selection is controlled by config.ENCODER_TYPE:
  - "lexical"  (default): Rust n-gram hashing via hippocampus crate
  - "semantic": BGE sentence-transformer + LSH projection

The semantic path stores/recalls via Python-side SQLite since the Rust
hot path uses its own internal encoder. The SDR format is identical,
so hamming distance works across both.
"""

import math
import sqlite3
import time
from typing import Optional

from .semantic_encoder import SemanticEncoder, hamming_distance, sdr_sparsity

# Lazy singleton for the semantic encoder (model loading is expensive)
_semantic_encoder: Optional[SemanticEncoder] = None


def get_semantic_encoder() -> SemanticEncoder:
    """Get or create the singleton SemanticEncoder instance."""
    global _semantic_encoder
    if _semantic_encoder is None:
        _semantic_encoder = SemanticEncoder()
    return _semantic_encoder


def encode(text: str, encoder_type: str = "lexical") -> bytes:
    """Encode text to a 2048-bit SDR.

    Args:
        text: Input text.
        encoder_type: "lexical" or "semantic".

    Returns:
        256 bytes (2048 bits) SDR.
    """
    if encoder_type == "semantic":
        enc = get_semantic_encoder()
        return enc.encode(text)
    elif encoder_type == "lexical":
        from harlo import hippocampus
        # Rust encoder is internal to py_recall/py_store_trace;
        # no direct encode export. For lexical, callers should use
        # hippocampus.py_store_trace / py_recall directly.
        raise RuntimeError(
            "Lexical encoding is handled internally by the Rust hippocampus crate. "
            "Use hippocampus.py_store_trace() and hippocampus.py_recall() directly."
        )
    else:
        raise ValueError(f"Unknown encoder_type: {encoder_type!r}. Use 'lexical' or 'semantic'.")


def _ensure_db_schema(conn: sqlite3.Connection):
    """Ensure the traces table exists (same schema as Rust store.rs)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS traces (
            id TEXT PRIMARY KEY,
            message TEXT NOT NULL,
            sdr_blob BLOB NOT NULL,
            initial_strength REAL NOT NULL DEFAULT 1.0,
            decay_lambda REAL NOT NULL DEFAULT 0.05,
            created_at INTEGER NOT NULL,
            last_accessed INTEGER NOT NULL,
            boosts_json TEXT NOT NULL DEFAULT '[]',
            tags_json TEXT NOT NULL DEFAULT '[]',
            domain TEXT,
            source TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_traces_created ON traces(created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_traces_domain ON traces(domain)")


def semantic_store(
    db_path: str,
    trace_id: str,
    message: str,
    tags: Optional[list[str]] = None,
    domain: Optional[str] = None,
    source: Optional[str] = None,
):
    """Store a trace with semantic SDR encoding.

    Encodes the message using the semantic encoder and writes
    directly to SQLite (same schema as the Rust store).

    Args:
        db_path: Path to SQLite database.
        trace_id: Unique trace identifier.
        message: Text to encode and store.
        tags: Optional list of tags.
        domain: Optional domain string.
        source: Optional source string.
    """
    import json

    enc = get_semantic_encoder()
    sdr_blob = enc.encode(message)
    now = int(time.time())
    tags_json = json.dumps(tags or [])

    conn = sqlite3.connect(db_path)
    try:
        _ensure_db_schema(conn)
        conn.execute(
            """INSERT OR REPLACE INTO traces
               (id, message, sdr_blob, initial_strength, decay_lambda,
                created_at, last_accessed, boosts_json, tags_json, domain, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (trace_id, message, sdr_blob, 1.0, 0.05, now, now, "[]", tags_json, domain, source),
        )
        conn.commit()
    finally:
        conn.close()


def semantic_recall(
    db_path: str,
    query: str,
    depth: str = "normal",
) -> dict:
    """Recall traces using semantic SDR encoding.

    Encodes the query with the semantic encoder, loads all SDR blobs,
    computes hamming distances, applies lazy decay, and returns results.

    Args:
        db_path: Path to SQLite database.
        query: Query text.
        depth: "normal" (k=5) or "deep" (k=15).

    Returns:
        Dict with keys: context, traces, confidence.
    """
    import json

    k = 15 if depth == "deep" else 5

    enc = get_semantic_encoder()
    query_sdr = enc.encode(query)

    now = int(time.time())

    conn = sqlite3.connect(db_path)
    try:
        _ensure_db_schema(conn)

        # Load all SDR blobs
        cursor = conn.execute("SELECT id, sdr_blob FROM traces")
        candidates = cursor.fetchall()

        if not candidates:
            return {"context": "", "traces": [], "confidence": 0.0}

        # XOR search: compute hamming distance for each candidate
        distances = []
        for trace_id, sdr_blob in candidates:
            dist = hamming_distance(query_sdr, bytes(sdr_blob))
            distances.append((trace_id, dist))

        # Sort by distance ascending, take top k
        distances.sort(key=lambda x: x[1])
        top_k = distances[:k]

        # Load full traces and compute lazy decay
        hits = []
        for trace_id, dist in top_k:
            row = conn.execute(
                """SELECT id, message, initial_strength, decay_lambda,
                          created_at, boosts_json, tags_json, domain
                   FROM traces WHERE id = ?""",
                (trace_id,),
            ).fetchone()

            if row is None:
                continue

            tid, message, initial_strength, decay_lambda, created_at, boosts_json, tags_json, domain = row

            # Lazy decay (Rule 4)
            boosts = json.loads(boosts_json) if boosts_json else []
            strength = _compute_lazy_decay(initial_strength, decay_lambda, created_at, boosts, now)

            tags = json.loads(tags_json) if tags_json else []

            hits.append({
                "trace_id": tid,
                "message": message,
                "distance": dist,
                "strength": strength,
                "tags": tags,
                "domain": domain,
            })

        # Sort by strength descending
        hits.sort(key=lambda h: h["strength"], reverse=True)

        # Compute confidence
        confidence = _compute_confidence(hits, top_k)

        # Build context string
        context = _build_context(hits)

        return {"context": context, "traces": hits, "confidence": confidence}
    finally:
        conn.close()


def _compute_lazy_decay(
    initial: float,
    decay_lambda: float,
    created_at: int,
    boosts: list,
    now: int,
) -> float:
    """Compute trace strength with lazy exponential decay.

    strength = initial * e^(-lambda * dt) + sum(boost_amount * e^(-lambda * dt_boost))

    Rule 4: No polling. Pure math on retrieval.
    """
    dt = max(0, now - created_at)
    strength = initial * math.exp(-decay_lambda * dt)

    for boost in boosts:
        if isinstance(boost, dict):
            b_time = boost.get("timestamp", created_at)
            b_amount = boost.get("amount", 0.0)
        else:
            continue
        dt_boost = max(0, now - b_time)
        strength += b_amount * math.exp(-decay_lambda * dt_boost)

    return strength


def _compute_confidence(hits: list, search_results: list) -> float:
    """Compute confidence score from search results."""
    if not hits or not search_results:
        return 0.0

    best_distance = search_results[0][1]
    max_distance = 2048.0
    distance_score = 1.0 - min(best_distance / max_distance, 1.0)

    avg_strength = sum(h["strength"] for h in hits) / len(hits)
    strength_score = min(avg_strength, 1.0)

    hit_ratio = len(hits) / max(len(search_results), 1)

    return min(distance_score * 0.5 + strength_score * 0.3 + hit_ratio * 0.2, 1.0)


def _build_context(hits: list) -> str:
    """Build context string from trace hits."""
    if not hits:
        return ""

    lines = []
    for h in hits[:10]:
        domain_tag = f" [{h['domain']}]" if h.get("domain") else ""
        lines.append(f"- {h['message']}{domain_tag} (strength: {h['strength']:.3f})")

    return "\n".join(lines)
