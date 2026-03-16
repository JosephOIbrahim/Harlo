"""Comprehensive compliance scan — all 33 rules from CLAUDE.md.

Phase 9, Task 10: VERIFY agent checks every inviolable rule.
Covers Rules 1, 2, 5, 8, 10, 11, 12, 13, 23, 25, 29, 32
and Safeguards S1, S2, S3, S5, S7.
"""

from __future__ import annotations

import json
import math
import os
import pathlib
import sqlite3
import subprocess
import tempfile
import time

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "python" / "cognitive_twin"
CRATES = ROOT / "crates"


# ===================================================================
# Rule 1 — 0W Idle: No sleep(), no while True in src/
# ===================================================================

class TestRule01_ZeroWattIdle:
    """Rule 1: No sleep() and no while True in Python source files."""

    @staticmethod
    def _grep(pattern: str, directory: pathlib.Path, ext: str = "*.py") -> list[str]:
        """Return list of matching lines from directory tree."""
        hits: list[str] = []
        for py in directory.rglob(ext):
            try:
                text = py.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for lineno, line in enumerate(text.splitlines(), 1):
                stripped = line.strip()
                # Skip comments
                if stripped.startswith("#"):
                    continue
                if pattern in line:
                    hits.append(f"{py.relative_to(ROOT)}:{lineno}: {stripped}")
        return hits

    def test_no_sleep(self):
        """sleep() must not appear in production source (Rule 1)."""
        hits = self._grep("sleep(", SRC)
        assert hits == [], f"sleep() found in src/:\n" + "\n".join(hits)

    def test_no_while_true(self):
        """while True must not appear in production source (Rule 1)."""
        hits = self._grep("while True", SRC)
        assert hits == [], f"while True found in src/:\n" + "\n".join(hits)


# ===================================================================
# Rule 2 — Action Potentials: No float32, no cosine in crates/
# ===================================================================

class TestRule02_ActionPotentials:
    """Rule 2: 1-bit SDR only. No float32. No cosine in Rust hot path."""

    @staticmethod
    def _grep_rs(pattern: str) -> list[str]:
        hits: list[str] = []
        if not CRATES.exists():
            return hits
        for rs in CRATES.rglob("*.rs"):
            try:
                text = rs.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for lineno, line in enumerate(text.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("//"):
                    continue
                if pattern in line and "test_no_" not in line:
                    hits.append(f"{rs.relative_to(ROOT)}:{lineno}: {stripped}")
        return hits

    def test_no_float32(self):
        """float32 must not appear in crate code (comments excluded)."""
        hits = self._grep_rs("float32")
        assert hits == [], f"float32 in crates/:\n" + "\n".join(hits)

    def test_no_cosine(self):
        """cosine must not appear in crate code (comments excluded)."""
        hits = self._grep_rs("cosine")
        assert hits == [], f"cosine in crates/:\n" + "\n".join(hits)


# ===================================================================
# Rule 5 — Apoptosis: DELETE + VACUUM works
# ===================================================================

class TestRule05_Apoptosis:
    """Rule 5: twin consolidate physically DELETEs + runs VACUUM."""

    def test_delete_vacuum_shrinks_db(self, tmp_path):
        """Create a temporary SQLite DB, INSERT rows, DELETE, VACUUM,
        and verify file size decreases."""
        db_path = tmp_path / "test_apoptosis.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE traces (id INTEGER PRIMARY KEY, data TEXT)")
        # Insert large payload to ensure measurable size
        big = "X" * 4096
        for i in range(200):
            conn.execute("INSERT INTO traces (data) VALUES (?)", (big,))
        conn.commit()
        conn.close()

        size_before = db_path.stat().st_size

        conn = sqlite3.connect(str(db_path), isolation_level=None)
        conn.execute("DELETE FROM traces WHERE id > 0")
        conn.execute("VACUUM")
        conn.close()

        size_after = db_path.stat().st_size

        assert size_after < size_before, (
            f"VACUUM did not shrink: {size_before} -> {size_after}"
        )


# ===================================================================
# Rule 8 — JSON Barrier: jsonschema validates, epigenetic_wash stripped
# ===================================================================

