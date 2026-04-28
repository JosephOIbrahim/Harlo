"""Path C reader — real-USD .usda file → BrainStage dataclass.

Inverse of writer.py. Reads 21 prim types from /Brain hierarchy.
Codec-blocker sidecars decoded via runtime-tier codecs.
InjectionPrim/InjectionContainerPrim are NOT read (D5; not in schema).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pxr import Plug, Sdf, Usd

from ..arc_types import ArcType
from ..hex_sdr import hex_to_sdr
from ..stage import BrainStage
from ..prims import (
    AssociationPrim,
    CognitiveProfilePrim,
    CompositionLayerPrim,
    CompositionPrim,
    ElenchusPrim,
    GateStatusPrim,
    InquiryContainerPrim,
    InquiryPrim,
    IntakeHistoryPrim,
    MerkleRootPrim,
    MotorContainerPrim,
    MotorGateStatus,
    MotorPrim,
    MultipliersPrim,
    Provenance,
    RetrievalPath,
    SessionPrim,
    SkillPrim,
    SkillsContainerPrim,
    SourceType,
    TracePrim,
    VerificationState,
)


_SCHEMA_REGISTERED = False
_SCHEMA_DIR = Path(__file__).resolve().parents[4] / "schema"


def _ensure_schema_registered() -> None:
    global _SCHEMA_REGISTERED
    if _SCHEMA_REGISTERED:
        return
    Plug.Registry().RegisterPlugins(str(_SCHEMA_DIR))
    _SCHEMA_REGISTERED = True


def _from_unix_seconds(secs: float) -> datetime:
    return datetime.fromtimestamp(float(secs), tz=timezone.utc)


def _get_attr(prim: "Usd.Prim", name: str, default=None):
    """Read an attribute value or return default if missing."""
    attr = prim.GetAttribute(name)
    if not attr.IsValid():
        return default
    val = attr.Get()
    return val if val is not None else default


def _read_trace(prim: "Usd.Prim") -> TracePrim:
    return TracePrim(
        trace_id=prim.GetName(),
        sdr=hex_to_sdr(_get_attr(prim, "sdr_hex", "0" * 512)),
        content_hash=_get_attr(prim, "content_hash", ""),
        strength=float(_get_attr(prim, "strength", 0.0)),
        last_accessed=_from_unix_seconds(_get_attr(prim, "last_accessed", 0.0)),
        co_activations=json.loads(_get_attr(prim, "co_activations_json", "{}")),
        competitions=json.loads(_get_attr(prim, "competitions_json", "{}")),
        hebbian_strengthen_mask=hex_to_sdr(_get_attr(prim, "hebbian_strengthen_mask_hex", "0" * 512)),
        hebbian_weaken_mask=hex_to_sdr(_get_attr(prim, "hebbian_weaken_mask_hex", "0" * 512)),
    )


def _read_provenance(host_prim: "Usd.Prim") -> Optional[Provenance]:
    """Read Provenance API-schema attrs from host prim if present."""
    src = _get_attr(host_prim, "source_type")
    if src is None:
        return None
    return Provenance(
        source_type=SourceType(src),
        origin_timestamp=_from_unix_seconds(_get_attr(host_prim, "origin_timestamp", 0.0)),
        event_hash=_get_attr(host_prim, "event_hash", ""),
        session_id=_get_attr(host_prim, "session_id", ""),
    )


def _read_layer(prim: "Usd.Prim") -> CompositionLayerPrim:
    arc_token = _get_attr(prim, "arc_type", "local")
    return CompositionLayerPrim(
        layer_id=prim.GetName(),
        arc_type=ArcType[arc_token.upper()],
        opinion=json.loads(_get_attr(prim, "opinion_json", "{}")),
        timestamp=_from_unix_seconds(_get_attr(prim, "timestamp", 0.0)),
        provenance=_read_provenance(prim),
        permanent=bool(_get_attr(prim, "permanent", False)),
    )


def _read_session(prim: "Usd.Prim") -> SessionPrim:
    return SessionPrim(
        current_session_id=_get_attr(prim, "current_session_id", ""),
        exchange_count=int(_get_attr(prim, "exchange_count", 0)),
        surprise_rolling_mean=float(_get_attr(prim, "surprise_rolling_mean", 0.0)),
        surprise_rolling_std=float(_get_attr(prim, "surprise_rolling_std", 0.0)),
        last_query_surprise=float(_get_attr(prim, "last_query_surprise", 0.0)),
        last_retrieval_path=RetrievalPath(_get_attr(prim, "last_retrieval_path", "system_1")),
    )


def _read_inquiries(stage: "Usd.Stage") -> list[InquiryPrim]:
    container = stage.GetPrimAtPath("/Brain/Inquiry")
    if not container.IsValid():
        return []
    out: list[tuple[int, InquiryPrim]] = []
    for child in container.GetChildren():
        name = child.GetName()
        if not name.startswith("hypothesis_"):
            continue
        idx = int(name.split("_", 1)[1])
        out.append((idx, InquiryPrim(
            hypothesis=_get_attr(child, "hypothesis", ""),
            confidence=float(_get_attr(child, "confidence", 0.0)),
        )))
    out.sort(key=lambda t: t[0])
    return [p for _, p in out]


def _read_motor(stage: "Usd.Stage") -> list[MotorPrim]:
    container = stage.GetPrimAtPath("/Brain/Motor")
    if not container.IsValid():
        return []
    out: list[tuple[int, MotorPrim]] = []
    for child in container.GetChildren():
        name = child.GetName()
        if not name.startswith("action_"):
            continue
        idx = int(name.split("_", 1)[1])
        out.append((idx, MotorPrim(
            action=_get_attr(child, "action", ""),
            gate_status=MotorGateStatus(_get_attr(child, "gate_status", "inhibited")),
        )))
    out.sort(key=lambda t: t[0])
    return [p for _, p in out]


def _read_skills(stage: "Usd.Stage") -> dict[str, SkillPrim]:
    container = stage.GetPrimAtPath("/Brain/Skills")
    if not container.IsValid():
        return {}
    domains: dict[str, SkillPrim] = {}
    for child in container.GetChildren():
        domain = child.GetName()
        domains[domain] = SkillPrim(
            domain=domain,
            trace_count=int(_get_attr(child, "trace_count", 0)),
            first_seen=_from_unix_seconds(_get_attr(child, "first_seen", 0.0)),
            last_seen=_from_unix_seconds(_get_attr(child, "last_seen", 0.0)),
            growth_arc=list(_get_attr(child, "growth_arc", []) or []),
            hebbian_density=float(_get_attr(child, "hebbian_density", 0.0)),
        )
    return domains


def _read_cognitive_profile(stage: "Usd.Stage") -> CognitiveProfilePrim:
    multipliers = MultipliersPrim()
    intake_history = IntakeHistoryPrim()

    m_prim = stage.GetPrimAtPath("/Brain/CognitiveProfile/Multipliers")
    if m_prim.IsValid():
        multipliers = MultipliersPrim(
            surprise_threshold=float(_get_attr(m_prim, "surprise_threshold", 2.0)),
            reconstruction_threshold=float(_get_attr(m_prim, "reconstruction_threshold", 0.3)),
            hebbian_alpha=float(_get_attr(m_prim, "hebbian_alpha", 0.01)),
            allostatic_threshold=float(_get_attr(m_prim, "allostatic_threshold", 1.0)),
            detail_orientation=float(_get_attr(m_prim, "detail_orientation", 0.5)),
        )

    ih_prim = stage.GetPrimAtPath("/Brain/CognitiveProfile/IntakeHistory")
    if ih_prim.IsValid():
        last_intake_raw = _get_attr(ih_prim, "last_intake")
        intake_version = _get_attr(ih_prim, "intake_version") or None
        embeddings_json = _get_attr(ih_prim, "answer_embeddings_json", "[]")
        intake_history = IntakeHistoryPrim(
            last_intake=_from_unix_seconds(last_intake_raw) if last_intake_raw is not None else None,
            intake_version=intake_version if intake_version else None,
            answer_embeddings=json.loads(embeddings_json),
        )

    return CognitiveProfilePrim(multipliers=multipliers, intake_history=intake_history)


def _read_elenchus(stage: "Usd.Stage") -> ElenchusPrim:
    gs = None
    mr = None
    gs_prim = stage.GetPrimAtPath("/Brain/Elenchus/GateStatus")
    if gs_prim.IsValid():
        gs = GateStatusPrim(
            verification_state=VerificationState(_get_attr(gs_prim, "verification_state", "pending")),
            cycle_count=int(_get_attr(gs_prim, "cycle_count", 0)),
            last_verified=_from_unix_seconds(_get_attr(gs_prim, "last_verified", 0.0)),
        )
    mr_prim = stage.GetPrimAtPath("/Brain/Elenchus/MerkleRoot")
    if mr_prim.IsValid():
        mr = MerkleRootPrim(
            root_hash=_get_attr(mr_prim, "root_hash", ""),
            trace_count=int(_get_attr(mr_prim, "trace_count", 0)),
        )
    return ElenchusPrim(gate_status=gs, merkle_root=mr)


def _read_association(stage: "Usd.Stage") -> AssociationPrim:
    container = stage.GetPrimAtPath("/Brain/Association/Traces")
    traces: dict[str, TracePrim] = {}
    if container.IsValid():
        for child in container.GetChildren():
            traces[child.GetName()] = _read_trace(child)
    return AssociationPrim(traces=traces)


def _read_composition(stage: "Usd.Stage") -> CompositionPrim:
    container = stage.GetPrimAtPath("/Brain/Composition/Layers")
    layers: dict[str, CompositionLayerPrim] = {}
    if container.IsValid():
        for child in container.GetChildren():
            layers[child.GetName()] = _read_layer(child)
    return CompositionPrim(layers=layers)


def read(input_path: str) -> BrainStage:
    """Read a real-USD .usda file into a BrainStage dataclass.

    Inverse of write(). Codec-blocker sidecars decoded via runtime-tier
    codecs. InjectionContainerPrim is never present on disk (D5).
    """
    _ensure_schema_registered()

    stage = Usd.Stage.Open(str(Path(input_path)))
    if stage is None:
        raise ValueError(f"Could not open USD stage at {input_path}")

    bs = BrainStage()
    bs.association = _read_association(stage)
    bs.composition = _read_composition(stage)
    bs.elenchus = _read_elenchus(stage)

    session_prim = stage.GetPrimAtPath("/Brain/Session")
    bs.session = _read_session(session_prim) if session_prim.IsValid() else None

    bs.inquiry = InquiryContainerPrim(active=_read_inquiries(stage))
    bs.motor = MotorContainerPrim(pending=_read_motor(stage))
    bs.skills = SkillsContainerPrim(domains=_read_skills(stage))
    bs.cognitive_profile = _read_cognitive_profile(stage)
    # InjectionContainerPrim left at default empty (D5; not in schema)

    return bs
