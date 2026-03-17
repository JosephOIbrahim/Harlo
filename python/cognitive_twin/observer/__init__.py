"""Observer — background process for Hot→Warm SDR promotion.

The Observer is NOT a daemon (Rule 1: 0W idle). It is invoked by
external scheduling (systemd timer, cron, or manual call).
Loads the ONNX encoder ONCE, reuses across promotion cycles.
No LLM client imports.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class Observer:
    """Background observer for Hot→Warm trace promotion.

    Wraps PromotionPipeline with ONNX encoder lifecycle management.
    The encoder loads once at init and is reused across cycles.
    """

    def __init__(self, db_path: str, model_path: str) -> None:
        """Initialize Observer with database and ONNX model paths.

        Args:
            db_path: Path to SQLite database file.
            model_path: Path to ONNX model file for SDR encoding.

        Raises:
            FileNotFoundError: If model_path does not exist.
        """
        if not Path(model_path).exists():
            raise FileNotFoundError(f"ONNX model not found: {model_path}")

        from cognitive_twin.hot_store import HotStore
        from cognitive_twin.encoder.onnx_encoder import OnnxEncoder
        from cognitive_twin.hot_store.promotion import PromotionPipeline

        self._hot_store = HotStore(db_path)
        self._encoder = OnnxEncoder(model_path)
        self._pipeline = PromotionPipeline(
            hot_store=self._hot_store,
            warm_db_path=db_path,
            encoder=self._encoder,
        )
        self._db_path = db_path

        logger.info("Observer initialized: db=%s, model=%s", db_path, model_path)

    def run_promotion_cycle(self, batch_size: int = 50) -> int:
        """Promote pending hot traces to warm tier.

        Args:
            batch_size: Maximum traces to promote per cycle.

        Returns:
            Number of traces promoted.
        """
        count = self._pipeline.promote_batch(batch_size=batch_size)
        if count > 0:
            logger.info("Promoted %d traces", count)
        return count

    def pending_count(self) -> int:
        """Return number of traces awaiting promotion."""
        return len(self._hot_store.get_pending(limit=10000))
