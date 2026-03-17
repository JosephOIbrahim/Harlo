"""Tests for the MCP server exposing Cognitive Twin tools.

All tests mock the semantic encoder to avoid loading the real BGE model.
"""

import json
import os
import sqlite3
import tempfile
from unittest.mock import patch, MagicMock

import pytest


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def tmp_db(tmp_path):
    """Create a temporary database path."""
    return str(tmp_path / "test_mcp.db")


@pytest.fixture
def mock_encoder():
    """Mock the semantic encoder to avoid loading the real model."""
    encoder = MagicMock()
    # Return a deterministic 256-byte SDR blob
    encoder.encode.return_value = b"\xaa" * 256
    with patch("cognitive_twin.encoder.get_semantic_encoder", return_value=encoder):
        with patch("cognitive_twin.encoder.SemanticEncoder", return_value=encoder):
            yield encoder


@pytest.fixture
def populated_db(tmp_db, mock_encoder):
    """Create a DB with some traces already stored."""
    from cognitive_twin.encoder import semantic_store

    semantic_store(tmp_db, "trace_001", "I enjoy solving complex problems", tags=["personal"], domain="reflection")
    semantic_store(tmp_db, "trace_002", "The architecture uses Merkle trees", tags=["technical"], domain="engineering")
    semantic_store(tmp_db, "trace_003", "Session timeout should be 30 minutes", tags=["config"], domain="engineering")
    return tmp_db


# ── Tool Import Helper ───────────────────────────────────────────────


def _patch_db(tmp_db):
    """Patch the MCP server's DB_PATH to use a temp database."""
    return patch("cognitive_twin.mcp_server.DB_PATH", tmp_db)


# ── Tests: twin_recall ───────────────────────────────────────────────


class TestTwinRecall:
    """Tests for the twin_recall tool."""

    def test_recall_returns_valid_json(self, populated_db, mock_encoder):
        from cognitive_twin.mcp_server import twin_recall

        with _patch_db(populated_db):
            result = json.loads(twin_recall("complex problems"))

        assert result["status"] == "ok"
        assert "traces" in result
        assert "confidence" in result

    def test_recall_empty_db(self, tmp_db, mock_encoder):
        from cognitive_twin.mcp_server import twin_recall

        with _patch_db(tmp_db):
            result = json.loads(twin_recall("anything"))

        assert result["status"] == "ok"
        assert result["traces"] == []
        assert result["confidence"] == 0.0

    def test_recall_deep_returns_more(self, populated_db, mock_encoder):
        from cognitive_twin.mcp_server import twin_recall

        with _patch_db(populated_db):
            normal = json.loads(twin_recall("test", depth="normal"))
            deep = json.loads(twin_recall("test", depth="deep"))

        # Deep should return at least as many as normal
        assert deep["trace_count"] >= normal["trace_count"]

    def test_recall_has_context_string(self, populated_db, mock_encoder):
        from cognitive_twin.mcp_server import twin_recall

        with _patch_db(populated_db):
            result = json.loads(twin_recall("architecture"))

        assert result["status"] == "ok"
        assert isinstance(result["context"], str)


# ── Tests: twin_store ─────────────────────────────────────────────────


class TestTwinStore:
    """Tests for the twin_store tool (v8 Hot Tier path)."""

    def test_store_returns_trace_id(self, tmp_path, mock_encoder):
        import cognitive_twin.mcp_server as srv

        srv._hot_store = None
        with patch.object(srv, "DATA_DIR", tmp_path):
            result = json.loads(srv.twin_store("A new memory trace"))

        assert result["status"] == "stored"
        assert result["tier"] == "hot"
        assert result["encoded"] is False
        assert len(result["trace_id"]) == 16
        srv._hot_store = None

    def test_store_with_tags_and_domain(self, tmp_path, mock_encoder):
        import cognitive_twin.mcp_server as srv

        srv._hot_store = None
        with patch.object(srv, "DATA_DIR", tmp_path):
            result = json.loads(srv.twin_store(
                "Tagged memory",
                tags=["important", "test"],
                domain="testing",
            ))

        assert result["status"] == "stored"
        assert result["tier"] == "hot"
        srv._hot_store = None

    def test_store_hot_trace_not_in_warm_recall(self, tmp_path, mock_encoder):
        """Hot-tier traces are NOT in warm-tier recall until promoted."""
        import cognitive_twin.mcp_server as srv

        srv._hot_store = None
        with patch.object(srv, "DATA_DIR", tmp_path), \
             _patch_db(str(tmp_path / "twin.db")):
            srv.twin_store("Unique memory about quantum computing")
            result = json.loads(srv.twin_recall("quantum"))

        assert result["status"] == "ok"
        assert result["trace_count"] == 0  # Not yet promoted to warm
        srv._hot_store = None


