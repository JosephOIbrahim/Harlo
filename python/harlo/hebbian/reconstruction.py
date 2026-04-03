"""Episodic context reconstruction from Hebbian-linked traces.

Patch 2: Apoptosis twilight zone clamp:
  reconstruction_threshold = max(apoptosis_threshold + 0.05, configured_threshold)

Patch 11: Reconsolidation boost on user-facing retrieval.
  When a reconstructed episode is surfaced to the user, contributing
  base traces receive a standard retrieval boost. Boost fires ONLY
  on user-facing retrieval, not internal computation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from ..usd_lite.prims import (
    CognitiveProfilePrim,
    MultipliersPrim,
    Provenance,
    SourceType,
    TracePrim,
)

_DEFAULT_RECONSTRUCTION_THRESHOLD = 0.3
_DEFAULT_APOPTOSIS_THRESHOLD = 0.05
_APOPTOSIS_CLAMP_MARGIN = 0.05
_RETRIEVAL_BOOST = 0.1
_TOP_N_LINKS = 5


@dataclass
class ReconstructedEpisode:
    """A reconstructed episode from Hebbian-linked fragments."""
    source_trace_id: str
    contributing_trace_ids: list[str]
    reconstructed: bool = True
    provenance: str = "HEBBIAN_DERIVED"
    strength: float = 0.0


def get_reconstruction_threshold(
    profile: Optional[CognitiveProfilePrim] = None,
    apoptosis_threshold: float = _DEFAULT_APOPTOSIS_THRESHOLD,
) -> float:
    """Compute reconstruction threshold with apoptosis clamp (Patch 2).

    threshold = max(apoptosis_threshold + 0.05, configured_threshold)
    This ensures reconstruction always fires before apoptosis.
    """
    configured = _DEFAULT_RECONSTRUCTION_THRESHOLD
    if profile is not None:
        configured = profile.multipliers.reconstruction_threshold

    return max(apoptosis_threshold + _APOPTOSIS_CLAMP_MARGIN, configured)


def needs_reconstruction(
    trace: TracePrim,
    profile: Optional[CognitiveProfilePrim] = None,
    apoptosis_threshold: float = _DEFAULT_APOPTOSIS_THRESHOLD,
) -> bool:
    """Check if a trace's strength is below reconstruction threshold."""
    threshold = get_reconstruction_threshold(profile, apoptosis_threshold)
    return trace.strength < threshold


def reconstruct_episode(
    degraded_trace: TracePrim,
    all_traces: dict[str, TracePrim],
    profile: Optional[CognitiveProfilePrim] = None,
) -> ReconstructedEpisode:
    """Reconstruct an episode from Hebbian-linked co-activations.

    1. Pull top-N co-activated traces
    2. Compose contributing strengths
    3. Mark as reconstructed with provenance HEBBIAN_DERIVED

    READ-ONLY: original traces are NOT modified during reconstruction.

    Adversarial safety:
    - Zero Hebbian links → return trace as-is
    - Contributing traces below apoptosis → use available fragments
    """
    # Get top-N co-activated traces
    co_acts = degraded_trace.co_activations
    if not co_acts:
        # No Hebbian links — return as-is
        return ReconstructedEpisode(
            source_trace_id=degraded_trace.trace_id,
            contributing_trace_ids=[],
            reconstructed=True,
            strength=degraded_trace.strength,
        )

    # Sort by co-activation count, take top N
    sorted_links = sorted(co_acts.items(), key=lambda x: x[1], reverse=True)
    top_links = sorted_links[:_TOP_N_LINKS]

    contributing_ids: list[str] = []
    total_strength = degraded_trace.strength

    for linked_id, count in top_links:
        if linked_id in all_traces:
            linked_trace = all_traces[linked_id]
            contributing_ids.append(linked_id)
            # Weighted contribution: linked strength * normalized co-activation
            max_count = top_links[0][1] if top_links else 1
            weight = count / max(max_count, 1)
            total_strength += linked_trace.strength * weight * 0.1

    return ReconstructedEpisode(
        source_trace_id=degraded_trace.trace_id,
        contributing_trace_ids=contributing_ids,
        reconstructed=True,
        provenance="HEBBIAN_DERIVED",
        strength=min(total_strength, 1.0),  # Cap at 1.0
    )


def apply_reconsolidation_boost(
    contributing_trace_ids: list[str],
    all_traces: dict[str, TracePrim],
    is_user_facing: bool,
) -> dict[str, TracePrim]:
    """Apply reconsolidation boost to contributing traces (Patch 11).

    CRITICAL: Boost fires ONLY on user-facing retrieval.
    Internal computation does NOT trigger boost.
    Traces must not bootstrap their own survival without user engagement.

    Returns updated traces dict (new TracePrim instances).
    """
    if not is_user_facing:
        return all_traces

    updated = dict(all_traces)
    for tid in contributing_trace_ids:
        if tid not in updated:
            continue
        trace = updated[tid]
        updated[tid] = TracePrim(
            trace_id=trace.trace_id,
            sdr=trace.sdr,
            content_hash=trace.content_hash,
            strength=min(trace.strength + _RETRIEVAL_BOOST, 1.0),
            last_accessed=datetime.now(timezone.utc),
            co_activations=trace.co_activations,
            competitions=trace.competitions,
            hebbian_strengthen_mask=trace.hebbian_strengthen_mask,
            hebbian_weaken_mask=trace.hebbian_weaken_mask,
        )
    return updated
