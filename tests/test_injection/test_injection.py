"""Tests for injection state integration.

Covers: InjectionStore CRUD, twin_store with injection_state,
coach formatter injection section, pattern detection, USD-Lite prim,
and round-trip store→recall verification.
"""

from __future__ import annotations

import json
import sqlite3
import time
from unittest.mock import patch

import pytest

from harlo.injection import InjectionStore, InjectionTrace


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def db_path(tmp_path):
    """Temporary database path."""
    return str(tmp_path / "test_injection.db")


@pytest.fixture
def inj_store(db_path):
    """InjectionStore backed by a temporary database."""
    return InjectionStore(db_path)


@pytest.fixture
def sample_state():
    """A valid injection state dict for twin_store."""
    return {
        "profile": "classical",
        "s_nm": 0.020,
        "alpha": 0.95,
        "exchange_count": 4,
        "transition": "activated",
        "session_id": "sess-001",
    }


# ── InjectionStore CRUD ──────────────────────────────────────────────


class TestInjectionStore:
    """Tests for InjectionStore persistence."""

    def test_store_returns_trace_id(self, inj_store):
        """Store returns a non-empty trace_id."""
        tid = inj_store.store(
            profile="classical", s_nm=0.020, alpha=0.95,
            exchange_count=4, transition="activated",
        )
        assert isinstance(tid, str)
        assert len(tid) == 16

    def test_store_with_explicit_id(self, inj_store):
        """Store uses the provided trace_id."""
        tid = inj_store.store(
            profile="classical", s_nm=0.020, alpha=0.95,
            exchange_count=4, transition="activated",
            trace_id="custom_inj_id",
        )
        assert tid == "custom_inj_id"

    def test_store_validates_profile(self, inj_store):
        """Store rejects invalid profiles."""
        with pytest.raises(ValueError, match="Invalid profile"):
            inj_store.store(
                profile="invalid", s_nm=0.01, alpha=0.5,
                exchange_count=1, transition="activated",
            )

    def test_store_validates_transition(self, inj_store):
        """Store rejects invalid transitions."""
        with pytest.raises(ValueError, match="Invalid transition"):
            inj_store.store(
                profile="classical", s_nm=0.01, alpha=0.5,
                exchange_count=1, transition="paused",
            )

    def test_store_validates_s_nm_range(self, inj_store):
        """Store rejects s_nm outside [0.0, 0.025]."""
        with pytest.raises(ValueError, match="s_nm"):
            inj_store.store(
                profile="classical", s_nm=0.05, alpha=0.5,
                exchange_count=1, transition="activated",
            )

    def test_store_validates_alpha_range(self, inj_store):
        """Store rejects alpha outside [0.0, 1.0]."""
        with pytest.raises(ValueError, match="alpha"):
            inj_store.store(
                profile="classical", s_nm=0.01, alpha=1.5,
                exchange_count=1, transition="activated",
            )

    def test_get_recent(self, inj_store):
        """get_recent returns traces in reverse chronological order."""
        inj_store.store(
            profile="microdose", s_nm=0.005, alpha=0.3,
            exchange_count=1, transition="activated", timestamp=100.0,
        )
        inj_store.store(
            profile="classical", s_nm=0.020, alpha=0.9,
            exchange_count=5, transition="activated", timestamp=200.0,
        )
        recent = inj_store.get_recent(limit=10)
        assert len(recent) == 2
        assert recent[0].profile == "classical"  # newer first
        assert recent[1].profile == "microdose"

    def test_get_by_profile(self, inj_store):
        """get_by_profile filters correctly."""
        inj_store.store(profile="classical", s_nm=0.02, alpha=0.9,
                        exchange_count=1, transition="activated")
        inj_store.store(profile="microdose", s_nm=0.005, alpha=0.3,
                        exchange_count=2, transition="activated")
        inj_store.store(profile="classical", s_nm=0.02, alpha=0.8,
                        exchange_count=3, transition="deactivated")

        classical = inj_store.get_by_profile("classical")
        assert len(classical) == 2
        assert all(t.profile == "classical" for t in classical)

    def test_get_by_session(self, inj_store):
        """get_by_session returns traces for a specific session."""
        inj_store.store(profile="classical", s_nm=0.02, alpha=0.9,
                        exchange_count=1, transition="activated",
                        session_id="sess-A")
        inj_store.store(profile="classical", s_nm=0.02, alpha=0.5,
                        exchange_count=10, transition="deactivated",
                        session_id="sess-A")
        inj_store.store(profile="microdose", s_nm=0.005, alpha=0.3,
                        exchange_count=1, transition="activated",
                        session_id="sess-B")

        sess_a = inj_store.get_by_session("sess-A")
        assert len(sess_a) == 2
        assert all(t.session_id == "sess-A" for t in sess_a)

    def test_count(self, inj_store):
        """count returns total injection traces."""
        assert inj_store.count() == 0
        inj_store.store(profile="none", s_nm=0.0, alpha=0.0,
                        exchange_count=0, transition="deactivated")
        assert inj_store.count() == 1

    def test_search_by_profile(self, inj_store):
        """search finds traces by profile name."""
        inj_store.store(profile="classical", s_nm=0.02, alpha=0.9,
                        exchange_count=1, transition="activated")
        inj_store.store(profile="microdose", s_nm=0.005, alpha=0.3,
                        exchange_count=2, transition="activated")

        results = inj_store.search("classical")
        assert len(results) == 1
        assert results[0].profile == "classical"

    def test_search_by_transition(self, inj_store):
        """search finds traces by transition type."""
        inj_store.store(profile="classical", s_nm=0.02, alpha=0.9,
                        exchange_count=1, transition="activated")
        inj_store.store(profile="classical", s_nm=0.02, alpha=0.0,
                        exchange_count=10, transition="red_override")

        results = inj_store.search("red_override")
        assert len(results) == 1
        assert results[0].transition == "red_override"

    def test_activation_count(self, inj_store):
        """get_activation_count counts only activations."""
        inj_store.store(profile="classical", s_nm=0.02, alpha=0.9,
                        exchange_count=1, transition="activated")
        inj_store.store(profile="classical", s_nm=0.02, alpha=0.0,
                        exchange_count=10, transition="deactivated")
        inj_store.store(profile="classical", s_nm=0.02, alpha=0.9,
                        exchange_count=15, transition="activated")

        assert inj_store.get_activation_count("classical") == 2

    def test_profile_frequency(self, inj_store):
        """get_profile_frequency returns per-profile activation counts."""
        for _ in range(3):
            inj_store.store(profile="classical", s_nm=0.02, alpha=0.9,
                            exchange_count=1, transition="activated")
        inj_store.store(profile="microdose", s_nm=0.005, alpha=0.3,
                        exchange_count=1, transition="activated")

        freq = inj_store.get_profile_frequency()
        assert freq["classical"] == 3
        assert freq["microdose"] == 1

    def test_all_valid_profiles(self, inj_store):
        """All valid profiles can be stored."""
        for profile in ("none", "microdose", "perceptual", "classical", "mdma"):
            tid = inj_store.store(
                profile=profile, s_nm=0.01, alpha=0.5,
                exchange_count=1, transition="activated",
            )
            assert isinstance(tid, str)

    def test_all_valid_transitions(self, inj_store):
        """All valid transitions can be stored."""
        for transition in ("activated", "deactivated", "red_override"):
            tid = inj_store.store(
                profile="classical", s_nm=0.01, alpha=0.5,
                exchange_count=1, transition=transition,
            )
            assert isinstance(tid, str)


