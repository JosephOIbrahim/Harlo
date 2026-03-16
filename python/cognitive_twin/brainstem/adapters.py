"""Per-subsystem adapters: native format ↔ USD-Lite prims.

Each subsystem gets one adapter pair (to_prim + from_prim).
All adapters are pure functions — no side effects, no DB access.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ..composition.layer import ArcType as CompArcType
from ..composition.layer import Layer
from ..usd_lite.arc_types import ArcType as UsdArcType
from ..usd_lite.prims import (
    AletheiaPrim,
    CompositionLayerPrim,
    GateStatusPrim,
    InquiryPrim,
    MerkleRootPrim,
    MotorGateStatus,
    MotorPrim,
    SessionPrim,
    TracePrim,
    VerificationState,
)


# ---------------------------------------------------------------
# Association adapter
# ---------------------------------------------------------------


def recall_to_traces(recall_result: dict) -> dict[str, TracePrim]:
    """Convert hippocampus RecallResult dict to TracePrim dict.

    Expects recall_result to contain 'traces' list of TraceHit dicts.
    Each TraceHit has: trace_id, strength, distance, and optionally sdr/tags.
    """
    traces: dict[str, TracePrim] = {}
    for hit in recall_result.get("traces", []):
        tid = hit["trace_id"]
        sdr = hit.get("sdr", [0] * 2048)
        # Convert bytes to list[int] if needed
        if isinstance(sdr, (bytes, bytearray)):
            sdr = _bytes_to_sdr(sdr)
        traces[tid] = TracePrim(
            trace_id=tid,
            sdr=sdr,
            content_hash=hit.get("content_hash", ""),
            strength=hit.get("strength", 0.0),
            last_accessed=datetime.now(timezone.utc),
        )
    return traces


def traces_to_recall(traces: dict[str, TracePrim], query_sdr: Optional[list[int]] = None) -> dict:
    """Convert TracePrims back to RecallResult-shaped dict.

    Recomputes hamming distances from query_sdr if provided.
    """
    trace_hits = []
    for tid, tp in sorted(traces.items()):
        distance = 0
        if query_sdr is not None:
            distance = _hamming(tp.sdr, query_sdr)
        trace_hits.append({
            "trace_id": tid,
            "strength": tp.strength,
            "distance": distance,
            "content_hash": tp.content_hash,
            "sdr": tp.sdr,
        })

    confidence = 0.0
    if trace_hits:
        confidence = max(h["strength"] for h in trace_hits)

    return {
        "traces": trace_hits,
        "confidence": confidence,
        "context": "",
    }


def _bytes_to_sdr(data: bytes) -> list[int]:
    """Convert 256 bytes (2048 bits) to list[int] of 0/1."""
    sdr: list[int] = []
    for byte in data:
        for bit in range(7, -1, -1):
            sdr.append((byte >> bit) & 1)
    return sdr


def _hamming(a: list[int], b: list[int]) -> int:
    """Compute hamming distance between two SDR lists."""
    return sum(x != y for x, y in zip(a, b))


# ---------------------------------------------------------------
# Composition adapter
# ---------------------------------------------------------------

# ArcType value mapping (both enums use 1-6)
_COMP_TO_USD = {v.value: UsdArcType(v.value) for v in CompArcType}
_USD_TO_COMP = {v.value: CompArcType(v.value) for v in UsdArcType}


def layers_to_composition(layers: list[Layer]) -> dict[str, CompositionLayerPrim]:
    """Convert composition.Layer list to CompositionLayerPrim dict."""
    result: dict[str, CompositionLayerPrim] = {}
    for layer in layers:
        result[layer.layer_id] = CompositionLayerPrim(
            layer_id=layer.layer_id,
            arc_type=_COMP_TO_USD[layer.arc_type.value],
            opinion=dict(layer.data),
            timestamp=datetime.fromtimestamp(layer.timestamp, tz=timezone.utc),
        )
    return result


def composition_to_layers(prims: dict[str, CompositionLayerPrim]) -> list[Layer]:
    """Convert CompositionLayerPrims back to composition.Layer list."""
    layers: list[Layer] = []
    for lid in sorted(prims):
        prim = prims[lid]
        layers.append(Layer(
            arc_type=_USD_TO_COMP[prim.arc_type.value],
            data=dict(prim.opinion),
            source=prim.provenance.session_id if prim.provenance else "",
            timestamp=int(prim.timestamp.timestamp()),
            layer_id=prim.layer_id,
        ))
    return layers


# ---------------------------------------------------------------
# Aletheia adapter
# ---------------------------------------------------------------

# Map between aletheia.states.VerificationState values and usd_lite VerificationState
_ALETHEIA_STATE_MAP = {
    "verified": VerificationState.TRUSTED,
    "fixable": VerificationState.CONTESTED,
    "spec_gamed": VerificationState.REFUTED,
    "unprovable": VerificationState.PENDING,
    "deferred": VerificationState.PENDING,
}

_USD_TO_ALETHEIA_STATE = {
    VerificationState.TRUSTED: "verified",
    VerificationState.CONTESTED: "fixable",
    VerificationState.REFUTED: "spec_gamed",
    VerificationState.PENDING: "unprovable",
}


def verification_to_aletheia(result: dict) -> AletheiaPrim:
    """Convert VerificationResult dict to AletheiaPrim.

    Maps verification state and cycle count into GateStatusPrim.
    """
    state_str = result.get("state", "deferred")
    if hasattr(state_str, "value"):
        state_str = state_str.value
    usd_state = _ALETHEIA_STATE_MAP.get(state_str, VerificationState.PENDING)

    return AletheiaPrim(
        gate_status=GateStatusPrim(
            verification_state=usd_state,
            cycle_count=result.get("cycle_count", 0),
            last_verified=datetime.now(timezone.utc),
        ),
    )


def aletheia_to_verification(prim: AletheiaPrim) -> dict:
    """Convert AletheiaPrim back to VerificationResult-shaped dict."""
    if prim.gate_status is None:
        return {"state": "deferred", "cycle_count": 0}

    gs = prim.gate_status
    state_str = _USD_TO_ALETHEIA_STATE.get(gs.verification_state, "unprovable")
    return {
        "state": state_str,
        "cycle_count": gs.cycle_count,
    }


# ---------------------------------------------------------------
# Session adapter
# ---------------------------------------------------------------


def session_to_prim(session: dict) -> SessionPrim:
    """Convert session manager dict to SessionPrim."""
    return SessionPrim(
        current_session_id=session.get("session_id", ""),
        exchange_count=session.get("exchange_count", 0),
    )


def prim_to_session(prim: SessionPrim) -> dict:
    """Convert SessionPrim back to session manager dict."""
    return {
        "session_id": prim.current_session_id,
        "exchange_count": prim.exchange_count,
    }


# ---------------------------------------------------------------
# Motor adapter
# ---------------------------------------------------------------

_GATE_STATUS_MAP = {
    "inhibited": MotorGateStatus.INHIBITED,
    "approved": MotorGateStatus.APPROVED,
    "executing": MotorGateStatus.EXECUTING,
}

_GATE_STATUS_REVERSE = {v: k for k, v in _GATE_STATUS_MAP.items()}


def motor_to_prims(actions: list[dict]) -> list[MotorPrim]:
    """Convert PlannedAction dicts to MotorPrim list."""
    result: list[MotorPrim] = []
    for action in actions:
        gate_str = action.get("gate_status", "inhibited")
        result.append(MotorPrim(
            action=action.get("action", action.get("description", "")),
            gate_status=_GATE_STATUS_MAP.get(gate_str, MotorGateStatus.INHIBITED),
        ))
    return result


def prims_to_motor(prims: list[MotorPrim]) -> list[dict]:
    """Convert MotorPrim list back to PlannedAction dicts."""
    return [
        {
            "action": p.action,
            "gate_status": _GATE_STATUS_REVERSE.get(p.gate_status, "inhibited"),
        }
        for p in prims
    ]


# ---------------------------------------------------------------
# Inquiry adapter
# ---------------------------------------------------------------


def inquiries_to_prims(inquiries: list[dict]) -> list[InquiryPrim]:
    """Convert Inquiry dicts to InquiryPrim list."""
    return [
        InquiryPrim(
            hypothesis=inq.get("hypothesis", ""),
            confidence=inq.get("confidence", 0.0),
        )
        for inq in inquiries
    ]


def prims_to_inquiries(prims: list[InquiryPrim]) -> list[dict]:
    """Convert InquiryPrim list back to Inquiry dicts."""
    return [
        {
            "hypothesis": p.hypothesis,
            "confidence": p.confidence,
        }
        for p in prims
    ]
