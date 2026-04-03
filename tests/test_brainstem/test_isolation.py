"""Gate 2b: Elenchus stage isolation — structural trace exclusion.

elenchus_stage() output MUST contain zero traces.
This is enforced by function signature (no trace parameter), not filtering.
"""

from __future__ import annotations

import inspect

from harlo.brainstem.stage_builder import elenchus_stage, full_stage


class TestElenchusStageIsolation:
    """elenchus_stage() structurally cannot include traces."""

    def test_no_traces_in_elenchus_stage(self) -> None:
        """Output has empty association."""
        stage = elenchus_stage()
        assert stage.association.traces == {}

    def test_no_traces_with_verification(self) -> None:
        """Even with verification data, no traces leak."""
        stage = elenchus_stage(
            verification_result={"state": "verified", "cycle_count": 1},
            merkle_root="abc123",
            trace_count=42,
        )
        assert stage.association.traces == {}
        assert stage.elenchus.merkle_root is not None
        assert stage.elenchus.merkle_root.trace_count == 42

    def test_no_traces_with_session(self) -> None:
        """Session data present but no traces."""
        stage = elenchus_stage(
            session={"session_id": "s1", "exchange_count": 10},
        )
        assert stage.association.traces == {}
        assert stage.session is not None
        assert stage.session.current_session_id == "s1"

    def test_signature_has_no_trace_param(self) -> None:
        """Structural: elenchus_stage has no parameter for traces."""
        sig = inspect.signature(elenchus_stage)
        param_names = set(sig.parameters.keys())
        # These should NOT exist
        assert "recall_result" not in param_names
        assert "traces" not in param_names
        assert "association" not in param_names

    def test_full_stage_has_trace_param(self) -> None:
        """Contrast: full_stage DOES accept recall_result."""
        sig = inspect.signature(full_stage)
        assert "recall_result" in sig.parameters

    def test_full_stage_includes_traces(self) -> None:
        """full_stage with traces populates association."""
        stage = full_stage(
            recall_result={
                "traces": [
                    {"trace_id": "t1", "strength": 0.9, "distance": 50,
                     "content_hash": "h1", "sdr": [0] * 2048},
                ],
                "confidence": 0.9,
                "context": "",
            },
        )
        assert len(stage.association.traces) == 1
        assert "t1" in stage.association.traces

    def test_elenchus_and_full_same_merkle(self) -> None:
        """Both paths produce the same Merkle root when given same hash."""
        a_stage = elenchus_stage(merkle_root="root_hash", trace_count=5)
        f_stage = full_stage(merkle_root="root_hash", trace_count=5)
        assert a_stage.elenchus.merkle_root.root_hash == f_stage.elenchus.merkle_root.root_hash
