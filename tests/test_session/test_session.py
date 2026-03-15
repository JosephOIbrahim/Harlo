"""Tests for session lifecycle management.

Adversarial: tries to break creation, retrieval, update, close,
timeout, persistence, concurrency, and edge cases.
"""

import json
import os
import tempfile

import pytest

from src.session.manager import Session, SessionManager


@pytest.fixture
def db_path():
    """Provide a temporary database path, cleaned up after test."""
    path = tempfile.mktemp(suffix=".db")
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def mgr(db_path):
    """Provide a SessionManager with 30-minute timeout."""
    return SessionManager(db_path=db_path, timeout_s=1800)


# ─────────────────────────────────────────────────────────────────────
# Session Creation
# ─────────────────────────────────────────────────────────────────────

class TestSessionCreation:
    """Test session creation."""

    def test_create_returns_session(self, mgr):
        """create() should return a Session object."""
        session = mgr.create()
        assert isinstance(session, Session)

    def test_create_generates_unique_ids(self, mgr):
        """Each session should get a unique ID."""
        ids = {mgr.create().session_id for _ in range(10)}
        assert len(ids) == 10

    def test_create_sets_defaults(self, mgr):
        """New sessions should have correct defaults."""
        session = mgr.create(now=1000)
        assert session.started_at == 1000
        assert session.last_active == 1000
        assert session.exchange_count == 0
        assert session.domain == "general"
        assert session.encoder_type == "semantic"
        assert session.closed is False
        assert session.history == []
        assert session.allostatic_tokens == 0

    def test_create_custom_domain(self, mgr):
        """create() should accept custom domain."""
        session = mgr.create(domain="medical")
        assert session.domain == "medical"

    def test_create_custom_encoder(self, mgr):
        """create() should accept custom encoder type."""
        session = mgr.create(encoder_type="lexical")
        assert session.encoder_type == "lexical"


# ─────────────────────────────────────────────────────────────────────
# Session Retrieval
# ─────────────────────────────────────────────────────────────────────

class TestSessionRetrieval:
    """Test session retrieval."""

    def test_get_existing_session(self, mgr):
        """get() should return the exact session that was created."""
        original = mgr.create(now=2000)
        loaded = mgr.get(original.session_id)
        assert loaded is not None
        assert loaded.session_id == original.session_id
        assert loaded.started_at == 2000

    def test_get_nonexistent_returns_none(self, mgr):
        """get() with unknown ID should return None."""
        assert mgr.get("nonexistent_id") is None

    def test_get_or_create_new(self, mgr):
        """get_or_create() with None should create a new session."""
        session = mgr.get_or_create(None)
        assert session.session_id is not None
        assert session.exchange_count == 0

    def test_get_or_create_existing(self, mgr):
        """get_or_create() with existing ID should return that session."""
        original = mgr.create(now=3000)
        retrieved = mgr.get_or_create(original.session_id, now=3000)
        assert retrieved.session_id == original.session_id

    def test_get_or_create_expired_creates_new(self, db_path):
        """get_or_create() with expired session should create a new one."""
        mgr = SessionManager(db_path=db_path, timeout_s=60)
        old = mgr.create(now=1000)
        # 2 minutes later — past 60s timeout
        new_session = mgr.get_or_create(old.session_id, now=1200)
        assert new_session.session_id != old.session_id

    def test_get_or_create_closed_creates_new(self, mgr):
        """get_or_create() with closed session should create a new one."""
        original = mgr.create()
        mgr.close(original.session_id, trigger_dmn=False)
        new_session = mgr.get_or_create(original.session_id)
        assert new_session.session_id != original.session_id


# ─────────────────────────────────────────────────────────────────────
# Session Update & Exchange Recording
# ─────────────────────────────────────────────────────────────────────

