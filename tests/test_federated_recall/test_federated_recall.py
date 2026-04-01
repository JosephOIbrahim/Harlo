"""Tests for federated recall (Hot + Warm merge)."""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from cognitive_twin.hot_store import HotStore
from cognitive_twin.federated_recall import (
    query_past_experience,
    _query_hot,
    _merge_results,
    RecallResult,
)


@pytest.fixture
def db_path(tmp_path):
    """Temporary database path."""
    return str(tmp_path / "federated.db")


@pytest.fixture
def hot_store(db_path):
    """Create HotStore with test data."""
    store = HotStore(db_path)
    store.store("quantum computing breakthrough", tags=["science"], domain="research")
    store.store("machine learning optimization", tags=["tech"], domain="engineering")
    store.store("morning coffee and reflection", tags=["personal"], domain="daily")
    return store


class TestHotRecall:
    """Gate 6a: Hot recall via FTS5."""

    def test_finds_stored_trace(self, db_path, hot_store):
        """Immediately finds a just-stored trace via FTS5."""
        results = _query_hot(db_path, "quantum")
        assert len(results) >= 1
        assert any("quantum" in r.message for r in results)

    def test_hot_results_have_tier(self, db_path, hot_store):
        """Hot results are tagged with tier='hot'."""
        results = _query_hot(db_path, "quantum")
        assert all(r.tier == "hot" for r in results)

    def test_hot_results_have_score(self, db_path, hot_store):
        """Hot results have normalized scores."""
        results = _query_hot(db_path, "quantum")
        for r in results:
            assert 0.0 <= r.score <= 1.0

    def test_no_results_for_unmatched(self, db_path, hot_store):
        """No results for unmatched query."""
        results = _query_hot(db_path, "xyznonexistent")
        assert len(results) == 0

    def test_nonexistent_db(self, tmp_path):
        """Non-existent DB returns empty."""
        results = _query_hot(str(tmp_path / "nope.db"), "test")
        assert results == []


class TestFederatedQuery:
    """Gate 6c: Federated merge across tiers."""

    def test_hot_only_results(self, db_path, hot_store):
        """With no warm data, returns hot results only."""
        with patch("cognitive_twin.encoder.semantic_recall") as mock:
            mock.return_value = {"traces": [], "confidence": 0.0}
            results = query_past_experience(db_path, "quantum")

        assert len(results) >= 1
        assert all(r.tier == "hot" for r in results)

    def test_deduplication(self):
        """Duplicate trace_ids are deduplicated (hot wins)."""
        hot = [RecallResult("t1", "hot msg", 0.9, "hot", "d", [])]
        warm = [RecallResult("t1", "warm msg", 0.5, "warm", "d", [])]

        merged = _merge_results(hot, warm)
        assert len(merged) == 1
        assert merged[0].tier == "hot"
        assert merged[0].message == "hot msg"

    def test_ranked_by_score(self):
        """Results are ranked by score descending."""
        hot = [RecallResult("t1", "low", 0.3, "hot", "d", [])]
        warm = [RecallResult("t2", "high", 0.9, "warm", "d", [])]

        merged = _merge_results(hot, warm)
        assert merged[0].trace_id == "t2"
        assert merged[1].trace_id == "t1"

    def test_respects_limit(self):
        """Merge respects limit parameter."""
        hot = [RecallResult(f"h{i}", f"hot {i}", 0.5, "hot", "d", []) for i in range(10)]
        warm = [RecallResult(f"w{i}", f"warm {i}", 0.4, "warm", "d", []) for i in range(10)]

        merged = _merge_results(hot, warm, limit=5)
        assert len(merged) == 5

    def test_empty_both_tiers(self, tmp_path):
        """Empty DB returns empty results."""
        db = str(tmp_path / "empty.db")
        results = query_past_experience(db, "anything")
        assert results == []
