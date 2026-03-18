""".usda serializer tests — round-trip fidelity for every prim type."""

from __future__ import annotations

import random
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
from cognitive_twin.usd_lite.serializer import parse, serialize
from cognitive_twin.usd_lite.stage import BrainStage


NOW = datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc)
EARLIER = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


class TestEmptyStage:
    """Empty stage round-trips."""

    def test_empty_roundtrip(self) -> None:
        stage = BrainStage()
        assert parse(serialize(stage)) == stage

    def test_header_present(self) -> None:
        text = serialize(BrainStage())
        assert text.startswith("#usda 1.0")


class TestTraceRoundTrip:
    """TracePrim serialization via hex SDR."""

    def test_single_trace(self) -> None:
        rng = random.Random(42)
        sdr = [rng.randint(0, 1) for _ in range(2048)]
        trace = TracePrim(
            trace_id="trace_001",
            sdr=sdr,
            content_hash="sha256_deadbeef",
            strength=0.87,
            last_accessed=NOW,
            co_activations={"trace_002": 5},
            competitions={"trace_003": 2},
        )
        stage = BrainStage(association=AssociationPrim(traces={"trace_001": trace}))
        restored = parse(serialize(stage))
        assert restored == stage
        assert restored.association.traces["trace_001"].sdr == sdr

    def test_multiple_traces_sorted(self) -> None:
        traces = {}
        for i in range(5):
            tid = f"trace_{i:03d}"
            traces[tid] = TracePrim(
                trace_id=tid,
                sdr=[0] * 2048,
                content_hash=f"hash_{i}",
                strength=0.5 + i * 0.1,
                last_accessed=NOW,
            )
        stage = BrainStage(association=AssociationPrim(traces=traces))
        restored = parse(serialize(stage))
        assert restored == stage

    def test_trace_with_hebbian_masks(self) -> None:
        strengthen = [0] * 2048
        weaken = [0] * 2048
        strengthen[0] = 1
        strengthen[100] = 1
        weaken[50] = 1
        trace = TracePrim(
            trace_id="t_hebb",
            sdr=[0] * 2048,
            content_hash="hash",
            strength=0.5,
            last_accessed=NOW,
            hebbian_strengthen_mask=strengthen,
            hebbian_weaken_mask=weaken,
        )
        stage = BrainStage(association=AssociationPrim(traces={"t_hebb": trace}))
        restored = parse(serialize(stage))
        assert restored.association.traces["t_hebb"].hebbian_strengthen_mask[0] == 1
        assert restored.association.traces["t_hebb"].hebbian_strengthen_mask[100] == 1
        assert restored.association.traces["t_hebb"].hebbian_weaken_mask[50] == 1


class TestCompositionRoundTrip:
    """CompositionLayerPrim serialization."""

    def test_single_layer(self) -> None:
        layer = CompositionLayerPrim(
            layer_id="layer_001",
            arc_type=ArcType.LOCAL,
            opinion={"claim": "earth is round", "confidence": 0.99},
            timestamp=NOW,
        )
        stage = BrainStage(composition=CompositionPrim(layers={"layer_001": layer}))
        assert parse(serialize(stage)) == stage

    def test_layer_with_provenance(self) -> None:
        prov = Provenance(
            source_type=SourceType.USER_DIRECT,
            origin_timestamp=NOW,
            event_hash="abc123hash",
            session_id="session_42",
        )
        layer = CompositionLayerPrim(
            layer_id="l_prov",
            arc_type=ArcType.VARIANT,
            opinion={"key": "value"},
            timestamp=NOW,
            provenance=prov,
            permanent=True,
        )
        stage = BrainStage(composition=CompositionPrim(layers={"l_prov": layer}))
        restored = parse(serialize(stage))
        assert restored == stage
        rl = restored.composition.layers["l_prov"]
        assert rl.permanent is True
        assert rl.provenance is not None
        assert rl.provenance.source_type == SourceType.USER_DIRECT

    def test_layer_without_provenance(self) -> None:
        layer = CompositionLayerPrim(
            layer_id="l_noprov",
            arc_type=ArcType.SUBLAYER,
            opinion={"x": 1},
            timestamp=NOW,
        )
        stage = BrainStage(composition=CompositionPrim(layers={"l_noprov": layer}))
        restored = parse(serialize(stage))
        assert restored.composition.layers["l_noprov"].provenance is None

    def test_all_arc_types(self) -> None:
        layers = {}
        for arc in ArcType:
            lid = f"layer_{arc.name.lower()}"
            layers[lid] = CompositionLayerPrim(
                layer_id=lid,
                arc_type=arc,
                opinion={"arc": arc.name},
                timestamp=NOW,
            )
        stage = BrainStage(composition=CompositionPrim(layers=layers))
        assert parse(serialize(stage)) == stage