class TestSessionUpdate:
    """Test session update and exchange recording."""

    def test_record_exchange_increments_count(self, mgr):
        """record_exchange() should increment exchange_count."""
        session = mgr.create()
        mgr.record_exchange(session.session_id, "hello", "hi there", tokens=10)
        updated = mgr.get(session.session_id)
        assert updated.exchange_count == 1

    def test_record_exchange_appends_history(self, mgr):
        """record_exchange() should add user and assistant messages."""
        session = mgr.create()
        mgr.record_exchange(session.session_id, "question", "answer", tokens=5)
        updated = mgr.get(session.session_id)
        history = updated.history
        assert len(history) == 2
        assert history[0] == {"role": "user", "content": "question"}
        assert history[1] == {"role": "assistant", "content": "answer"}

    def test_record_multiple_exchanges(self, mgr):
        """Multiple exchanges should accumulate correctly."""
        session = mgr.create()
        for i in range(5):
            mgr.record_exchange(session.session_id, f"q{i}", f"a{i}", tokens=10)
        updated = mgr.get(session.session_id)
        assert updated.exchange_count == 5
        assert len(updated.history) == 10  # 5 exchanges * 2 messages

    def test_allostatic_tokens_accumulate(self, mgr):
        """Token counts should accumulate across exchanges."""
        session = mgr.create()
        mgr.record_exchange(session.session_id, "q1", "a1", tokens=100)
        mgr.record_exchange(session.session_id, "q2", "a2", tokens=200)
        mgr.record_exchange(session.session_id, "q3", "a3", tokens=300)
        updated = mgr.get(session.session_id)
        assert updated.allostatic_tokens == 600

    def test_record_exchange_updates_last_active(self, mgr):
        """record_exchange() should update last_active timestamp."""
        session = mgr.create(now=1000)
        mgr.record_exchange(session.session_id, "q", "a", tokens=1, now=5000)
        updated = mgr.get(session.session_id)
        assert updated.last_active == 5000

    def test_record_exchange_on_closed_session_returns_none(self, mgr):
        """record_exchange() on a closed session should return None."""
        session = mgr.create()
        mgr.close(session.session_id, trigger_dmn=False)
        result = mgr.record_exchange(session.session_id, "q", "a", tokens=1)
        assert result is None

    def test_record_exchange_on_nonexistent_returns_none(self, mgr):
        """record_exchange() on unknown session should return None."""
        result = mgr.record_exchange("bogus_id", "q", "a", tokens=1)
        assert result is None

    def test_history_cap_at_100_messages(self, mgr):
        """History should be capped at 100 messages (50 exchanges)."""
        session = mgr.create()
        for i in range(60):
            mgr.record_exchange(session.session_id, f"q{i}", f"a{i}", tokens=1)
        updated = mgr.get(session.session_id)
        assert len(updated.history) == 100  # Capped, not 120


# ─────────────────────────────────────────────────────────────────────
# Session Close
# ─────────────────────────────────────────────────────────────────────

class TestSessionClose:
    """Test session closing."""

    def test_close_marks_session_closed(self, mgr):
        """close() should set closed=True."""
        session = mgr.create()
        closed = mgr.close(session.session_id, trigger_dmn=False)
        assert closed.closed is True

    def test_close_persists(self, mgr):
        """Closed state should persist in database."""
        session = mgr.create()
        mgr.close(session.session_id, trigger_dmn=False)
        loaded = mgr.get(session.session_id)
        assert loaded.closed is True

    def test_close_nonexistent_returns_none(self, mgr):
        """close() on unknown session should return None."""
        assert mgr.close("bogus", trigger_dmn=False) is None

    def test_close_is_idempotent(self, mgr):
        """Closing an already-closed session should not fail."""
        session = mgr.create()
        mgr.close(session.session_id, trigger_dmn=False)
        again = mgr.close(session.session_id, trigger_dmn=False)
        assert again.closed is True

    def test_close_triggers_dmn_teardown(self, mgr):
        """close() with trigger_dmn=True should invoke DMN teardown."""
        from unittest.mock import patch, MagicMock

        session = mgr.create()
        mock_teardown = MagicMock()

        with patch("src.daemon.dmn_teardown.get_teardown", return_value=mock_teardown):
            mgr.close(session.session_id, trigger_dmn=True)

        mock_teardown.start.assert_called_once()
        call_args = mock_teardown.start.call_args
        context = call_args[0][1]
        assert context["session_id"] == session.session_id


# ─────────────────────────────────────────────────────────────────────
# Session Timeout
# ─────────────────────────────────────────────────────────────────────

