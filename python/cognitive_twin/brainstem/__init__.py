"""Brainstem: Lossless translation layer between subsystems and USD stages.

Every subsystem gets one adapter (to_stage + from_stage), not N-1 pairwise bridges.
Round-trip fidelity: from_stage(to_stage(native_data)) == native_data.

Phase 4: Absorbed all bridge/ functionality.
"""

from .adapters import (
    elenchus_to_verification,
    composition_to_layers,
    inquiries_to_prims,
    layers_to_composition,
    motor_to_prims,
    prim_to_session,
    prims_to_inquiries,
    prims_to_motor,
    recall_to_traces,
    session_to_prim,
    traces_to_recall,
    verification_to_elenchus,
)
from .amygdala import is_amygdala_trigger, create_amygdala_reflex
from .consolidation import consolidate_resolution, lookup_reflex, list_reflexes
from .epistemological_bypass import should_bypass_elenchus, emit_perception_gap, accept_blind_spot
from .escalation import should_escalate, escalate
from .generate import generate
from .integrity import verify_merkle_root
from .intent_check import check_intent_preserved
from .merkle import compute_trace_merkle
from .provenance import make_event_hash, migrate_legacy_provenance, stamp_provenance
from .reflex_compiler import compile_to_reflex
from .routing import (
    DEFAULT_SURPRISE_THRESHOLD,
    ROLLING_WINDOW,
    SurpriseResult,
    compute_surprise,
    get_surprise_threshold,
    route_recall,
    update_rolling_stats,
)
from .session_updater import update_session_after_recall
from .stage_builder import elenchus_stage, full_stage

__all__ = [
    "accept_blind_spot",
    "elenchus_stage",
    "elenchus_to_verification",
    "check_intent_preserved",
    "compile_to_reflex",
    "compose",
    "composition_to_layers",
    "compute_surprise",
    "compute_trace_merkle",
    "consolidate_resolution",
    "create_amygdala_reflex",
    "DEFAULT_SURPRISE_THRESHOLD",
    "emit_perception_gap",
    "escalate",
    "full_stage",
    "generate",
    "get_surprise_threshold",
    "inquiries_to_prims",
    "is_amygdala_trigger",
    "layers_to_composition",
    "list_reflexes",
    "lookup_reflex",
    "make_event_hash",
    "migrate_legacy_provenance",
    "motor_to_prims",
    "prim_to_session",
    "prims_to_inquiries",
    "prims_to_motor",
    "recall_to_traces",
    "ROLLING_WINDOW",
    "route_recall",
    "session_to_prim",
    "should_bypass_elenchus",
    "should_escalate",
    "stamp_provenance",
    "SurpriseResult",
    "traces_to_recall",
    "update_rolling_stats",
    "update_session_after_recall",
    "verification_to_elenchus",
    "verify_merkle_root",
]
