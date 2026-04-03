"""Gate 5b: Episodic reconstruction + Patch 2 apoptosis clamp + Patch 11 reconsolidation.

Tests:
- Degraded trace with Hebbian links → reconstructed episode
- Reconstruction is READ-ONLY
- Provenance = HEBBIAN_DERIVED
- Apoptosis clamp: max(apoptosis + 0.05, threshold)
- Reconsolidation boost on user-facing retrieval only
- Adversarial: zero links → trace as-is
- Adversarial: contributing traces below apoptosis → still works
"""

from __future__ import annotations

from datetime import datetime, timezone

from harlo.hebbian.reconstruction import (
    ReconstructedEpisode,
    apply_reconsolidation_boost,
    get_reconstruction_threshold,
    needs_reconstruction,
    reconstruct_episode,
)
from harlo.usd_lite.prims import (
    CognitiveProfilePrim,
    MultipliersPrim,
    TracePrim,
)

NOW = datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc)


def _make_trace(tid: str, strength: float = 0.5) -> TracePrim:
    return TracePrim(
        trace_id=tid,
        sdr=[0] * 2048,
        content_hash=f"hash_{tid}",
        strength=strength,
        last_accessed=NOW,
    )


class TestReconstructionThreshold:
    """Patch 2: Apoptosis twilight zone clamp."""

    def test_default_threshold(self) -> None:
        threshold = get_reconstruction_threshold()
        assert threshold == 0.3

    def test_apoptosis_clamp(self) -> None:
        """threshold = max(apoptosis + 0.05, configured)."""
        # apoptosis=0.3, configured=0.3 → max(0.35, 0.3) = 0.35
        threshold = get_reconstruction_threshold(apoptosis_threshold=0.3)
        assert threshold == 0.35

    def test_configured_wins_when_higher(self) -> None:
        """Configured > apoptosis + 0.05 → configured wins."""
        profile = CognitiveProfilePrim(
            multipliers=MultipliersPrim(reconstruction_threshold=0.5),
        )
        threshold = get_reconstruction_threshold(profile, apoptosis_threshold=0.1)
        # max(0.15, 0.5) = 0.5
        assert threshold == 0.5

    def test_clamp_always_above_apoptosis(self) -> None:
        """Threshold is always at least apoptosis + 0.05."""
        for apo in [0.0, 0.1, 0.2, 0.3, 0.4]:
            threshold = get_reconstruction_threshold(apoptosis_threshold=apo)
            assert threshold >= apo + 0.05 - 1e-9

    def test_profile_scaled(self) -> None:
        """Different profiles → different thresholds."""
        low = CognitiveProfilePrim(multipliers=MultipliersPrim(reconstruction_threshold=0.15))
        high = CognitiveProfilePrim(multipliers=MultipliersPrim(reconstruction_threshold=0.5))
        t_low = get_reconstruction_threshold(low)
        t_high = get_reconstruction_threshold(high)
        assert t_high > t_low


class TestNeedsReconstruction:
    """Degraded trace detection."""

    def test_below_threshold_needs_reconstruction(self) -> None:
        trace = _make_trace("t1", strength=0.1)
        assert needs_reconstruction(trace) is True

    def test_above_threshold_no_reconstruction(self) -> None:
        trace = _make_trace("t1", strength=0.9)
        assert needs_reconstruction(trace) is False


class TestReconstructEpisode:
    """Episodic reconstruction from Hebbian links."""

    def test_reconstruction_with_links(self) -> None:
        degraded = _make_trace("t1", strength=0.1)
        degraded.co_activations = {"t2": 5, "t3": 3}
        all_traces = {
            "t1": degraded,
            "t2": _make_trace("t2", strength=0.8),
            "t3": _make_trace("t3", strength=0.6),
        }
        episode = reconstruct_episode(degraded, all_traces)
        assert episode.reconstructed is True
        assert episode.source_trace_id == "t1"
        assert "t2" in episode.contributing_trace_ids
        assert episode.provenance == "HEBBIAN_DERIVED"
        assert episode.strength > degraded.strength

    def test_reconstruction_is_read_only(self) -> None:
        """Original traces are NOT modified."""
        degraded = _make_trace("t1", strength=0.1)
        degraded.co_activations = {"t2": 5}
        t2 = _make_trace("t2", strength=0.8)
        original_strength = t2.strength
        all_traces = {"t1": degraded, "t2": t2}
        reconstruct_episode(degraded, all_traces)
        assert t2.strength == original_strength

    def test_adversarial_zero_links(self) -> None:
        """Degraded trace with zero Hebbian links → return as-is, not crash."""
        degraded = _make_trace("t1", strength=0.1)
        episode = reconstruct_episode(degraded, {"t1": degraded})
        assert episode.reconstructed is True
        assert episode.contributing_trace_ids == []
        assert episode.strength == 0.1

    def test_adversarial_contributing_below_apoptosis(self) -> None:
        """Contributing traces below apoptosis → still works with fragments."""
        degraded = _make_trace("t1", strength=0.05)
        degraded.co_activations = {"t2": 10}
        t2 = _make_trace("t2", strength=0.01)  # Below apoptosis
        all_traces = {"t1": degraded, "t2": t2}
        episode = reconstruct_episode(degraded, all_traces)
        assert episode.reconstructed is True
        assert "t2" in episode.contributing_trace_ids

    def test_contributing_trace_missing(self) -> None:
        """Co-activated trace not in all_traces → skip gracefully."""
        degraded = _make_trace("t1", strength=0.1)
        degraded.co_activations = {"t_missing": 5}
        episode = reconstruct_episode(degraded, {"t1": degraded})
        assert episode.contributing_trace_ids == []


class TestReconsolidationBoost:
    """Patch 11: Boost on user-facing retrieval only."""

    def test_boost_on_user_facing(self) -> None:
        """User-facing retrieval → boost contributing traces."""
        t1 = _make_trace("t1", strength=0.5)
        t2 = _make_trace("t2", strength=0.3)
        all_traces = {"t1": t1, "t2": t2}
        updated = apply_reconsolidation_boost(["t1", "t2"], all_traces, is_user_facing=True)
        assert updated["t1"].strength > 0.5
        assert updated["t2"].strength > 0.3

    def test_no_boost_on_internal(self) -> None:
        """Internal computation → NO boost. Traces must not self-bootstrap."""
        t1 = _make_trace("t1", strength=0.5)
        all_traces = {"t1": t1}
        updated = apply_reconsolidation_boost(["t1"], all_traces, is_user_facing=False)
        assert updated["t1"].strength == 0.5  # Unchanged

    def test_boost_caps_at_one(self) -> None:
        """Strength never exceeds 1.0."""
        t1 = _make_trace("t1", strength=0.95)
        all_traces = {"t1": t1}
        updated = apply_reconsolidation_boost(["t1"], all_traces, is_user_facing=True)
        assert updated["t1"].strength <= 1.0

    def test_missing_trace_skipped(self) -> None:
        """Non-existent trace ID → skip gracefully."""
        t1 = _make_trace("t1", strength=0.5)
        all_traces = {"t1": t1}
        updated = apply_reconsolidation_boost(["t1", "t_missing"], all_traces, is_user_facing=True)
        assert updated["t1"].strength > 0.5
        assert "t_missing" not in updated

    def test_boost_updates_last_accessed(self) -> None:
        """Boost updates last_accessed timestamp."""
        t1 = _make_trace("t1", strength=0.5)
        all_traces = {"t1": t1}
        updated = apply_reconsolidation_boost(["t1"], all_traces, is_user_facing=True)
        assert updated["t1"].last_accessed >= NOW