class TestSessionTimeout:
    """Test session timeout detection and expiration."""

    def test_is_expired_within_timeout(self):
        """Session within timeout should not be expired."""
        session = Session(
            session_id="test", started_at=1000, last_active=1000,
        )
        assert session.is_expired(timeout_s=1800, now=1500) is False

    def test_is_expired_past_timeout(self):
        """Session past timeout should be expired."""
        session = Session(
            session_id="test", started_at=1000, last_active=1000,
        )
        assert session.is_expired(timeout_s=1800, now=5000) is True

    def test_closed_session_is_expired(self):
        """Closed session should always report expired."""
        session = Session(
            session_id="test", started_at=1000, last_active=1000, closed=True,
        )
        assert session.is_expired(timeout_s=1800, now=1001) is True

    def test_close_expired_finds_old_sessions(self, db_path):
        """close_expired() should close sessions past timeout."""
        mgr = SessionManager(db_path=db_path, timeout_s=60)
        old = mgr.create(now=1000)
        fresh = mgr.create(now=1180)  # Only 20s before check — within 60s timeout
        closed_ids = mgr.close_expired(now=1200)
        assert old.session_id in closed_ids
        assert fresh.session_id not in closed_ids

    def test_close_expired_marks_closed_in_db(self, db_path):
        """close_expired() should persist closed state."""
        mgr = SessionManager(db_path=db_path, timeout_s=60)
        old = mgr.create(now=1000)
        mgr.close_expired(now=1200)
        loaded = mgr.get(old.session_id)
        assert loaded.closed is True


# ─────────────────────────────────────────────────────────────────────
# Concurrent Sessions
# ─────────────────────────────────────────────────────────────────────

class TestConcurrentSessions:
    """Test that concurrent sessions don't interfere."""

    def test_two_sessions_independent(self, mgr):
        """Two sessions should track state independently."""
        s1 = mgr.create(domain="science")
        s2 = mgr.create(domain="art")
        mgr.record_exchange(s1.session_id, "q1", "a1", tokens=100)
        mgr.record_exchange(s2.session_id, "q2", "a2", tokens=200)
        mgr.record_exchange(s2.session_id, "q3", "a3", tokens=300)

        loaded_s1 = mgr.get(s1.session_id)
        loaded_s2 = mgr.get(s2.session_id)

        assert loaded_s1.exchange_count == 1
        assert loaded_s1.allostatic_tokens == 100
        assert loaded_s1.domain == "science"

        assert loaded_s2.exchange_count == 2
        assert loaded_s2.allostatic_tokens == 500
        assert loaded_s2.domain == "art"

    def test_closing_one_doesnt_affect_other(self, mgr):
        """Closing one session should not affect another."""
        s1 = mgr.create()
        s2 = mgr.create()
        mgr.close(s1.session_id, trigger_dmn=False)

        loaded_s2 = mgr.get(s2.session_id)
        assert loaded_s2.closed is False


# ─────────────────────────────────────────────────────────────────────
# Persistence Across Manager Instances
# ─────────────────────────────────────────────────────────────────────

class TestPersistence:
    """Test that sessions survive manager restart (new instance, same DB)."""

    def test_session_survives_manager_restart(self, db_path):
        """Session created by one manager should be loadable by another."""
        mgr1 = SessionManager(db_path=db_path, timeout_s=1800)
        session = mgr1.create(domain="test_domain", now=5000)
        mgr1.record_exchange(session.session_id, "hello", "world", tokens=42, now=5001)

        # Create a NEW manager instance (simulates process restart)
        mgr2 = SessionManager(db_path=db_path, timeout_s=1800)
        loaded = mgr2.get(session.session_id)

        assert loaded is not None
        assert loaded.domain == "test_domain"
        assert loaded.exchange_count == 1
        assert loaded.allostatic_tokens == 42
        assert len(loaded.history) == 2

    def test_closed_session_persists_across_restart(self, db_path):
        """Closed state should persist across manager instances."""
        mgr1 = SessionManager(db_path=db_path, timeout_s=1800)
        session = mgr1.create()
        mgr1.close(session.session_id, trigger_dmn=False)

        mgr2 = SessionManager(db_path=db_path, timeout_s=1800)
        loaded = mgr2.get(session.session_id)
        assert loaded.closed is True


# ─────────────────────────────────────────────────────────────────────
# List Active
# ─────────────────────────────────────────────────────────────────────

