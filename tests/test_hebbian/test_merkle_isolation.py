"""Gate 5a: Merkle isolation — Patch 4.

Hebbian deltas live in [V] Variant USD layer as dual masks.
Base SDR in SQLite is untouched. Merkle hash computed over base traces only.
"""

from __future__ import annotations

from datetime import datetime, timezone

from harlo.brainstem.merkle import compute_trace_merkle
from harlo.hebbian.learning import compute_effective_sdr
from harlo.usd_lite.prims import TracePrim

NOW = datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc)


def _make_trace(tid: str = "t1") -> TracePrim:
    sdr = [0] * 2048
    sdr[0] = 1
    sdr[100] = 1
    return TracePrim(
        trace_id=tid,
        sdr=sdr,
        content_hash=f"hash_{tid}",
        strength=0.5,
        last_accessed=NOW,
    )


class TestMerkleIsolation:
    """Base SDR pristine, Merkle over base only."""

    def test_base_sdr_untouched_by_masks(self) -> None:
        """Masks don't modify the base SDR field."""
        trace = _make_trace()
        original_sdr = list(trace.sdr)
        trace.hebbian_strengthen_mask[50] = 1
        trace.hebbian_weaken_mask[0] = 1
        # Base SDR is unchanged
        assert trace.sdr == original_sdr

    def test_effective_sdr_differs_from_base(self) -> None:
        """Effective SDR (with masks) differs from base when masks are set."""
        trace = _make_trace()
        trace.hebbian_strengthen_mask[50] = 1
        effective = compute_effective_sdr(
            trace.sdr, trace.hebbian_strengthen_mask, trace.hebbian_weaken_mask,
        )
        assert effective != trace.sdr
        assert effective[50] == 1  # Strengthened

    def test_merkle_uses_base_not_effective(self) -> None:
        """Merkle hash is computed over base traces, not effective."""
        trace = _make_trace()
        traces = {"t1": trace}
        hash_before = compute_trace_merkle(traces)

        # Add Hebbian masks — should NOT change Merkle
        trace.hebbian_strengthen_mask[50] = 1
        trace.hebbian_strengthen_mask[200] = 1
        trace.hebbian_weaken_mask[0] = 1
        hash_after = compute_trace_merkle(traces)

        assert hash_before == hash_after

    def test_merkle_changes_when_base_changes(self) -> None:
        """Merkle DOES change when base SDR changes (not masks)."""
        trace = _make_trace()
        traces = {"t1": trace}
        hash1 = compute_trace_merkle(traces)

        # Modify base SDR directly (simulating a different trace)
        trace2 = _make_trace()
        trace2.sdr[500] = 1
        traces2 = {"t1": trace2}
        hash2 = compute_trace_merkle(traces2)

        assert hash1 != hash2

    def test_masks_are_variant_layer_data(self) -> None:
        """Masks represent [V] Variant layer opinion — separate from base."""
        trace = _make_trace()
        # Base has bits at 0, 100
        assert trace.sdr[0] == 1
        assert trace.sdr[100] == 1
        # Masks are all zeros by default
        assert sum(trace.hebbian_strengthen_mask) == 0
        assert sum(trace.hebbian_weaken_mask) == 0
        # Setting masks doesn't touch base
        trace.hebbian_strengthen_mask[500] = 1
        assert trace.sdr[500] == 0  # Base unchanged
