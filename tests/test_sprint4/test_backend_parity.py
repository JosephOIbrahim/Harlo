"""Tests for Sprint 4 Phase 2: Backend parity.

Verifies CognitiveStage produces identical results to MockUsdStage
for all core operations used by Sprint 1+3.
"""

import pytest

from src.cognitive_stage import CognitiveStage
from src.mock_usd_stage import MockUsdStage
from src.mock_cogexec import evaluate_dag
from src.schemas import (
    CognitiveObservation,
    DynamicsBlock,
    Burnout,
    Energy,
    Momentum,
    StateBlock,
)
from src.stage_factory import create_stage


# -------------------------------------------------------------------
# Parametrized stage fixture: both backends
# -------------------------------------------------------------------

@pytest.fixture(params=["mock", "real_usd"])
def stage(request):
    if request.param == "real_usd":
        return CognitiveStage(in_memory=True)
    return MockUsdStage()


# -------------------------------------------------------------------
# Parity tests — must pass on BOTH backends
# -------------------------------------------------------------------

class TestBackendParity:
    def test_author_read_round_trip(self, stage):
        obs = CognitiveObservation(exchange_index=3, state=StateBlock(momentum=Momentum.ROLLING))
        stage.author("/state", 3, obs)
        result = stage.read("/state", 3)
        assert result is not None
        assert result.state.momentum == Momentum.ROLLING

    def test_read_previous_at_zero(self, stage):
        result = stage.read_previous("/state", 0)
        assert result is not None
        assert result.state.momentum == Momentum.COLD_START
        assert result.state.energy == Energy.MEDIUM

    def test_read_previous_reads_t_minus_1(self, stage):
        obs = CognitiveObservation(exchange_index=5, state=StateBlock(energy=Energy.HIGH))
        stage.author("/state", 5, obs)
        result = stage.read_previous("/state", 6)
        assert result.state.energy == Energy.HIGH

    def test_read_missing_returns_none(self, stage):
        assert stage.read("/nonexistent", 99) is None

    def test_thresholds(self, stage):
        assert stage.get_threshold("building_task_threshold") == 3

    def test_max_exchange_index(self, stage):
        assert stage.max_exchange_index() == -1
        stage.author("/state", 0, CognitiveObservation())
        stage.author("/state", 7, CognitiveObservation())
        assert stage.max_exchange_index() == 7

    def test_keys_populated(self, stage):
        stage.author("/state", 0, CognitiveObservation())
        stage.author("/state", 1, CognitiveObservation())
        assert len(stage.keys()) >= 2

    def test_delegate_sublayer_write_read(self, stage):
        stage.create_delegate_sublayer("test_delegate")
        stage.author_to_sublayer("test_delegate", "/delegates/test", 0, {"ok": True})
        result = stage.read_from_sublayer("test_delegate", "/delegates/test", 0)
        assert result == {"ok": True}

    def test_dag_evaluation(self, stage):
        """Run MockCogExec DAG against both backends."""
        obs = CognitiveObservation(
            exchange_index=0,
            dynamics=DynamicsBlock(tasks_completed=5, exchange_velocity=0.6, topic_coherence=0.8),
        )
        result = evaluate_dag(stage, obs, 0)
        assert isinstance(result, CognitiveObservation)
        assert result.state.burnout in list(Burnout)

    def test_multi_exchange_trajectory(self, stage):
        """5-exchange trajectory on both backends."""
        for i in range(5):
            obs = CognitiveObservation(
                exchange_index=i,
                dynamics=DynamicsBlock(
                    tasks_completed=i,
                    exchange_velocity=0.5,
                    topic_coherence=0.7,
                    session_exchange_count=i,
                ),
            )
            result = evaluate_dag(stage, obs, i)
            assert result is not None

    def test_clear(self, stage):
        stage.author("/state", 0, CognitiveObservation())
        stage.clear()
        assert stage.read("/state", 0) is None


class TestStageFactory:
    def test_create_mock(self):
        stage = create_stage(use_real_usd=False)
        assert isinstance(stage, MockUsdStage)

    def test_create_real_usd(self):
        stage = create_stage(use_real_usd=True, in_memory=True)
        assert isinstance(stage, CognitiveStage)

    def test_both_backends_same_interface(self):
        mock = create_stage(use_real_usd=False)
        real = create_stage(use_real_usd=True, in_memory=True)
        for stage in [mock, real]:
            stage.author("/test", 0, {"val": 1})
            assert stage.read("/test", 0) is not None
            assert stage.read_previous("/test", 0) is not None
            assert stage.get_threshold("building_task_threshold") == 3
