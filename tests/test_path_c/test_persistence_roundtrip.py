"""Round-trip fidelity tests for the Path C persistence layer.

Per Phase 1 design §8 + Phase 2 implementation plan §5.3.
Validates BrainStage → real-USD .usda → BrainStage round-trip
preserves all non-blocker fields under float-tolerant equality
(BrainStage.__eq__ uses math.isclose(rel_tol=1e-9)).
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest


def _import_persistence_or_skip():
    try:
        from harlo.usd_lite.persistence import write, read  # noqa: F401
    except ImportError as exc:
        pytest.skip(f"persistence layer unavailable: {exc}")


# -----------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------

@pytest.fixture
def tmp_usda(tmp_path):
    return str(tmp_path / "brain.usda")


@pytest.fixture
def empty_stage():
    from harlo.usd_lite.stage import BrainStage
    return BrainStage()


@pytest.fixture
def populated_stage():
    """A BrainStage with all 19 concrete prim types populated."""
    from harlo.usd_lite.stage import BrainStage
    from harlo.usd_lite.prims import (
        AssociationPrim, CognitiveProfilePrim, CompositionLayerPrim,
        CompositionPrim, ElenchusPrim, GateStatusPrim,
        InquiryContainerPrim, InquiryPrim, IntakeHistoryPrim,
        MerkleRootPrim, MotorContainerPrim, MotorGateStatus, MotorPrim,
        MultipliersPrim, Provenance, RetrievalPath, SessionPrim,
        SkillPrim, SkillsContainerPrim, SourceType, TracePrim,
        VerificationState,
    )
    from harlo.usd_lite.arc_types import ArcType

    ts = datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc)

    sdr = [0] * 2048
    sdr[0] = sdr[1023] = sdr[2047] = 1  # sparse pattern

    trace = TracePrim(
        trace_id="ab12cd34",
        sdr=sdr,
        content_hash="deadbeefcafebabe",
        strength=0.875,
        last_accessed=ts,
        co_activations={"other_trace_id": 3},
        competitions={"rival_trace_id": 1},
        hebbian_strengthen_mask=[0] * 2048,
        hebbian_weaken_mask=[0] * 2048,
    )

    layer = CompositionLayerPrim(
        layer_id="layer_001",
        arc_type=ArcType.LOCAL,
        opinion={"key": "value", "n": 42},
        timestamp=ts,
        provenance=Provenance(
            source_type=SourceType.USER_DIRECT,
            origin_timestamp=ts,
            event_hash="event_hash_xyz",
            session_id="sess_abc",
        ),
        permanent=True,
    )

    return BrainStage(
        association=AssociationPrim(traces={"ab12cd34": trace}),
        composition=CompositionPrim(layers={"layer_001": layer}),
        elenchus=ElenchusPrim(
            gate_status=GateStatusPrim(
                verification_state=VerificationState.TRUSTED,
                cycle_count=2,
                last_verified=ts,
            ),
            merkle_root=MerkleRootPrim(
                root_hash="merkle_root_hex",
                trace_count=1,
            ),
        ),
        session=SessionPrim(
            current_session_id="sess_abc",
            exchange_count=10,
            surprise_rolling_mean=0.42,
            surprise_rolling_std=0.13,
            last_query_surprise=0.55,
            last_retrieval_path=RetrievalPath.SYSTEM_2,
        ),
        inquiry=InquiryContainerPrim(active=[
            InquiryPrim(hypothesis="What if?", confidence=0.7),
            InquiryPrim(hypothesis="Then what?", confidence=0.3),
        ]),
        motor=MotorContainerPrim(pending=[
            MotorPrim(action="store_trace", gate_status=MotorGateStatus.APPROVED),
        ]),
        skills=SkillsContainerPrim(domains={
            "vfx": SkillPrim(
                domain="vfx",
                trace_count=42,
                first_seen=ts,
                last_seen=ts,
                growth_arc=[0.1, 0.5, 0.8],
                hebbian_density=0.65,
            ),
        }),
        cognitive_profile=CognitiveProfilePrim(
            multipliers=MultipliersPrim(
                surprise_threshold=2.0,
                reconstruction_threshold=0.3,
                hebbian_alpha=0.01,
                allostatic_threshold=1.0,
                detail_orientation=0.5,
            ),
            intake_history=IntakeHistoryPrim(
                last_intake=ts,
                intake_version="v1.0",
                answer_embeddings=[0.1, 0.2, 0.3, 0.4],
            ),
        ),
    )


# -----------------------------------------------------------------
# Round-trip tests
# -----------------------------------------------------------------

def test_empty_stage_roundtrip(tmp_usda, empty_stage):
    """An empty BrainStage round-trips losslessly."""
    _import_persistence_or_skip()
    from harlo.usd_lite.persistence import write, read

    write(empty_stage, tmp_usda)
    assert os.path.exists(tmp_usda)
    bs2 = read(tmp_usda)
    assert empty_stage == bs2


def test_populated_stage_roundtrip(tmp_usda, populated_stage):
    """A BrainStage with all 19 concrete prim types populated round-trips
    losslessly under float-tolerant equality."""
    _import_persistence_or_skip()
    from harlo.usd_lite.persistence import write, read

    write(populated_stage, tmp_usda)
    bs2 = read(tmp_usda)
    assert populated_stage == bs2


def test_no_injection_in_schema(tmp_usda, populated_stage):
    """D5: InjectionPrim and InjectionContainerPrim are NOT in the
    .usda output. The runtime dataclass keeps the field; the
    persistence layer omits it."""
    _import_persistence_or_skip()
    from harlo.usd_lite.persistence import write
    from pxr import Usd

    write(populated_stage, tmp_usda)
    stage = Usd.Stage.Open(tmp_usda)

    # No prim should claim the InjectionContainerPrim or InjectionPrim type.
    for prim in stage.TraverseAll():
        type_name = prim.GetTypeName()
        assert type_name not in ("InjectionPrim", "InjectionContainerPrim"), (
            f"D5 violation: {prim.GetPath()} has typeName {type_name}"
        )


def test_lower_case_arc_type_token(tmp_usda, populated_stage):
    """Cmd 11 / D11: arc_type token is lower-case in .usda output."""
    _import_persistence_or_skip()
    from harlo.usd_lite.persistence import write
    from pxr import Usd

    write(populated_stage, tmp_usda)
    stage = Usd.Stage.Open(tmp_usda)

    layer_prim = stage.GetPrimAtPath("/Brain/Composition/Layers/layer_001")
    assert layer_prim.IsValid(), "layer_001 not written"
    arc_attr = layer_prim.GetAttribute("arc_type")
    assert arc_attr.IsValid()
    val = arc_attr.Get()
    assert val == "local", f"expected lower-case 'local', got {val!r}"


def test_hex_sdr_codec_fidelity(tmp_usda):
    """SDR hex codec round-trips a known sparse pattern without bit-level loss."""
    _import_persistence_or_skip()
    from harlo.usd_lite.persistence import write, read
    from harlo.usd_lite.stage import BrainStage
    from harlo.usd_lite.prims import AssociationPrim, TracePrim

    # Build a deterministic sparse SDR
    sdr = [0] * 2048
    for i in [0, 7, 42, 511, 1024, 2047]:
        sdr[i] = 1

    trace = TracePrim(
        trace_id="codec_test",
        sdr=sdr,
        content_hash="x" * 16,
        strength=0.5,
        last_accessed=datetime(2026, 4, 28, tzinfo=timezone.utc),
    )

    bs = BrainStage(association=AssociationPrim(traces={"codec_test": trace}))
    write(bs, tmp_usda)
    bs2 = read(tmp_usda)

    out = bs2.association.traces["codec_test"].sdr
    assert out == sdr, "hex SDR codec round-trip lost bit-level fidelity"


def test_json_blob_codec_fidelity(tmp_usda):
    """JSON-string sidecars round-trip dict and list payloads."""
    _import_persistence_or_skip()
    from harlo.usd_lite.persistence import write, read
    from harlo.usd_lite.stage import BrainStage
    from harlo.usd_lite.prims import (
        AssociationPrim, TracePrim, CognitiveProfilePrim, MultipliersPrim,
        IntakeHistoryPrim,
    )

    co_acts = {"trace_a": 5, "trace_b": 12, "trace_c": 1}
    embeddings = [0.0, 0.1, -0.5, 1.5, 1e-6]

    trace = TracePrim(
        trace_id="json_test",
        sdr=[0] * 2048,
        content_hash="y" * 16,
        strength=1.0,
        last_accessed=datetime(2026, 4, 28, tzinfo=timezone.utc),
        co_activations=co_acts,
    )
    bs = BrainStage(
        association=AssociationPrim(traces={"json_test": trace}),
        cognitive_profile=CognitiveProfilePrim(
            multipliers=MultipliersPrim(),
            intake_history=IntakeHistoryPrim(answer_embeddings=embeddings),
        ),
    )
    write(bs, tmp_usda)
    bs2 = read(tmp_usda)

    assert bs2.association.traces["json_test"].co_activations == co_acts
    assert bs2.cognitive_profile.intake_history.answer_embeddings == embeddings


def test_roundtrip_byte_stability(tmp_usda, populated_stage):
    """Adversarial: write-read-write produces byte-identical .usda output.

    Catches non-deterministic attribute ordering. With declaration-order
    discipline (alphabetical attrs in HarloSchema.usda), USD's writer
    should emit attributes in the same order each run."""
    _import_persistence_or_skip()
    from harlo.usd_lite.persistence import write, read

    write(populated_stage, tmp_usda)
    bytes_1 = Path(tmp_usda).read_bytes()
    bs2 = read(tmp_usda)

    # Write the round-tripped stage to a second path and compare bytes
    second_path = tmp_usda.replace(".usda", "_second.usda")
    write(bs2, second_path)
    bytes_2 = Path(second_path).read_bytes()

    assert bytes_1 == bytes_2, (
        f"byte-stability FAIL\n"
        f"file 1: {len(bytes_1)} bytes\nfile 2: {len(bytes_2)} bytes"
    )


def test_writer_omits_optional_session(tmp_usda, empty_stage):
    """SessionPrim is optional; absent on disk if BrainStage.session is None."""
    _import_persistence_or_skip()
    from harlo.usd_lite.persistence import write
    from pxr import Usd

    assert empty_stage.session is None
    write(empty_stage, tmp_usda)
    stage = Usd.Stage.Open(tmp_usda)
    assert not stage.GetPrimAtPath("/Brain/Session").IsValid()


def test_writer_creates_session_when_present(tmp_usda):
    """SessionPrim written to /Brain/Session when present."""
    _import_persistence_or_skip()
    from harlo.usd_lite.persistence import write
    from harlo.usd_lite.stage import BrainStage
    from harlo.usd_lite.prims import SessionPrim, RetrievalPath
    from pxr import Usd

    bs = BrainStage(session=SessionPrim(
        current_session_id="sess_xyz",
        exchange_count=7,
        surprise_rolling_mean=0.0,
        surprise_rolling_std=0.0,
        last_query_surprise=0.0,
        last_retrieval_path=RetrievalPath.SYSTEM_1,
    ))
    write(bs, tmp_usda)
    stage = Usd.Stage.Open(tmp_usda)
    sess = stage.GetPrimAtPath("/Brain/Session")
    assert sess.IsValid()
    assert sess.GetTypeName() == "SessionPrim"
    assert sess.GetAttribute("current_session_id").Get() == "sess_xyz"
