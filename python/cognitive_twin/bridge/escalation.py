"""Escalation logic — deciding when Association results need Composition.

Escalate when: confidence < threshold (raised by allostatic load),
conflict detected, audit required, or user requests.

Rule 12: Only VERIFIED resolutions consolidate.
Rule 14: Intent preservation check on every escalation output.
Rule 16: UNPROVABLE carries metadata.
"""

from __future__ import annotations

from typing import Optional

from ..aletheia.protocol import run_gvr
from ..aletheia.states import VerificationResult, VerificationState
from ..composition.resolver import resolve as composition_resolve, Resolution
from ..composition.stage import MerkleStage

from .amygdala import is_amygdala_trigger, create_amygdala_reflex
from .consolidation import consolidate_resolution
from .intent_check import check_intent_preserved


# ------------------------------------------------------------------
# Confidence threshold
# ------------------------------------------------------------------

_BASE_CONFIDENCE_THRESHOLD = 0.70


def _effective_threshold(allostatic_load: float) -> float:
    """Raise confidence threshold under high allostatic load.

    When the system is under stress, demand *more* confidence before
    accepting an Association-only result (escalate sooner).
    """
    # Clamp load to [0, 1]
    load = max(0.0, min(1.0, allostatic_load))
    # Threshold rises linearly from base to 0.95 as load goes 0 -> 1
    return _BASE_CONFIDENCE_THRESHOLD + (0.95 - _BASE_CONFIDENCE_THRESHOLD) * load


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def should_escalate(recall_result: dict, allostatic_load: float) -> bool:
    """Decide if an Association result needs full Composition.

    Triggers:
      - confidence below threshold (threshold rises with allostatic load)
      - conflict detected in the result
      - explicit audit flag
      - user-requested escalation
    """
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
      2. Amygdala check (Rule 7 — safety/consent 1-shot bypass)
      3. Aletheia GVR (skipped if amygdala trigger)
      4. Intent preservation check (Rule 14)
      5. VERIFIED  -> consolidate
      6. SPEC_GAMED -> return to user
      7. UNPROVABLE -> park with metadata (Rule 16)

    Returns:
        dict with keys: resolution, verification, intent_check,
        consolidated (bool), reflex_hash (str|None), action.
    """
    # --- Step 1: Composition resolve ---
    stage = _load_or_create_stage(stage_id)
    resolution: Resolution = composition_resolve(stage)

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

    # --- Step 2: Amygdala check (Rule 7) ---
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

    # --- Step 3: Aletheia GVR ---
    intent = context.get("intent", query)
    output_text = _outcome_to_text(resolution.outcome)
    generator_fn = context.get("generator_fn")
    gvr_result: VerificationResult = run_gvr(
        intent=intent, output=output_text, generator_fn=generator_fn,
    )
    result["verification"] = gvr_result.to_dict()
    resolution_dict["gvr_state"] = gvr_result.state.value

    # --- Step 4: Intent preservation (Rule 14) ---
    profile = context.get("profile")
    intent_result = check_intent_preserved(intent, resolution_dict, profile=profile)
    result["intent_check"] = intent_result

    # --- Step 5/6/7: Act on verification state ---
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


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

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
