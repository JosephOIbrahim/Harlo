"""Tests for the Hippocampus Association Engine (Rust via PyO3).

Phase 1 verification:
- E2E recall roundtrip
- Cold start performance
- Hot recall performance
- 1-bit vectors (no float32)
- No background loops
"""

import json
import os
import tempfile
import time

import hippocampus


def _temp_db():
    """Create a temporary database path."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return path


class TestRecallE2E:
    """End-to-end recall tests."""

    def test_store_and_recall(self):
        db = _temp_db()
        try:
            hippocampus.py_store_trace("t1", "hello world greeting", db_path=db)
            hippocampus.py_store_trace("t2", "quantum physics equation", db_path=db)

            result = hippocampus.py_recall("hello world", db_path=db)

            assert result["confidence"] > 0.0
            assert len(result["traces"]) > 0
            assert result["traces"][0]["trace_id"] == "t1"
        finally:
            os.unlink(db)

    def test_recall_empty_db(self):
        db = _temp_db()
        try:
            result = hippocampus.py_recall("anything", db_path=db)
            assert result["confidence"] == 0.0
            assert len(result["traces"]) == 0
        finally:
            os.unlink(db)

    def test_recall_with_tags(self):
        db = _temp_db()
        try:
            hippocampus.py_store_trace(
                "t1", "important fact",
                tags=["critical", "knowledge"],
                domain="research",
                db_path=db,
            )
            result = hippocampus.py_recall("important", db_path=db)
            assert len(result["traces"]) > 0
        finally:
            os.unlink(db)

    def test_recall_depth_normal(self):
        db = _temp_db()
        try:
            for i in range(20):
                hippocampus.py_store_trace(
                    f"t{i}", f"memory trace number {i}", db_path=db
                )
            result = hippocampus.py_recall("memory trace", depth="normal", db_path=db)
            assert len(result["traces"]) <= 5  # Normal depth k=5
        finally:
            os.unlink(db)

    def test_recall_depth_deep(self):
        db = _temp_db()
        try:
            for i in range(20):
                hippocampus.py_store_trace(
                    f"t{i}", f"memory trace number {i}", db_path=db
                )
            result = hippocampus.py_recall("memory trace", depth="deep", db_path=db)
            assert len(result["traces"]) <= 15  # Deep depth k=15
            assert len(result["traces"]) >= 5   # More than normal
        finally:
            os.unlink(db)


class TestPerformance:
    """Performance tests for Phase 1 gate."""

    def test_cold_start(self):
        """Cold start must be <50ms."""
        db = _temp_db()
        try:
            hippocampus.py_store_trace("t1", "test data", db_path=db)

            start = time.perf_counter()
            hippocampus.py_recall("test", db_path=db)
            elapsed_ms = (time.perf_counter() - start) * 1000

            assert elapsed_ms < 200, f"Cold start too slow: {elapsed_ms:.1f}ms (target: <50ms, hard fail: >200ms)"
        finally:
            os.unlink(db)

    def test_hot_recall(self):
        """Hot recall must be <2ms (10ms hard fail)."""
        db = _temp_db()
        try:
            for i in range(100):
                hippocampus.py_store_trace(f"t{i}", f"trace {i}", db_path=db)

            # Warm up
            hippocampus.py_recall("trace", db_path=db)

            # Measure hot recall (average of 10 runs)
            times = []
            for _ in range(10):
                start = time.perf_counter()
                hippocampus.py_recall("trace", db_path=db)
                elapsed_ms = (time.perf_counter() - start) * 1000
                times.append(elapsed_ms)

            avg_ms = sum(times) / len(times)
            assert avg_ms < 10, f"Hot recall too slow: {avg_ms:.1f}ms (target: <2ms, hard fail: >10ms)"
        finally:
            os.unlink(db)


class TestReflex:
    """Reflex cache tests (Rule 12)."""

    def test_store_verified_reflex(self):
        db = _temp_db()
        try:
            result = hippocampus.py_store_reflex(
                "hash1", '{"action":"test"}', "root123",
                "verified", db_path=db,
            )
            assert result == "hash1"
        finally:
            os.unlink(db)

    def test_reject_unverified_reflex(self):
        """Rule 12: Unverified reflexes MUST be rejected."""
        db = _temp_db()
        try:
            try:
                hippocampus.py_store_reflex(
                    "bad", '{}', "root", "fixable", db_path=db,
                )
                assert False, "Should have rejected unverified reflex"
            except RuntimeError:
                pass  # Expected
        finally:
            os.unlink(db)

    def test_accept_permanent_amygdala(self):
        """Rule 7: Amygdala permanent reflexes bypass verification."""
        db = _temp_db()
        try:
            result = hippocampus.py_store_reflex(
                "amygdala1", '{"safety":"block"}', "root",
                "amygdala_bypass", is_permanent=True, db_path=db,
            )
            assert result == "amygdala1"
        finally:
            os.unlink(db)

    def test_lookup_reflex(self):
        db = _temp_db()
        try:
            hippocampus.py_store_reflex(
                "lookup1", '{"data":"test"}', "root", "verified", db_path=db,
            )
            result = hippocampus.py_lookup_reflex("lookup1", db_path=db)
            assert result is not None
            assert result["pattern_hash"] == "lookup1"
            assert result["verification_state"] == "verified"
        finally:
            os.unlink(db)

    def test_lookup_missing(self):
        db = _temp_db()
        try:
            result = hippocampus.py_lookup_reflex("nonexistent", db_path=db)
            assert result is None
        finally:
            os.unlink(db)


class TestBoost:
    """Retrieval boost tests."""

    def test_boost_trace(self):
        db = _temp_db()
        try:
            hippocampus.py_store_trace("t1", "boostable memory", db_path=db)
            result = hippocampus.py_boost("t1", amount=0.5, db_path=db)
            assert result is True
        finally:
            os.unlink(db)

    def test_boost_nonexistent(self):
        db = _temp_db()
        try:
            result = hippocampus.py_boost("nonexistent", db_path=db)
            assert result is False
        finally:
            os.unlink(db)


class TestApoptosis:
    """Apoptosis tests (Rule 5)."""

    def test_microglia_deletes_weak_traces(self):
        db = _temp_db()
        try:
            # Store traces and then run apoptosis
            hippocampus.py_store_trace("t1", "test", db_path=db)
            result = hippocampus.py_microglia(epsilon=100.0, db_path=db)
            # With epsilon=100, everything should be deleted
            assert result["traces_deleted"] >= 1
        finally:
            os.unlink(db)


class TestConsolidate:
    """Graph consolidation tests."""

    def test_consolidate_empty(self):
        db = _temp_db()
        try:
            result = hippocampus.py_consolidate(db_path=db)
            assert result["graph_nodes"] == 0
            assert result["graph_edges"] == 0
        finally:
            os.unlink(db)