class TestListActive:
    """Test listing active sessions."""

    def test_list_active_excludes_closed(self, mgr):
        """list_active() should not include closed sessions."""
        s1 = mgr.create(now=1000)
        s2 = mgr.create(now=1000)
        mgr.close(s1.session_id, trigger_dmn=False)
        active = mgr.list_active(now=1000)
        ids = [s.session_id for s in active]
        assert s1.session_id not in ids
        assert s2.session_id in ids

    def test_list_active_excludes_expired(self, db_path):
        """list_active() should not include expired sessions."""
        mgr = SessionManager(db_path=db_path, timeout_s=60)
        old = mgr.create(now=1000)
        fresh = mgr.create(now=1050)
        active = mgr.list_active(now=1100)
        ids = [s.session_id for s in active]
        assert old.session_id not in ids
        assert fresh.session_id in ids

    def test_list_active_empty(self, mgr):
        """list_active() on empty database should return empty list."""
        assert mgr.list_active() == []


# ─────────────────────────────────────────────────────────────────────
# Session Serialization
# ─────────────────────────────────────────────────────────────────────

class TestSessionSerialization:
    """Test session to_dict serialization."""

    def test_to_dict_has_all_keys(self, mgr):
        """to_dict() should include all expected keys."""
        session = mgr.create()
        d = session.to_dict()
        expected_keys = {
            "session_id", "started_at", "last_active", "exchange_count",
            "domain", "encoder_type", "closed", "allostatic_tokens", "history_length",
        }
        assert set(d.keys()) == expected_keys

    def test_to_dict_history_length_correct(self, mgr):
        """to_dict() history_length should match actual history."""
        session = mgr.create()
        mgr.record_exchange(session.session_id, "q", "a", tokens=1)
        updated = mgr.get(session.session_id)
        d = updated.to_dict()
        assert d["history_length"] == 2


# ─────────────────────────────────────────────────────────────────────
# Router Integration
# ─────────────────────────────────────────────────────────────────────

class TestRouterIntegration:
    """Test session commands through the daemon router."""

    def test_router_session_start(self):
        """Router should handle session_start command."""
        from src.daemon.router import route_command

        result = route_command("session_start", {})
        assert result["status"] == "ok"
        assert "session_id" in result["result"]

    def test_router_session_status(self):
        """Router should handle session_status command."""
        from src.daemon.router import route_command

        start = route_command("session_start", {})
        sid = start["result"]["session_id"]

        result = route_command("session_status", {"session_id": sid})
        assert result["status"] == "ok"
        assert result["result"]["session_id"] == sid

    def test_router_session_close(self):
        """Router should handle session_close command."""
        from src.daemon.router import route_command

        start = route_command("session_start", {})
        sid = start["result"]["session_id"]

        result = route_command("session_close", {"session_id": sid})
        assert result["status"] == "ok"
        assert result["result"]["closed"] is True

    def test_router_session_list(self):
        """Router should handle session_list command."""
        from src.daemon.router import route_command

        route_command("session_start", {})
        result = route_command("session_list", {})
        assert result["status"] == "ok"
        assert result["result"]["count"] >= 1

    def test_router_session_close_missing_id(self):
        """Router should reject session_close without session_id."""
        from src.daemon.router import route_command

        result = route_command("session_close", {})
        assert result["status"] == "error"
        assert "session_id" in result["message"]

    def test_router_session_status_not_found(self):
        """Router should handle session_status for non-existent session."""
        from src.daemon.router import route_command

        result = route_command("session_status", {"session_id": "nonexistent"})
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()


# ─────────────────────────────────────────────────────────────────────
# CLI Registration
# ─────────────────────────────────────────────────────────────────────

class TestCLIRegistration:
    """Test CLI session command registration."""

    def test_session_command_registered(self):
        """session command should be registered in CLI."""
        from src.cli.main import cli

        assert "session" in cli.commands

    def test_session_subcommands(self):
        """session should have start, close, status, list subcommands."""
        from src.cli.commands.session import session

        subcommands = set(session.commands.keys())
        assert {"start", "close", "status", "list"} <= subcommands


# ─────────────────────────────────────────────────────────────────────
# Compliance
# ─────────────────────────────────────────────────────────────────────

class TestCompliance:
    """Verify no rules violated by session code."""

    def test_no_sleep_in_session(self):
        """Rule 1: No sleep() in session code."""
        import inspect
        from src.session import manager
        source = inspect.getsource(manager)
        assert "sleep(" not in source

    def test_no_while_true_in_session(self):
        """Rule 1: No while True in session code."""
        import inspect
        from src.session import manager
        source = inspect.getsource(manager)
        assert "while True" not in source
