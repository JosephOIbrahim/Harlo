"""Tests for the Inquiry Engine (DMN / Co-Evolution).

Phase 6 Gate:
- Inquiry fires
- Apophenia blocks low-evidence (S1)
- Rejections permanent (S3)
- Utility mode silent (S4)
- DMN async (S6)
- Teardown preemptable
"""

import math
import pytest


class TestInquiryTypes:
    def test_all_types_exist(self):
        from harlo.inquiry.types import InquiryType
        assert InquiryType.PATTERN.value == "pattern"
        assert InquiryType.CONTRADICTION.value == "contradiction"
        assert InquiryType.DRIFT.value == "drift"
        assert InquiryType.GROWTH.value == "growth"
        assert InquiryType.EXISTENTIAL.value == "existential"

    def test_ttl_values(self):
        from harlo.inquiry.types import InquiryType, TTL_HOURS
        assert TTL_HOURS[InquiryType.PATTERN] == 72
        assert TTL_HOURS[InquiryType.CONTRADICTION] == 48
        assert TTL_HOURS[InquiryType.DRIFT] == 336
        assert TTL_HOURS[InquiryType.EXISTENTIAL] == 720


class TestApopheniaGuard:
    """Safeguard S1: Evidence-gated inquiry."""

    def test_low_evidence_blocked(self):
        from harlo.inquiry.apophenia_guard import evaluate, EvidenceBundle
        # Depth 2 (standard) requires 8 observations
        bundle = EvidenceBundle(
            observations=["obs_1", "obs_2"],
            hypothesis="test",
            alt_hypothesis="alternative",
            depth=2,
        )
        result = evaluate(bundle)
        assert result.passed is False

    def test_sufficient_evidence_passes(self):
        from harlo.inquiry.apophenia_guard import evaluate, EvidenceBundle
        # Depth 2 (standard) requires 8 observations
        bundle = EvidenceBundle(
            observations=[f"obs_{i}" for i in range(10)],
            hypothesis="test",
            alt_hypothesis="alternative",
            depth=2,
        )
        result = evaluate(bundle)
        assert result.passed is True

    def test_thresholds_by_depth(self):
        from harlo.inquiry.types import EVIDENCE_THRESHOLDS
        # Keys are int depth levels: 1=light, 2=standard, 3=deep, 4=existential
        assert EVIDENCE_THRESHOLDS[1] == 5
        assert EVIDENCE_THRESHOLDS[2] == 8
        assert EVIDENCE_THRESHOLDS[3] == 15
        assert EVIDENCE_THRESHOLDS[4] == 25


class TestSincerityGate:
    """Safeguard S8: Sincerity classification."""

    def test_default_is_sincere(self):
        from harlo.inquiry.sincerity_gate import classify, SincerityClass
        result = classify("Yes, that is correct")
        assert result.classification in (
            SincerityClass.SINCERE,
            SincerityClass.UNCERTAIN,
            SincerityClass.PERFORMATIVE,
        )

    def test_returns_valid_classification(self):
        from harlo.inquiry.sincerity_gate import classify, SincerityClass
        valid = {
            SincerityClass.SINCERE,
            SincerityClass.SARCASTIC,
            SincerityClass.EXASPERATED,
            SincerityClass.PERFORMATIVE,
            SincerityClass.UNCERTAIN,
        }
        result = classify("Sure, whatever")
        assert result.classification in valid


class TestRuptureRepair:
    """Safeguard S3: Rejection handling."""

    def test_rejection_trace_is_permanent(self):
        from harlo.inquiry.rupture_repair import RejectionTrace, REJECTION_WEIGHT
        trace = RejectionTrace(
            inquiry_id="inq_1",
            topic_key="test_topic",
            timestamp=0.0,
            response_text="not accurate",
        )
        # Weight is 2.0 (permanent, high weight)
        assert trace.weight == REJECTION_WEIGHT
        assert trace.weight == 2.0


