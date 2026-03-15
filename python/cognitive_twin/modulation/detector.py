"""Pattern detection — semantic clustering over stored traces.

Detects recurring themes, temporal patterns, co-occurrences, and
escalation trends using SDR hamming distance from the semantic encoder.

Storage: SQLite patterns table in the shared twin.db database.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass, field
from typing import List, Optional

# ── Legacy pattern labels (kept for backward compat) ────────────────
_PATTERNS = {"adhd", "analytical", "creative", "depleted", "default"}

# ── Clustering constants ────────────────────────────────────────────
DEFAULT_SIMILARITY_THRESHOLD = 100  # Hamming distance < this = "similar"
MIN_CLUSTER_SIZE = 3                # Minimum traces to form a pattern
TEMPORAL_WINDOW_S = 86400           # 24 hours for temporal co-occurrence


@dataclass
class DetectedPattern:
    """A detected pattern in trace history."""

    pattern_id: str
    pattern_type: str          # "recurring_theme", "temporal", "co_occurrence", "escalation"
    description: str
    trace_ids: list[str]
    confidence: float
    detected_at: int
    topic_key: str = ""
    messages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to a plain dict."""
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type,
            "description": self.description,
            "trace_ids": self.trace_ids,
            "confidence": self.confidence,
            "detected_at": self.detected_at,
            "topic_key": self.topic_key,
            "evidence_count": len(self.trace_ids),
        }


def _ensure_patterns_table(conn: sqlite3.Connection) -> None:
    """Create the patterns table if it does not exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS patterns (
            pattern_id TEXT PRIMARY KEY,
            pattern_type TEXT NOT NULL,
            description TEXT NOT NULL,
            trace_ids_json TEXT NOT NULL DEFAULT '[]',
            messages_json TEXT NOT NULL DEFAULT '[]',
            confidence REAL NOT NULL DEFAULT 0.0,
            detected_at INTEGER NOT NULL,
            topic_key TEXT NOT NULL DEFAULT ''
        )
    """)


def _hamming_distance(a: bytes, b: bytes) -> int:
    """Compute hamming distance between two SDR byte arrays via XOR + popcount."""
    return sum(bin(ab ^ bb).count("1") for ab, bb in zip(a, b))


