"""Hot Tier (L1) trace store — SQLite + FTS5, zero-encoding.

Provides immediate persistence without model loading or SDR encoding.
Traces are stored as plaintext with full-text search indexing.
Promotion to Warm Tier (L2) happens asynchronously via the Observer.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from harlo.hot_store.schema import ensure_schema


@dataclass
class HotTrace:
    """A trace in the Hot Tier (L1, zero-encoding)."""

    trace_id: str
    message: str
    tags: list[str]
    domain: str
    timestamp: float
    encoded: bool


class HotStore:
    """SQLite + FTS5 Hot Tier for zero-latency trace storage.

    Provides immediate persistence without model loading or SDR encoding.
    Traces are stored as plaintext with full-text search indexing.
    Uses a persistent connection with WAL journal mode for
    sub-millisecond write latency.
    """

    def __init__(self, db_path: str) -> None:
        """Initialize HotStore with database path.

        Args:
            db_path: Path to SQLite database file.
        """
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = self._open(db_path)
        ensure_schema(self._conn)

    @staticmethod
    def _open(db_path: str) -> sqlite3.Connection:
        """Open a connection with WAL mode and optimized pragmas."""
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def store(
        self,
        message: str,
        tags: Optional[list[str]] = None,
        domain: str = "general",
        trace_id: Optional[str] = None,
        timestamp: Optional[float] = None,
    ) -> str:
        """Store a trace in the Hot Tier.

        Args:
            message: Trace content text.
            tags: Optional list of tag strings.
            domain: Knowledge domain (default: "general").
            trace_id: Optional explicit ID (generated UUID4 if None).
            timestamp: Optional explicit timestamp (time.time() if None).

        Returns:
            The trace_id of the stored trace.

        Raises:
            sqlite3.IntegrityError: If trace_id already exists.
        """
        if trace_id is None:
            trace_id = uuid.uuid4().hex[:16]
        if timestamp is None:
            timestamp = time.time()

        tags_json = json.dumps(tags or [])

        self._conn.execute(
            "INSERT INTO hot_traces (trace_id, message, tags, domain, timestamp, encoded) "
            "VALUES (?, ?, ?, ?, ?, 0)",
            (trace_id, message, tags_json, domain, timestamp),
        )
        self._conn.commit()

        return trace_id

    def search(self, query: str, limit: int = 10) -> list[HotTrace]:
        """Full-text search over Hot Tier traces.

        Uses FTS5 MATCH syntax. Returns results ranked by BM25 relevance.

        Args:
            query: Search query string (FTS5 syntax).
            limit: Maximum results to return.

        Returns:
            List of matching HotTrace objects, ranked by relevance.
        """
        cursor = self._conn.execute(
            "SELECT h.trace_id, h.message, h.tags, h.domain, h.timestamp, h.encoded "
            "FROM hot_traces h "
            "JOIN hot_traces_fts f ON h.rowid = f.rowid "
            "WHERE hot_traces_fts MATCH ? "
            "ORDER BY rank "
            "LIMIT ?",
            (query, limit),
        )
        return [self._row_to_trace(row) for row in cursor.fetchall()]

    def get(self, trace_id: str) -> Optional[HotTrace]:
        """Retrieve a single trace by ID.

        Args:
            trace_id: The trace ID to look up.

        Returns:
            HotTrace if found, None otherwise.
        """
        cursor = self._conn.execute(
            "SELECT trace_id, message, tags, domain, timestamp, encoded "
            "FROM hot_traces WHERE trace_id = ?",
            (trace_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_trace(row)

    def get_pending(self, limit: int = 100) -> list[HotTrace]:
        """Retrieve traces pending SDR encoding (encoded=FALSE).

        Args:
            limit: Maximum traces to return.

        Returns:
            List of un-encoded HotTrace objects, oldest first.
        """
        cursor = self._conn.execute(
            "SELECT trace_id, message, tags, domain, timestamp, encoded "
            "FROM hot_traces WHERE encoded = 0 "
            "ORDER BY timestamp ASC LIMIT ?",
            (limit,),
        )
        return [self._row_to_trace(row) for row in cursor.fetchall()]

    def mark_encoded(self, trace_ids: list[str]) -> int:
        """Mark traces as promoted to Warm Tier.

        Args:
            trace_ids: List of trace IDs to mark as encoded.

        Returns:
            Number of traces actually updated.
        """
        if not trace_ids:
            return 0

        placeholders = ",".join("?" for _ in trace_ids)
        cursor = self._conn.execute(
            f"UPDATE hot_traces SET encoded = 1 WHERE trace_id IN ({placeholders})",
            trace_ids,
        )
        self._conn.commit()
        return cursor.rowcount

    @staticmethod
    def _row_to_trace(row: tuple) -> HotTrace:
        """Convert a database row to a HotTrace dataclass."""
        return HotTrace(
            trace_id=row[0],
            message=row[1],
            tags=json.loads(row[2]),
            domain=row[3],
            timestamp=row[4],
            encoded=bool(row[5]),
        )
