"""Tests for Sprint 1 Phase 5: Full integration.

End-to-end test: 50-exchange simulated session with all systems connected.
- MockUsdStage + MockCogExec DAG + HdClaude + ObservationBuffer + Predictor
"""

import pytest

from src.bridge import Bridge, SessionResult
from src.delegate_base import TaskContext
from src.delegate_claude import HdClaude
from src.mock_usd_stage import MockUsdStage
from src.observation_buffer import ObservationBuffer
from src.schemas import (
    BurstPhase,
    Burnout,
    CognitiveObservation,
    DynamicsBlock,
    Energy,
    Momentum,
    StateBlock,
)
from src.validator import validate_trajectory


# -------------------------------------------------------------------
# HdClaude delegate
# -------------------------------------------------------------------

class TestHdClaude:
    def test_sync_and_execute(self):
        delegate = HdClaude()
        ctx = TaskContext(task_type="reasoning", signal_class="test")
        delegate.sync({}, {"momentum": 1, "burnout": 0, "energy": 2}, ctx)
        response = delegate.execute("test")
        assert response.tokens_used > 0
        assert response.response != ""

    def test_execute_without_sync(self):
        delegate = HdClaude()
        response = delegate.execute("test")
        assert response.response == ""  # no sync → empty context

    def test_commit_resources(self):
        delegate = HdClaude()
        ctx = TaskContext(task_type="reasoning", signal_class="test")
        delegate.sync({}, {}, ctx)
        result = delegate.execute("test")
        resources = delegate.commit_resources(result)
        assert "/delegate/claude/exchange_count" in resources


# -------------------------------------------------------------------
# ObservationBuffer
# -------------------------------------------------------------------

class TestObservationBuffer:
    def test_add_and_size(self):
        buf = ObservationBuffer(db_path=":memory:")
        obs = CognitiveObservation()
        buf.add(obs, partition="organic", surprise_score=0.5)
        stats = buf.size()
        assert stats["organic"] == 1
        assert stats["total"] == 1
        buf.close()

    def test_anchor_partition(self):
        buf = ObservationBuffer(db_path=":memory:")
        obs = CognitiveObservation()
        buf.add(obs, partition="anchor")
        stats = buf.size()
        assert stats["anchor"] == 1
        buf.close()

    def test_sample_maintains_ratio(self):
        buf = ObservationBuffer(db_path=":memory:")
        # Add 20 anchors and 80 organics
        for _ in range(20):
            buf.add(CognitiveObservation(), partition="anchor")
        for i in range(80):
            buf.add(CognitiveObservation(), partition="organic", surprise_score=float(i))

        sample = buf.sample(n=50)
        assert len(sample) == 50
        anchors = [s for s in sample if s.partition == "anchor"]
        assert len(anchors) >= 1  # At least some anchors
        buf.close()

    def test_eviction(self):
        buf = ObservationBuffer(db_path=":memory:", max_size=10)
        for i in range(20):
            buf.add(CognitiveObservation(), partition="organic", surprise_score=float(i))
        stats = buf.size()
        assert stats["total"] <= 10
        buf.close()

    def test_anchor_batch(self):
        buf = ObservationBuffer(db_path=":memory:")
        obs_list = [CognitiveObservation() for _ in range(5)]
        count = buf.add_anchor_batch(obs_list)
        assert count == 5
        assert buf.size()["anchor"] == 5
        buf.close()


# -------------------------------------------------------------------
# Full Bridge integration
# -------------------------------------------------------------------

class TestBridgeIntegration:
    def test_50_exchange_session(self):
        """End-to-end: 50-exchange simulated session."""
        bridge = Bridge(seed=42)
        result = bridge.run_session(
            session_id="integration-test",
            num_exchanges=50,
            validate=True,
        )

        # Session completed
        assert len(result.exchanges) == 50
        assert result.session_id == "integration-test"

        # No invariant violations
        assert len(result.violations) == 0, f"Violations: {result.violations}"

        # All observations are valid
        for ex in result.exchanges:
            obs = ex.observation
            assert isinstance(obs, CognitiveObservation)
            assert obs.state.burnout in list(Burnout)
            assert obs.state.energy in list(Energy)
            assert obs.state.momentum in list(Momentum)

        # Delegate consumed tokens
        assert result.total_tokens > 0

        # Observations were buffered
        assert result.observations_buffered == 50

        # Buffer has observations
        stats = bridge.get_buffer_stats()
        assert stats["organic"] == 50

        # Final state exists
        assert result.final_state is not None

        bridge.close()

    def test_session_with_predictor(self):
        """Integration with trained predictor."""
        bridge = Bridge(
            seed=42,
            predictor_path="models/cognitive_predictor_v1.joblib",
        )
        result = bridge.run_session(
            session_id="predictor-test",
            num_exchanges=50,
            validate=True,
        )

        # Predictions available after exchange 2 (need 3-observation window)
        predictions_made = sum(
            1 for ex in result.exchanges if ex.prediction is not None
        )
        assert predictions_made == 48  # exchanges 2-49

        # Predictions have correct keys
        for ex in result.exchanges:
            if ex.prediction is not None:
                assert "momentum" in ex.prediction
                assert "burnout" in ex.prediction
                assert "energy" in ex.prediction
                assert "burst_phase" in ex.prediction

        assert len(result.violations) == 0, f"Violations: {result.violations}"
        bridge.close()

    def test_delegate_resources(self):
        bridge = Bridge(seed=42)
        bridge.run_session(num_exchanges=10)
        resources = bridge.get_delegate_resources()
        assert resources["exchanges"] == 10
        bridge.close()

    def test_momentum_progression(self):
        """Verify momentum actually progresses during a session."""
        bridge = Bridge(seed=42)
        result = bridge.run_session(num_exchanges=50)
        momentums = [ex.observation.state.momentum for ex in result.exchanges]
        # Should see some progression from COLD_START
        max_momentum = max(momentums)
        assert max_momentum >= Momentum.BUILDING
        bridge.close()

    def test_state_stored_in_stage(self):
        """Verify MockUsdStage accumulates state."""
        bridge = Bridge(seed=42)
        bridge.run_session(num_exchanges=20)
        # Stage should have entries
        assert bridge._stage.max_exchange_index() == 19
        bridge.close()

    def test_multiple_sessions(self):
        """Run multiple sessions sequentially."""
        bridge = Bridge(seed=42)
        for session_num in range(3):
            bridge._stage.clear()
            result = bridge.run_session(
                session_id=f"multi-{session_num}",
                num_exchanges=20,
            )
            assert len(result.violations) == 0
        bridge.close()