def _make_pattern_id(pattern_type: str, trace_ids: list[str]) -> str:
    """Generate a deterministic pattern ID from type and traces."""
    raw = f"{pattern_type}:{'|'.join(sorted(trace_ids))}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class PatternDetector:
    """Detects patterns in stored traces using SDR semantic similarity."""

    def __init__(self, db_path: str, threshold: int = DEFAULT_SIMILARITY_THRESHOLD) -> None:
        """Initialize the pattern detector.

        Args:
            db_path: Path to the SQLite database.
            threshold: Hamming distance threshold for similarity.
        """
        self._db_path = db_path
        self._threshold = threshold

    def _connect(self) -> sqlite3.Connection:
        """Open a database connection."""
        return sqlite3.connect(self._db_path)

    def detect_all(self, min_cluster_size: int = MIN_CLUSTER_SIZE) -> list[DetectedPattern]:
        """Run all pattern detection algorithms and return results.

        Args:
            min_cluster_size: Minimum traces to form a cluster.

        Returns:
            List of detected patterns, sorted by confidence descending.
        """
        conn = self._connect()
        try:
            _ensure_patterns_table(conn)
            traces = self._load_traces(conn)

            patterns: list[DetectedPattern] = []

            if len(traces) >= min_cluster_size:
                patterns.extend(self._detect_recurring_themes(traces, min_cluster_size))
                patterns.extend(self._detect_temporal_patterns(traces, min_cluster_size))

            # Escalation operates on sessions, not traces — always run it
            patterns.extend(self._detect_escalation(conn))

            # Persist detected patterns
            for p in patterns:
                self._store_pattern(conn, p)
            conn.commit()

            patterns.sort(key=lambda p: p.confidence, reverse=True)
            return patterns
        finally:
            conn.close()

    def _load_traces(self, conn: sqlite3.Connection) -> list[dict]:
        """Load all traces with their SDR blobs and metadata."""
        # Ensure the traces table exists (it may not if the DB is fresh)
        try:
            rows = conn.execute(
                """SELECT id, message, sdr_blob, created_at, tags_json, domain
                   FROM traces ORDER BY created_at"""
            ).fetchall()
        except sqlite3.OperationalError:
            return []

        return [
            {
                "id": r[0],
                "message": r[1],
                "sdr": bytes(r[2]) if r[2] else None,
                "created_at": r[3],
                "tags": r[4],
                "domain": r[5],
            }
            for r in rows
            if r[2] is not None  # Skip traces without SDR data
        ]

    def _detect_recurring_themes(
        self, traces: list[dict], min_size: int
    ) -> list[DetectedPattern]:
        """Find clusters of semantically similar traces.

        Uses single-linkage clustering: two traces in the same cluster
        if their hamming distance is below threshold. Clusters with
        min_size or more members become recurring theme patterns.
        """
        n = len(traces)
        if n < min_size:
            return []

        # Union-Find for clustering
        parent = list(range(n))

        def find(x: int) -> int:
            """Find root of x with path compression."""
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: int, b: int) -> None:
            """Merge clusters containing a and b."""
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        # Compare all pairs
        for i in range(n):
            for j in range(i + 1, n):
                sdr_i, sdr_j = traces[i]["sdr"], traces[j]["sdr"]
                if sdr_i and sdr_j and len(sdr_i) == len(sdr_j):
                    dist = _hamming_distance(sdr_i, sdr_j)
                    if dist < self._threshold:
                        union(i, j)

        # Group by cluster root
        clusters: dict[int, list[int]] = {}
        for i in range(n):
            root = find(i)
            clusters.setdefault(root, []).append(i)

        # Convert clusters to patterns
        now = int(time.time())
        patterns: list[DetectedPattern] = []

        for members in clusters.values():
            if len(members) < min_size:
                continue

            trace_ids = [traces[i]["id"] for i in members]
            messages = [traces[i]["message"] for i in members]
            confidence = min(len(members) / 10.0, 1.0)

            # Use the first message as a representative theme description
            theme_sample = messages[0][:80] if messages else "unknown"
            description = f"Recurring theme ({len(members)} traces): {theme_sample}"

            pattern = DetectedPattern(
                pattern_id=_make_pattern_id("recurring_theme", trace_ids),
                pattern_type="recurring_theme",
                description=description,
                trace_ids=trace_ids,
                confidence=confidence,
                detected_at=now,
                topic_key=f"pattern:{theme_sample[:50]}",
                messages=messages,
            )
            patterns.append(pattern)

        return patterns

    def _detect_temporal_patterns(
        self, traces: list[dict], min_size: int
    ) -> list[DetectedPattern]:
        """Find traces that are semantically similar AND temporally close.

        A temporal pattern is a semantic cluster where all traces occurred
        within TEMPORAL_WINDOW_S of each other.
        """
        n = len(traces)
        if n < min_size:
            return []

        now = int(time.time())
        patterns: list[DetectedPattern] = []

        # For each pair of similar traces, check temporal proximity
        temporal_groups: dict[str, list[int]] = {}

        for i in range(n):
            for j in range(i + 1, n):
                sdr_i, sdr_j = traces[i]["sdr"], traces[j]["sdr"]
                if not sdr_i or not sdr_j or len(sdr_i) != len(sdr_j):
                    continue
                dist = _hamming_distance(sdr_i, sdr_j)
                if dist >= self._threshold:
                    continue

                # Check temporal proximity
                dt = abs(traces[i]["created_at"] - traces[j]["created_at"])
                if dt > TEMPORAL_WINDOW_S:
                    continue

                # Group by the earlier trace's ID
                key = traces[min(i, j)]["id"]
                if key not in temporal_groups:
                    temporal_groups[key] = [min(i, j)]
                if max(i, j) not in temporal_groups[key]:
                    temporal_groups[key].append(max(i, j))

        for members in temporal_groups.values():
            if len(members) < min_size:
                continue

            trace_ids = [traces[i]["id"] for i in members]
            messages = [traces[i]["message"] for i in members]
            confidence = min(len(members) / 8.0, 1.0)

            description = f"Temporal cluster ({len(members)} traces within 24h)"
            pattern = DetectedPattern(
                pattern_id=_make_pattern_id("temporal", trace_ids),
                pattern_type="temporal",
                description=description,
                trace_ids=trace_ids,
                confidence=confidence,
                detected_at=now,
                topic_key=f"temporal:{trace_ids[0][:20]}",
                messages=messages,
            )
            patterns.append(pattern)

        return patterns

    def _detect_escalation(self, conn: sqlite3.Connection) -> list[DetectedPattern]:
        """Detect allostatic load escalation across sessions.

        Checks if recent sessions show increasing allostatic token counts.
        """
        try:
            rows = conn.execute(
                """SELECT session_id, allostatic_tokens, started_at
                   FROM sessions
                   WHERE closed = 1 AND allostatic_tokens > 0
                   ORDER BY started_at DESC
                   LIMIT 10"""
            ).fetchall()
        except sqlite3.OperationalError:
            return []

        if len(rows) < 3:
            return []

        # Check for upward trend (later sessions have more tokens)
        # Rows are newest-first, reverse for chronological order
        tokens = [r[1] for r in reversed(rows)]
        session_ids = [r[0] for r in reversed(rows)]

        # Simple trend: compare first half average to second half average
        mid = len(tokens) // 2
        first_half_avg = sum(tokens[:mid]) / max(mid, 1)
        second_half_avg = sum(tokens[mid:]) / max(len(tokens) - mid, 1)

        if first_half_avg == 0 or second_half_avg <= first_half_avg:
            return []

        ratio = second_half_avg / first_half_avg
        if ratio < 1.3:  # Need at least 30% increase
            return []

        now = int(time.time())
        confidence = min((ratio - 1.0), 1.0)

        return [DetectedPattern(
            pattern_id=_make_pattern_id("escalation", session_ids),
            pattern_type="escalation",
            description=(
                f"Allostatic load escalation: {ratio:.1f}x increase "
                f"across {len(tokens)} sessions"
            ),
            trace_ids=session_ids,
            confidence=confidence,
            detected_at=now,
            topic_key="escalation:allostatic_load",
        )]

    def _store_pattern(self, conn: sqlite3.Connection, pattern: DetectedPattern) -> None:
        """Persist a detected pattern to SQLite."""
        _ensure_patterns_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO patterns
               (pattern_id, pattern_type, description, trace_ids_json,
                messages_json, confidence, detected_at, topic_key)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                pattern.pattern_id,
                pattern.pattern_type,
                pattern.description,
                json.dumps(pattern.trace_ids),
                json.dumps(pattern.messages),
                pattern.confidence,
                pattern.detected_at,
                pattern.topic_key,
            ),
        )

    def get_stored_patterns(self) -> list[DetectedPattern]:
        """Load all persisted patterns from SQLite."""
        conn = self._connect()
        try:
            _ensure_patterns_table(conn)
            rows = conn.execute(
                """SELECT pattern_id, pattern_type, description, trace_ids_json,
                          messages_json, confidence, detected_at, topic_key
                   FROM patterns ORDER BY confidence DESC"""
            ).fetchall()
        finally:
            conn.close()

        return [
            DetectedPattern(
                pattern_id=r[0],
                pattern_type=r[1],
                description=r[2],
                trace_ids=json.loads(r[3]),
                confidence=r[5],
                detected_at=r[6],
                topic_key=r[7],
                messages=json.loads(r[4]),
            )
            for r in rows
        ]

    def clear_patterns(self) -> int:
        """Delete all stored patterns. Returns count deleted."""
        conn = self._connect()
        try:
            _ensure_patterns_table(conn)
            count = conn.execute("SELECT COUNT(*) FROM patterns").fetchone()[0]
            conn.execute("DELETE FROM patterns")
            conn.commit()
            return count
        finally:
            conn.close()


# ── Legacy API (backward compatible) ────────────────────────────────

def detect_pattern(messages: List[dict]) -> str:
    """Detect conversational pattern from message history.

    Legacy heuristic interface. For full pattern detection, use
    PatternDetector.detect_all() instead.

    Args:
        messages: List of message dicts with 'content' key.

    Returns:
        One of: "adhd", "analytical", "creative", "depleted", "default".
    """
    if not messages:
        return "default"

    def _msg_len(m):
        """Compute message length."""
        if isinstance(m, dict):
            return len(str(m.get("content", "")))
        return len(str(m))

    total_len = sum(_msg_len(m) for m in messages)
    count = len(messages)

    if count == 0:
        return "default"

    avg_len = total_len / count

    if avg_len < 20 and count > 5:
        return "adhd"

    if avg_len > 200:
        return "analytical"

    return "default"