# ── twin_store with injection_state ──────────────────────────────────


class TestTwinStoreInjection:
    """Tests for twin_store MCP tool with injection_state parameter."""

    def test_store_without_injection_unchanged(self, tmp_path):
        """twin_store without injection_state works exactly as before."""
        import harlo.mcp_server as srv

        srv._hot_store = None
        srv._injection_store = None
        with patch.object(srv, "DATA_DIR", tmp_path):
            result = json.loads(srv.twin_store("A normal trace"))

        assert result["status"] == "stored"
        assert result["tier"] == "hot"
        assert "injection_trace_id" not in result
        srv._hot_store = None
        srv._injection_store = None

    def test_store_with_injection_state(self, tmp_path, sample_state):
        """twin_store with injection_state stores both trace and injection."""
        import harlo.mcp_server as srv

        srv._hot_store = None
        srv._injection_store = None
        with patch.object(srv, "DATA_DIR", tmp_path):
            result = json.loads(srv.twin_store(
                "Injection activated",
                tags=["injection"],
                domain="modulation",
                injection_state=sample_state,
            ))

        assert result["status"] == "stored"
        assert result["tier"] == "hot"
        assert "injection_trace_id" in result
        assert len(result["injection_trace_id"]) == 16
        srv._hot_store = None
        srv._injection_store = None

    def test_store_injection_invalid_profile_returns_error(self, tmp_path):
        """Invalid injection_state returns error, not crash."""
        import harlo.mcp_server as srv

        srv._hot_store = None
        srv._injection_store = None
        with patch.object(srv, "DATA_DIR", tmp_path):
            result = json.loads(srv.twin_store(
                "Bad injection",
                injection_state={
                    "profile": "invalid",
                    "s_nm": 0.01,
                    "alpha": 0.5,
                    "exchange_count": 1,
                    "transition": "activated",
                },
            ))

        # The hot store write succeeds, but injection validation fails
        # — the error handler catches it
        assert result["status"] == "error"
        srv._hot_store = None
        srv._injection_store = None