class TestElenchusRoundTrip:
    """ElenchusPrim serialization."""

    def test_full_elenchus(self) -> None:
        ale = ElenchusPrim(
            gate_status=GateStatusPrim(
                verification_state=VerificationState.TRUSTED,
                cycle_count=2,
                last_verified=NOW,
            ),
            merkle_root=MerkleRootPrim(root_hash="deadbeef" * 8, trace_count=42),
        )
        stage = BrainStage(elenchus=ale)
        assert parse(serialize(stage)) == stage

    def test_empty_elenchus(self) -> None:
        stage = BrainStage(elenchus=ElenchusPrim())
        assert parse(serialize(stage)) == stage

    def test_all_verification_states(self) -> None:
        for vs in VerificationState:
            ale = ElenchusPrim(
                gate_status=GateStatusPrim(
                    verification_state=vs,
                    cycle_count=1,
                    last_verified=NOW,
                )
            )
            stage = BrainStage(elenchus=ale)
            restored = parse(serialize(stage))
            assert restored.elenchus.gate_status.verification_state == vs


class TestSessionRoundTrip:
    """SessionPrim serialization."""

    def test_session_with_all_fields(self) -> None:
        sess = SessionPrim(
            current_session_id="sess_abc",
            exchange_count=100,
            surprise_rolling_mean=15.3,
            surprise_rolling_std=4.2,
            last_query_surprise=2.1,
            last_retrieval_path=RetrievalPath.SYSTEM_2,
        )
        stage = BrainStage(session=sess)
        assert parse(serialize(stage)) == stage

    def test_session_defaults(self) -> None:
        sess = SessionPrim(current_session_id="s1", exchange_count=0)
        stage = BrainStage(session=sess)
        restored = parse(serialize(stage))
        assert restored.session.surprise_rolling_mean == 0.0
        assert restored.session.last_retrieval_path == RetrievalPath.SYSTEM_1

    def test_no_session(self) -> None:
        stage = BrainStage()
        assert stage.session is None
        restored = parse(serialize(stage))
        assert restored.session is None


class TestInquiryMotorRoundTrip:
    """Inquiry and Motor container serialization."""

    def test_inquiry_with_hypotheses(self) -> None:
        stage = BrainStage(inquiry=InquiryContainerPrim(active=[
            InquiryPrim(hypothesis="pattern detected", confidence=0.82),
            InquiryPrim(hypothesis="second hypothesis", confidence=0.45),
        ]))
        assert parse(serialize(stage)) == stage

    def test_motor_with_pending(self) -> None:
        stage = BrainStage(motor=MotorContainerPrim(pending=[
            MotorPrim(action="send_email", gate_status=MotorGateStatus.APPROVED),
            MotorPrim(action="delete_file", gate_status=MotorGateStatus.INHIBITED),
        ]))
        assert parse(serialize(stage)) == stage

    def test_empty_inquiry_and_motor(self) -> None:
        stage = BrainStage()
        restored = parse(serialize(stage))
        assert restored.inquiry.active == []
        assert restored.motor.pending == []


class TestSkillsRoundTrip:
    """Skills container serialization."""

    def test_skills_with_domains(self) -> None:
        stage = BrainStage(skills=SkillsContainerPrim(domains={
            "python": SkillPrim(
                domain="python",
                trace_count=50,
                first_seen=EARLIER,
                last_seen=NOW,
                growth_arc=[0.1, 0.3, 0.5, 0.8],
                hebbian_density=0.42,
            ),
            "math": SkillPrim(
                domain="math",
                trace_count=20,
                first_seen=EARLIER,
                last_seen=NOW,
                growth_arc=[0.2, 0.4],
                hebbian_density=0.15,
            ),
        }))
        assert parse(serialize(stage)) == stage

    def test_empty_growth_arc(self) -> None:
        stage = BrainStage(skills=SkillsContainerPrim(domains={
            "empty": SkillPrim(
                domain="empty",
                trace_count=0,
                first_seen=NOW,
                last_seen=NOW,
            ),
        }))
        assert parse(serialize(stage)) == stage


