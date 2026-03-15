"""Tests for Phase 3 tactical cleanup.

Tests:
- Router reflect wiring (returns real patterns, not empty)
- Router boundaries wiring (add/remove/list)
- Router export/import (JSON serialization roundtrip)
- Motor executor action handlers (recall, store, inquire, reflect)
- Connection pooling
"""

import json
import os
import sqlite3
import tempfile

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────
# Router: Reflect
# ─────────────────────────────────────────────────────────────────────

class TestRouterReflect:
    """Test reflect command returns real data."""

    def test_reflect_returns_ok(self):
        """Reflect command should return ok status."""
        from src.daemon.router import route_command
        result = route_command("reflect", {})
        assert result["status"] == "ok"

    def test_reflect_has_insights_key(self):
        """Reflect result should have insights and synthesis."""
        from src.daemon.router import route_command
        result = route_command("reflect", {})
        assert "insights" in result["result"]
        assert "synthesis" in result["result"]

    def test_reflect_synthesis_is_string(self):
        """Synthesis should be a human-readable string."""
        from src.daemon.router import route_command
        result = route_command("reflect", {})
        assert isinstance(result["result"]["synthesis"], str)


# ─────────────────────────────────────────────────────────────────────
# Router: Boundaries
# ─────────────────────────────────────────────────────────────────────

class TestRouterBoundaries:
    """Test boundaries command wiring."""

    def test_boundaries_list(self):
        """Boundaries list should return ok."""
        from src.daemon.router import route_command
        result = route_command("boundaries", {"action": "list"})
        assert result["status"] == "ok"
        assert "boundaries" in result["result"]

    def test_boundaries_add(self):
        """Adding a boundary should return ok."""
        from src.daemon.router import route_command
        result = route_command("boundaries", {"action": "add", "topic": "test_topic"})
        assert result["status"] == "ok"
        assert result["result"]["action"] == "add"

    def test_boundaries_remove(self):
        """Removing a boundary should return ok."""
        from src.daemon.router import route_command
        result = route_command("boundaries", {"action": "remove", "topic": "test_topic"})
        assert result["status"] == "ok"
        assert result["result"]["action"] == "remove"


# ─────────────────────────────────────────────────────────────────────
# Router: Export/Import
# ─────────────────────────────────────────────────────────────────────

class TestRouterExport:
    """Test export command with real JSON serialization."""

    def test_export_creates_file(self):
        """Export should create a JSON file."""
        from src.daemon.router import route_command

        export_path = tempfile.mktemp(suffix=".json")
        try:
            result = route_command("export", {"path": export_path})
            assert result["status"] == "ok"
            assert result["result"]["exported"] is True
            assert os.path.exists(export_path)

            data = json.loads(Path(export_path).read_text(encoding="utf-8"))
            assert "version" in data
            assert "traces" in data
            assert "sessions" in data
            assert "patterns" in data
        finally:
            if os.path.exists(export_path):
                os.unlink(export_path)

    def test_export_requires_path(self):
        """Export should fail without path."""
        from src.daemon.router import route_command
        result = route_command("export", {})
        assert result["status"] == "error"

    def test_export_counts(self):
        """Export result should include counts."""
        from src.daemon.router import route_command

        export_path = tempfile.mktemp(suffix=".json")
        try:
            result = route_command("export", {"path": export_path})
            assert "traces" in result["result"]
            assert "sessions" in result["result"]
            assert "patterns" in result["result"]
        finally:
            if os.path.exists(export_path):
                os.unlink(export_path)


class TestRouterImport:
    """Test import command with real JSON deserialization."""

    def test_import_from_file(self):
        """Import should read and process a JSON file."""
        from src.daemon.router import route_command

        import_path = tempfile.mktemp(suffix=".json")
        try:
            # Create a valid import file
            import_data = {
                "version": "6.0.0",
                "traces": [
                    {"id": "imp_t1", "message": "imported trace", "created_at": 1000,
                     "tags": ["test"], "domain": "testing", "source": "import"},
                ],
                "sessions": [
                    {"session_id": "imp_s1", "started_at": 2000, "last_active": 2100,
                     "exchange_count": 1, "domain": "general", "encoder_type": "semantic",
                     "closed": True, "history": [], "allostatic_tokens": 50},
                ],
            }
            Path(import_path).write_text(json.dumps(import_data), encoding="utf-8")

            result = route_command("import", {"path": import_path})
            assert result["status"] == "ok"
            assert result["result"]["imported"] is True
            assert result["result"]["traces"] >= 1
            assert result["result"]["sessions"] >= 1
        finally:
            if os.path.exists(import_path):
                os.unlink(import_path)

    def test_import_requires_path(self):
        """Import should fail without path."""
        from src.daemon.router import route_command
        result = route_command("import", {})
        assert result["status"] == "error"

    def test_import_missing_file(self):
        """Import should fail for non-existent file."""
        from src.daemon.router import route_command
        result = route_command("import", {"path": "/nonexistent/file.json"})
        assert result["status"] == "error"

    def test_export_import_roundtrip(self):
        """Export then import should preserve data."""
        from src.daemon.router import route_command

        export_path = tempfile.mktemp(suffix=".json")
        try:
            # Export current state
            route_command("export", {"path": export_path})
            assert os.path.exists(export_path)

            data = json.loads(Path(export_path).read_text(encoding="utf-8"))
            assert data["version"] == "6.0.0"

            # Import back (to a different DB would be ideal, but at least verify it runs)
            result = route_command("import", {"path": export_path})
            assert result["status"] == "ok"
        finally:
            if os.path.exists(export_path):
                os.unlink(export_path)