# ── Coach formatter injection section ────────────────────────────────


class TestCoachInjection:
    """Tests for injection history in coach formatter output."""

    def test_coach_no_injection_history(self, db_path):
        """Coach output omits injection section when no history exists."""
        from harlo.coach import project_coach
        from harlo.hot_store import HotStore

        HotStore(db_path)  # ensure schema
        result = project_coach(db_path)
        assert "<injection-history>" not in result

    def test_coach_includes_injection_section(self, db_path):
        """Coach output includes injection section when history exists."""
        from harlo.coach import project_coach
        from harlo.hot_store import HotStore

        HotStore(db_path)  # ensure schema
        inj = InjectionStore(db_path)
        inj.store(profile="classical", s_nm=0.02, alpha=0.95,
                   exchange_count=4, transition="activated",
                   session_id="sess-001")

        result = project_coach(db_path)
        assert "<injection-history>" in result
        assert "classical" in result
        assert "</injection-history>" in result

    def test_coach_injection_shows_recent_sessions(self, db_path):
        """Coach output shows recent activation summaries."""
        from harlo.coach import project_coach
        from harlo.hot_store import HotStore

        HotStore(db_path)
        inj = InjectionStore(db_path)
        inj.store(profile="classical", s_nm=0.02, alpha=0.95,
                   exchange_count=35, transition="activated", timestamp=100.0)
        inj.store(profile="perceptual", s_nm=0.015, alpha=0.8,
                   exchange_count=28, transition="activated", timestamp=200.0)

        result = project_coach(db_path)
        assert "<recent-sessions>" in result
        assert "perceptual" in result
        assert "classical" in result

    def test_coach_injection_shows_last_state(self, db_path):
        """Coach output shows last injection state."""
        from harlo.coach import project_coach
        from harlo.hot_store import HotStore

        HotStore(db_path)
        inj = InjectionStore(db_path)
        inj.store(profile="mdma", s_nm=0.025, alpha=1.0,
                   exchange_count=1, transition="activated", timestamp=300.0)

        result = project_coach(db_path)
        assert '<last-injection profile="mdma"' in result
        assert 'alpha="1.00"' in result

    def test_format_xml_no_injection(self):
        """_format_xml omits injection section when injection_history is None."""
        from harlo.coach import _format_xml

        result = _format_xml([], {}, 0)
        assert "<injection-history>" not in result

    def test_format_xml_empty_injection(self):
        """_format_xml omits injection section when injection_history is empty list."""
        from harlo.coach import _format_xml

        result = _format_xml([], {}, 0, injection_history=[])
        assert "<injection-history>" not in result


