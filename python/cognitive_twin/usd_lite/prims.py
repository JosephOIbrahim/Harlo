"""USD-Lite prim dataclasses for the Cognitive Twin brain state.

Every subsystem writes to a shared USD stage.  Each prim type maps to a
subtree in the schema (Section 2.1.3).  Forward-declared types for
Provenance (Phase 3), CognitiveProfile (Phase 4), and Hebbian fields
(Phase 5) are structurally complete.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from .arc_types import ArcType

# ---------------------------------------------------------------
# Enums
# ---------------------------------------------------------------


class SourceType(Enum):
    """Provenance source classification (Phase 3)."""
    USER_DIRECT = "user_direct"
    EXTERNAL_REFERENCE = "external_reference"
    SYSTEM_INFERRED = "system_inferred"
    HEBBIAN_DERIVED = "hebbian_derived"
    INTAKE_CALIBRATED = "intake_calibrated"


class VerificationState(Enum):
    """Aletheia verification states."""
    TRUSTED = "trusted"
    CONTESTED = "contested"
    REFUTED = "refuted"
    PENDING = "pending"


class RetrievalPath(Enum):
    """Dual-process retrieval path (Phase 2)."""
    SYSTEM_1 = "system_1"
    SYSTEM_2 = "system_2"


class MotorGateStatus(Enum):
    """Basal ganglia gate status for motor actions."""
    INHIBITED = "inhibited"
    APPROVED = "approved"
    EXECUTING = "executing"


# ---------------------------------------------------------------
# Forward-declared / Phase-boundary types
# ---------------------------------------------------------------


@dataclass
class Provenance:
    """Structured provenance for composition layers (Phase 3)."""
    source_type: SourceType
    origin_timestamp: datetime
    event_hash: str
    session_id: str

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "source_type": self.source_type.value,
            "origin_timestamp": self.origin_timestamp.isoformat(),
            "event_hash": self.event_hash,
            "session_id": self.session_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Provenance:
        """Deserialize from dict."""
        return cls(
            source_type=SourceType(d["source_type"]),
            origin_timestamp=datetime.fromisoformat(d["origin_timestamp"]),
            event_hash=d["event_hash"],
            session_id=d["session_id"],
        )


# ---------------------------------------------------------------
# Leaf prim types
# ---------------------------------------------------------------


def _empty_sdr() -> list[int]:
    """Return a 2048-element zero SDR."""
    return [0] * 2048


@dataclass
class TracePrim:
    """A single memory trace in the Association Engine (/Association/Traces/{trace_id})."""
    trace_id: str
    sdr: list[int]                          # 2048-bit SDR (boolean array)
    content_hash: str
    strength: float                         # Lazy decay: initial * e^(-lambda*t) + sum(boosts)
    last_accessed: datetime
    co_activations: dict[str, int] = field(default_factory=dict)
    competitions: dict[str, int] = field(default_factory=dict)
    hebbian_strengthen_mask: list[int] = field(default_factory=_empty_sdr)
    hebbian_weaken_mask: list[int] = field(default_factory=_empty_sdr)

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "trace_id": self.trace_id,
            "sdr": self.sdr,
            "content_hash": self.content_hash,
            "strength": self.strength,
            "last_accessed": self.last_accessed.isoformat(),
            "co_activations": dict(self.co_activations),
            "competitions": dict(self.competitions),
            "hebbian_strengthen_mask": self.hebbian_strengthen_mask,
            "hebbian_weaken_mask": self.hebbian_weaken_mask,
        }

    @classmethod
    def from_dict(cls, d: dict) -> TracePrim:
        """Deserialize from dict."""
        return cls(
            trace_id=d["trace_id"],
            sdr=d["sdr"],
            content_hash=d["content_hash"],
            strength=d["strength"],
            last_accessed=datetime.fromisoformat(d["last_accessed"]),
            co_activations=d.get("co_activations", {}),
            competitions=d.get("competitions", {}),
            hebbian_strengthen_mask=d.get("hebbian_strengthen_mask", _empty_sdr()),
            hebbian_weaken_mask=d.get("hebbian_weaken_mask", _empty_sdr()),
        )


@dataclass
class CompositionLayerPrim:
    """A single opinion layer in composition (/Composition/Layers/{layer_id})."""
    layer_id: str
    arc_type: ArcType
    opinion: dict
    timestamp: datetime
    provenance: Optional[Provenance] = None
    permanent: bool = False

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "layer_id": self.layer_id,
            "arc_type": self.arc_type.value,
            "opinion": self.opinion,
            "timestamp": self.timestamp.isoformat(),
            "provenance": self.provenance.to_dict() if self.provenance else None,
            "permanent": self.permanent,
        }

    @classmethod
    def from_dict(cls, d: dict) -> CompositionLayerPrim:
        """Deserialize from dict."""
        prov_data = d.get("provenance")
        return cls(
            layer_id=d["layer_id"],
            arc_type=ArcType(d["arc_type"]),
            opinion=d["opinion"],
            timestamp=datetime.fromisoformat(d["timestamp"]),
            provenance=Provenance.from_dict(prov_data) if prov_data else None,
            permanent=d.get("permanent", False),
        )


@dataclass
class GateStatusPrim:
    """Current Aletheia verification gate status (/Aletheia/GateStatus)."""
    verification_state: VerificationState
    cycle_count: int
    last_verified: datetime

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "verification_state": self.verification_state.value,
            "cycle_count": self.cycle_count,
            "last_verified": self.last_verified.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> GateStatusPrim:
        """Deserialize from dict."""
        return cls(
            verification_state=VerificationState(d["verification_state"]),
            cycle_count=d["cycle_count"],
            last_verified=datetime.fromisoformat(d["last_verified"]),
        )


@dataclass
class MerkleRootPrim:
    """Merkle hash over /Association/Traces subtree (/Aletheia/MerkleRoot)."""
    root_hash: str
    trace_count: int

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "root_hash": self.root_hash,
            "trace_count": self.trace_count,
        }

    @classmethod
    def from_dict(cls, d: dict) -> MerkleRootPrim:
        """Deserialize from dict."""
        return cls(
            root_hash=d["root_hash"],
            trace_count=d["trace_count"],
        )


@dataclass
class SessionPrim:
    """Session metadata and routing state (/Session)."""
    current_session_id: str
    exchange_count: int
    surprise_rolling_mean: float = 0.0
    surprise_rolling_std: float = 0.0
    last_query_surprise: float = 0.0
    last_retrieval_path: RetrievalPath = RetrievalPath.SYSTEM_1

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "current_session_id": self.current_session_id,
            "exchange_count": self.exchange_count,
            "surprise_rolling_mean": self.surprise_rolling_mean,
            "surprise_rolling_std": self.surprise_rolling_std,
            "last_query_surprise": self.last_query_surprise,
            "last_retrieval_path": self.last_retrieval_path.value,
        }

    @classmethod
    def from_dict(cls, d: dict) -> SessionPrim:
        """Deserialize from dict."""
        return cls(
            current_session_id=d["current_session_id"],
            exchange_count=d["exchange_count"],
            surprise_rolling_mean=d.get("surprise_rolling_mean", 0.0),
            surprise_rolling_std=d.get("surprise_rolling_std", 0.0),
            last_query_surprise=d.get("last_query_surprise", 0.0),
            last_retrieval_path=RetrievalPath(d.get("last_retrieval_path", "system_1")),
        )


@dataclass
class InquiryPrim:
    """An active DMN hypothesis (/Inquiry/Active)."""
    hypothesis: str
    confidence: float

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "hypothesis": self.hypothesis,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, d: dict) -> InquiryPrim:
        """Deserialize from dict."""
        return cls(
            hypothesis=d["hypothesis"],
            confidence=d["confidence"],
        )


@dataclass
class MotorPrim:
    """A pending motor action proposal (/Motor/Pending)."""
    action: str
    gate_status: MotorGateStatus

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "action": self.action,
            "gate_status": self.gate_status.value,
        }

    @classmethod
    def from_dict(cls, d: dict) -> MotorPrim:
        """Deserialize from dict."""
        return cls(
            action=d["action"],
            gate_status=MotorGateStatus(d["gate_status"]),
        )


@dataclass
class SkillPrim:
    """Competence tracking for a single domain (/Skills/{domain})."""
    domain: str
    trace_count: int
    first_seen: datetime
    last_seen: datetime
    growth_arc: list[float] = field(default_factory=list)
    hebbian_density: float = 0.0

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "domain": self.domain,
            "trace_count": self.trace_count,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "growth_arc": list(self.growth_arc),
            "hebbian_density": self.hebbian_density,
        }

    @classmethod
    def from_dict(cls, d: dict) -> SkillPrim:
        """Deserialize from dict."""
        return cls(
            domain=d["domain"],
            trace_count=d["trace_count"],
            first_seen=datetime.fromisoformat(d["first_seen"]),
            last_seen=datetime.fromisoformat(d["last_seen"]),
            growth_arc=d.get("growth_arc", []),
            hebbian_density=d.get("hebbian_density", 0.0),
        )


@dataclass
class MultipliersPrim:
    """Personal calibration multipliers derived from intake (/CognitiveProfile/Multipliers)."""
    surprise_threshold: float = 2.0
    reconstruction_threshold: float = 0.3
    hebbian_alpha: float = 0.01
    allostatic_threshold: float = 1.0
    detail_orientation: float = 0.5

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "surprise_threshold": self.surprise_threshold,
            "reconstruction_threshold": self.reconstruction_threshold,
            "hebbian_alpha": self.hebbian_alpha,
            "allostatic_threshold": self.allostatic_threshold,
            "detail_orientation": self.detail_orientation,
        }

    @classmethod
    def from_dict(cls, d: dict) -> MultipliersPrim:
        """Deserialize from dict."""
        return cls(
            surprise_threshold=d.get("surprise_threshold", 2.0),
            reconstruction_threshold=d.get("reconstruction_threshold", 0.3),
            hebbian_alpha=d.get("hebbian_alpha", 0.01),
            allostatic_threshold=d.get("allostatic_threshold", 1.0),
            detail_orientation=d.get("detail_orientation", 0.5),
        )


@dataclass
class IntakeHistoryPrim:
    """Intake administration history (/CognitiveProfile/IntakeHistory)."""
    last_intake: Optional[datetime] = None
    intake_version: Optional[str] = None
    answer_embeddings: list = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "last_intake": self.last_intake.isoformat() if self.last_intake else None,
            "intake_version": self.intake_version,
            "answer_embeddings": list(self.answer_embeddings),
        }

    @classmethod
    def from_dict(cls, d: dict) -> IntakeHistoryPrim:
        """Deserialize from dict."""
        li = d.get("last_intake")
        return cls(
            last_intake=datetime.fromisoformat(li) if li else None,
            intake_version=d.get("intake_version"),
            answer_embeddings=d.get("answer_embeddings", []),
        )


# ---------------------------------------------------------------
# Container prim types
# ---------------------------------------------------------------


@dataclass
class AssociationPrim:
    """Container for all memory traces (/Association)."""
    traces: dict[str, TracePrim] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "traces": {k: v.to_dict() for k, v in self.traces.items()},
        }

    @classmethod
    def from_dict(cls, d: dict) -> AssociationPrim:
        """Deserialize from dict."""
        return cls(
            traces={k: TracePrim.from_dict(v) for k, v in d.get("traces", {}).items()},
        )


@dataclass
class CompositionPrim:
    """Container for all composition layers (/Composition)."""
    layers: dict[str, CompositionLayerPrim] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "layers": {k: v.to_dict() for k, v in self.layers.items()},
        }

    @classmethod
    def from_dict(cls, d: dict) -> CompositionPrim:
        """Deserialize from dict."""
        return cls(
            layers={
                k: CompositionLayerPrim.from_dict(v)
                for k, v in d.get("layers", {}).items()
            },
        )


@dataclass
class AletheiaPrim:
    """Container for verification engine state (/Aletheia)."""
    gate_status: Optional[GateStatusPrim] = None
    merkle_root: Optional[MerkleRootPrim] = None

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "gate_status": self.gate_status.to_dict() if self.gate_status else None,
            "merkle_root": self.merkle_root.to_dict() if self.merkle_root else None,
        }

    @classmethod
    def from_dict(cls, d: dict) -> AletheiaPrim:
        """Deserialize from dict."""
        gs = d.get("gate_status")
        mr = d.get("merkle_root")
        return cls(
            gate_status=GateStatusPrim.from_dict(gs) if gs else None,
            merkle_root=MerkleRootPrim.from_dict(mr) if mr else None,
        )


@dataclass
class InquiryContainerPrim:
    """Container for DMN hypotheses (/Inquiry)."""
    active: list[InquiryPrim] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "active": [p.to_dict() for p in self.active],
        }

    @classmethod
    def from_dict(cls, d: dict) -> InquiryContainerPrim:
        """Deserialize from dict."""
        return cls(
            active=[InquiryPrim.from_dict(p) for p in d.get("active", [])],
        )


@dataclass
class MotorContainerPrim:
    """Container for motor action proposals (/Motor)."""
    pending: list[MotorPrim] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "pending": [p.to_dict() for p in self.pending],
        }

    @classmethod
    def from_dict(cls, d: dict) -> MotorContainerPrim:
        """Deserialize from dict."""
        return cls(
            pending=[MotorPrim.from_dict(p) for p in d.get("pending", [])],
        )


@dataclass
class SkillsContainerPrim:
    """Container for all skill domains (/Skills)."""
    domains: dict[str, SkillPrim] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "domains": {k: v.to_dict() for k, v in self.domains.items()},
        }

    @classmethod
    def from_dict(cls, d: dict) -> SkillsContainerPrim:
        """Deserialize from dict."""
        return cls(
            domains={k: SkillPrim.from_dict(v) for k, v in d.get("domains", {}).items()},
        )


@dataclass
class CognitiveProfilePrim:
    """Container for personal calibration (/CognitiveProfile)."""
    multipliers: MultipliersPrim = field(default_factory=MultipliersPrim)
    intake_history: IntakeHistoryPrim = field(default_factory=IntakeHistoryPrim)

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "multipliers": self.multipliers.to_dict(),
            "intake_history": self.intake_history.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> CognitiveProfilePrim:
        """Deserialize from dict."""
        return cls(
            multipliers=MultipliersPrim.from_dict(d.get("multipliers", {})),
            intake_history=IntakeHistoryPrim.from_dict(d.get("intake_history", {})),
        )