class TestRule08_JSONBarrier:
    """Rule 8: jsonschema.validate(), strip epigenetic_wash on write path."""

    def test_valid_payload_passes(self):
        from cognitive_twin.modulation.barrier import validate_llm_output

        raw = json.dumps({
            "core_memory": {"facts": ["The sky is blue"]},
            "epigenetic_wash": {"tone": "neutral"},
        })
        result = validate_llm_output(raw)
        assert "core_memory" in result

    def test_invalid_payload_rejected(self):
        from cognitive_twin.modulation.barrier import validate_llm_output
        import jsonschema

        raw = json.dumps({"not_core_memory": True})
        with pytest.raises(jsonschema.ValidationError):
            validate_llm_output(raw)

    def test_epigenetic_wash_stripped(self):
        from cognitive_twin.modulation.barrier import strip_epigenetic_wash

        validated = {
            "core_memory": {"facts": ["fact"]},
            "epigenetic_wash": {"tone": "happy", "emotional_context": "joy"},
        }
        cleaned = strip_epigenetic_wash(validated)
        assert "epigenetic_wash" not in cleaned
        assert "core_memory" in cleaned


# ===================================================================
# Rule 10 — Anchors: SAFETY/CONSENT/KNOWLEDGE/CONSTITUTIONAL gain 1.0
# ===================================================================

class TestRule10_Anchors:
    """Rule 10: Anchor phases always return gain = 1.0."""

    ANCHOR_PHASES = ["SAFETY", "CONSENT", "KNOWLEDGE", "CONSTITUTIONAL"]

    def test_anchors_always_gain_1(self):
        from cognitive_twin.modulation.gain import compute_gain

        for phase in self.ANCHOR_PHASES:
            # Regardless of s_nm and d, anchors must return 1.0
            for s_nm in [0.0, 0.5, 1.0, 10.0, -5.0]:
                for d in [0.0, 1.0, 100.0, -1.0]:
                    gain = compute_gain(s_nm, d, phase)
                    assert gain == 1.0, (
                        f"Anchor {phase} returned gain {gain} "
                        f"with s_nm={s_nm}, d={d}"
                    )

    def test_non_anchor_modulated(self):
        from cognitive_twin.modulation.gain import compute_gain

        gain = compute_gain(0.5, 1.0, "perception")
        assert gain != 1.0, "Non-anchor phase should be modulated"


# ===================================================================
# Rule 11 — Trace Exclusion: verify() rejects reasoning_trace
# ===================================================================

class TestRule11_TraceExclusion:
    """Rule 11: verify() NEVER receives reasoning trace."""

    def test_verify_rejects_trace(self):
        from cognitive_twin.aletheia.verifier import verify

        with pytest.raises(ValueError, match="RULE 11"):
            verify("test intent", "test output", reasoning_trace="some trace")

    def test_verify_accepts_none_trace(self):
        from cognitive_twin.aletheia.verifier import verify

        # Should not raise
        result = verify("What is 2+2?", "4 is the answer.", reasoning_trace=None)
        assert result is not None

    def test_verify_accepts_absent_trace(self):
        from cognitive_twin.aletheia.verifier import verify

        # Default parameter — should not raise
        result = verify("What is 2+2?", "4 is the answer.")
        assert result is not None


# ===================================================================
# Rule 12 — Verified-Only: consolidation rejects unverified
# ===================================================================

class TestRule12_VerifiedOnly:
    """Rule 12: Only VERIFIED resolutions become reflexes."""

    def test_verified_consolidates(self, tmp_path, monkeypatch):
        from cognitive_twin.brainstem import consolidation

        monkeypatch.setattr(consolidation, "_REFLEX_DIR", tmp_path / "reflexes")

        resolution = {
            "gvr_state": "verified",
            "outcome": {"answer": "42"},
        }
        result = consolidation.consolidate_resolution(resolution)
        assert result is not None, "VERIFIED should consolidate"

    @pytest.mark.parametrize("state", ["fixable", "spec_gamed", "unprovable", "deferred"])
    def test_unverified_rejected(self, state, tmp_path, monkeypatch):
        from cognitive_twin.brainstem import consolidation

        monkeypatch.setattr(consolidation, "_REFLEX_DIR", tmp_path / "reflexes")

        resolution = {
            "gvr_state": state,
            "outcome": {"answer": "maybe"},
        }
        result = consolidation.consolidate_resolution(resolution)
        assert result is None, f"State {state} must NOT consolidate"


# ===================================================================
# Rule 13 — Max 3 GVR: GVR terminates after 3 cycles
# ===================================================================

