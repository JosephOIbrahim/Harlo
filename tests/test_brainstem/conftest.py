"""Hypothesis strategies for brainstem fidelity testing."""

from __future__ import annotations

import random

import hypothesis.strategies as st

from cognitive_twin.composition.layer import ArcType as CompArcType

# Pre-generate a fixed pool of SDRs to avoid slow Hypothesis draws
_RNG = random.Random(42)
_SDR_POOL = []
for _ in range(20):
    sdr = [0] * 2048
    for idx in _RNG.sample(range(2048), 80):
        sdr[idx] = 1
    _SDR_POOL.append(sdr)


# ---------------------------------------------------------------
# Native format strategies
# ---------------------------------------------------------------

@st.composite
def sdr_lists(draw: st.DrawFn) -> list[int]:
    """Pick a pre-generated SDR from the pool."""
    idx = draw(st.integers(min_value=0, max_value=len(_SDR_POOL) - 1))
    return list(_SDR_POOL[idx])


@st.composite
def trace_hit_dicts(draw: st.DrawFn) -> dict:
    """Generate a random TraceHit dict (hippocampus output)."""
    tid = f"trace_{draw(st.integers(min_value=0, max_value=9999)):04d}"
    return {
        "trace_id": tid,
        "strength": draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False)),
        "distance": draw(st.integers(min_value=0, max_value=2048)),
        "content_hash": f"hash_{tid}",
        "sdr": draw(sdr_lists()),
    }


@st.composite
def recall_results(draw: st.DrawFn) -> dict:
    """Generate a random RecallResult dict."""
    n_traces = draw(st.integers(min_value=0, max_value=5))
    traces = [draw(trace_hit_dicts()) for _ in range(n_traces)]
    # Deduplicate trace_ids
    seen: set[str] = set()
    unique_traces = []
    for t in traces:
        if t["trace_id"] not in seen:
            seen.add(t["trace_id"])
            unique_traces.append(t)
    confidence = max((t["strength"] for t in unique_traces), default=0.0)
    return {
        "traces": unique_traces,
        "confidence": confidence,
        "context": "",
    }


@st.composite
def composition_layer_lists(draw: st.DrawFn) -> list:
    """Generate a random list of composition.Layer objects."""
    from cognitive_twin.composition.layer import Layer

    n = draw(st.integers(min_value=1, max_value=5))
    layers = []
    for i in range(n):
        arc = draw(st.sampled_from(list(CompArcType)))
        layers.append(Layer(
            arc_type=arc,
            data={f"key_{i}": f"value_{i}"},
            source=f"source_{i}",
            timestamp=draw(st.integers(min_value=1000000000, max_value=2000000000)),
            layer_id=f"layer_{i:03d}",
        ))
    return layers


@st.composite
def verification_result_dicts(draw: st.DrawFn) -> dict:
    """Generate a random VerificationResult dict."""
    state = draw(st.sampled_from(["verified", "fixable", "spec_gamed", "unprovable", "deferred"]))
    return {
        "state": state,
        "cycle_count": draw(st.integers(min_value=0, max_value=3)),
    }


@st.composite
def session_dicts(draw: st.DrawFn) -> dict:
    """Generate a random session dict."""
    return {
        "session_id": f"sess_{draw(st.integers(min_value=0, max_value=9999)):04d}",
        "exchange_count": draw(st.integers(min_value=0, max_value=1000)),
    }


@st.composite
def motor_action_dicts(draw: st.DrawFn) -> list[dict]:
    """Generate a random list of motor action dicts."""
    n = draw(st.integers(min_value=0, max_value=3))
    return [
        {
            "action": f"action_{i}",
            "gate_status": draw(st.sampled_from(["inhibited", "approved", "executing"])),
        }
        for i in range(n)
    ]


@st.composite
def inquiry_dicts(draw: st.DrawFn) -> list[dict]:
    """Generate a random list of inquiry dicts."""
    n = draw(st.integers(min_value=0, max_value=3))
    return [
        {
            "hypothesis": f"hypothesis_{i}",
            "confidence": draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False)),
        }
        for i in range(n)
    ]
