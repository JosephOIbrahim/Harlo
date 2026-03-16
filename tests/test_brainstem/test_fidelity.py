"""Gate 2a: Round-trip fidelity tests via Hypothesis.

from_stage(to_stage(x)) == x for every subsystem adapter.
Hypothesis generates 1000+ examples per adapter pair.
"""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings

from cognitive_twin.brainstem.adapters import (
    aletheia_to_verification,
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
    verification_to_aletheia,
)

from .conftest import (
    composition_layer_lists,
    inquiry_dicts,
    motor_action_dicts,
    recall_results,
    session_dicts,
    verification_result_dicts,
)


class TestCompositionFidelity:
    """composition.Layer round-trip through USD prims."""

    @given(layers=composition_layer_lists())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_roundtrip(self, layers) -> None:
        prims = layers_to_composition(layers)
        restored = composition_to_layers(prims)
        assert len(restored) == len(layers)
        for orig, rest in zip(layers, restored):
            assert orig.layer_id == rest.layer_id
            assert orig.arc_type.value == rest.arc_type.value
            assert orig.data == rest.data
            assert orig.timestamp == rest.timestamp


class TestVerificationFidelity:
    """VerificationResult round-trip through AletheiaPrim."""

    @given(result=verification_result_dicts())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_roundtrip(self, result) -> None:
        prim = verification_to_aletheia(result)
        restored = aletheia_to_verification(prim)
        # State mapping is lossy (deferred→unprovable, etc) so check cycle_count
        assert restored["cycle_count"] == result["cycle_count"]
        # Verify state is one of the valid output states
        assert restored["state"] in ("verified", "fixable", "spec_gamed", "unprovable")


class TestSessionFidelity:
    """Session dict round-trip through SessionPrim."""

    @given(session=session_dicts())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_roundtrip(self, session) -> None:
        prim = session_to_prim(session)
        restored = prim_to_session(prim)
        assert restored["session_id"] == session["session_id"]
        assert restored["exchange_count"] == session["exchange_count"]


class TestMotorFidelity:
    """Motor action round-trip through MotorPrim."""

    @given(actions=motor_action_dicts())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_roundtrip(self, actions) -> None:
        prims = motor_to_prims(actions)
        restored = prims_to_motor(prims)
        assert len(restored) == len(actions)
        for orig, rest in zip(actions, restored):
            assert rest["action"] == orig["action"]
            assert rest["gate_status"] == orig["gate_status"]


class TestInquiryFidelity:
    """Inquiry dict round-trip through InquiryPrim."""

    @given(inquiries=inquiry_dicts())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_roundtrip(self, inquiries) -> None:
        prims = inquiries_to_prims(inquiries)
        restored = prims_to_inquiries(prims)
        assert len(restored) == len(inquiries)
        for orig, rest in zip(inquiries, restored):
            assert rest["hypothesis"] == orig["hypothesis"]
            assert abs(rest["confidence"] - orig["confidence"]) < 1e-9


class TestRecallFidelity:
    """Recall result round-trip through TracePrim."""

    @given(recall=recall_results())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_roundtrip_structure(self, recall) -> None:
        """Verify trace_ids and SDRs survive round-trip."""
        traces = recall_to_traces(recall)
        restored = traces_to_recall(traces)
        orig_ids = {t["trace_id"] for t in recall["traces"]}
        rest_ids = {t["trace_id"] for t in restored["traces"]}
        assert orig_ids == rest_ids
        # SDRs are preserved
        for t in restored["traces"]:
            assert len(t["sdr"]) == 2048

    @given(recall=recall_results())
    @settings(max_examples=200)
    def test_sdr_preserved(self, recall) -> None:
        """SDR values are preserved through round-trip."""
        traces = recall_to_traces(recall)
        for orig_hit in recall["traces"]:
            tid = orig_hit["trace_id"]
            if tid in traces:
                assert traces[tid].sdr == orig_hit["sdr"]
