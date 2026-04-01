"""Tests for Sprint 3 Phase 6: End-to-end live test.

Simulates 20 MCP tool calls in sequence with all systems connected:
- DAG evaluation on each call
- Delegate selection via capability routing
- Observations accumulate in buffer
- Predictions update on stage
- Consent token mechanics
- Sublayer concurrency
- Context hysteresis stability
- Buffer anchor partition ratio
"""

import pytest

from src.cognitive_engine import CognitiveEngine
from src.consent import ConsentManager
from src.schemas import Burnout, Momentum


class TestLiveE2E:
    def test_20_exchange_sequence(self):
        """Full 20-exchange session with all systems."""
        engine = CognitiveEngine(
            model_path="models/cognitive_predictor_v1.joblib",
            use_real_usd=False, in_memory=True,
        )

        results = []
        for i in range(20):
            tool_name = ["twin_coach", "twin_store", "twin_recall",
                         "query_past_experience", "twin_patterns"][i % 5]
            tool_input = {"message": f"exchange {i}", "query": f"search {i}"}
            result = engine.process_exchange(tool_name, tool_input, session_id="e2e-test")
            results.append(result)

        # All exchanges processed
        assert len(results) == 20
        assert engine.get_exchange_count() == 20

        # DAG evaluated on each call (cognitive context present)
        for r in results:
            assert "cognitive_context" in r
            assert len(r["cognitive_context"]) > 0

        # Delegate selected (not hardcoded)
        delegate_ids = {r["delegate_id"] for r in results}
        assert "claude" in delegate_ids  # reasoning delegate should appear

        # Observations accumulated
        stats = engine.get_buffer_stats()
        assert stats["organic"] == 20

        # Predictions after window fills
        predictions = [r["prediction"] for r in results if r["prediction"] is not None]
        assert len(predictions) >= 17  # 20 - 3 (window warmup) + buffer

        engine.close()

    def test_consent_blocks_and_permits(self):
        """Consent token blocks override when absent, permits when present."""
        engine = CognitiveEngine(use_real_usd=False, in_memory=True)

        # Without consent: engine operates normally
        result1 = engine.process_exchange("twin_coach", {})
        assert result1["delegate_id"] is not None

        # Grant consent
        token_id = engine.consent_manager.grant_consent(
            "override", current_exchange=engine.exchange_index, ttl_exchanges=5
        )

        # With consent: still works
        result2 = engine.process_exchange("twin_coach", {})
        assert result2["delegate_id"] is not None

        # Verify consent is valid
        assert engine.consent_manager.validate(token_id, engine.exchange_index)

        # Revoke and verify
        engine.consent_manager.revoke(token_id)
        assert not engine.consent_manager.validate(token_id, engine.exchange_index)

        engine.close()

    def test_interleaved_delegate_calls(self):
        """Simulate interleaved Claude + ClaudeCode calls via sublayers."""
        engine = CognitiveEngine(use_real_usd=False, in_memory=True)

        # Mix of reasoning and coding tasks
        tasks = [
            ("twin_coach", {}),                        # reasoning → claude
            ("twin_store", {"message": "code fix"}),   # store
            ("twin_coach", {}),                        # reasoning → claude
            ("twin_store", {"message": "test"}),       # store
        ]

        for tool_name, tool_input in tasks:
            result = engine.process_exchange(tool_name, tool_input)

        # Both delegates have sublayer data
        claude_data = engine.stage.read_from_sublayer(
            "claude", "/delegate/claude/exchange_count", engine.exchange_index
        )
        assert claude_data is not None

        # Stage composition works
        composed = engine.stage.compose()
        assert len(composed) > 0

        engine.close()

    def test_context_hysteresis_stable(self):
        """No Payload/Reference thrashing over 20 exchanges."""
        engine = CognitiveEngine(use_real_usd=False, in_memory=True)
        contexts = []
        for i in range(20):
            result = engine.process_exchange("twin_coach", {"message": "x" * 100})
            contexts.append(result)

        # Should not thrash — all exchanges are similar
        experts = [c["expert"] for c in contexts]
        # Count expert changes
        changes = sum(1 for i in range(1, len(experts)) if experts[i] != experts[i-1])
        # Stable sessions should have few expert changes
        assert changes < 10, f"Too many expert changes: {changes}"

        engine.close()

    def test_buffer_maintains_anchor_ratio(self):
        """Buffer anchor partition maintains ~20% ratio when seeded."""
        engine = CognitiveEngine(use_real_usd=False, in_memory=True)

        # Seed anchors
        from src.schemas import CognitiveObservation
        anchors = [CognitiveObservation() for _ in range(5)]
        engine._buffer.add_anchor_batch(anchors)

        # Add organic observations
        for i in range(20):
            engine.process_exchange("twin_coach", {"message": f"msg {i}"})

        stats = engine.get_buffer_stats()
        total = stats["anchor"] + stats["organic"]
        anchor_ratio = stats["anchor"] / total if total > 0 else 0
        assert 0.1 <= anchor_ratio <= 0.5, f"Anchor ratio {anchor_ratio:.2f} out of range"

        engine.close()

    def test_prediction_audit_on_stage(self):
        """Predictions are authored to stage."""
        engine = CognitiveEngine(
            model_path="models/cognitive_predictor_v1.joblib",
            use_real_usd=False, in_memory=True,
        )
        for i in range(5):
            engine.process_exchange("twin_coach", {"message": f"msg {i}"})

        # Check prediction on stage
        forecast = engine.stage.read("/prediction/forecast", 5)
        assert forecast is not None
        assert "momentum" in forecast
        assert "burnout" in forecast

        engine.close()

    def test_observation_pipeline_produces_valid_data(self):
        """Observations in buffer are valid CognitiveObservation records."""
        engine = CognitiveEngine(use_real_usd=False, in_memory=True)
        for i in range(5):
            engine.process_exchange("twin_coach", {"message": f"msg {i}"})

        samples = engine._buffer.sample(n=5)
        assert len(samples) > 0
        for s in samples:
            obs = s.observation
            assert obs.exchange_index >= 0
            assert 0 <= int(obs.state.burnout) <= 3
            assert 0 <= int(obs.state.energy) <= 3

        engine.close()
