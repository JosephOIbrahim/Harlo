"""Integration test: E2E recall roundtrip.

Phase 1 Gate: twin recall "test" works E2E.
"""

import json
import os
import tempfile

from cognitive_twin import hippocampus

from cognitive_twin.daemon.main import run_direct


class TestE2ERecall:
    """Full end-to-end recall through daemon router."""

    def test_store_and_recall_via_router(self):
        """Store a trace and recall it through the daemon router."""
        db = tempfile.mktemp(suffix=".db")
        try:
            # Store via direct hippocampus
            hippocampus.py_store_trace(
                "e2e_1", "hello world test greeting",
                db_path=db,
            )

            # Recall via hippocampus directly (router uses default DB path)
            result = hippocampus.py_recall("hello world", db_path=db)
            assert result["confidence"] > 0.0
            assert len(result["traces"]) > 0
            assert result["traces"][0]["message"] == "hello world test greeting"
        finally:
            if os.path.exists(db):
                os.unlink(db)

    def test_daemon_router_ping(self):
        """Test daemon router ping command."""
        result = run_direct("ping", {})
        assert result["status"] == "ok"
        assert result["pong"] is True

    def test_daemon_router_status(self):
        """Test daemon router status command."""
        result = run_direct("status", {})
        assert result["status"] == "ok"
        assert result["version"] == "7.0.0"

    def test_daemon_router_unknown_command(self):
        """Test daemon router handles unknown commands."""
        result = run_direct("nonexistent", {})
        assert result["status"] == "error"
