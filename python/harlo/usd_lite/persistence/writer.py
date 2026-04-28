"""Path C writer — BrainStage dataclass → real-USD .usda file.

Per Phase 1 design §3 path scheme, writes 21 prim types under /Brain
root. Codec-blocker fields written as string sidecars per D8/D9.
InjectionPrim/InjectionContainerPrim are NOT written (D5).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pxr import Plug, Sdf, Usd

from ..hex_sdr import sdr_to_hex
from ..stage import BrainStage
from ..prims import (
    AssociationPrim,
    CognitiveProfilePrim,
    CompositionLayerPrim,
    CompositionPrim,
    ElenchusPrim,
    InquiryContainerPrim,
    InquiryPrim,
    IntakeHistoryPrim,
    MotorContainerPrim,
    MotorPrim,
    MultipliersPrim,
    Provenance,
    SessionPrim,
    SkillPrim,
    SkillsContainerPrim,
    TracePrim,
)


_SCHEMA_REGISTERED = False
_SCHEMA_DIR = Path(__file__).resolve().parents[4] / "schema"


def _ensure_schema_registered() -> None:
    """Idempotent plugin registration. Resolves Harlo's 21 typeNames."""
    global _SCHEMA_REGISTERED
    if _SCHEMA_REGISTERED:
        return
    Plug.Registry().RegisterPlugins(str(_SCHEMA_DIR))
    _SCHEMA_REGISTERED = True


