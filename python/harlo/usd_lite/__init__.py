"""USD-Lite: Lightweight Universal Scene Description for Harlo brain state.

Not full OpenUSD (2GB C++ dependency).  Implements ~5% of USD:
dataclasses, .usda serialization, and LIVRPS composition.
"""

from .arc_types import ArcType
from .composer import CompositionResult, compose
from .hex_sdr import hex_to_sdr, sdr_to_hex
from .prims import (
    ElenchusPrim,
    AssociationPrim,
    CognitiveProfilePrim,
    CompositionLayerPrim,
    CompositionPrim,
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
from .serializer import parse, serialize
from .stage import BrainStage

__all__ = [
    "ArcType",
    "ElenchusPrim",
    "AssociationPrim",
    "BrainStage",
    "CognitiveProfilePrim",
    "CompositionLayerPrim",
    "CompositionPrim",
    "CompositionResult",
    "GateStatusPrim",
    "InquiryContainerPrim",
    "InquiryPrim",
    "IntakeHistoryPrim",
    "MerkleRootPrim",
    "MotorContainerPrim",
    "MotorGateStatus",
    "MotorPrim",
    "MultipliersPrim",
    "Provenance",
    "RetrievalPath",
    "SessionPrim",
    "SkillPrim",
    "SkillsContainerPrim",
    "SourceType",
    "TracePrim",
    "VerificationState",
    "compose",
    "hex_to_sdr",
    "parse",
    "sdr_to_hex",
    "serialize",
]
