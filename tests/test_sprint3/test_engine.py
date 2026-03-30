"""Tests for Sprint 3 Phase 5: CognitiveEngine."""

import pytest

from src.cognitive_engine import CognitiveEngine


class TestCognitiveEngine:
    def test_initializes_without_errors(self):
        engine = CognitiveEngine()
        assert engine.exchange_index == 0
        assert len(engine.registry.list_delegates()) == 2
        engine.close()

    def test_process_exchange_returns_valid_response(self):
        engine = CognitiveEngine()
        result = engine.process_exchange("twin_coach", {"session_id": "test"})
        assert "cognitive_context" in result
        assert "delegate_id" in result
        assert "expert" in result
        assert result["exchange_index"] == 1
        engine.close()

    def test_exchange_index_increments(self):
        engine = CognitiveEngine()
        engine.process_exchange("twin_coach", {})
        engine.process_exchange("twin_store", {"message": "test"})
        assert engine.get_exchange_count() == 2
        engine.close()

    def test_observation_logged_to_buffer(self):
        engine = CognitiveEngine()
        engine.process_exchange("twin_coach", {})
        stats = engine.get_buffer_stats()
        assert stats["organic"] == 1
        engine.close()

    def test_observation_logging_disabled(self):
        engine = CognitiveEngine(observation_logging=False)
        engine.process_exchange("twin_coach", {})
        stats = engine.get_buffer_stats()
        assert stats["organic"] == 0
        engine.close()

    def test_prediction_with_model(self):
        engine = CognitiveEngine(
            model_path="models/cognitive_predictor_v1.joblib",
            prediction_enabled=True,
        )
        # Need 3 exchanges for prediction window
        for i in range(5):
            result = engine.process_exchange("twin_coach", {"message": f"msg {i}"})
        # Predictions start after 3rd exchange
        assert result["prediction"] is not None
        engine.close()

    def test_prediction_disabled(self):
        engine = CognitiveEngine(prediction_enabled=False)
        for i in range(5):
            result = engine.process_exchange("twin_coach", {})
        assert result["prediction"] is None
        engine.close()

    def test_delegate_routing(self):
        engine = CognitiveEngine()
        result = engine.process_exchange("twin_coach", {})
        # Default routing should select claude for reasoning
        assert result["delegate_id"] == "claude"
        engine.close()

    def test_cognitive_context_not_empty(self):
        engine = CognitiveEngine()
        result = engine.process_exchange("twin_coach", {})
        assert len(result["cognitive_context"]) > 0
        assert "COGNITIVE STATE" in result["cognitive_context"]
        engine.close()

    def test_multiple_exchanges_stable(self):
        engine = CognitiveEngine()
        for i in range(20):
            result = engine.process_exchange("twin_coach", {"message": f"exchange {i}"})
            assert result["exchange_index"] == i + 1
        engine.close()

    def test_graceful_without_model(self):
        engine = CognitiveEngine(model_path="nonexistent.joblib")
        result = engine.process_exchange("twin_coach", {})
        assert result["prediction"] is None  # graceful fallback
        engine.close()

    def test_sublayer_writes(self):
        engine = CognitiveEngine()
        engine.process_exchange("twin_coach", {})
        # Check delegate sublayer has data
        val = engine.stage.read_from_sublayer("claude", "/delegate/claude/exchange_count", 1)
        assert val is not None
        engine.close()