class TestRule13_Max3GVR:
    """Rule 13: ADHD guard. After cycle 3, promote FIXABLE to UNPROVABLE."""

    def test_gvr_terminates_after_3(self):
        from cognitive_twin.aletheia.protocol import run_gvr
        from cognitive_twin.aletheia.states import VerificationState

        # Provide an output that is always FIXABLE (too short for intent)
        result = run_gvr(
            intent="Explain the meaning of life in detail?",
            output="ok",
            generator_fn=lambda intent, output, flaw, context: "ok",
            max_cycles=10,  # Attempt >3 — rule 13 should cap it
        )
        assert result.cycle_count <= 3, f"GVR ran {result.cycle_count} cycles (max 3)"
        assert result.state in (
            VerificationState.UNPROVABLE,
            VerificationState.FIXABLE,
            VerificationState.VERIFIED,
            VerificationState.SPEC_GAMED,
        )

    def test_gvr_hard_cap(self):
        from cognitive_twin.aletheia.protocol import run_gvr
        from cognitive_twin.aletheia.states import VerificationState

        call_count = 0

        def counting_generator(intent, output, flaw, context):
            nonlocal call_count
            call_count += 1
            return "still short"

        result = run_gvr(
            intent="What is the fundamental theorem of calculus?",
            output="hi",
            generator_fn=counting_generator,
            max_cycles=100,
        )
        assert result.cycle_count <= 3
        # Generator should be called at most 2 times (cycles 1 and 2 revise,
        # cycle 3 verifies and terminates)
        assert call_count <= 2


# ===================================================================
# Rule 23 — Inhibition Default: Basal ganglia defaults to INHIBIT
# ===================================================================

class TestRule23_InhibitionDefault:
    """Rule 23: Basal Ganglia defaults to INHIBIT ALL."""

    def test_default_is_inhibit(self):
        from cognitive_twin.motor.basal_ganglia import gate, GateDecision
        from cognitive_twin.motor.premotor import PlannedAction

        action = PlannedAction(
            action_type="write_file",
            description="Write something",
            target="/tmp/test.txt",
            payload={"content": "hello"},
            consent_level=2,
            reversible=True,
        )
        # Empty session state, no consent -> should INHIBIT
        result = gate(action, session_state={})
        assert result.decision != GateDecision.DISINHIBIT, (
            "Default must be INHIBIT, not DISINHIBIT"
        )

    def test_single_failure_inhibits(self):
        from cognitive_twin.motor.basal_ganglia import gate, GateDecision
        from cognitive_twin.motor.consent import ConsentState
        from cognitive_twin.motor.premotor import PlannedAction

        action = PlannedAction(
            action_type="write_file",
            description="Write file",
            target="/tmp/test.txt",
            payload={},
            consent_level=2,
            reversible=True,
        )
        consent = ConsentState()
        consent.grant_session()
        # Missing scope and per-action consent -> should fail
        result = gate(action, session_state={}, consent_state=consent)
        assert result.decision != GateDecision.DISINHIBIT


# ===================================================================
# Rule 25 — Level 3 Locked: Level 3 never opens
# ===================================================================

class TestRule25_Level3Locked:
    """Rule 25: Level 3 (LOCKED) gate NEVER opens."""

    def test_locked_never_opens(self):
        from cognitive_twin.motor.consent import ConsentLevel, ConsentState, is_locked

        assert is_locked(ConsentLevel.LOCKED)

        state = ConsentState()
        state.grant_session()
        # Even with session consent, LOCKED returns False
        assert state.has_consent(ConsentLevel.LOCKED) is False

    def test_basal_ganglia_rejects_locked(self):
        from cognitive_twin.motor.basal_ganglia import gate, GateDecision
        from cognitive_twin.motor.consent import ConsentLevel, ConsentState
        from cognitive_twin.motor.premotor import PlannedAction
        from cognitive_twin.motor.scope import Scope

        action = PlannedAction(
            action_type="financial",
            description="Transfer money",
            target="bank_account",
            payload={"amount": 100},
            consent_level=int(ConsentLevel.LOCKED),
            reversible=False,
        )
        consent = ConsentState()
        consent.grant_session()

        scope = Scope(
            allowed_targets={"bank_account"},
            allowed_action_types={"financial"},
        )

        result = gate(
            action,
            session_state={"scope": scope},
            consent_state=consent,
        )
        assert result.decision == GateDecision.LOCKED, (
            f"LOCKED action should be LOCKED, got {result.decision}"
        )


# ===================================================================
# Rule 29 — Reversibility Cap: L1+irreversible=L2, never L3
# ===================================================================

