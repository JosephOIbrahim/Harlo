"""Tests for Sprint 5 Phase 3: MCP integration verification.

All 7 tools with engine ON, all 7 with engine OFF.
Engine crash mid-call → MCP tool still responds.
"""

import pytest

from src.cognitive_engine import CognitiveEngine
from src import engine_config


def _make_engine():
    return CognitiveEngine(use_real_usd=False, in_memory=True)


# -------------------------------------------------------------------
# All 7 MCP tools with engine ON
# -------------------------------------------------------------------

class TestMCPToolsEngineOn:
    def test_twin_recall(self):
        engine = _make_engine()
        result = engine.process_exchange("twin_recall", {"query": "test", "depth": "normal"})
        assert result["exchange_index"] == 1
        assert result["observation_logged"] is True
        engine.close()

    def test_query_past_experience(self):
        engine = _make_engine()
        result = engine.process_exchange("query_past_experience", {"query": "test"})
        assert result is not None
        engine.close()

    def test_twin_store(self):
        engine = _make_engine()
        result = engine.process_exchange("twin_store", {"message": "test trace"})
        assert result["exchange_index"] == 1
        engine.close()

    def test_twin_coach(self):
        engine = _make_engine()
        result = engine.process_exchange("twin_coach", {"session_id": "test"})
        assert "cognitive_context" in result
        assert "COGNITIVE STATE" in result["cognitive_context"]
        engine.close()

    def test_twin_patterns(self):
        engine = _make_engine()
        result = engine.process_exchange("twin_patterns", {})
        assert result is not None
        engine.close()

    def test_twin_session_status(self):
        engine = _make_engine()
        result = engine.process_exchange("twin_session_status", {})
        assert result is not None
        engine.close()

    def test_resolve_verifications(self):
        engine = _make_engine()
        result = engine.process_exchange("resolve_verifications", {"verdicts": []})
        assert result is not None
        engine.close()


# -------------------------------------------------------------------
# All 7 tools with engine OFF
# -------------------------------------------------------------------

class TestMCPToolsEngineOff:
    def test_all_tools_return_none_when_disabled(self, monkeypatch):
        monkeypatch.setattr(engine_config, "ENGINE_ENABLED", False)
        engine = _make_engine()
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
            assert result is None, f"{tool_name} should return None when engine disabled"
        engine.close()
        monkeypatch.setattr(engine_config, "ENGINE_ENABLED", True)


# -------------------------------------------------------------------
# Engine failure during MCP call
# -------------------------------------------------------------------

class TestEngineCrashRecovery:
    def test_dag_crash_returns_fallback(self):
        """If DAG evaluation crashes, engine returns fallback response."""
        engine = _make_engine()
        # Corrupt stage to force DAG failure
        original_author = engine.stage.author
        engine.stage.author = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom"))

        result = engine.process_exchange("twin_coach", {})
        assert result is not None
        assert result["delegate_id"] == "none"
        assert result["cognitive_context"] == ""

        engine.stage.author = original_author
        engine.close()

    def test_subsequent_exchange_works_after_crash(self):
        """After one exchange crashes, next one works."""
        engine = _make_engine()
        # First: crash the DAG
        original = engine.stage.author
        engine.stage.author = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom"))
        result1 = engine.process_exchange("twin_coach", {})
        assert result1["delegate_id"] == "none"

        # Second: restore and process normally
        engine.stage.author = original
        result2 = engine.process_exchange("twin_coach", {"message": "test"})
        assert result2["delegate_id"] == "claude"
        assert "COGNITIVE STATE" in result2["cognitive_context"]
        engine.close()


# -------------------------------------------------------------------
# Observation accumulation
# -------------------------------------------------------------------

class TestObservationFlow:
    def test_observations_accumulate_across_tools(self):
        engine = _make_engine()
        for tool_name in ["twin_coach", "twin_store", "twin_recall",
                          "twin_patterns", "twin_session_status"]:
            engine.process_exchange(tool_name, {"message": "x", "query": "x"})
        stats = engine.get_buffer_stats()
        assert stats["organic"] == 5
        engine.close()

    def test_observations_not_lost_on_partial_failure(self):
        """Observation logged even if prediction fails."""
        engine = _make_engine()
        engine._predictor = None  # Disable predictor
        engine.process_exchange("twin_coach", {})
        stats = engine.get_buffer_stats()
        assert stats["organic"] >= 1
        engine.close()

    def test_health_after_10_exchanges(self):
        engine = _make_engine()
        for i in range(10):
            engine.process_exchange("twin_coach", {"message": f"msg {i}"})
        health = engine.get_health()
        assert health["exchange_index"] == 10
        assert health["observations_logged"] >= 10
        assert health["engine"] == "active"
        assert health["delegates_registered"] == 2
        engine.close()
