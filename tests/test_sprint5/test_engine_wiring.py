"""Tests for Sprint 5 Phase 1: CognitiveEngine wired to real USD."""

import os
import pytest

from src.cognitive_engine import CognitiveEngine
from src import engine_config


class TestEngineWiring:
    def test_initializes_with_stage_factory(self):
        """Engine uses stage_factory, not hardcoded MockUsdStage."""
        engine = CognitiveEngine(in_memory=True)
        assert engine.stage is not None
        assert engine.stage_type in ("real_usd", "mock")
        engine.close()

    def test_fallback_to_mock_on_usd_failure(self):
        """If USD unavailable, falls back to mock."""
        engine = CognitiveEngine(use_real_usd=False, in_memory=True)
        assert engine.stage_type == "mock"
        engine.close()

    def test_process_exchange_with_dag(self):
        """DAG evaluates against stage on each exchange."""
        engine = CognitiveEngine(in_memory=True, use_real_usd=False)
        result = engine.process_exchange("twin_coach", {"message": "test"})
        assert result is not None
        assert result["exchange_index"] == 1
        assert "cognitive_context" in result
        engine.close()

    def test_observation_emitted(self):
        """Observation written to buffer after exchange."""
        engine = CognitiveEngine(in_memory=True, use_real_usd=False)
        engine.process_exchange("twin_coach", {})
        stats = engine.get_buffer_stats()
        assert stats["organic"] >= 1
        engine.close()

    def test_prediction_authored(self):
        """Prediction authored to stage after window fills."""
        engine = CognitiveEngine(
            in_memory=True, use_real_usd=False,
            model_path="models/cognitive_predictor_v1.joblib",
        )
        for i in range(5):
            engine.process_exchange("twin_coach", {"message": f"msg {i}"})
        # Prediction should be on stage
        pred = engine.stage.read("/prediction/forecast", 5)
        assert pred is not None
        engine.close()

    def test_health_check(self):
        """Health check returns accurate status."""
        engine = CognitiveEngine(in_memory=True, use_real_usd=False)
        engine.process_exchange("twin_coach", {})
        health = engine.get_health()
        assert health["engine"] == "active"
        assert health["exchange_index"] == 1
        assert health["delegates_registered"] == 2
        assert health["observations_logged"] >= 1
        engine.close()

    def test_delegates_registered(self):
        """Both delegates registered at init."""
        engine = CognitiveEngine(in_memory=True, use_real_usd=False)
        caps = engine.registry.list_delegates()
        ids = {c.delegate_id for c in caps}
        assert "claude" in ids
        assert "claude_code" in ids
        engine.close()

    def test_sublayers_created(self):
        """Delegate sublayers created at init."""
        engine = CognitiveEngine(in_memory=True, use_real_usd=False)
        engine.process_exchange("twin_coach", {})
        val = engine.stage.read_from_sublayer("claude", "/delegate/claude/exchange_count", 1)
        assert val is not None
        engine.close()


class TestEngineDisabled:
    def test_disabled_returns_none(self, monkeypatch):
        """When ENGINE_ENABLED=False, process_exchange returns None."""
        monkeypatch.setattr(engine_config, "ENGINE_ENABLED", False)
        engine = CognitiveEngine(in_memory=True, use_real_usd=False)
        result = engine.process_exchange("twin_coach", {})
        assert result is None
        engine.close()
        monkeypatch.setattr(engine_config, "ENGINE_ENABLED", True)