# ── Pattern detection: injection frequency ───────────────────────────


class TestInjectionPatternDetection:
    """Tests for injection frequency pattern detection."""

    def test_no_pattern_below_threshold(self, db_path):
        """No pattern detected with fewer than 3 activations."""
        from harlo.modulation.detector import PatternDetector

        inj = InjectionStore(db_path)
        inj.store(profile="classical", s_nm=0.02, alpha=0.9,
                   exchange_count=1, transition="activated")
        inj.store(profile="classical", s_nm=0.02, alpha=0.9,
                   exchange_count=5, transition="activated")

        detector = PatternDetector(db_path)
        patterns = detector.detect_all()
        injection_patterns = [p for p in patterns if p.pattern_type == "injection_frequency"]
        assert len(injection_patterns) == 0

    def test_pattern_detected_at_threshold(self, db_path):
        """Pattern detected when profile activated 3+ times."""
        from harlo.modulation.detector import PatternDetector

        inj = InjectionStore(db_path)
        for i in range(3):
            inj.store(profile="classical", s_nm=0.02, alpha=0.9,
                       exchange_count=i * 10, transition="activated",
                       trace_id=f"inj_{i}")

        detector = PatternDetector(db_path)
        patterns = detector.detect_all()
        injection_patterns = [p for p in patterns if p.pattern_type == "injection_frequency"]
        assert len(injection_patterns) == 1
        assert injection_patterns[0].topic_key == "injection:classical"
        assert injection_patterns[0].confidence == 3 / 5.0

    def test_deactivations_not_counted(self, db_path):
        """Deactivations don't count toward injection frequency pattern."""
        from harlo.modulation.detector import PatternDetector

        inj = InjectionStore(db_path)
        inj.store(profile="classical", s_nm=0.02, alpha=0.9,
                   exchange_count=1, transition="activated")
        inj.store(profile="classical", s_nm=0.02, alpha=0.0,
                   exchange_count=10, transition="deactivated")
        inj.store(profile="classical", s_nm=0.02, alpha=0.0,
                   exchange_count=15, transition="deactivated")

        detector = PatternDetector(db_path)
        patterns = detector.detect_all()
        injection_patterns = [p for p in patterns if p.pattern_type == "injection_frequency"]
        assert len(injection_patterns) == 0

    def test_multiple_profiles_detected(self, db_path):
        """Multiple profiles can each trigger independent patterns."""
        from harlo.modulation.detector import PatternDetector

        inj = InjectionStore(db_path)
        for i in range(4):
            inj.store(profile="classical", s_nm=0.02, alpha=0.9,
                       exchange_count=i, transition="activated")
        for i in range(3):
            inj.store(profile="microdose", s_nm=0.005, alpha=0.3,
                       exchange_count=i, transition="activated")

        detector = PatternDetector(db_path)
        patterns = detector.detect_all()
        injection_patterns = [p for p in patterns if p.pattern_type == "injection_frequency"]
        profiles = {p.topic_key for p in injection_patterns}
        assert "injection:classical" in profiles
        assert "injection:microdose" in profiles


# ── USD-Lite prim composition ────────────────────────────────────────