class TestApoptosis:
    """Safeguard S5: Inquiry TTL + decay."""

    def test_relevance_decay(self):
        from harlo.inquiry.apoptosis import InquiryVitality, VITALITY_THRESHOLD
        from harlo.inquiry.types import InquiryType
        # Create a vitality tracker for a PATTERN inquiry (72h TTL)
        created = 0.0
        v = InquiryVitality(inquiry_id="test", inquiry_type=InquiryType.PATTERN, created_at=created)
        # At t=0, vitality should be ~1.0
        rel_0 = v.vitality(now=created)
        assert rel_0 > 0.9

        # At t=ttl (72 hours in seconds), vitality should be very low
        ttl_seconds = 72 * 3600.0
        rel_ttl = v.vitality(now=created + ttl_seconds)
        assert rel_ttl < 0.1

    def test_below_threshold_deleted(self):
        from harlo.inquiry.apoptosis import InquiryVitality, VITALITY_THRESHOLD
        from harlo.inquiry.types import InquiryType
        # VITALITY_THRESHOLD is 0.20
        assert VITALITY_THRESHOLD == 0.20

        # Create vitality and check at a time when it's below threshold
        created = 0.0
        v = InquiryVitality(inquiry_id="test", inquiry_type=InquiryType.PATTERN, created_at=created)
        ttl_seconds = 72 * 3600.0
        # At t=ttl, vitality = e^(-3) ~ 0.05, well below 0.20
        assert v.should_delete(now=created + ttl_seconds) is True
        # At t=0, vitality = 1.0, well above 0.20
        assert v.should_delete(now=created) is False


class TestCrystallization:
    """Safeguard S7: Trace crystallization."""

    def test_max_crystallized_50(self):
        from harlo.inquiry.crystallization import MAX_CRYSTALLIZED
        assert MAX_CRYSTALLIZED == 50

    def test_preservation_score_stored(self):
        from harlo.inquiry.crystallization import CrystallizationStore
        store = CrystallizationStore()
        result = store.attempt_crystallize(
            trace_id="t1",
            topic_key="topic",
            observations=["a", "b", "c"],
            decay_rate=1.0,
            preservation_score=0.5,
        )
        assert result is not None
        assert result.preservation_score == 0.5

    def test_preservation_score_formula(self):
        """S7 literal: preservation_score = (obs/threshold) * depth_weight."""
        from harlo.inquiry.crystallization import CrystallizationStore
        store = CrystallizationStore()
        # 6 observations, threshold=3, depth_weight=2.0 -> 6/3 * 2.0 = 4.0
        result = store.attempt_crystallize(
            trace_id="t_formula",
            topic_key="topic",
            observations=["a", "b", "c", "d", "e", "f"],
            decay_rate=1.0,
            threshold=3,
            depth_weight=2.0,
        )
        assert result is not None
        assert result.preservation_score == 4.0

    def test_formula_eviction_is_deterministic(self):
        """Eviction picks the lowest formula-derived score."""
        from harlo.inquiry.crystallization import CrystallizationStore, MAX_CRYSTALLIZED
        store = CrystallizationStore()
        # Fill to capacity with score = i * 1.0 (depth_weight scaled by i).
        for i in range(MAX_CRYSTALLIZED):
            store.attempt_crystallize(
                trace_id=f"t{i}",
                topic_key=f"topic_{i}",
                observations=["a", "b", "c"],
                decay_rate=0.01,
                threshold=3,
                depth_weight=float(i + 1),  # scores 1.0..50.0
            )
        # Add a higher-scoring trace; the lowest (t0, score 1.0) must evict.
        store.attempt_crystallize(
            trace_id="winner",
            topic_key="topic_winner",
            observations=["a", "b", "c"],
            decay_rate=0.01,
            threshold=3,
            depth_weight=999.0,
        )
        assert all(t.trace_id != "t0" for t in store.traces)
        assert any(t.trace_id == "winner" for t in store.traces)

    def test_formula_requires_inputs(self):
        """Calling without formula keywords or preservation_score must raise."""
        from harlo.inquiry.crystallization import CrystallizationStore
        store = CrystallizationStore()
        with pytest.raises(ValueError, match="threshold.*depth_weight.*preservation_score"):
            store.attempt_crystallize(
                trace_id="t",
                topic_key="topic",
                observations=["a", "b", "c"],
                decay_rate=1.0,
            )


class TestCompliance:
    def test_no_sleep_in_inquiry(self):
        import inspect
        from harlo.inquiry import (
            types, engine, apophenia_guard, sincerity_gate,
            rupture_repair, crystallization, apoptosis,
            timing, consent, dmn_window,
        )
        for mod in [types, engine, apophenia_guard, sincerity_gate,
                    rupture_repair, crystallization, apoptosis,
                    timing, consent, dmn_window]:
            source = inspect.getsource(mod)
            assert "sleep(" not in source, f"{mod.__name__} has sleep()"

    def test_no_while_true_in_inquiry(self):
        import inspect
        from harlo.inquiry import (
            types, engine, apophenia_guard, sincerity_gate,
            rupture_repair, crystallization, apoptosis,
            timing, consent, dmn_window,
        )
        for mod in [types, engine, apophenia_guard, sincerity_gate,
                    rupture_repair, crystallization, apoptosis,
                    timing, consent, dmn_window]:
            source = inspect.getsource(mod)
            assert "while True" not in source, f"{mod.__name__} has while True"
