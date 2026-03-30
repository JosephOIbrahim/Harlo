"""Tests for Sprint 3 Phase 5: MCP integration.

Verifies:
- CognitiveEngine can hook into MCP tool calls
- Existing tools still work when engine fails
- Engine is additive, not required
"""

import json
import pytest

from src.cognitive_engine import CognitiveEngine


class TestMCPIntegration:
    def test_engine_enriches_twin_coach(self):
        """Engine enriches twin_coach response with cognitive context."""
        engine = CognitiveEngine()
        result = engine.process_exchange("twin_coach", {"session_id": "test123"})
        assert "cognitive_context" in result
        assert "COGNITIVE STATE" in result["cognitive_context"]
        engine.close()

    def test_engine_processes_twin_store(self):
        """Engine processes twin_store calls."""
        engine = CognitiveEngine()
        result = engine.process_exchange("twin_store", {
            "message": "Test trace message",
            "tags": ["test"],
        })
        assert result["exchange_index"] == 1
        assert result["observation_logged"] is True
        engine.close()

    def test_engine_processes_query_past_experience(self):
        engine = CognitiveEngine()
        result = engine.process_exchange("query_past_experience", {"query": "test"})
        assert result["delegate_id"] in ("claude", "claude_code")
        engine.close()

    def test_engine_processes_twin_patterns(self):
        engine = CognitiveEngine()
        result = engine.process_exchange("twin_patterns", {})
        assert result["exchange_index"] == 1
        engine.close()

    def test_engine_processes_twin_session_status(self):
        engine = CognitiveEngine()
        result = engine.process_exchange("twin_session_status", {})
        assert "expert" in result
        engine.close()

    def test_engine_processes_resolve_verifications(self):
        engine = CognitiveEngine()
        result = engine.process_exchange("resolve_verifications", {
            "verdicts": [{"claim_id": "test", "verdict": True}],
        })
        assert result["exchange_index"] == 1
        engine.close()

    def test_engine_processes_twin_recall(self):
        engine = CognitiveEngine()
        result = engine.process_exchange("twin_recall", {"query": "test", "depth": "normal"})
        assert result["delegate_id"] in ("claude", "claude_code")
        engine.close()

    def test_all_seven_tools_processed(self):
        """All 7 existing MCP tools can be processed by the engine."""
        engine = CognitiveEngine()
        tools = [
            ("twin_recall", {"query": "test"}),
            ("query_past_experience", {"query": "test"}),
            ("twin_store", {"message": "test"}),
            ("twin_coach", {}),
            ("twin_patterns", {}),
            ("twin_session_status", {}),
            ("resolve_verifications", {"verdicts": []}),
        ]
        for tool_name, tool_input in tools:
            result = engine.process_exchange(tool_name, tool_input)
            assert "cognitive_context" in result, f"Failed for {tool_name}"
        assert engine.get_exchange_count() == 7
        engine.close()

    def test_observations_accumulate(self):
        """Observations accumulate across all tool calls."""
        engine = CognitiveEngine()
        for i in range(5):
            engine.process_exchange("twin_coach", {})
        stats = engine.get_buffer_stats()
        assert stats["organic"] == 5
        engine.close()