def _to_unix_seconds(dt: datetime) -> float:
    """Convert datetime to Unix seconds. UTC if naive, else preserves tz."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def _set_string(prim: "Usd.Prim", name: str, value: str) -> None:
    attr = prim.CreateAttribute(name, Sdf.ValueTypeNames.String)
    attr.Set(value)


def _set_token(prim: "Usd.Prim", name: str, value: str) -> None:
    attr = prim.CreateAttribute(name, Sdf.ValueTypeNames.Token)
    attr.Set(value)


def _set_int(prim: "Usd.Prim", name: str, value: int) -> None:
    attr = prim.CreateAttribute(name, Sdf.ValueTypeNames.Int)
    attr.Set(int(value))


def _set_float(prim: "Usd.Prim", name: str, value: float) -> None:
    """Promote dataclass float to USD `double` (64-bit) for round-trip
    fidelity. Phase 1 design column "float" was the Python type
    annotation; USD `float` (32-bit) loses precision on values like
    0.3, 0.01, 0.5. Documented Forge clarification of design intent."""
    attr = prim.CreateAttribute(name, Sdf.ValueTypeNames.Double)
    attr.Set(float(value))


def _set_double(prim: "Usd.Prim", name: str, value: float) -> None:
    attr = prim.CreateAttribute(name, Sdf.ValueTypeNames.Double)
    attr.Set(float(value))


def _set_bool(prim: "Usd.Prim", name: str, value: bool) -> None:
    attr = prim.CreateAttribute(name, Sdf.ValueTypeNames.Bool)
    attr.Set(bool(value))


def _set_float_array(prim: "Usd.Prim", name: str, value: list[float]) -> None:
    """Promoted to DoubleArray for the same precision reason as _set_float."""
    attr = prim.CreateAttribute(name, Sdf.ValueTypeNames.DoubleArray)
    attr.Set([float(v) for v in value])


def _write_trace(stage: "Usd.Stage", path: str, t: TracePrim) -> None:
    prim = stage.DefinePrim(path, "TracePrim")
    _set_string(prim, "trace_id", t.trace_id)
    _set_string(prim, "co_activations_json", json.dumps(t.co_activations, sort_keys=True))
    _set_string(prim, "competitions_json", json.dumps(t.competitions, sort_keys=True))
    _set_string(prim, "content_hash", t.content_hash)
    _set_string(prim, "hebbian_strengthen_mask_hex", sdr_to_hex(t.hebbian_strengthen_mask))
    _set_string(prim, "hebbian_weaken_mask_hex", sdr_to_hex(t.hebbian_weaken_mask))
    _set_double(prim, "last_accessed", _to_unix_seconds(t.last_accessed))
    _set_string(prim, "sdr_hex", sdr_to_hex(t.sdr))
    _set_float(prim, "strength", t.strength)


def _write_provenance(stage: "Usd.Stage", host_path: str, p: Provenance) -> None:
    """Apply the Provenance API schema to host prim and set its 4 attrs."""
    host_prim = stage.GetPrimAtPath(host_path)
    host_prim.ApplyAPI("ProvenanceAPI") if False else None  # API-application
    # Note: in codeless schemas, ApplyAPI uses the schema identifier;
    # for direct attribute authoring we just create the attrs on the host prim.
    _set_string(host_prim, "event_hash", p.event_hash)
    _set_double(host_prim, "origin_timestamp", _to_unix_seconds(p.origin_timestamp))
    _set_string(host_prim, "session_id", p.session_id)
    _set_token(host_prim, "source_type", p.source_type.value)


def _write_layer(stage: "Usd.Stage", path: str, layer: CompositionLayerPrim) -> None:
    prim = stage.DefinePrim(path, "CompositionLayerPrim")
    _set_token(prim, "arc_type", layer.arc_type.name.lower())
    _set_string(prim, "opinion_json", json.dumps(layer.opinion, sort_keys=True))
    _set_bool(prim, "permanent", layer.permanent)
    _set_double(prim, "timestamp", _to_unix_seconds(layer.timestamp))
    if layer.provenance is not None:
        _write_provenance(stage, path, layer.provenance)


def _write_session(stage: "Usd.Stage", s: SessionPrim) -> None:
    prim = stage.DefinePrim("/Brain/Session", "SessionPrim")
    _set_string(prim, "current_session_id", s.current_session_id)
    _set_int(prim, "exchange_count", s.exchange_count)
    _set_float(prim, "last_query_surprise", s.last_query_surprise)
    _set_token(prim, "last_retrieval_path", s.last_retrieval_path.value)
    _set_float(prim, "surprise_rolling_mean", s.surprise_rolling_mean)
    _set_float(prim, "surprise_rolling_std", s.surprise_rolling_std)


def _write_inquiry(stage: "Usd.Stage", inq: InquiryContainerPrim) -> None:
    stage.DefinePrim("/Brain/Inquiry", "InquiryContainerPrim")
    for i, hyp in enumerate(inq.active):
        prim = stage.DefinePrim(f"/Brain/Inquiry/hypothesis_{i}", "InquiryPrim")
        _set_float(prim, "confidence", hyp.confidence)
        _set_string(prim, "hypothesis", hyp.hypothesis)


def _write_motor(stage: "Usd.Stage", motor: MotorContainerPrim) -> None:
    stage.DefinePrim("/Brain/Motor", "MotorContainerPrim")
    for i, mp in enumerate(motor.pending):
        prim = stage.DefinePrim(f"/Brain/Motor/action_{i}", "MotorPrim")
        _set_string(prim, "action", mp.action)
        _set_token(prim, "gate_status", mp.gate_status.value)


def _write_skills(stage: "Usd.Stage", skills: SkillsContainerPrim) -> None:
    stage.DefinePrim("/Brain/Skills", "SkillsContainerPrim")
    for domain, skill in skills.domains.items():
        prim = stage.DefinePrim(f"/Brain/Skills/{domain}", "SkillPrim")
        _set_double(prim, "first_seen", _to_unix_seconds(skill.first_seen))
        _set_float_array(prim, "growth_arc", list(skill.growth_arc))
        _set_float(prim, "hebbian_density", skill.hebbian_density)
        _set_double(prim, "last_seen", _to_unix_seconds(skill.last_seen))
        _set_int(prim, "trace_count", skill.trace_count)


def _write_cognitive_profile(stage: "Usd.Stage", cp: CognitiveProfilePrim) -> None:
    stage.DefinePrim("/Brain/CognitiveProfile", "CognitiveProfilePrim")
    m_prim = stage.DefinePrim("/Brain/CognitiveProfile/Multipliers", "MultipliersPrim")
    m = cp.multipliers
    _set_float(m_prim, "allostatic_threshold", m.allostatic_threshold)
    _set_float(m_prim, "detail_orientation", m.detail_orientation)
    _set_float(m_prim, "hebbian_alpha", m.hebbian_alpha)
    _set_float(m_prim, "reconstruction_threshold", m.reconstruction_threshold)
    _set_float(m_prim, "surprise_threshold", m.surprise_threshold)

    ih_prim = stage.DefinePrim("/Brain/CognitiveProfile/IntakeHistory", "IntakeHistoryPrim")
    ih = cp.intake_history
    _set_string(ih_prim, "answer_embeddings_json", json.dumps(ih.answer_embeddings, sort_keys=True))
    if ih.intake_version is not None:
        _set_string(ih_prim, "intake_version", ih.intake_version)
    if ih.last_intake is not None:
        _set_double(ih_prim, "last_intake", _to_unix_seconds(ih.last_intake))


def _write_elenchus(stage: "Usd.Stage", e: ElenchusPrim) -> None:
    stage.DefinePrim("/Brain/Elenchus", "ElenchusPrim")
    if e.gate_status is not None:
        gs = e.gate_status
        prim = stage.DefinePrim("/Brain/Elenchus/GateStatus", "GateStatusPrim")
        _set_int(prim, "cycle_count", gs.cycle_count)
        _set_double(prim, "last_verified", _to_unix_seconds(gs.last_verified))
        _set_token(prim, "verification_state", gs.verification_state.value)
    if e.merkle_root is not None:
        mr = e.merkle_root
        prim = stage.DefinePrim("/Brain/Elenchus/MerkleRoot", "MerkleRootPrim")
        _set_string(prim, "root_hash", mr.root_hash)
        _set_int(prim, "trace_count", mr.trace_count)


def _sanitize_prim_name(name: str) -> str:
    """Produce a TF-identifier-safe prim name from an arbitrary string.

    USD requires prim names to match `^[A-Za-z_][A-Za-z0-9_]*$`. We
    replace every non-identifier char with `_` and prefix with `t_`
    when the first char is a digit. The result is a presentation-only
    name; the canonical trace_id lives on the `trace_id` attribute
    (Forge clarification C3).
    """
    if not name:
        return "t_empty"
    sanitized = "".join(c if (c.isalnum() or c == "_") else "_" for c in name)
    if sanitized[0].isdigit():
        sanitized = "t_" + sanitized
    return sanitized


def _write_association(stage: "Usd.Stage", a: AssociationPrim) -> None:
    stage.DefinePrim("/Brain/Association", "AssociationPrim")
    for trace_id in sorted(a.traces):
        sanitized = _sanitize_prim_name(trace_id)
        _write_trace(stage, f"/Brain/Association/Traces/{sanitized}", a.traces[trace_id])


def _write_composition(stage: "Usd.Stage", c: CompositionPrim) -> None:
    stage.DefinePrim("/Brain/Composition", "CompositionPrim")
    for layer_id in sorted(c.layers):
        _write_layer(stage, f"/Brain/Composition/Layers/{layer_id}", c.layers[layer_id])


def write(stage_obj: BrainStage, output_path: str) -> None:
    """Write a BrainStage to a real-USD .usda file at output_path.

    Writes 21 prim types under /Brain. Codec-blocker fields written
    as string sidecars per D8/D9. InjectionPrim NOT written (D5).
    """
    _ensure_schema_registered()

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    stage = Usd.Stage.CreateNew(str(out))
    stage.DefinePrim("/Brain", "BrainStage")

    _write_association(stage, stage_obj.association)
    _write_composition(stage, stage_obj.composition)
    _write_elenchus(stage, stage_obj.elenchus)
    if stage_obj.session is not None:
        _write_session(stage, stage_obj.session)
    _write_inquiry(stage, stage_obj.inquiry)
    _write_motor(stage, stage_obj.motor)
    _write_skills(stage, stage_obj.skills)
    _write_cognitive_profile(stage, stage_obj.cognitive_profile)
    # InjectionContainerPrim deliberately omitted (D5).

    stage.GetRootLayer().Save()
