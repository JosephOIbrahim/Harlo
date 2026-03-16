"""Escalation logic — deciding when Association results need Composition.

Absorbed from bridge/ in Phase 4. Uses brainstem adapters and provenance.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ..aletheia.protocol import run_gvr
from ..aletheia.states import VerificationResult, VerificationState
from ..composition.resolver import resolve as composition_resolve, Resolution
from ..composition.stage import MerkleStage
from ..usd_lite.prims import SourceType

from .adapters import layers_to_composition, composition_to_layers
from .amygdala import is_amygdala_trigger, create_amygdala_reflex
from .consolidation import consolidate_resolution
from .intent_check import check_intent_preserved
from .provenance import stamp_provenance
from .stage_builder import full_stage, aletheia_stage


_BASE_CONFIDENCE_THRESHOLD = 0.70


def _effective_threshold(allostatic_load: float) -> float:
    """Raise confidence threshold under high allostatic load."""
    load = max(0.0, min(1.0, allostatic_load))
    return _BASE_CONFIDENCE_THRESHOLD + (0.95 - _BASE_CONFIDENCE_THRESHOLD) * load


def should_escalate(recall_result: dict, allostatic_load: float) -> bool:
    """Decide if an Association result needs full Composition."""
    threshold = _effective_threshold(allostatic_load)
    confidence = recall_result.get("confidence", 0.0)
    if confidence < threshold:
        return True
    if recall_result.get("conflicts"):
        return True
    if recall_result.get("audit_required", False):
        return True
    if recall_result.get("user_escalation", False):
        return True
    return False


def escalate(query: str, context: dict, stage_id: str) -> dict:
    """Run the full escalation pipeline.

    Steps:
      1. Composition resolve
      2. Amygdala check (Rule 7)
      3. Aletheia GVR
      4. Intent preservation check (Rule 14)
      5-7. Act on verification state
    """
    stage = _load_or_create_stage(stage_id)
    resolution: Resolution = composition_resolve(stage)

    # Route through brainstem, stamp provenance
    session_id = context.get("session_id", "unknown")
    comp_prims = layers_to_composition(stage.get_layers())
    for lid, prim in comp_prims.items():
        source = SourceType.USER_DIRECT if context.get("user_direct") else SourceType.SYSTEM_INFERRED
        comp_prims[lid] = stamp_provenance(prim, source, session_id)

    _bs_full = full_stage(composition_layers=stage.get_layers())
    _bs_ale = aletheia_stage(merkle_root=resolution.merkle_root)

    result: dict = {
        "stage_id": stage_id,
        "resolution": {
            "merkle_root": resolution.merkle_root,
            "outcome": resolution.outcome,
        },
        "verification": None,
        "intent_check": None,
        "consolidated": False,
        "reflex_hash": None,
        "action": "pending",
    }

    resolution_dict = {
        "outcome": resolution.outcome,
        "merkle_root": resolution.merkle_root,
        "trace": resolution.trace,
        "tags": context.get("tags", []),
    }

    if is_amygdala_trigger(resolution_dict):
        reflex = create_amygdala_reflex(resolution_dict)
        reflex_hash = consolidate_resolution(
            {**resolution_dict, "gvr_state": "VERIFIED"},
            is_amygdala=True,
        )
        result["consolidated"] = True
        result["reflex_hash"] = reflex_hash
        result["action"] = "amygdala_reflex"
        result["amygdala_reflex"] = reflex
        return result

    intent = context.get("intent", query)
    output_text = _outcome_to_text(resolution.outcome)
    generator_fn = context.get("generator_fn")
    gvr_result: VerificationResult = run_gvr(
        intent=intent, output=output_text, generator_fn=generator_fn,
    )
    result["verification"] = gvr_result.to_dict()
    resolution_dict["gvr_state"] = gvr_result.state.value

    profile = context.get("profile")
    intent_result = check_intent_preserved(intent, resolution_dict, profile=profile)
    result["intent_check"] = intent_result

    if gvr_result.is_verified:
        if intent_result.get("preserved", False):
            reflex_hash = consolidate_resolution(resolution_dict)
            result["consolidated"] = True
            result["reflex_hash"] = reflex_hash
            result["action"] = "consolidated"
        else:
            result["action"] = "intent_drift"
    elif gvr_result.is_spec_gamed:
        result["action"] = "spec_gamed"
    elif gvr_result.is_unprovable:
        result["action"] = "unprovable"
        result["unprovable_metadata"] = {
            "reason": gvr_result.unprovable_reason,
            "what_would_help": gvr_result.what_would_help,
            "partial_progress": gvr_result.partial_progress,
        }
    else:
        result["action"] = "fixable"

    return result


def _load_or_create_stage(stage_id: str) -> MerkleStage:
    """Load an existing stage or create a new empty one."""
    try:
        return MerkleStage.load(stage_id)
    except (FileNotFoundError, OSError):
        return MerkleStage(stage_id=stage_id)


def _outcome_to_text(outcome: dict) -> str:
    """Flatten an outcome dict into a text string for verification."""
    parts = []
    for key, value in outcome.items():
        parts.append(f"{key}: {value}")
    return "; ".join(parts) if parts else ""