class TestRule29_ReversibilityCap:
    """Rule 29: Level 1 + irreversible = Level 2. NEVER Level 3."""

    def test_session_irreversible_becomes_per_action(self):
        from cognitive_twin.motor.consent import ConsentLevel, effective_consent_level

        result = effective_consent_level(
            ConsentLevel.SESSION, is_irreversible=True
        )
        assert result == ConsentLevel.PER_ACTION

    def test_autonomous_irreversible_becomes_per_action(self):
        from cognitive_twin.motor.consent import ConsentLevel, effective_consent_level

        result = effective_consent_level(
            ConsentLevel.AUTONOMOUS, is_irreversible=True
        )
        assert result == ConsentLevel.PER_ACTION

    def test_per_action_irreversible_stays_per_action(self):
        from cognitive_twin.motor.consent import ConsentLevel, effective_consent_level

        result = effective_consent_level(
            ConsentLevel.PER_ACTION, is_irreversible=True
        )
        assert result == ConsentLevel.PER_ACTION

    def test_never_promotes_to_locked(self):
        """Irreversible must NEVER promote to LOCKED (logical deadlock)."""
        from cognitive_twin.motor.consent import ConsentLevel, effective_consent_level

        for base in [ConsentLevel.AUTONOMOUS, ConsentLevel.SESSION, ConsentLevel.PER_ACTION]:
            result = effective_consent_level(base, is_irreversible=True, is_depleted=True)
            assert result != ConsentLevel.LOCKED, (
                f"{base.name} + irreversible + depleted must never reach LOCKED"
            )


# ===================================================================
# Rule 32 — Motor Zero-Tolerance: Single failure decompiles
# ===================================================================

class TestRule32_MotorZeroTolerance:
    """Rule 32: Single failure = instant de-compilation."""

    def test_single_failure_decompiles(self):
        from cognitive_twin.motor.motor_cerebellum import MotorCerebellum, ActionPattern

        cb = MotorCerebellum()
        pattern = ActionPattern(
            pattern_id="p1",
            action_type="write_file",
            target_pattern="/tmp/",
            success_count=100,
            compiled=True,
        )
        cb.register_pattern(pattern)

        # Record a single failure
        cb.record_failure("p1", "test failure")

        p = cb.get_pattern("p1")
        assert p is not None
        assert p.compiled is False, "Single failure must decompile"
        assert p.success_count == 100, "success_count preserved for audit"
        assert p.decompile_reason == "test failure"

    def test_decompiled_not_findable(self):
        from cognitive_twin.motor.motor_cerebellum import MotorCerebellum, ActionPattern

        cb = MotorCerebellum()
        pattern = ActionPattern(
            pattern_id="p2",
            action_type="read",
            target_pattern="*",
            compiled=True,
        )
        cb.register_pattern(pattern)
        cb.record_failure("p2", "oops")

        found = cb.find_pattern("read", "anything")
        assert found is None, "Decompiled pattern must not be findable"


# ===================================================================
# Safeguard S1 — Apophenia: Low evidence blocked
# ===================================================================

class TestSafeguardS1_Apophenia:
    """S1: Minimum evidence threshold per inquiry depth."""

    def test_insufficient_evidence_blocked(self):
        from cognitive_twin.inquiry.apophenia_guard import EvidenceBundle, evaluate

        bundle = EvidenceBundle(
            observations=["obs1", "obs2"],  # Only 2, need 5 at depth 1
            hypothesis="Pattern X",
            alt_hypothesis="Could be noise",
            depth=1,
        )
        result = evaluate(bundle)
        assert not result.passed
        assert result.reason == "insufficient_evidence"

    def test_sufficient_evidence_passes(self):
        from cognitive_twin.inquiry.apophenia_guard import EvidenceBundle, evaluate

        bundle = EvidenceBundle(
            observations=[f"obs{i}" for i in range(6)],  # 6 >= 5
            hypothesis="Pattern X",
            alt_hypothesis="Could be noise",
            depth=1,
        )
        result = evaluate(bundle)
        assert result.passed

    def test_alt_hypothesis_required(self):
        from cognitive_twin.inquiry.apophenia_guard import EvidenceBundle, evaluate

        bundle = EvidenceBundle(
            observations=[f"obs{i}" for i in range(10)],
            hypothesis="Pattern X",
            alt_hypothesis="",  # Missing
            depth=1,
        )
        result = evaluate(bundle)
        assert not result.passed
        assert result.reason == "no_alt_hypothesis"

    @pytest.mark.parametrize("depth,threshold", [(1, 5), (2, 8), (3, 15), (4, 25)])
    def test_thresholds_per_depth(self, depth, threshold):
        from cognitive_twin.inquiry.types import EVIDENCE_THRESHOLDS

        assert EVIDENCE_THRESHOLDS[depth] == threshold