class TestCognitiveProfileRoundTrip:
    """CognitiveProfile serialization."""

    def test_full_profile(self) -> None:
        stage = BrainStage(cognitive_profile=CognitiveProfilePrim(
            multipliers=MultipliersPrim(
                surprise_threshold=2.3,
                reconstruction_threshold=0.25,
                hebbian_alpha=0.015,
                allostatic_threshold=0.8,
                detail_orientation=0.4,
            ),
            intake_history=IntakeHistoryPrim(
                last_intake=NOW,
                intake_version="1.0",
                answer_embeddings=[0.1, 0.2, 0.3],
            ),
        ))
        assert parse(serialize(stage)) == stage

    def test_default_profile(self) -> None:
        stage = BrainStage()
        restored = parse(serialize(stage))
        assert restored.cognitive_profile.multipliers.surprise_threshold == 2.0
        assert restored.cognitive_profile.intake_history.last_intake is None


class TestFullStageRoundTrip:
    """Complete stage with all prim types populated."""

    def test_fully_populated(self) -> None:
        rng = random.Random(42)
        sdr = [rng.randint(0, 1) for _ in range(2048)]

        stage = BrainStage(
            association=AssociationPrim(traces={
                "t1": TracePrim(
                    trace_id="t1",
                    sdr=sdr,
                    content_hash="hash1",
                    strength=0.9,
                    last_accessed=NOW,
                    co_activations={"t2": 3},
                ),
            }),
            composition=CompositionPrim(layers={
                "l1": CompositionLayerPrim(
                    layer_id="l1",
                    arc_type=ArcType.VARIANT,
                    opinion={"claim": "test"},
                    timestamp=NOW,
                    provenance=Provenance(
                        source_type=SourceType.HEBBIAN_DERIVED,
                        origin_timestamp=NOW,
                        event_hash="evt_hash",
                        session_id="s1",
                    ),
                    permanent=True,
                ),
            }),
            elenchus=ElenchusPrim(
                gate_status=GateStatusPrim(
                    verification_state=VerificationState.CONTESTED,
                    cycle_count=1,
                    last_verified=NOW,
                ),
                merkle_root=MerkleRootPrim(root_hash="mrhash", trace_count=1),
            ),
            session=SessionPrim(
                current_session_id="sess_full",
                exchange_count=42,
                surprise_rolling_mean=10.5,
                surprise_rolling_std=2.1,
                last_query_surprise=3.5,
                last_retrieval_path=RetrievalPath.SYSTEM_2,
            ),
            inquiry=InquiryContainerPrim(active=[
                InquiryPrim(hypothesis="full test", confidence=0.99),
            ]),
            motor=MotorContainerPrim(pending=[
                MotorPrim(action="approve", gate_status=MotorGateStatus.EXECUTING),
            ]),
            skills=SkillsContainerPrim(domains={
                "testing": SkillPrim(
                    domain="testing",
                    trace_count=100,
                    first_seen=EARLIER,
                    last_seen=NOW,
                    growth_arc=[0.1, 0.5, 0.9],
                    hebbian_density=0.7,
                ),
            }),
            cognitive_profile=CognitiveProfilePrim(
                multipliers=MultipliersPrim(
                    surprise_threshold=1.8,
                    reconstruction_threshold=0.35,
                    hebbian_alpha=0.02,
                    allostatic_threshold=0.9,
                    detail_orientation=0.7,
                ),
                intake_history=IntakeHistoryPrim(
                    last_intake=NOW,
                    intake_version="2.0",
                    answer_embeddings=[0.5, 0.6],
                ),
            ),
        )
        restored = parse(serialize(stage))
        assert restored == stage

    def test_deterministic_output(self) -> None:
        """Same stage serializes to the same string every time."""
        stage = BrainStage(session=SessionPrim(
            current_session_id="s1", exchange_count=1
        ))
        text1 = serialize(stage)
        text2 = serialize(stage)
        assert text1 == text2


class TestMalformedInput:
    """Parser raises ValueError on malformed input."""

    def test_no_header(self) -> None:
        with pytest.raises(ValueError, match="header"):
            parse('def BrainStage "Brain"\n{\n}\n')

    def test_no_brainstage(self) -> None:
        with pytest.raises(ValueError, match="BrainStage"):
            parse('#usda 1.0\ndef OtherThing "x"\n{\n}\n')

    def test_empty_string(self) -> None:
        with pytest.raises((ValueError, IndexError)):
            parse("")
