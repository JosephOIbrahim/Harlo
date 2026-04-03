"""Hot → Warm promotion pipeline.

Reads un-encoded traces from HotStore, encodes them via OnnxEncoder,
writes SDR blobs to the warm-tier traces table, and marks
hot traces as encoded. All-or-nothing per batch.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from harlo.encoder.onnx_encoder import OnnxEncoder
    from harlo.hot_store import HotStore

logger = logging.getLogger(__name__)


class PromotionPipeline:
    """Promotes traces from Hot Tier (L1) to Warm Tier (L2).

    Reads un-encoded traces from HotStore, encodes them via OnnxEncoder,
    writes SDR blobs to the warm-tier traces table, and marks
    hot traces as encoded.
    """

    def __init__(
        self,
        hot_store: HotStore,
        warm_db_path: str,
        encoder: OnnxEncoder,
    ) -> None:
        """Initialize promotion pipeline.

        Args:
            hot_store: HotStore instance for reading pending traces.
            warm_db_path: Path to warm-tier SQLite DB (existing traces table).
            encoder: OnnxEncoder instance (model already loaded).
        """
        self._hot_store = hot_store
        self._warm_db_path = warm_db_path
        self._encoder = encoder

    def promote_batch(self, batch_size: int = 50) -> int:
        """Promote a batch of pending traces from Hot to Warm.

        Pipeline per trace:
        1. Read from hot_store.get_pending(batch_size)
        2. Encode messages via OnnxEncoder.encode_batch() → SDR blobs
        3. INSERT into warm-tier traces table
        4. Mark hot traces as encoded

        All-or-nothing per batch: if encoding fails, no traces are marked.

        Args:
            batch_size: Maximum traces to promote in one batch.

        Returns:
            Number of traces promoted.
        """
        pending = self._hot_store.get_pending(limit=batch_size)
        if not pending:
            return 0

        messages = [t.message for t in pending]
        sdr_blobs = self._encoder.encode_batch(messages)

        conn = sqlite3.connect(self._warm_db_path)
        try:
            self._ensure_warm_schema(conn)

            for trace, sdr_blob in zip(pending, sdr_blobs):
                self._write_warm_trace(
                    conn=conn,
                    trace_id=trace.trace_id,
                    message=trace.message,
                    sdr_blob=sdr_blob,
                    tags=trace.tags,
                    domain=trace.domain,
                    timestamp=trace.timestamp,
                )

            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        trace_ids = [t.trace_id for t in pending]
        self._hot_store.mark_encoded(trace_ids)

        logger.info("Promoted %d traces from Hot to Warm", len(pending))
        return len(pending)

    @staticmethod
    def _ensure_warm_schema(conn: sqlite3.Connection) -> None:
        """Ensure the warm-tier traces table exists."""
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

    @staticmethod
    def _write_warm_trace(
        conn: sqlite3.Connection,
        trace_id: str,
        message: str,
        sdr_blob: bytes,
        tags: list[str],
        domain: str,
        timestamp: float,
    ) -> None:
        """Write a single trace to the warm-tier traces table.

        Uses v7 defaults: initial_strength=1.0, decay_lambda=0.05.

        Args:
            conn: Active SQLite connection.
            trace_id: Trace identifier.
            message: Original message text.
            sdr_blob: 256-byte SDR blob from OnnxEncoder.
            tags: Tag list.
            domain: Knowledge domain.
            timestamp: Original store timestamp.
        """
        now = int(timestamp)
        tags_json = json.dumps(tags)

        conn.execute(
            """INSERT OR IGNORE INTO traces
               (id, message, sdr_blob, initial_strength, decay_lambda,
                created_at, last_accessed, boosts_json, tags_json, domain, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                trace_id,
                message,
                sdr_blob,
                1.0,
                0.05,
                now,
                now,
                "[]",
                tags_json,
                domain,
                "hot_promotion",
            ),
        )
