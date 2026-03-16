"""Stage builders: full_stage() and aletheia_stage().

Path A (full_stage): Complete USD stage with all prims including /Association.
Path B (aletheia_stage): Restricted stage — structurally cannot include traces.

Rule 11: Trace exclusion is STRUCTURAL (different function signature), not filtering.
"""

from __future__ import annotations

from typing import Optional

from ..usd_lite.prims import (
    AletheiaPrim,
    AssociationPrim,
    CompositionPrim,
    InquiryContainerPrim,
    MerkleRootPrim,
    MotorContainerPrim,
    SessionPrim,
    TracePrim,
)
from ..usd_lite.stage import BrainStage
from .adapters import (
    inquiries_to_prims,
    layers_to_composition,
    motor_to_prims,
    recall_to_traces,
    session_to_prim,
    verification_to_aletheia,
)


def full_stage(
    recall_result: Optional[dict] = None,
    composition_layers: Optional[list] = None,
    verification_result: Optional[dict] = None,
    session: Optional[dict] = None,
    inquiries: Optional[list[dict]] = None,
    motor_actions: Optional[list[dict]] = None,
    merkle_root: Optional[str] = None,
    trace_count: int = 0,
) -> BrainStage:
    """Build a complete USD stage from all subsystem native data.

    This is Path A — includes /Association with all traces.
    Used for: session capsules, export, skill building.
    """
    stage = BrainStage()

    # Association
    if recall_result is not None:
        stage.association = AssociationPrim(traces=recall_to_traces(recall_result))

    # Composition
    if composition_layers is not None:
        stage.composition = CompositionPrim(
            layers=layers_to_composition(composition_layers)
        )

    # Aletheia
    if verification_result is not None:
        stage.aletheia = verification_to_aletheia(verification_result)
    if merkle_root is not None:
        if stage.aletheia.gate_status is None:
            stage.aletheia = AletheiaPrim()
        stage.aletheia.merkle_root = MerkleRootPrim(
            root_hash=merkle_root,
            trace_count=trace_count,
        )

    # Session
    if session is not None:
        stage.session = session_to_prim(session)

    # Inquiry
    if inquiries is not None:
        stage.inquiry = InquiryContainerPrim(active=inquiries_to_prims(inquiries))

    # Motor
    if motor_actions is not None:
        stage.motor = MotorContainerPrim(pending=motor_to_prims(motor_actions))

    return stage


def aletheia_stage(
    verification_result: Optional[dict] = None,
    merkle_root: Optional[str] = None,
    trace_count: int = 0,
    session: Optional[dict] = None,
) -> BrainStage:
    """Build a restricted USD stage for Aletheia verification.

    This is Path B — structurally CANNOT include /Association.
    The function signature does not accept recall_result or traces.
    Aletheia receives only: its own state, gate status, Merkle root, session.

    Rule 11: Trace exclusion is STRUCTURAL, not filtering.
    """
    stage = BrainStage()
    # association is always empty — structurally guaranteed

    # Aletheia
    if verification_result is not None:
        stage.aletheia = verification_to_aletheia(verification_result)
    if merkle_root is not None:
        if stage.aletheia.gate_status is None:
            stage.aletheia = AletheiaPrim()
        stage.aletheia.merkle_root = MerkleRootPrim(
            root_hash=merkle_root,
            trace_count=trace_count,
        )

    # Session (non-trace metadata only)
    if session is not None:
        stage.session = session_to_prim(session)

    return stage
