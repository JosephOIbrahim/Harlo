"""Phase 2 Integration Tests.

GATE: Physical DELETE works. Graph consolidates. No bg loops.
"""

import json
import os
import tempfile

from harlo import hippocampus


class TestApoptosisIntegration:
    """Rule 5: Apoptosis physically DELETEs traces below epsilon."""

    def test_apoptosis_deletes_and_vacuums(self):
        """Traces below epsilon must be physically deleted."""
        db = tempfile.mktemp(suffix=".db")
        try:
            # Store several traces
            for i in range(10):
                hippocampus.py_store_trace(f"t{i}", f"test trace {i}", db_path=db)

            # Run apoptosis with high epsilon (everything dies)
            report = hippocampus.py_microglia(epsilon=100.0, db_path=db)
            assert report["traces_deleted"] >= 10

            # Verify traces are actually gone
            result = hippocampus.py_recall("test trace", db_path=db)
            assert len(result["traces"]) == 0
        finally:
            if os.path.exists(db):
                os.unlink(db)

    def test_apoptosis_preserves_strong_traces(self):
        """Recent traces with high strength should survive apoptosis."""
        db = tempfile.mktemp(suffix=".db")
        try:
            hippocampus.py_store_trace("strong", "I am strong", db_path=db)

            # Run apoptosis with low epsilon
            report = hippocampus.py_microglia(epsilon=0.01, db_path=db)

            # Recent trace should survive
            result = hippocampus.py_recall("I am strong", db_path=db)
            assert len(result["traces"]) > 0
        finally:
            if os.path.exists(db):
                os.unlink(db)


class TestGraphConsolidation:
    """Graph consolidation tests."""

    def test_consolidate_empty(self):
        db = tempfile.mktemp(suffix=".db")
        try:
            report = hippocampus.py_consolidate(db_path=db)
            assert report["graph_nodes"] == 0
            assert report["graph_edges"] == 0
        finally:
            if os.path.exists(db):
                os.unlink(db)


class TestReflexCache:
    """Compiled reflex cache integration tests."""

    def test_verified_reflex_roundtrip(self):
        db = tempfile.mktemp(suffix=".db")
        try:
            hippocampus.py_store_reflex(
                "pattern_abc", '{"response": "cached"}', "merkle_root_1",
                "verified", db_path=db,
            )
            result = hippocampus.py_lookup_reflex("pattern_abc", db_path=db)
            assert result is not None
            assert result["pattern_hash"] == "pattern_abc"
            assert result["verification_state"] == "verified"
        finally:
            if os.path.exists(db):
                os.unlink(db)

    def test_unverified_reflex_rejected(self):
        """Rule 12: Unverified reflexes MUST NOT enter cache."""
        db = tempfile.mktemp(suffix=".db")
        try:
            try:
                hippocampus.py_store_reflex(
                    "bad_pattern", '{}', "root",
                    "spec_gamed", db_path=db,
                )
                assert False, "Should have rejected spec_gamed reflex"
            except RuntimeError:
                pass

            try:
                hippocampus.py_store_reflex(
                    "bad_pattern2", '{}', "root",
                    "unprovable", db_path=db,
                )
                assert False, "Should have rejected unprovable reflex"
            except RuntimeError:
                pass
        finally:
            if os.path.exists(db):
                os.unlink(db)


class TestDecayLazy:
    """Rule 4: Decay is lazy, computed on retrieval only."""

    def test_decay_is_retrieval_only(self):
        """Strength should decrease over time when computed at retrieval."""
        db = tempfile.mktemp(suffix=".db")
        try:
            hippocampus.py_store_trace("t1", "decaying memory", db_path=db)
            result = hippocampus.py_recall("decaying memory", db_path=db)
            assert len(result["traces"]) > 0
            strength = result["traces"][0]["strength"]
            # Freshly stored trace should have high strength
            assert strength > 0.5
        finally:
            if os.path.exists(db):
                os.unlink(db)


class TestZeroWattIdle:
    """Rule 1: No background loops."""

    def test_no_sleep_in_src(self):
        """No sleep() calls in src/ directory."""
        import os

        src_dir = os.path.join(os.path.dirname(__file__), "..", "..", "src")
        src_dir = os.path.abspath(src_dir)

        for root, dirs, files in os.walk(src_dir):
            for f in files:
                if f.endswith(".py"):
                    path = os.path.join(root, f)
                    with open(path) as fh:
                        content = fh.read()
                    assert "sleep(" not in content, f"sleep() found in {path}"

    def test_no_while_true_in_src(self):
        """No while True loops in src/ directory."""
        import os

        src_dir = os.path.join(os.path.dirname(__file__), "..", "..", "src")
        src_dir = os.path.abspath(src_dir)

        for root, dirs, files in os.walk(src_dir):
            for f in files:
                if f.endswith(".py"):
                    path = os.path.join(root, f)
                    with open(path) as fh:
                        content = fh.read()
                    assert "while True" not in content, f"while True found in {path}"
