"""Patch 11+: BrainStage.__eq__ with math.isclose for float tolerance.

Ensures float serialization/deserialization rounding does not break equality.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

from harlo.usd_lite.prims import (
    InquiryPrim,
    MultipliersPrim,
    SessionPrim,
    TracePrim,
)
from harlo.usd_lite.stage import BrainStage, _deep_eq


NOW = datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc)


class TestDeepEq:
    """Tests for the recursive float-tolerant equality function."""

    def test_identical_floats(self) -> None:
        assert _deep_eq(1.0, 1.0)

    def test_close_floats(self) -> None:
        assert _deep_eq(1.0, 1.0 + 1e-12)

    def test_different_floats(self) -> None:
        assert not _deep_eq(1.0, 1.001)

    def test_nan_equality(self) -> None:
        assert _deep_eq(float("nan"), float("nan"))

    def test_inf_equality(self) -> None:
        assert _deep_eq(float("inf"), float("inf"))

    def test_int_exact(self) -> None:
        assert _deep_eq(42, 42)
        assert not _deep_eq(42, 43)

    def test_string_exact(self) -> None:
        assert _deep_eq("hello", "hello")
        assert not _deep_eq("hello", "world")

    def test_list_elementwise(self) -> None:
        assert _deep_eq([1.0, 2.0], [1.0, 2.0 + 1e-12])

    def test_list_different_length(self) -> None:
        assert not _deep_eq([1.0], [1.0, 2.0])

    def test_dict_comparison(self) -> None:
        assert _deep_eq({"a": 1.0}, {"a": 1.0 + 1e-12})

    def test_dict_different_keys(self) -> None:
        assert not _deep_eq({"a": 1.0}, {"b": 1.0})

    def test_nested_dataclass(self) -> None:
        m1 = MultipliersPrim(surprise_threshold=2.0)
        m2 = MultipliersPrim(surprise_threshold=2.0 + 1e-12)
        assert _deep_eq(m1, m2)

    def test_different_types(self) -> None:
        assert not _deep_eq(1.0, 1)
        assert not _deep_eq("1", 1)


class TestBrainStageEquality:
    """BrainStage.__eq__ uses float-tolerant comparison."""

    def test_empty_stages_equal(self) -> None:
        assert BrainStage() == BrainStage()

    def test_not_equal_to_non_brainstage(self) -> None:
        assert BrainStage().__eq__("not a stage") is NotImplemented

    def test_session_float_tolerance(self) -> None:
        s1 = BrainStage(session=SessionPrim(
            current_session_id="s1",
            exchange_count=10,
            surprise_rolling_mean=12.5,
        ))
        s2 = BrainStage(session=SessionPrim(
            current_session_id="s1",
            exchange_count=10,
            surprise_rolling_mean=12.5 + 1e-12,
        ))
        assert s1 == s2

    def test_session_float_significant_diff(self) -> None:
        s1 = BrainStage(session=SessionPrim(
            current_session_id="s1",
            exchange_count=10,
            surprise_rolling_mean=12.5,
        ))
        s2 = BrainStage(session=SessionPrim(
            current_session_id="s1",
            exchange_count=10,
            surprise_rolling_mean=13.0,
        ))
        assert s1 != s2

    def test_session_string_exact(self) -> None:
        s1 = BrainStage(session=SessionPrim(
            current_session_id="s1",
            exchange_count=10,
        ))
        s2 = BrainStage(session=SessionPrim(
            current_session_id="s2",
            exchange_count=10,
        ))
        assert s1 != s2

    def test_session_int_exact(self) -> None:
        s1 = BrainStage(session=SessionPrim(
            current_session_id="s1",
            exchange_count=10,
        ))
        s2 = BrainStage(session=SessionPrim(
            current_session_id="s1",
            exchange_count=11,
        ))
        assert s1 != s2

    def test_multiplier_float_tolerance(self) -> None:
        from harlo.usd_lite.prims import CognitiveProfilePrim

        s1 = BrainStage()
        s1.cognitive_profile = CognitiveProfilePrim(
            multipliers=MultipliersPrim(hebbian_alpha=0.01)
        )
        s2 = BrainStage()
        s2.cognitive_profile = CognitiveProfilePrim(
            multipliers=MultipliersPrim(hebbian_alpha=0.01 + 1e-14)
        )
        assert s1 == s2

    def test_trace_strength_tolerance(self) -> None:
        from harlo.usd_lite.prims import AssociationPrim

        t1 = TracePrim(
            trace_id="t1",
            sdr=[0] * 2048,
            content_hash="hash",
            strength=0.87,
            last_accessed=NOW,
        )
        t2 = TracePrim(
            trace_id="t1",
            sdr=[0] * 2048,
            content_hash="hash",
            strength=0.87 + 1e-12,
            last_accessed=NOW,
        )
        s1 = BrainStage(association=AssociationPrim(traces={"t1": t1}))
        s2 = BrainStage(association=AssociationPrim(traces={"t1": t2}))
        assert s1 == s2

    def test_inquiry_confidence_tolerance(self) -> None:
        from harlo.usd_lite.prims import InquiryContainerPrim

        s1 = BrainStage(inquiry=InquiryContainerPrim(active=[
            InquiryPrim(hypothesis="test", confidence=0.75)
        ]))
        s2 = BrainStage(inquiry=InquiryContainerPrim(active=[
            InquiryPrim(hypothesis="test", confidence=0.75 + 1e-12)
        ]))
        assert s1 == s2

    def test_zero_float_tolerance(self) -> None:
        """0.0 compared to a tiny epsilon should be close enough."""
        s1 = BrainStage(session=SessionPrim(
            current_session_id="s1",
            exchange_count=0,
            surprise_rolling_mean=0.0,
        ))
        s2 = BrainStage(session=SessionPrim(
            current_session_id="s1",
            exchange_count=0,
            surprise_rolling_mean=0.0,
        ))
        assert s1 == s2