# ── Tests: twin_ask ───────────────────────────────────────────────────


class TestTwinAsk:
    """Tests for the twin_ask tool."""

    def test_ask_without_api_key(self, tmp_db, mock_encoder):
        from cognitive_twin.mcp_server import twin_ask

        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        with _patch_db(tmp_db), patch.dict(os.environ, env, clear=True):
            result = json.loads(twin_ask("What is the meaning of life?"))

        assert result["status"] == "error"
        assert "ANTHROPIC_API_KEY" in result["error"]

    def test_ask_with_mock_provider(self, populated_db, mock_encoder):
        """Mock the provider to test the full pipeline without a real API call."""
        from cognitive_twin.mcp_server import twin_ask

        mock_provider = MagicMock()
        mock_provider.model_name = "mock-model"
        mock_provider.generate.return_value = "This is a mock response."

        with _patch_db(populated_db), \
             patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test-fake"}), \
             patch("cognitive_twin.provider.get_provider", return_value=mock_provider):
            result = json.loads(twin_ask("Test question"))

        assert result["status"] == "ok"
        assert "response" in result
        assert result["model"] == "mock-model"


# ── Tests: twin_patterns ─────────────────────────────────────────────


class TestTwinPatterns:
    """Tests for the twin_patterns tool."""

    def test_patterns_empty_db(self, tmp_db, mock_encoder):
        from cognitive_twin.mcp_server import twin_patterns

        with _patch_db(tmp_db):
            result = json.loads(twin_patterns())

        assert result["status"] == "ok"
        assert result["count"] == 0

    def test_patterns_returns_list(self, populated_db, mock_encoder):
        from cognitive_twin.mcp_server import twin_patterns

        with _patch_db(populated_db):
            result = json.loads(twin_patterns())

        assert result["status"] == "ok"
        assert isinstance(result["patterns"], list)


# ── Tests: twin_session_status ────────────────────────────────────────


class TestTwinSessionStatus:
    """Tests for the twin_session_status tool."""

    def test_session_status_empty(self, tmp_db, mock_encoder):
        from cognitive_twin.mcp_server import twin_session_status

        with _patch_db(tmp_db):
            result = json.loads(twin_session_status())

        assert result["status"] == "ok"
        assert result["count"] == 0

    def test_session_status_with_active_session(self, tmp_db, mock_encoder):
        from cognitive_twin.mcp_server import twin_session_status
        from cognitive_twin.session.manager import SessionManager

        mgr = SessionManager(tmp_db)
        mgr.create(domain="testing")

        with _patch_db(tmp_db):
            result = json.loads(twin_session_status())

        assert result["status"] == "ok"
        assert result["count"] >= 1
        assert result["active_sessions"][0]["domain"] == "testing"


# ── Tests: Server initialization ─────────────────────────────────────


class TestServerInit:
    """Test the MCP server initializes correctly."""

    def test_server_object_exists(self):
        from cognitive_twin.mcp_server import server
        assert server is not None
        assert server.name == "cognitive-twin"

    def test_all_tools_registered(self):
        """All 5 tools should be registered on the server."""
        from cognitive_twin.mcp_server import server

        # FastMCP stores tools internally; check they're callable
        from cognitive_twin import mcp_server
        assert callable(mcp_server.twin_recall)
        assert callable(mcp_server.twin_store)
        assert callable(mcp_server.twin_ask)
        assert callable(mcp_server.twin_patterns)
        assert callable(mcp_server.twin_session_status)
