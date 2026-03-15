"""Tests for pattern detection — Phase 1.

Tests:
- Recurring theme detection via SDR clustering
- Empty/patternless data returns nothing
- Temporal pattern detection
- Escalation pattern detection
- Pattern persistence in SQLite
- Persistence across detector instances
- Inquiry engine integration via router
- Legacy detect_pattern backward compat
- Edge cases
"""

import json
import os
import sqlite3
import tempfile
import time

import pytest

from src.modulation.detector import (
    DetectedPattern,
    PatternDetector,
    detect_pattern,
    _hamming_distance,
)


@pytest.fixture
def db_path():
    """Provide a temporary database path."""
    path = tempfile.mktemp(suffix=".db")
    yield path
    if os.path.exists(path):
        os.unlink(path)


def _store_trace_with_sdr(db_path: str, trace_id: str, message: str, sdr: bytes, created_at: int = 0):
    """Helper: store a trace with a specific SDR blob directly in SQLite."""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS traces (
            id TEXT PRIMARY KEY,
            message TEXT NOT NULL,
            sdr_blob BLOB NOT NULL,
            initial_strength REAL NOT NULL DEFAULT 1.0,
            decay_lambda REAL NOT NULL DEFAULT 0.05,
            created_at INTEGER NOT NULL,
            last_accessed INTEGER NOT NULL,
            boosts_json TEXT NOT NULL DEFAULT '[]',
            tags_json TEXT NOT NULL DEFAULT '[]',
            domain TEXT,
            source TEXT
        )
    """)
    ts = created_at or int(time.time())
    conn.execute(
        """INSERT OR REPLACE INTO traces
           (id, message, sdr_blob, initial_strength, decay_lambda,
            created_at, last_accessed, boosts_json, tags_json, domain, source)
           VALUES (?, ?, ?, 1.0, 0.05, ?, ?, '[]', '[]', NULL, NULL)""",
        (trace_id, message, sdr, ts, ts),
    )
    conn.commit()
    conn.close()


def _make_sdr(active_bits: list[int]) -> bytes:
    """Create a 256-byte SDR with specific bits set."""
    sdr = bytearray(256)
    for bit in active_bits:
        byte_idx = bit // 8
        bit_offset = bit % 8
        sdr[byte_idx] |= (1 << bit_offset)
    return bytes(sdr)


def _store_session(db_path: str, session_id: str, tokens: int, started_at: int):
    """Helper: store a closed session with allostatic token count."""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            started_at INTEGER NOT NULL,
            last_active INTEGER NOT NULL,
            exchange_count INTEGER NOT NULL DEFAULT 0,
            domain TEXT NOT NULL DEFAULT 'general',
            encoder_type TEXT NOT NULL DEFAULT 'semantic',
            closed INTEGER NOT NULL DEFAULT 0,
            history_json TEXT NOT NULL DEFAULT '[]',
            allostatic_tokens INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.execute(
        """INSERT INTO sessions
           (session_id, started_at, last_active, exchange_count, domain,
            encoder_type, closed, history_json, allostatic_tokens)
           VALUES (?, ?, ?, 5, 'general', 'semantic', 1, '[]', ?)""",
        (session_id, started_at, started_at + 100, tokens),
    )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────
# Hamming Distance
# ─────────────────────────────────────────────────────────────────────

class TestHammingDistance:
    """Test the internal hamming distance function."""

    def test_identical_zero(self):
        """Identical SDRs have zero distance."""
        sdr = _make_sdr([0, 10, 20])
        assert _hamming_distance(sdr, sdr) == 0

    def test_completely_different(self):
        """All-ones vs all-zeros have max distance."""
        a = bytes(256)
        b = bytes([0xFF] * 256)
        assert _hamming_distance(a, b) == 2048

    def test_single_bit_difference(self):
        """One bit difference gives distance 1."""
        a = _make_sdr([0])
        b = _make_sdr([])
        assert _hamming_distance(a, b) == 1


# ─────────────────────────────────────────────────────────────────────
# Recurring Theme Detection
# ─────────────────────────────────────────────────────────────────────

class TestRecurringThemes:
    """Test semantic clustering for recurring themes."""

    def test_detects_similar_cluster(self, db_path):
        """Three traces with identical SDRs should form a recurring theme."""
        sdr = _make_sdr(list(range(0, 80)))  # 80 active bits
        _store_trace_with_sdr(db_path, "t1", "cats are wonderful", sdr)
        _store_trace_with_sdr(db_path, "t2", "cats are amazing", sdr)
        _store_trace_with_sdr(db_path, "t3", "cats are great", sdr)

        detector = PatternDetector(db_path)
        patterns = detector.detect_all()
        themes = [p for p in patterns if p.pattern_type == "recurring_theme"]
        assert len(themes) >= 1
        assert len(themes[0].trace_ids) == 3

    def test_no_pattern_for_dissimilar_traces(self, db_path):
        """Traces with very different SDRs should not cluster."""
        _store_trace_with_sdr(db_path, "t1", "hello", _make_sdr(list(range(0, 80))))
        _store_trace_with_sdr(db_path, "t2", "world", _make_sdr(list(range(200, 280))))
        _store_trace_with_sdr(db_path, "t3", "test", _make_sdr(list(range(400, 480))))

        detector = PatternDetector(db_path)
        themes = [p for p in detector.detect_all() if p.pattern_type == "recurring_theme"]
        assert len(themes) == 0

    def test_requires_minimum_cluster_size(self, db_path):
        """Two similar traces should NOT form a pattern (need 3)."""
        sdr = _make_sdr(list(range(0, 80)))
        _store_trace_with_sdr(db_path, "t1", "hello", sdr)
        _store_trace_with_sdr(db_path, "t2", "hello again", sdr)

        detector = PatternDetector(db_path)
        patterns = detector.detect_all()
        assert len(patterns) == 0

    def test_multiple_clusters_detected(self, db_path):
        """Two separate clusters should be detected separately."""
        sdr_a = _make_sdr(list(range(0, 80)))
        sdr_b = _make_sdr(list(range(500, 580)))

        _store_trace_with_sdr(db_path, "a1", "topic A one", sdr_a)
        _store_trace_with_sdr(db_path, "a2", "topic A two", sdr_a)
        _store_trace_with_sdr(db_path, "a3", "topic A three", sdr_a)
        _store_trace_with_sdr(db_path, "b1", "topic B one", sdr_b)
        _store_trace_with_sdr(db_path, "b2", "topic B two", sdr_b)
        _store_trace_with_sdr(db_path, "b3", "topic B three", sdr_b)

        detector = PatternDetector(db_path)
        themes = [p for p in detector.detect_all() if p.pattern_type == "recurring_theme"]
        assert len(themes) == 2

    def test_similar_but_not_identical_cluster(self, db_path):
        """Traces with slightly different SDRs (< threshold) should cluster."""
        base_bits = list(range(0, 80))
        sdr1 = _make_sdr(base_bits)
        sdr2 = _make_sdr(base_bits[:75] + [100, 101, 102, 103, 104])  # 5 bits different
        sdr3 = _make_sdr(base_bits[:70] + [200, 201, 202, 203, 204, 205, 206, 207, 208, 209])

        _store_trace_with_sdr(db_path, "t1", "msg1", sdr1)
        _store_trace_with_sdr(db_path, "t2", "msg2", sdr2)
        _store_trace_with_sdr(db_path, "t3", "msg3", sdr3)

        # Hamming between sdr1 and sdr2 is 10 (5 removed + 5 added), well under 100
        detector = PatternDetector(db_path)
        themes = [p for p in detector.detect_all() if p.pattern_type == "recurring_theme"]
        assert len(themes) >= 1


# ─────────────────────────────────────────────────────────────────────
# Empty / Patternless Data
# ─────────────────────────────────────────────────────────────────────

class TestEmptyData:
    """Test that detector handles empty/small data correctly."""

    def test_empty_db_returns_nothing(self, db_path):
        """Empty database should return no patterns."""
        detector = PatternDetector(db_path)
        assert detector.detect_all() == []

    def test_single_trace_returns_nothing(self, db_path):
        """One trace cannot form a pattern."""
        _store_trace_with_sdr(db_path, "t1", "lonely", _make_sdr([0, 1, 2]))
        detector = PatternDetector(db_path)
        assert detector.detect_all() == []

    def test_two_traces_returns_nothing(self, db_path):
        """Two traces is below minimum cluster size."""
        sdr = _make_sdr([0, 1, 2])
        _store_trace_with_sdr(db_path, "t1", "one", sdr)
        _store_trace_with_sdr(db_path, "t2", "two", sdr)
        detector = PatternDetector(db_path)
        assert detector.detect_all() == []


# ─────────────────────────────────────────────────────────────────────
# Temporal Patterns
# ─────────────────────────────────────────────────────────────────────

class TestTemporalPatterns:
    """Test temporal proximity detection."""

    def test_temporal_cluster_within_window(self, db_path):
        """Similar traces within 24h should form a temporal pattern."""
        sdr = _make_sdr(list(range(0, 80)))
        base_time = 1000000
        _store_trace_with_sdr(db_path, "t1", "morning thought", sdr, base_time)
        _store_trace_with_sdr(db_path, "t2", "afternoon thought", sdr, base_time + 3600)
        _store_trace_with_sdr(db_path, "t3", "evening thought", sdr, base_time + 7200)

        detector = PatternDetector(db_path)
        temporals = [p for p in detector.detect_all() if p.pattern_type == "temporal"]
        assert len(temporals) >= 1

    def test_no_temporal_pattern_across_days(self, db_path):
        """Similar traces spread over many days should NOT form temporal pattern."""
        sdr = _make_sdr(list(range(0, 80)))
        _store_trace_with_sdr(db_path, "t1", "day1", sdr, 1000000)
        _store_trace_with_sdr(db_path, "t2", "day5", sdr, 1000000 + 5 * 86400)
        _store_trace_with_sdr(db_path, "t3", "day10", sdr, 1000000 + 10 * 86400)

        detector = PatternDetector(db_path)
        temporals = [p for p in detector.detect_all() if p.pattern_type == "temporal"]
        assert len(temporals) == 0


# ─────────────────────────────────────────────────────────────────────
# Escalation Detection
# ─────────────────────────────────────────────────────────────────────

class TestEscalation:
    """Test allostatic load escalation detection."""

    def test_escalation_detected(self, db_path):
        """Increasing allostatic tokens across sessions = escalation."""
        for i in range(6):
            _store_session(db_path, f"s{i}", tokens=100 * (i + 1), started_at=1000 + i * 1000)

        detector = PatternDetector(db_path)
        escalations = [p for p in detector.detect_all() if p.pattern_type == "escalation"]
        assert len(escalations) >= 1

    def test_no_escalation_stable_load(self, db_path):
        """Stable allostatic tokens should NOT trigger escalation."""
        for i in range(6):
            _store_session(db_path, f"s{i}", tokens=100, started_at=1000 + i * 1000)

        detector = PatternDetector(db_path)
        escalations = [p for p in detector.detect_all() if p.pattern_type == "escalation"]
        assert len(escalations) == 0

    def test_no_escalation_with_few_sessions(self, db_path):
        """Fewer than 3 sessions cannot detect escalation."""
        _store_session(db_path, "s1", tokens=100, started_at=1000)
        _store_session(db_path, "s2", tokens=200, started_at=2000)

        detector = PatternDetector(db_path)
        escalations = [p for p in detector.detect_all() if p.pattern_type == "escalation"]
        assert len(escalations) == 0


# ─────────────────────────────────────────────────────────────────────
# Pattern Persistence
# ─────────────────────────────────────────────────────────────────────

class TestPersistence:
    """Test pattern storage in SQLite."""

    def test_patterns_persisted_after_detection(self, db_path):
        """detect_all() should persist patterns to SQLite."""
        sdr = _make_sdr(list(range(0, 80)))
        for i in range(4):
            _store_trace_with_sdr(db_path, f"t{i}", f"msg {i}", sdr)

        detector = PatternDetector(db_path)
        detector.detect_all()

        stored = detector.get_stored_patterns()
        assert len(stored) >= 1

    def test_patterns_survive_new_instance(self, db_path):
        """Patterns should be loadable by a new PatternDetector instance."""
        sdr = _make_sdr(list(range(0, 80)))
        for i in range(4):
            _store_trace_with_sdr(db_path, f"t{i}", f"msg {i}", sdr)

        d1 = PatternDetector(db_path)
        d1.detect_all()

        d2 = PatternDetector(db_path)
        stored = d2.get_stored_patterns()
        assert len(stored) >= 1

    def test_clear_patterns(self, db_path):
        """clear_patterns() should remove all stored patterns."""
        sdr = _make_sdr(list(range(0, 80)))
        for i in range(4):
            _store_trace_with_sdr(db_path, f"t{i}", f"msg {i}", sdr)

        detector = PatternDetector(db_path)
        detector.detect_all()
        assert len(detector.get_stored_patterns()) >= 1

        deleted = detector.clear_patterns()
        assert deleted >= 1
        assert len(detector.get_stored_patterns()) == 0


# ─────────────────────────────────────────────────────────────────────
# DetectedPattern Serialization
# ─────────────────────────────────────────────────────────────────────

class TestPatternSerialization:
    """Test DetectedPattern.to_dict()."""

    def test_to_dict_has_expected_keys(self):
        """to_dict() should include all expected keys."""
        p = DetectedPattern(
            pattern_id="abc",
            pattern_type="recurring_theme",
            description="test",
            trace_ids=["t1", "t2", "t3"],
            confidence=0.5,
            detected_at=1000,
        )
        d = p.to_dict()
        assert d["pattern_id"] == "abc"
        assert d["pattern_type"] == "recurring_theme"
        assert d["evidence_count"] == 3
        assert d["confidence"] == 0.5


# ─────────────────────────────────────────────────────────────────────
# Router Integration
# ─────────────────────────────────────────────────────────────────────

class TestRouterIntegration:
    """Test detector integration through the daemon router."""

    def test_inquire_returns_patterns(self):
        """Router inquire command should return detected patterns."""
        from src.daemon.router import route_command

        result = route_command("inquire", {"depth": "standard"})
        assert result["status"] == "ok"
        assert "inquiries" in result["result"]

    def test_detect_command_exists(self):
        """Router should have a detect command."""
        from src.daemon.router import route_command

        result = route_command("detect", {})
        assert result["status"] == "ok"
        assert "patterns" in result["result"]
        assert "count" in result["result"]


# ─────────────────────────────────────────────────────────────────────
# Legacy API
# ─────────────────────────────────────────────────────────────────────

class TestLegacyAPI:
    """Test backward-compatible detect_pattern function."""

    def test_empty_messages_returns_default(self):
        """Empty messages should return 'default'."""
        assert detect_pattern([]) == "default"

    def test_adhd_pattern(self):
        """Many short messages should return 'adhd'."""
        messages = [{"content": "hi"} for _ in range(10)]
        assert detect_pattern(messages) == "adhd"

    def test_analytical_pattern(self):
        """Long messages should return 'analytical'."""
        messages = [{"content": "x" * 250} for _ in range(3)]
        assert detect_pattern(messages) == "analytical"

    def test_default_pattern(self):
        """Normal-length messages should return 'default'."""
        messages = [{"content": "A normal message of medium length"} for _ in range(3)]
        assert detect_pattern(messages) == "default"


# ─────────────────────────────────────────────────────────────────────
# Compliance
# ─────────────────────────────────────────────────────────────────────

class TestCompliance:
    """Verify no rules violated."""

    def test_no_sleep_in_detector(self):
        """Rule 1: No sleep() in detector code."""
        import inspect
        from src.modulation import detector
        source = inspect.getsource(detector)
        assert "sleep(" not in source

    def test_no_while_true_in_detector(self):
        """Rule 1: No while True in detector code."""
        import inspect
        from src.modulation import detector
        source = inspect.getsource(detector)
        assert "while True" not in source