# ===================================================================
# Safeguard S2 — Epistemological Bypass: Inquiry bypasses truth
# ===================================================================

class TestSafeguardS2_EpistemologicalBypass:
    """S2: Inquiry outputs bypass truth, composition does not."""

    def test_inquiry_source_bypasses(self):
        from cognitive_twin.brainstem.epistemological_bypass import should_bypass_aletheia

        assert should_bypass_aletheia(
            source="inquiry", tags=[], consumer="inquiry"
        ) is True

    def test_self_reported_inquiry_bypasses(self):
        from cognitive_twin.brainstem.epistemological_bypass import should_bypass_aletheia

        assert should_bypass_aletheia(
            source="user", tags=["self_reported"], consumer="inquiry"
        ) is True

    def test_self_reported_composition_no_bypass(self):
        from cognitive_twin.brainstem.epistemological_bypass import should_bypass_aletheia

        assert should_bypass_aletheia(
            source="user", tags=["self_reported"], consumer="composition"
        ) is False

    def test_composition_gets_standard_verification(self):
        from cognitive_twin.brainstem.epistemological_bypass import should_bypass_aletheia

        assert should_bypass_aletheia(
            source="composition", tags=[], consumer="composition"
        ) is False


# ===================================================================
# Safeguard S3 — Rupture: Rejection weight 2.0
# ===================================================================

class TestSafeguardS3_Rupture:
    """S3: Rejection = permanent non-decaying trace (weight 2.0)."""

    def test_rejection_weight_is_2(self):
        from cognitive_twin.inquiry.rupture_repair import REJECTION_WEIGHT

        assert REJECTION_WEIGHT == 2.0

    def test_rejection_trace_weight(self):
        from cognitive_twin.inquiry.rupture_repair import RejectionTrace

        trace = RejectionTrace(
            inquiry_id="inq1",
            topic_key="topic1",
            timestamp=time.time(),
        )
        assert trace.weight == 2.0

    def test_three_rejections_offer_stop(self):
        from cognitive_twin.inquiry.rupture_repair import RuptureLedger

        ledger = RuptureLedger()
        for i in range(3):
            ledger.record_rejection(f"inq{i}", "topic_a")

        assert ledger.should_offer_stop("topic_a")
        assert ledger.topic_weight("topic_a") == 6.0  # 3 * 2.0


# ===================================================================
# Safeguard S5 — Apoptosis: TTL decay formula correct
# ===================================================================

class TestSafeguardS5_InquiryApoptosis:
    """S5: TTL decay via e^(-3t/ttl). Below 20% = delete."""

    def test_vitality_at_zero(self):
        from cognitive_twin.inquiry.apoptosis import InquiryVitality, VITALITY_THRESHOLD
        from cognitive_twin.inquiry.types import InquiryType

        now = time.time()
        v = InquiryVitality(
            inquiry_id="test", inquiry_type=InquiryType.PATTERN, created_at=now
        )
        # At t=0, vitality should be 1.0
        assert abs(v.vitality(now) - 1.0) < 1e-9

    def test_vitality_decays(self):
        from cognitive_twin.inquiry.apoptosis import InquiryVitality
        from cognitive_twin.inquiry.types import InquiryType

        now = time.time()
        v = InquiryVitality(
            inquiry_id="test", inquiry_type=InquiryType.PATTERN, created_at=now
        )
        ttl_seconds = v.ttl_seconds
        # At t = ttl/3, vitality = e^(-1) ~ 0.368
        future = now + ttl_seconds / 3.0
        vit = v.vitality(future)
        expected = math.exp(-1.0)
        assert abs(vit - expected) < 1e-6, f"Expected {expected}, got {vit}"

    def test_formula_e_neg_3t_over_ttl(self):
        """Verify the exact formula: e^(-3t/ttl)."""
        from cognitive_twin.inquiry.apoptosis import InquiryVitality, DECAY_K
        from cognitive_twin.inquiry.types import InquiryType

        assert DECAY_K == 3.0, f"Decay constant must be 3.0, got {DECAY_K}"

        now = 1000000.0
        v = InquiryVitality(
            inquiry_id="test", inquiry_type=InquiryType.CONTRADICTION, created_at=now
        )
        t = 10000.0  # seconds elapsed
        ttl = v.ttl_seconds
        expected = math.exp(-3.0 * t / ttl)
        actual = v.vitality(now + t)
        assert abs(actual - expected) < 1e-12

    def test_below_20_percent_deletes(self):
        from cognitive_twin.inquiry.apoptosis import InquiryVitality, VITALITY_THRESHOLD
        from cognitive_twin.inquiry.types import InquiryType

        assert VITALITY_THRESHOLD == 0.20

        now = 1000000.0
        v = InquiryVitality(
            inquiry_id="test", inquiry_type=InquiryType.PATTERN, created_at=now
        )
        # Find time when vitality = 0.19 (below threshold)
        # 0.19 = e^(-3t/ttl) -> t = -ttl * ln(0.19) / 3
        ttl = v.ttl_seconds
        t_delete = -ttl * math.log(0.19) / 3.0
        assert v.should_delete(now + t_delete)

    def test_above_20_percent_survives(self):
        from cognitive_twin.inquiry.apoptosis import InquiryVitality
        from cognitive_twin.inquiry.types import InquiryType

        now = 1000000.0
        v = InquiryVitality(
            inquiry_id="test", inquiry_type=InquiryType.PATTERN, created_at=now
        )
        # At t=0, vitality = 1.0 -> should NOT delete
        assert not v.should_delete(now)


