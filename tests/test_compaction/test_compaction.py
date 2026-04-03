"""Tests for temporal compaction engine."""

from __future__ import annotations

import json
import math

import pytest

from harlo.compaction import CompactionEngine, Variant


@pytest.fixture
def engine(tmp_path):
    """Create a CompactionEngine with temp DB."""
    return CompactionEngine(
        str(tmp_path / "compact.db"),
        archive_dir=str(tmp_path / "archive"),
    )


class TestCompactionCorrectness:
    """Gate 5a: Compaction produces correct resolved baseline."""

    def test_single_variant(self, engine):
        """Single variant compacts to itself (with decay)."""
        t_now = 1000.0
        engine.add_variant(Variant("v1", {"score": 10.0}, timestamp=t_now, decay_lambda=0.0))

        result = engine.compact(t_now=t_now)

        assert result.variants_compacted == 1
        assert result.baseline_written is True
        baseline = engine.get_baseline()
        assert baseline["score"] == pytest.approx(10.0)

    def test_decay_applied(self, engine):
        """Decay reduces old variant contributions."""
        t_old = 0.0
        t_now = 100.0
        decay = 0.05

        engine.add_variant(Variant("v1", {"score": 10.0}, timestamp=t_old, decay_lambda=decay))

        result = engine.compact(t_now=t_now)

        expected = 10.0 * math.exp(-decay * 100)
        baseline = engine.get_baseline()
        assert baseline["score"] == pytest.approx(expected, rel=1e-6)

    def test_ten_variants_correct(self, engine):
        """10 variants with known decay match manual computation."""
        t_now = 100.0
        decay = 0.05

        for i in range(10):
            engine.add_variant(
                Variant(f"v{i}", {"score": 1.0}, timestamp=float(i * 10), decay_lambda=decay)
            )

        engine.compact(t_now=t_now)

        expected = sum(
            1.0 * math.exp(-decay * (t_now - i * 10)) for i in range(10)
        )
        baseline = engine.get_baseline()
        assert baseline["score"] == pytest.approx(expected, rel=1e-6)

    def test_decay_commutation(self, engine):
        """flatten(decay(variants)) ≈ decay(flatten(variants)) within epsilon."""
        t_now = 50.0
        decay = 0.05
        variants = [
            Variant("v1", {"x": 3.0}, timestamp=10.0, decay_lambda=decay),
            Variant("v2", {"x": 5.0}, timestamp=30.0, decay_lambda=decay),
        ]

        for v in variants:
            engine.add_variant(v)

        # Path A: compact (flatten then read)
        engine.compact(t_now=t_now)
        path_a = engine.get_baseline()["x"]

        # Path B: manual decay then sum
        path_b = sum(
            v.data["x"] * math.exp(-decay * (t_now - v.timestamp))
            for v in variants
        )

        assert path_a == pytest.approx(path_b, rel=1e-9)

    def test_empty_compact(self, engine):
        """Compacting empty variant stack is no-op."""
        result = engine.compact()
        assert result.variants_compacted == 0
        assert result.baseline_written is False
        assert result.archive_path is None

    def test_non_numeric_last_write_wins(self, engine):
        """Non-numeric values use last-write-wins."""
        t_now = 10.0
        engine.add_variant(Variant("v1", {"name": "alice"}, timestamp=5.0, decay_lambda=0.0))
        engine.add_variant(Variant("v2", {"name": "bob"}, timestamp=8.0, decay_lambda=0.0))

        engine.compact(t_now=t_now)

        baseline = engine.get_baseline()
        assert baseline["name"] == "bob"


class TestArchiveIntegrity:
    """Gate 5b: Archives are intact and recoverable."""

    def test_archive_created(self, engine):
        """Archive file is created after compaction."""
        engine.add_variant(Variant("v1", {"x": 1}, timestamp=0.0, decay_lambda=0.0))
        result = engine.compact(t_now=0.0)

        assert result.archive_path is not None
        from pathlib import Path
        assert Path(result.archive_path).exists()

    def test_archive_data_recoverable(self, engine):
        """Archived variant data can be loaded."""
        original = Variant("v1", {"x": 42, "y": "hello"}, timestamp=100.0, decay_lambda=0.05)
        engine.add_variant(original)
        result = engine.compact(t_now=100.0)

        from pathlib import Path
        archive_data = json.loads(Path(result.archive_path).read_text())

        assert len(archive_data) == 1
        assert archive_data[0]["variant_id"] == "v1"
        assert archive_data[0]["data"]["x"] == 42
        assert archive_data[0]["data"]["y"] == "hello"
        assert archive_data[0]["timestamp"] == 100.0

    def test_variants_cleared_after_compact(self, engine):
        """Active variant table is empty after compaction."""
        engine.add_variant(Variant("v1", {"x": 1}, timestamp=0.0, decay_lambda=0.0))
        engine.compact(t_now=0.0)

        assert engine.get_variants() == []

    def test_idempotent(self, engine):
        """Compacting twice (already compacted) is no-op."""
        engine.add_variant(Variant("v1", {"x": 5.0}, timestamp=0.0, decay_lambda=0.0))
        engine.compact(t_now=0.0)

        result = engine.compact(t_now=0.0)
        assert result.variants_compacted == 0

    def test_baseline_overwritten_on_recompact(self, engine):
        """New compaction overwrites baseline."""
        engine.add_variant(Variant("v1", {"x": 5.0}, timestamp=0.0, decay_lambda=0.0))
        engine.compact(t_now=0.0)

        engine.add_variant(Variant("v2", {"x": 10.0}, timestamp=0.0, decay_lambda=0.0))
        engine.compact(t_now=0.0)

        baseline = engine.get_baseline()
        assert baseline["x"] == pytest.approx(10.0)
