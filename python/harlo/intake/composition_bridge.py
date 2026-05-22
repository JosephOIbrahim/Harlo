"""Bridge from intake outputs to Composition Merkle layers (Rule 6).

Produces three layers:

  1. `UserProfile` — derived multipliers + intake history hash.
  2. `InitialAnchorAnnotations` — read-only framing notes per anchor;
     anchor GAINS stay structural 1.0 (Rule 7, Rule 10).
  3. `CoachingContext` — voice hints + apophenia delta consumed by
     `project_coach()` and the DMN.

All three layers carry `Provenance.INTAKE_CALIBRATED` so future
consolidation can find and evict them when the user re-runs intake.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from harlo.composition.layer import ArcType, Layer
from harlo.usd_lite.prims import Provenance, SourceType

from .coaching_scaffold import CoachingScaffold
from .questionnaire import IntakeSession


def _hash_session(session: IntakeSession) -> str:
    """Deterministic hash of the session's scored answers."""
    payload = sorted(session.answers.items())
    h = hashlib.sha256()
    for qid, score in payload:
        h.update(qid.encode("utf-8"))
        h.update(b"=")
        h.update(f"{score:.6f}".encode("utf-8"))
        h.update(b";")
    return h.hexdigest()


def _provenance(session_id: str, event_hash: str) -> Provenance:
    return Provenance(
        source_type=SourceType.INTAKE_CALIBRATED,
        origin_timestamp=datetime.now(tz=timezone.utc),
        event_hash=event_hash,
        session_id=session_id,
    )


def _user_profile_layer(
    session_id: str,
    derived_multipliers: dict[str, float],
    intake_hash: str,
) -> dict[str, Any]:
    return {
        "layer_id": "UserProfile",
        "provenance": _provenance(session_id, intake_hash).to_dict(),
        "content": {
            "multipliers": derived_multipliers,
            "intake_hash": intake_hash,
        },
    }


def _anchor_annotations_layer(
    session_id: str,
    annotations: dict[str, str],
    intake_hash: str,
) -> dict[str, Any]:
    return {
        "layer_id": "InitialAnchorAnnotations",
        "provenance": _provenance(session_id, intake_hash).to_dict(),
        "content": {
            "note": (
                "Read-only annotations. Anchor gains remain structural "
                "1.0 per Rule 7 and Rule 10."
            ),
            "annotations": annotations,
            "anchors_structural_1_0": True,
        },
    }


def _coaching_context_layer(
    session_id: str,
    scaffold_out: CoachingScaffold,
    intake_hash: str,
) -> dict[str, Any]:
    return {
        "layer_id": "CoachingContext",
        "provenance": _provenance(session_id, intake_hash).to_dict(),
        "content": {
            "voice": asdict(scaffold_out.voice),
            "apophenia_baseline_delta": scaffold_out.apophenia_baseline_delta,
            "inquiry_templates": [
                asdict(t) for t in scaffold_out.inquiry_templates
            ],
        },
    }


def to_layers(
    session: IntakeSession,
    session_id: str,
    derived_multipliers: dict[str, float],
    scaffold_out: CoachingScaffold,
) -> list[dict[str, Any]]:
    """Build the three INTAKE_CALIBRATED layer dicts.

    Returns wire-format payloads (used by `--json` output and tests).
    For Merkle persistence, see `to_merkle_layers`.
    """
    intake_hash = _hash_session(session)
    return [
        _user_profile_layer(session_id, derived_multipliers, intake_hash),
        _anchor_annotations_layer(
            session_id, scaffold_out.anchor_annotations, intake_hash
        ),
        _coaching_context_layer(session_id, scaffold_out, intake_hash),
    ]


def to_merkle_layers(
    session: IntakeSession,
    session_id: str,
    derived_multipliers: dict[str, float],
    scaffold_out: CoachingScaffold,
) -> list[Layer]:
    """Build the three INTAKE_CALIBRATED layers as `Layer` objects.

    These are LIVRPS LOCAL (strongest opinion — user-direct
    calibration). Caller hands them to
    `composition.stage.MerkleStage.add_layer` for hashing and
    persistence into `STAGES_DIR / intake-{session_id}.json`.
    """
    dicts = to_layers(
        session=session,
        session_id=session_id,
        derived_multipliers=derived_multipliers,
        scaffold_out=scaffold_out,
    )
    ts = int(datetime.now(tz=timezone.utc).timestamp())
    return [
        Layer(
            arc_type=ArcType.LOCAL,
            data={
                "content": d["content"],
                "provenance": d["provenance"],
            },
            source="intake",
            timestamp=ts,
            layer_id=d["layer_id"],
        )
        for d in dicts
    ]


__all__ = ["to_layers", "to_merkle_layers"]