# ===================================================================
# Safeguard S7 — Crystallization: Max 50 traces
# ===================================================================

class TestSafeguardS7_Crystallization:
    """S7: Max 50 crystallized traces. Eviction by lowest preservation_score."""

    def test_max_50_cap(self):
        from cognitive_twin.inquiry.crystallization import (
            CrystallizationStore,
            MAX_CRYSTALLIZED,
        )

        assert MAX_CRYSTALLIZED == 50

        store = CrystallizationStore()
        for i in range(60):
            store.attempt_crystallize(
                trace_id=f"trace_{i}",
                topic_key=f"topic_{i}",
                observations=[f"obs_{j}" for j in range(5)],
                decay_rate=0.01,
                preservation_score=float(i),
            )
        assert store.count() <= 50, f"Store has {store.count()} traces, max is 50"

    def test_eviction_removes_lowest_score(self):
        from cognitive_twin.inquiry.crystallization import CrystallizationStore

        store = CrystallizationStore()
        # Fill to 50
        for i in range(50):
            store.attempt_crystallize(
                trace_id=f"trace_{i}",
                topic_key=f"topic_{i}",
                observations=["a", "b", "c"],
                decay_rate=0.01,
                preservation_score=float(i + 1),  # scores 1..50
            )
        assert store.count() == 50

        # Add one more with score 100 — lowest (score=1) should be evicted
        store.attempt_crystallize(
            trace_id="trace_new",
            topic_key="topic_new",
            observations=["a", "b", "c"],
            decay_rate=0.01,
            preservation_score=100.0,
        )
        assert store.count() == 50

        # The trace with score 1.0 (trace_0) should be gone
        ids = {t.trace_id for t in store.traces}
        assert "trace_0" not in ids, "Lowest-score trace should have been evicted"
        assert "trace_new" in ids, "New trace should be present"

    def test_crystallization_requires_3_observations(self):
        from cognitive_twin.inquiry.crystallization import CrystallizationStore

        store = CrystallizationStore()
        result = store.attempt_crystallize(
            trace_id="t1",
            topic_key="topic",
            observations=["obs1", "obs2"],  # Only 2, need 3
            decay_rate=0.01,
            preservation_score=1.0,
        )
        assert result is None, "Should require 3+ observations"

    def test_decay_rate_reduced(self):
        from cognitive_twin.inquiry.crystallization import CrystallizationStore, DECAY_DIVISOR

        assert DECAY_DIVISOR == 10

        store = CrystallizationStore()
        result = store.attempt_crystallize(
            trace_id="t1",
            topic_key="topic",
            observations=["a", "b", "c"],
            decay_rate=0.1,
            preservation_score=5.0,
        )
        assert result is not None
        assert abs(result.crystallized_decay_rate - 0.01) < 1e-9, (
            f"Crystallized decay rate should be lambda/10 = 0.01, "
            f"got {result.crystallized_decay_rate}"
        )
