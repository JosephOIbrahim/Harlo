"""Aletheia v8 — deferred verification via Actor.

Observer queues unverified claims. Actor verifies when connected.
No local LLM required. "Renting cloud LLM compute to verify
sovereign local state."
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PendingClaim:
    """A claim awaiting Actor verification."""

    claim_id: str
    claim_text: str
    source_traces: list[str]
    structural_score: float
    timestamp: float
    status: str  # "pending", "verified", "rejected"


class AletheiaQueue:
    """Manages the pending verification queue.

    Observer evaluates structural/heuristic checks locally.
    Semantic claims that need LLM evaluation are queued here.
    Actor resolves them via resolve_verifications MCP tool.
    """

    def __init__(self, db_path: str) -> None:
        """Initialize Aletheia queue.

        Args:
            db_path: Path to SQLite database file.
        """
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS aletheia_pending (
                claim_id TEXT PRIMARY KEY,
                claim_text TEXT NOT NULL,
                source_traces TEXT NOT NULL DEFAULT '[]',
                structural_score REAL NOT NULL DEFAULT 0.0,
                timestamp REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
            )
        """)
        conn.commit()
        conn.close()

    def queue_claim(
        self,
        claim_text: str,
        source_traces: Optional[list[str]] = None,
        structural_score: float = 0.0,
        claim_id: Optional[str] = None,
    ) -> str:
        """Queue a claim for Actor verification.

        Args:
            claim_text: The claim to verify.
            source_traces: Trace IDs supporting this claim.
            structural_score: Observer's heuristic confidence [0.0, 1.0].
            claim_id: Optional explicit ID.

        Returns:
            The claim_id.
        """
        if claim_id is None:
            claim_id = uuid.uuid4().hex[:16]

        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(
                "INSERT INTO aletheia_pending "
                "(claim_id, claim_text, source_traces, structural_score, timestamp, status) "
                "VALUES (?, ?, ?, ?, ?, 'pending')",
                (
                    claim_id,
                    claim_text,
                    json.dumps(source_traces or []),
                    structural_score,
                    time.time(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

        return claim_id

    def get_pending(self, limit: int = 10) -> list[PendingClaim]:
        """Get pending claims for Actor verification.

        Args:
            limit: Maximum claims to return.

        Returns:
            List of PendingClaim objects, oldest first.
        """
        conn = sqlite3.connect(self._db_path)
        try:
            cursor = conn.execute(
                "SELECT claim_id, claim_text, source_traces, structural_score, timestamp, status "
                "FROM aletheia_pending WHERE status = 'pending' "
                "ORDER BY timestamp ASC LIMIT ?",
                (limit,),
            )
            return [self._row_to_claim(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def resolve(self, claim_id: str, verdict: bool) -> Optional[PendingClaim]:
        """Resolve a claim with Actor's verdict.

        Args:
            claim_id: The claim to resolve.
            verdict: True = verified, False = rejected.

        Returns:
            Updated PendingClaim, or None if not found.
        """
        new_status = "verified" if verdict else "rejected"

        conn = sqlite3.connect(self._db_path)
        try:
            cursor = conn.execute(
                "UPDATE aletheia_pending SET status = ? WHERE claim_id = ? AND status = 'pending'",
                (new_status, claim_id),
            )
            conn.commit()

            if cursor.rowcount == 0:
                return None

            row = conn.execute(
                "SELECT claim_id, claim_text, source_traces, structural_score, timestamp, status "
                "FROM aletheia_pending WHERE claim_id = ?",
                (claim_id,),
            ).fetchone()

            return self._row_to_claim(row) if row else None
        finally:
            conn.close()

    def get_verified(self) -> list[PendingClaim]:
        """Get all verified claims."""
        return self._get_by_status("verified")

    def get_rejected(self) -> list[PendingClaim]:
        """Get all rejected claims."""
        return self._get_by_status("rejected")

    def pending_count(self) -> int:
        """Count pending claims."""
        conn = sqlite3.connect(self._db_path)
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM aletheia_pending WHERE status = 'pending'"
            ).fetchone()
            return row[0] if row else 0
        finally:
            conn.close()

    def _get_by_status(self, status: str) -> list[PendingClaim]:
        """Get claims by status."""
        conn = sqlite3.connect(self._db_path)
        try:
            cursor = conn.execute(
                "SELECT claim_id, claim_text, source_traces, structural_score, timestamp, status "
                "FROM aletheia_pending WHERE status = ? ORDER BY timestamp ASC",
                (status,),
            )
            return [self._row_to_claim(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def _row_to_claim(row: tuple) -> PendingClaim:
        """Convert a database row to PendingClaim."""
        return PendingClaim(
            claim_id=row[0],
            claim_text=row[1],
            source_traces=json.loads(row[2]),
            structural_score=row[3],
            timestamp=row[4],
            status=row[5],
        )
