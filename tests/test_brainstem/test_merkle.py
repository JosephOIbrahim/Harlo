"""Merkle hash computation tests over /Association/Traces."""

from __future__ import annotations

import random
from datetime import datetime, timezone

from harlo.brainstem.merkle import compute_trace_merkle
from harlo.usd_lite.prims import TracePrim


NOW = datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc)


def _make_trace(trace_id: str, sdr: list[int] | None = None) -> TracePrim:
    if sdr is None:
        sdr = [0] * 2048
    return TracePrim(
        trace_id=trace_id,
        sdr=sdr,
        content_hash=f"hash_{trace_id}",
        strength=0.5,
        last_accessed=NOW,
    )


class TestComputeTraceMerkle:
    """Merkle hash over /Association/Traces."""

    def test_empty_traces(self) -> None:
        """Empty traces → deterministic hash."""
        h1 = compute_trace_merkle({})
        h2 = compute_trace_merkle({})
        assert h1 == h2
        assert len(h1) == 64  # SHA256 hex digest

    def test_single_trace(self) -> None:
        """Single trace → valid hash."""
        traces = {"t1": _make_trace("t1")}
        h = compute_trace_merkle(traces)
        assert len(h) == 64

    def test_deterministic(self) -> None:
        """Same traces → same hash every time."""
        traces = {
            "t1": _make_trace("t1"),
            "t2": _make_trace("t2"),
        }
        h1 = compute_trace_merkle(traces)
        h2 = compute_trace_merkle(traces)
        assert h1 == h2

    def test_adding_trace_changes_root(self) -> None:
        """Adding a trace changes the Merkle root."""
        traces1 = {"t1": _make_trace("t1")}
        traces2 = {"t1": _make_trace("t1"), "t2": _make_trace("t2")}
        assert compute_trace_merkle(traces1) != compute_trace_merkle(traces2)

    def test_sorted_by_trace_id(self) -> None:
        """Order of dict keys doesn't matter — sorted internally."""
        traces_a = {"z_trace": _make_trace("z_trace"), "a_trace": _make_trace("a_trace")}
        traces_b = {"a_trace": _make_trace("a_trace"), "z_trace": _make_trace("z_trace")}
        assert compute_trace_merkle(traces_a) == compute_trace_merkle(traces_b)

    def test_base_sdr_used_not_effective(self) -> None:
        """Hebbian masks don't affect Merkle hash — only base SDR."""
        trace = _make_trace("t1")
        traces_base = {"t1": trace}
        h_base = compute_trace_merkle(traces_base)

        # Same trace but with Hebbian masks set
        trace_masked = _make_trace("t1")
        trace_masked.hebbian_strengthen_mask[0] = 1
        trace_masked.hebbian_strengthen_mask[100] = 1
        trace_masked.hebbian_weaken_mask[50] = 1
        traces_masked = {"t1": trace_masked}
        h_masked = compute_trace_merkle(traces_masked)

        # Masks don't change the hash — base SDR is the same
        assert h_base == h_masked

    def test_different_sdr_different_hash(self) -> None:
        """Different base SDR → different hash."""
        sdr1 = [0] * 2048
        sdr2 = [0] * 2048
        sdr2[0] = 1
        traces1 = {"t1": _make_trace("t1", sdr1)}
        traces2 = {"t1": _make_trace("t1", sdr2)}
        assert compute_trace_merkle(traces1) != compute_trace_merkle(traces2)

    def test_different_content_hash_different_merkle(self) -> None:
        """Different content_hash → different Merkle root."""
        t1 = _make_trace("t1")
        t2 = _make_trace("t1")
        t2.content_hash = "different_hash"
        assert compute_trace_merkle({"t1": t1}) != compute_trace_merkle({"t1": t2})