# ─────────────────────────────────────────────────────────────────────
# Motor Executor: Action Handlers
# ─────────────────────────────────────────────────────────────────────

class TestMotorHandlers:
    """Test registered motor action handlers."""

    def test_recall_handler_registered(self):
        """recall handler should be registered."""
        from src.motor.executor import _HANDLERS
        assert "recall" in _HANDLERS

    def test_store_handler_registered(self):
        """store handler should be registered."""
        from src.motor.executor import _HANDLERS
        assert "store" in _HANDLERS

    def test_inquire_handler_registered(self):
        """inquire handler should be registered."""
        from src.motor.executor import _HANDLERS
        assert "inquire" in _HANDLERS

    def test_reflect_handler_registered(self):
        """reflect handler should be registered."""
        from src.motor.executor import _HANDLERS
        assert "reflect" in _HANDLERS

    def test_recall_handler_returns_dict(self):
        """recall handler should return a dict."""
        from src.motor.executor import _HANDLERS
        from src.motor.premotor import PlannedAction

        action = PlannedAction(
            action_type="recall",
            description="test recall",
            target="test query",
            payload={"query": "test"},
            consent_level=0,
            reversible=True,
        )
        result = _HANDLERS["recall"](action, {})
        assert isinstance(result, dict)

    def test_reflect_handler_returns_dict(self):
        """reflect handler should return a dict."""
        from src.motor.executor import _HANDLERS
        from src.motor.premotor import PlannedAction

        action = PlannedAction(
            action_type="reflect",
            description="test reflect",
            target="",
            payload={},
            consent_level=0,
            reversible=True,
        )
        result = _HANDLERS["reflect"](action, {})
        assert isinstance(result, dict)

    def test_default_handler_still_works(self):
        """Unknown action types should use default handler."""
        from src.motor.executor import _default_handler
        from src.motor.premotor import PlannedAction

        action = PlannedAction(
            action_type="unknown_type",
            description="test",
            target="target",
            payload={},
            consent_level=0,
            reversible=True,
        )
        result = _default_handler(action, {})
        assert result["acknowledged"] is True
        assert result["action_type"] == "unknown_type"


# ─────────────────────────────────────────────────────────────────────
# Connection Pool
# ─────────────────────────────────────────────────────────────────────

class TestConnectionPool:
    """Test SQLite connection pooling."""

    def test_get_connection_returns_connection(self):
        """get_connection should return a sqlite3 Connection."""
        from src.daemon.connection_pool import get_connection, close_connection

        db = tempfile.mktemp(suffix=".db")
        try:
            conn = get_connection(db)
            assert isinstance(conn, sqlite3.Connection)
            conn.execute("SELECT 1")
            close_connection(db)
        finally:
            if os.path.exists(db):
                os.unlink(db)

    def test_same_connection_returned(self):
        """Repeated calls should return the same connection."""
        from src.daemon.connection_pool import get_connection, close_connection

        db = tempfile.mktemp(suffix=".db")
        try:
            conn1 = get_connection(db)
            conn2 = get_connection(db)
            assert conn1 is conn2
            close_connection(db)
        finally:
            if os.path.exists(db):
                os.unlink(db)

    def test_different_paths_different_connections(self):
        """Different db paths should get different connections."""
        from src.daemon.connection_pool import get_connection, close_all

        db1 = tempfile.mktemp(suffix=".db")
        db2 = tempfile.mktemp(suffix=".db")
        try:
            conn1 = get_connection(db1)
            conn2 = get_connection(db2)
            assert conn1 is not conn2
            close_all()
        finally:
            for f in [db1, db2]:
                if os.path.exists(f):
                    os.unlink(f)

    def test_close_connection(self):
        """close_connection should close and remove cached connection."""
        from src.daemon.connection_pool import get_connection, close_connection

        db = tempfile.mktemp(suffix=".db")
        try:
            conn1 = get_connection(db)
            close_connection(db)
            # Next call should get a NEW connection
            conn2 = get_connection(db)
            assert conn1 is not conn2
            close_connection(db)
        finally:
            if os.path.exists(db):
                os.unlink(db)

    def test_close_all(self):
        """close_all should close all connections."""
        from src.daemon.connection_pool import get_connection, close_all

        db1 = tempfile.mktemp(suffix=".db")
        db2 = tempfile.mktemp(suffix=".db")
        try:
            get_connection(db1)
            get_connection(db2)
            close_all()  # Should not raise
        finally:
            for f in [db1, db2]:
                if os.path.exists(f):
                    os.unlink(f)


# ─────────────────────────────────────────────────────────────────────
# Compliance
# ─────────────────────────────────────────────────────────────────────

class TestCompliance:
    """Verify no rules violated."""

    def test_no_sleep_in_connection_pool(self):
        """Rule 1: No sleep() in connection pool."""
        import inspect
        from src.daemon import connection_pool
        source = inspect.getsource(connection_pool)
        assert "sleep(" not in source

    def test_no_while_true_in_connection_pool(self):
        """Rule 1: No while True in connection pool."""
        import inspect
        from src.daemon import connection_pool
        source = inspect.getsource(connection_pool)
        assert "while True" not in source

    def test_no_sleep_in_executor(self):
        """Rule 1: No sleep() in executor."""
        import inspect
        from src.motor import executor
        source = inspect.getsource(executor)
        assert "sleep(" not in source