class TestInjectionPrim:
    """Tests for InjectionPrim and InjectionContainerPrim."""

    def test_prim_to_dict_round_trip(self):
        """InjectionPrim serializes and deserializes correctly."""
        from harlo.usd_lite.prims import InjectionPrim

        prim = InjectionPrim(
            profile="classical",
            s_nm=0.020,
            alpha=0.95,
            transition="activated",
            exchange_count=4,
            session_id="sess-001",
        )
        d = prim.to_dict()
        restored = InjectionPrim.from_dict(d)

        assert restored.profile == "classical"
        assert restored.s_nm == 0.020
        assert restored.alpha == 0.95
        assert restored.transition == "activated"
        assert restored.exchange_count == 4
        assert restored.session_id == "sess-001"

    def test_container_prim_round_trip(self):
        """InjectionContainerPrim serializes and deserializes correctly."""
        from harlo.usd_lite.prims import InjectionPrim, InjectionContainerPrim

        container = InjectionContainerPrim(history=[
            InjectionPrim(
                profile="classical", s_nm=0.02, alpha=0.9,
                transition="activated", exchange_count=1,
            ),
            InjectionPrim(
                profile="classical", s_nm=0.02, alpha=0.0,
                transition="deactivated", exchange_count=10,
            ),
        ])
        d = container.to_dict()
        restored = InjectionContainerPrim.from_dict(d)

        assert len(restored.history) == 2
        assert restored.history[0].profile == "classical"
        assert restored.history[1].transition == "deactivated"

    def test_brain_stage_includes_injection(self):
        """BrainStage includes injection container."""
        from harlo.usd_lite.stage import BrainStage
        from harlo.usd_lite.prims import InjectionPrim, InjectionContainerPrim

        stage = BrainStage()
        assert hasattr(stage, "injection")
        assert isinstance(stage.injection, InjectionContainerPrim)

        # Add injection and round-trip
        stage.injection = InjectionContainerPrim(history=[
            InjectionPrim(
                profile="perceptual", s_nm=0.015, alpha=0.8,
                transition="activated", exchange_count=3,
                session_id="s1",
            ),
        ])
        d = stage.to_dict()
        restored = BrainStage.from_dict(d)

        assert len(restored.injection.history) == 1
        assert restored.injection.history[0].profile == "perceptual"

    def test_brain_stage_default_empty_injection(self):
        """BrainStage defaults to empty injection container."""
        from harlo.usd_lite.stage import BrainStage

        stage = BrainStage()
        assert stage.injection.history == []

    def test_brain_stage_from_dict_without_injection_key(self):
        """BrainStage.from_dict handles missing injection key gracefully."""
        from harlo.usd_lite.stage import BrainStage

        # Simulate a pre-injection dict
        d = BrainStage().to_dict()
        del d["injection"]
        restored = BrainStage.from_dict(d)
        assert restored.injection.history == []


# ── Round-trip: store → recall → verify ──────────────────────────────


class TestRoundTrip:
    """End-to-end: store injection trace, recall it, verify fields."""

    def test_store_and_retrieve_fields_match(self, db_path):
        """Fields match after store→get_recent round trip."""
        inj = InjectionStore(db_path)
        ts = 1710000000.0
        tid = inj.store(
            profile="classical",
            s_nm=0.020,
            alpha=0.95,
            exchange_count=4,
            transition="activated",
            session_id="sess-001",
            trace_id="rt_test_001",
            timestamp=ts,
        )

        traces = inj.get_recent(limit=1)
        assert len(traces) == 1
        t = traces[0]
        assert t.trace_id == "rt_test_001"
        assert t.profile == "classical"
        assert t.s_nm == 0.020
        assert t.alpha == 0.95
        assert t.exchange_count == 4
        assert t.transition == "activated"
        assert t.session_id == "sess-001"
        assert t.timestamp == ts

    def test_store_and_search_by_profile(self, db_path):
        """Searching by profile name returns the stored trace."""
        inj = InjectionStore(db_path)
        inj.store(
            profile="classical",
            s_nm=0.020,
            alpha=0.95,
            exchange_count=4,
            transition="activated",
        )
        results = inj.search("classical")
        assert len(results) == 1
        assert results[0].profile == "classical"

    def test_boundary_values(self, db_path):
        """Edge-case boundary values store and retrieve correctly."""
        inj = InjectionStore(db_path)

        # Min values
        inj.store(profile="none", s_nm=0.0, alpha=0.0,
                   exchange_count=0, transition="deactivated",
                   trace_id="min_vals")
        t = inj.get_recent(limit=1)[0]
        assert t.s_nm == 0.0
        assert t.alpha == 0.0

        # Max values
        inj.store(profile="mdma", s_nm=0.025, alpha=1.0,
                   exchange_count=9999, transition="activated",
                   trace_id="max_vals")
        results = inj.search("mdma")
        assert len(results) == 1
        assert results[0].s_nm == 0.025
        assert results[0].alpha == 1.0
