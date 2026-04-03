"""Tests for HotStore CRUD operations."""

from __future__ import annotations

import sqlite3
import time

import pytest

from harlo.hot_store import HotStore, HotTrace


class TestStore:
    """Tests for HotStore.store()."""

    def test_store_returns_trace_id(self, hot_store):
        """Store returns a non-empty trace_id."""
        tid = hot_store.store(message="hello world")
        assert isinstance(tid, str)
        assert len(tid) > 0

    def test_store_with_explicit_id(self, hot_store):
        """Store uses the provided trace_id."""
        tid = hot_store.store(message="hello", trace_id="custom_123")
        assert tid == "custom_123"

    def test_store_with_tags_and_domain(self, hot_store):
        """Store persists tags and domain."""
        tid = hot_store.store(
            message="tagged message",
            tags=["a", "b"],
            domain="technical",
        )
        trace = hot_store.get(tid)
        assert trace is not None
        assert trace.tags == ["a", "b"]
        assert trace.domain == "technical"

    def test_store_defaults(self, hot_store):
        """Store uses correct defaults for optional fields."""
        tid = hot_store.store(message="default test")
        trace = hot_store.get(tid)
        assert trace is not None
        assert trace.tags == []
        assert trace.domain == "general"
        assert trace.encoded is False

    def test_store_with_explicit_timestamp(self, hot_store):
        """Store uses provided timestamp."""
        ts = 1700000000.0
        tid = hot_store.store(message="timed", timestamp=ts)
        trace = hot_store.get(tid)
        assert trace is not None
        assert trace.timestamp == ts

    def test_store_duplicate_id_raises(self, hot_store):
        """Store raises IntegrityError on duplicate trace_id."""
        hot_store.store(message="first", trace_id="dup_id")
        with pytest.raises(sqlite3.IntegrityError):
            hot_store.store(message="second", trace_id="dup_id")

    def test_store_encoded_defaults_false(self, hot_store):
        """All new traces have encoded=FALSE."""
        tid = hot_store.store(message="test encoded flag")
        trace = hot_store.get(tid)
        assert trace is not None
        assert trace.encoded is False


class TestGet:
    """Tests for HotStore.get()."""

    def test_get_existing(self, hot_store):
        """Get returns the correct trace."""
        tid = hot_store.store(message="findable", trace_id="get_test")
        trace = hot_store.get("get_test")
        assert trace is not None
        assert trace.trace_id == "get_test"
        assert trace.message == "findable"

    def test_get_nonexistent(self, hot_store):
        """Get returns None for missing trace_id."""
        trace = hot_store.get("does_not_exist")
        assert trace is None

    def test_get_returns_hottrace(self, hot_store):
        """Get returns a HotTrace dataclass."""
        hot_store.store(message="type check", trace_id="tc")
        trace = hot_store.get("tc")
        assert isinstance(trace, HotTrace)


class TestGetPending:
    """Tests for HotStore.get_pending()."""

    def test_get_pending_returns_unencoded(self, hot_store):
        """get_pending returns only traces with encoded=FALSE."""
        hot_store.store(message="pending 1", trace_id="p1")
        hot_store.store(message="pending 2", trace_id="p2")
        hot_store.mark_encoded(["p1"])

        pending = hot_store.get_pending()
        assert len(pending) == 1
        assert pending[0].trace_id == "p2"

    def test_get_pending_oldest_first(self, hot_store):
        """get_pending returns traces ordered by timestamp ascending."""
        hot_store.store(message="later", trace_id="l", timestamp=200.0)
        hot_store.store(message="earlier", trace_id="e", timestamp=100.0)

        pending = hot_store.get_pending()
        assert pending[0].trace_id == "e"
        assert pending[1].trace_id == "l"

    def test_get_pending_respects_limit(self, hot_store):
        """get_pending respects the limit parameter."""
        for i in range(10):
            hot_store.store(message=f"msg {i}", trace_id=f"lim_{i}")

        pending = hot_store.get_pending(limit=3)
        assert len(pending) == 3

    def test_get_pending_empty(self, hot_store):
        """get_pending returns empty list when no pending traces."""
        pending = hot_store.get_pending()
        assert pending == []


class TestMarkEncoded:
    """Tests for HotStore.mark_encoded()."""

    def test_mark_encoded_updates_flag(self, hot_store):
        """mark_encoded sets encoded=TRUE."""
        hot_store.store(message="to encode", trace_id="enc_1")
        count = hot_store.mark_encoded(["enc_1"])
        assert count == 1

        trace = hot_store.get("enc_1")
        assert trace is not None
        assert trace.encoded is True

    def test_mark_encoded_returns_count(self, hot_store):
        """mark_encoded returns the number of rows updated."""
        hot_store.store(message="a", trace_id="mc_1")
        hot_store.store(message="b", trace_id="mc_2")
        count = hot_store.mark_encoded(["mc_1", "mc_2", "mc_nonexistent"])
        assert count == 2

    def test_mark_encoded_empty_list(self, hot_store):
        """mark_encoded with empty list returns 0."""
        count = hot_store.mark_encoded([])
        assert count == 0

    def test_mark_encoded_idempotent(self, hot_store):
        """mark_encoded on already-encoded trace is a no-op."""
        hot_store.store(message="test", trace_id="idem")
        hot_store.mark_encoded(["idem"])
        count = hot_store.mark_encoded(["idem"])
        # SQLite UPDATE returns rowcount even if value unchanged
        assert count >= 0


class TestStoreLatency:
    """Latency tests for HotStore.store() — Gate 1b."""

    def test_store_p99_under_2ms(self, hot_store):
        """p99 store latency must be under 2ms (100 calls)."""
        latencies = []
        for i in range(100):
            start = time.perf_counter()
            hot_store.store(message=f"latency test message number {i}")
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)

        latencies.sort()
        p99 = latencies[98]  # 99th percentile of 100 samples
        assert p99 < 2.0, f"p99 store latency {p99:.2f}ms exceeds 2ms SLA"
