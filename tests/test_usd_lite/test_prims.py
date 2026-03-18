"""Prim dataclass tests — instantiation, to_dict/from_dict round-trip, validation."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cognitive_twin.usd_lite.arc_types import ArcType
from cognitive_twin.usd_lite.prims import (
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

NOW = datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------


def _make_trace(**overrides) -> TracePrim:
    defaults = dict(
        trace_id="t1",
        sdr=[0] * 2048,
        content_hash="sha256_abc",
        strength=0.87,
        last_accessed=NOW,
    )
    defaults.update(overrides)
    return TracePrim(**defaults)


def _make_layer(**overrides) -> CompositionLayerPrim:
    defaults = dict(
        layer_id="l1",
        arc_type=ArcType.LOCAL,
        opinion={"key": "value"},
        timestamp=NOW,
    )
    defaults.update(overrides)
    return CompositionLayerPrim(**defaults)


# ---------------------------------------------------------------
# Instantiation tests
# ---------------------------------------------------------------


class TestInstantiationDefaults:
    """All prims instantiate with minimal required fields."""

    def test_trace_prim(self) -> None:
        t = _make_trace()
        assert t.trace_id == "t1"
        assert len(t.sdr) == 2048
        assert t.co_activations == {}
        assert t.competitions == {}
        assert len(t.hebbian_strengthen_mask) == 2048
        assert len(t.hebbian_weaken_mask) == 2048

    def test_composition_layer_prim(self) -> None:
        layer = _make_layer()
        assert layer.permanent is False
        assert layer.provenance is None

    def test_gate_status_prim(self) -> None:
        gs = GateStatusPrim(
            verification_state=VerificationState.PENDING,
            cycle_count=0,
            last_verified=NOW,
        )
        assert gs.cycle_count == 0

    def test_merkle_root_prim(self) -> None:
        mr = MerkleRootPrim(root_hash="abc", trace_count=10)
        assert mr.trace_count == 10

    def test_session_prim(self) -> None:
        s = SessionPrim(current_session_id="s1", exchange_count=5)
        assert s.surprise_rolling_mean == 0.0
        assert s.last_retrieval_path == RetrievalPath.SYSTEM_1

    def test_inquiry_prim(self) -> None:
        ip = InquiryPrim(hypothesis="test", confidence=0.5)
        assert ip.confidence == 0.5

    def test_motor_prim(self) -> None:
        mp = MotorPrim(action="test", gate_status=MotorGateStatus.INHIBITED)
        assert mp.gate_status == MotorGateStatus.INHIBITED

    def test_skill_prim(self) -> None:
        sp = SkillPrim(domain="math", trace_count=10, first_seen=NOW, last_seen=NOW)
        assert sp.growth_arc == []
        assert sp.hebbian_density == 0.0

    def test_multipliers_prim(self) -> None:
        m = MultipliersPrim()
        assert m.surprise_threshold == 2.0
        assert m.detail_orientation == 0.5

    def test_intake_history_prim(self) -> None:
        ih = IntakeHistoryPrim()
        assert ih.last_intake is None
        assert ih.answer_embeddings == []

    def test_provenance(self) -> None:
        p = Provenance(
            source_type=SourceType.USER_DIRECT,
            origin_timestamp=NOW,
            event_hash="hash123",
            session_id="sess1",
        )
        assert p.source_type == SourceType.USER_DIRECT


class TestContainerPrims:
    """Container prims instantiate with empty defaults."""

    def test_association_prim(self) -> None:
        a = AssociationPrim()
        assert a.traces == {}

    def test_composition_prim(self) -> None:
        c = CompositionPrim()
        assert c.layers == {}

    def test_elenchus_prim(self) -> None:
        a = ElenchusPrim()
        assert a.gate_status is None
        assert a.merkle_root is None

    def test_inquiry_container(self) -> None:
        ic = InquiryContainerPrim()
        assert ic.active == []

    def test_motor_container(self) -> None:
        mc = MotorContainerPrim()
        assert mc.pending == []

    def test_skills_container(self) -> None:
        sc = SkillsContainerPrim()
        assert sc.domains == {}

    def test_cognitive_profile(self) -> None:
        cp = CognitiveProfilePrim()
        assert cp.multipliers.surprise_threshold == 2.0
        assert cp.intake_history.last_intake is None


# ---------------------------------------------------------------
# to_dict / from_dict round-trip
# ---------------------------------------------------------------


class TestDictRoundTrip:
    """to_dict(prim) -> from_dict -> equals original."""

    def test_trace_roundtrip(self) -> None:
        t = _make_trace(co_activations={"t2": 3}, competitions={"t3": 1})
        assert TracePrim.from_dict(t.to_dict()).to_dict() == t.to_dict()

    def test_layer_roundtrip(self) -> None:
        layer = _make_layer()
        assert CompositionLayerPrim.from_dict(layer.to_dict()).to_dict() == layer.to_dict()

    def test_layer_with_provenance_roundtrip(self) -> None:
        prov = Provenance(
            source_type=SourceType.SYSTEM_INFERRED,
            origin_timestamp=NOW,
            event_hash="hash",
            session_id="s1",
        )
        layer = _make_layer(provenance=prov, permanent=True)
        restored = CompositionLayerPrim.from_dict(layer.to_dict())
        assert restored.provenance is not None
        assert restored.provenance.source_type == SourceType.SYSTEM_INFERRED
        assert restored.permanent is True

    def test_gate_status_roundtrip(self) -> None:
        gs = GateStatusPrim(
            verification_state=VerificationState.TRUSTED,
            cycle_count=2,
            last_verified=NOW,
        )
        restored = GateStatusPrim.from_dict(gs.to_dict())
        assert restored.verification_state == VerificationState.TRUSTED
        assert restored.cycle_count == 2

    def test_merkle_root_roundtrip(self) -> None:
        mr = MerkleRootPrim(root_hash="abc123", trace_count=42)
        assert MerkleRootPrim.from_dict(mr.to_dict()).to_dict() == mr.to_dict()

    def test_session_roundtrip(self) -> None:
        s = SessionPrim(
            current_session_id="s1",
            exchange_count=10,
            surprise_rolling_mean=12.5,
            surprise_rolling_std=3.2,
            last_query_surprise=1.8,
            last_retrieval_path=RetrievalPath.SYSTEM_2,
        )
        restored = SessionPrim.from_dict(s.to_dict())
        assert restored.last_retrieval_path == RetrievalPath.SYSTEM_2
        assert restored.surprise_rolling_mean == 12.5

    def test_inquiry_roundtrip(self) -> None:
        ip = InquiryPrim(hypothesis="test hypothesis", confidence=0.75)
        assert InquiryPrim.from_dict(ip.to_dict()).to_dict() == ip.to_dict()

    def test_motor_roundtrip(self) -> None:
        mp = MotorPrim(action="send_email", gate_status=MotorGateStatus.APPROVED)
        restored = MotorPrim.from_dict(mp.to_dict())
        assert restored.gate_status == MotorGateStatus.APPROVED

    def test_skill_roundtrip(self) -> None:
        sp = SkillPrim(
            domain="python",
            trace_count=50,
            first_seen=NOW,
            last_seen=NOW,
            growth_arc=[0.1, 0.3, 0.5, 0.8],
            hebbian_density=0.42,
        )
        assert SkillPrim.from_dict(sp.to_dict()).to_dict() == sp.to_dict()

    def test_multipliers_roundtrip(self) -> None:
        m = MultipliersPrim(
            surprise_threshold=2.3,
            reconstruction_threshold=0.25,
            hebbian_alpha=0.015,
            allostatic_threshold=0.8,
            detail_orientation=0.4,
        )
        assert MultipliersPrim.from_dict(m.to_dict()).to_dict() == m.to_dict()

    def test_intake_history_roundtrip(self) -> None:
        ih = IntakeHistoryPrim(
            last_intake=NOW,
            intake_version="1.0",
            answer_embeddings=[0.1, 0.2, 0.3],
        )
        restored = IntakeHistoryPrim.from_dict(ih.to_dict())
        assert restored.last_intake is not None
        assert restored.intake_version == "1.0"

    def test_intake_history_none_roundtrip(self) -> None:
        ih = IntakeHistoryPrim()
        restored = IntakeHistoryPrim.from_dict(ih.to_dict())
        assert restored.last_intake is None
        assert restored.intake_version is None

    def test_association_container_roundtrip(self) -> None:
        t = _make_trace()
        a = AssociationPrim(traces={"t1": t})
        restored = AssociationPrim.from_dict(a.to_dict())
        assert "t1" in restored.traces
        assert restored.traces["t1"].strength == 0.87

    def test_elenchus_container_roundtrip(self) -> None:
        ale = ElenchusPrim(
            gate_status=GateStatusPrim(
                verification_state=VerificationState.CONTESTED,
                cycle_count=1,
                last_verified=NOW,
            ),
            merkle_root=MerkleRootPrim(root_hash="hash", trace_count=5),
        )
        restored = ElenchusPrim.from_dict(ale.to_dict())
        assert restored.gate_status is not None
        assert restored.gate_status.verification_state == VerificationState.CONTESTED
        assert restored.merkle_root is not None
        assert restored.merkle_root.trace_count == 5

    def test_cognitive_profile_roundtrip(self) -> None:
        cp = CognitiveProfilePrim(
            multipliers=MultipliersPrim(surprise_threshold=2.5),
            intake_history=IntakeHistoryPrim(intake_version="2.0"),
        )
        restored = CognitiveProfilePrim.from_dict(cp.to_dict())
        assert restored.multipliers.surprise_threshold == 2.5
        assert restored.intake_history.intake_version == "2.0"


class TestEnumValues:
    """Enum values are valid strings."""

    def test_source_type_values(self) -> None:
        for st in SourceType:
            assert isinstance(st.value, str)

    def test_verification_state_values(self) -> None:
        for vs in VerificationState:
            assert isinstance(vs.value, str)

    def test_retrieval_path_values(self) -> None:
        assert RetrievalPath.SYSTEM_1.value == "system_1"
        assert RetrievalPath.SYSTEM_2.value == "system_2"

    def test_motor_gate_status_values(self) -> None:
        assert len(MotorGateStatus) == 3

    def test_invalid_source_type_raises(self) -> None:
        with pytest.raises(ValueError):
            SourceType("nonexistent")

    def test_invalid_verification_state_raises(self) -> None:
        with pytest.raises(ValueError):
            VerificationState("nonexistent")


class TestMutableDefaults:
    """Mutable defaults are independent across instances."""

    def test_trace_masks_independent(self) -> None:
        t1 = _make_trace()
        t2 = _make_trace()
        t1.hebbian_strengthen_mask[0] = 1
        assert t2.hebbian_strengthen_mask[0] == 0

    def test_trace_dicts_independent(self) -> None:
        t1 = _make_trace()
        t2 = _make_trace()
        t1.co_activations["x"] = 1
        assert "x" not in t2.co_activations

    def test_association_traces_independent(self) -> None:
        a1 = AssociationPrim()
        a2 = AssociationPrim()
        a1.traces["t"] = _make_trace()
        assert "t" not in a2.traces
