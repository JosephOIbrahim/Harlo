"""Federated recall — merges Hot (FTS5) and Warm (SDR Hamming) results.

Executes two simultaneous queries:
1. FTS5 plaintext search on Hot Tier (zero-latency, un-encoded)
2. SDR Hamming search on Warm Tier (semantic, encoded)

Merges results by normalized relevance score and deduplicates.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Maximum Hamming distance for SDR (2048-bit)
MAX_HAMMING = 2048.0


@dataclass
class RecallResult:
    """A single recall result from either tier."""

    trace_id: str
    message: str
    score: float  # Normalized relevance [0.0, 1.0]
    tier: str  # "hot" or "warm"
    domain: str
    tags: list[str]


def query_past_experience(
    db_path: str,
    query: str,
    limit: int = 10,
) -> list[RecallResult]:
    """Federated recall across Hot and Warm tiers.

    Args:
        db_path: Path to SQLite database.
        query: Search query text.
        limit: Maximum total results to return.

    Returns:
        Merged, deduplicated, ranked list of RecallResults.
    """
    hot_results = _query_hot(db_path, query, limit=limit)
    warm_results = _query_warm(db_path, query, limit=limit)

    return _merge_results(hot_results, warm_results, limit=limit)


def _query_hot(db_path: str, query: str, limit: int = 10) -> list[RecallResult]:
    """FTS5 search on Hot Tier.

    Args:
        db_path: Path to SQLite database.
        query: Search query text.
        limit: Maximum results.

    Returns:
        List of RecallResults from hot tier.
    """
    if not Path(db_path).exists():
        return []

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(
            "SELECT h.trace_id, h.message, h.tags, h.domain, rank "
            "FROM hot_traces h "
            "JOIN hot_traces_fts f ON h.rowid = f.rowid "
            "WHERE hot_traces_fts MATCH ? "
            "ORDER BY rank "
            "LIMIT ?",
            (query, limit),
        )
        results = []
        for row in cursor.fetchall():
            # FTS5 rank is negative (lower = better). Normalize to [0, 1].
            raw_rank = abs(row[4]) if row[4] else 0.0
            score = 1.0 / (1.0 + raw_rank)  # Sigmoid-like normalization

            results.append(RecallResult(
                trace_id=row[0],
                message=row[1],
                score=score,
                tier="hot",
                domain=row[3],
                tags=json.loads(row[2]) if row[2] else [],
            ))
        return results
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


def _query_warm(db_path: str, query: str, limit: int = 10) -> list[RecallResult]:
    """SDR Hamming search on Warm Tier.

    Args:
        db_path: Path to SQLite database.
        query: Search query text.
        limit: Maximum results.

    Returns:
        List of RecallResults from warm tier.
    """
    if not Path(db_path).exists():
        return []

    try:
        from harlo.encoder import semantic_recall
        result = semantic_recall(db_path, query, depth="normal")
        traces = result.get("traces", [])

        results = []
        for t in traces[:limit]:
            dist = t.get("distance", MAX_HAMMING)
            score = 1.0 - (dist / MAX_HAMMING)

            results.append(RecallResult(
                trace_id=t["trace_id"],
                message=t["message"],
                score=score,
                tier="warm",
                domain=t.get("domain", ""),
                tags=t.get("tags", []),
            ))
        return results
    except Exception:
        return []


def _merge_results(
    hot: list[RecallResult],
    warm: list[RecallResult],
    limit: int = 10,
) -> list[RecallResult]:
    """Merge and deduplicate results from both tiers.

    Deduplication by trace_id (hot tier wins on conflict).
    Ranked by score descending.

    Args:
        hot: Results from hot tier.
        warm: Results from warm tier.
        limit: Maximum results to return.

    Returns:
        Merged, ranked list.
    """
    seen: dict[str, RecallResult] = {}

    # Hot tier has priority (more recent)
    for r in hot:
        seen[r.trace_id] = r

    # Warm tier fills gaps
    for r in warm:
        if r.trace_id not in seen:
            seen[r.trace_id] = r

    merged = sorted(seen.values(), key=lambda r: r.score, reverse=True)
    return merged[:limit]
