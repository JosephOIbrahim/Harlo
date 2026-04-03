"""Tests for Coach Core projection engine."""

from __future__ import annotations

import json
import sqlite3

import pytest

from harlo.coach import project_coach, _format_xml
from harlo.hot_store import HotStore


@pytest.fixture
def db_path(tmp_path):
    """Temporary database path."""
    return str(tmp_path / "coach_test.db")


@pytest.fixture
def populated_db(db_path):
    """DB with hot traces and session."""
    store = HotStore(db_path)
    store.store("First trace about quantum computing", tags=["science"], domain="research")
    store.store("Second trace about feelings", tags=["personal"], domain="reflection")
    store.store("Third trace about architecture", tags=["tech"], domain="engineering")

    # Create a session
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
        "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("sess-001", 1710000000, 1710000100, 5, "research", "semantic", 0, "[]", 150),
    )
    conn.commit()
    conn.close()
    return db_path


class TestProjectCoach:
    """Tests for project_coach()."""

    def test_empty_db_returns_xml(self, db_path):
        """Even with empty DB, returns valid XML."""
        result = project_coach(db_path)
        assert '<harlo-context version="8.0">' in result
        assert "</harlo-context>" in result

    def test_nonexistent_db_returns_xml(self, tmp_path):
        """Non-existent DB returns minimal XML."""
        result = project_coach(str(tmp_path / "nonexistent.db"))
        assert '<harlo-context version="8.0">' in result

    def test_includes_recent_traces(self, populated_db):
        """Output includes recent hot traces."""
        result = project_coach(populated_db)
        assert "<recent-traces>" in result
        assert "architecture" in result
        assert "<trace>" in result

    def test_includes_session_info(self, populated_db):
        """Output includes active session info."""
        result = project_coach(populated_db, session_id="sess-001")
        assert "<session>" in result
        assert "<exchanges>5</exchanges>" in result
        assert "<domain>research</domain>" in result

    def test_includes_trust_level(self, populated_db):
        """Output includes trust level from TrustLedger."""
        result = project_coach(populated_db)
        assert "<trust-level>" in result

    def test_includes_pattern_count(self, populated_db):
        """Output includes pattern count."""
        result = project_coach(populated_db)
        assert "<patterns-detected>" in result

    def test_deterministic(self, populated_db):
        """Same input produces same output."""
        r1 = project_coach(populated_db, session_id="sess-001")
        r2 = project_coach(populated_db, session_id="sess-001")
        assert r1 == r2


class TestFormatXml:
    """Tests for _format_xml()."""

    def test_empty_state(self):
        """Empty state produces minimal XML."""
        result = _format_xml([], {}, 0, trust_score=0.0)
        assert '<harlo-context version="8.0">' in result
        assert "<trust-level>0.00</trust-level>" in result
        assert "<patterns-detected>0</patterns-detected>" in result
        assert "<session>" not in result
        assert "<recent-traces>" not in result

    def test_with_traces_only(self):
        """Traces render correctly."""
        traces = [{"message": "hello", "domain": "test", "tags": ["a", "b"], "timestamp": 0}]
        result = _format_xml(traces, {}, 0)
        assert "<recent-traces>" in result
        assert "<message>hello</message>" in result
        assert "<tags>a, b</tags>" in result

    def test_with_session_only(self):
        """Session renders correctly."""
        session = {"session_id": "s1", "exchange_count": 3, "domain": "dev", "allostatic_tokens": 50}
        result = _format_xml([], session, 0)
        assert "<session>" in result
        assert "<id>s1</id>" in result
        assert "<exchanges>3</exchanges>" in result


class TestCoachNoLLM:
    """Verify Coach has no LLM client dependencies."""

    def test_no_anthropic_import(self):
        """Coach module does not import anthropic."""
        import harlo.coach as coach
        source = open(coach.__file__).read()
        assert "anthropic" not in source

    def test_no_provider_import(self):
        """Coach module does not import provider."""
        import harlo.coach as coach
        source = open(coach.__file__).read()
        assert "provider" not in source
