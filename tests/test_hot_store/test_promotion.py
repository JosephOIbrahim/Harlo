"""Tests for Hot → Warm promotion pipeline."""

from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock

import pytest

from cognitive_twin.hot_store import HotStore
from cognitive_twin.hot_store.promotion import PromotionPipeline


@pytest.fixture
def hot_store(tmp_path):
    """Create a HotStore with a temporary database."""
    db_path = str(tmp_path / "test.db")
    return HotStore(db_path)


@pytest.fixture
def warm_db_path(tmp_path):
    """Path for warm-tier database."""
    return str(tmp_path / "warm.db")


@pytest.fixture
def mock_encoder():
    """Mock OnnxEncoder that returns deterministic 256-byte SDR blobs."""
    encoder = MagicMock()

    def mock_encode_batch(texts):
        return [bytes(range(256)) for _ in texts]

    encoder.encode_batch = mock_encode_batch
    return encoder


@pytest.fixture
def pipeline(hot_store, warm_db_path, mock_encoder):
    """Create a PromotionPipeline with mocked encoder."""
    return PromotionPipeline(hot_store, warm_db_path, mock_encoder)


class TestPromoteBatch:
    """Tests for promote_batch()."""

    def test_promote_empty_returns_zero(self, pipeline):
        """No pending traces → returns 0."""
        assert pipeline.promote_batch() == 0

    def test_promote_single_trace(self, hot_store, pipeline, warm_db_path):
        """Single trace promoted from Hot to Warm."""
        trace_id = hot_store.store("test message", tags=["tag1"], domain="testing")

        count = pipeline.promote_batch()

        assert count == 1

        # Verify trace marked as encoded in Hot
        trace = hot_store.get(trace_id)
        assert trace is not None
        assert trace.encoded is True

        # Verify trace exists in Warm
        conn = sqlite3.connect(warm_db_path)
        row = conn.execute(
            "SELECT id, message, sdr_blob, domain FROM traces WHERE id = ?",
            (trace_id,),
        ).fetchone()
        conn.close()

        assert row is not None
        assert row[0] == trace_id
        assert row[1] == "test message"
        assert len(row[2]) == 256  # SDR blob
        assert row[3] == "testing"

    def test_promote_multiple_traces(self, hot_store, pipeline):
        """Multiple traces promoted in one batch."""
        for i in range(5):
            hot_store.store(f"message {i}")

        count = pipeline.promote_batch(batch_size=10)

        assert count == 5

        # All should be marked encoded
        pending = hot_store.get_pending()
        assert len(pending) == 0

    def test_promote_respects_batch_size(self, hot_store, pipeline):
        """Only promotes up to batch_size traces."""
        for i in range(10):
            hot_store.store(f"message {i}")

        count = pipeline.promote_batch(batch_size=3)

        assert count == 3

        pending = hot_store.get_pending()
        assert len(pending) == 7

    def test_promote_idempotent(self, hot_store, pipeline, warm_db_path):
        """Already-encoded traces are not re-promoted."""
        hot_store.store("test message")

        pipeline.promote_batch()
        count = pipeline.promote_batch()

        assert count == 0

        # Warm should have exactly 1 trace
        conn = sqlite3.connect(warm_db_path)
        rows = conn.execute("SELECT COUNT(*) FROM traces").fetchone()
        conn.close()
        assert rows[0] == 1

    def test_promote_preserves_tags(self, hot_store, pipeline, warm_db_path):
        """Tags are preserved during promotion."""
        trace_id = hot_store.store(
            "tagged message", tags=["alpha", "beta"], domain="research"
        )

        pipeline.promote_batch()

        conn = sqlite3.connect(warm_db_path)
        row = conn.execute(
            "SELECT tags_json, domain, source FROM traces WHERE id = ?",
            (trace_id,),
        ).fetchone()
        conn.close()

        assert row is not None
        assert row[0] == '["alpha", "beta"]'
        assert row[1] == "research"
        assert row[2] == "hot_promotion"

    def test_promote_warm_schema_created(self, hot_store, pipeline, warm_db_path):
        """Warm-tier schema is created on first promotion."""
        hot_store.store("trigger schema creation")
        pipeline.promote_batch()

        conn = sqlite3.connect(warm_db_path)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='traces'"
        ).fetchall()
        conn.close()

        assert len(tables) == 1


class TestPromoteFailure:
    """Tests for failure handling in promotion."""

    def test_encoding_failure_leaves_hot_unchanged(self, hot_store, warm_db_path):
        """If encoder fails, hot traces stay un-encoded."""
        failing_encoder = MagicMock()
        failing_encoder.encode_batch.side_effect = RuntimeError("ONNX failed")

        pipeline = PromotionPipeline(hot_store, warm_db_path, failing_encoder)
        hot_store.store("will fail")

        with pytest.raises(RuntimeError, match="ONNX failed"):
            pipeline.promote_batch()

        # Hot trace should still be pending
        pending = hot_store.get_pending()
        assert len(pending) == 1
        assert pending[0].encoded is False

    def test_warm_write_failure_leaves_hot_unchanged(self, hot_store, tmp_path):
        """If warm DB write fails, hot traces stay un-encoded."""
        encoder = MagicMock()
        encoder.encode_batch.return_value = [bytes(256)]

        # Use a read-only path to force write failure
        bad_path = str(tmp_path / "readonly" / "warm.db")

        pipeline = PromotionPipeline(hot_store, bad_path, encoder)
        hot_store.store("will fail to write")

        with pytest.raises(Exception):
            pipeline.promote_batch()

        pending = hot_store.get_pending()
        assert len(pending) == 1
