"""Tests for Sprint 1 Phase 1: Schemas and MockUsdStage.

Covers:
- Ordinal IntEnum ordering and values
- CognitiveObservation defaults and validation
- MockUsdStage author/read/read_previous with baseline guarantees
- Commandment 5: exchange_index == 0 returns schema defaults, NEVER None
"""

import pytest

from src.schemas import (
    ActionType,
    Altitude,
    AllostasisBlock,
    AllostasisTrend,
    BASELINE_OBSERVATION,
    BASELINE_STATE,
    BurstPhase,
    Burnout,
    CognitiveObservation,
    ContextLevel,
    DelegateBlock,
    DynamicsBlock,
    Energy,
    InjectionBlock,
    InjectionPhase,
    InjectionProfile,
    Momentum,
    SleepQuality,
    StateBlock,
)
from src.mock_usd_stage import MockUsdStage


# -------------------------------------------------------------------
# IntEnum ordinal ordering (Commandment 10)
# -------------------------------------------------------------------

class TestOrdinalEnums:
    def test_momentum_ordering(self):
        assert Momentum.CRASHED < Momentum.COLD_START < Momentum.BUILDING
        assert Momentum.BUILDING < Momentum.ROLLING < Momentum.PEAK
        assert int(Momentum.CRASHED) == 0
        assert int(Momentum.PEAK) == 4

    def test_burnout_ordering(self):
        assert Burnout.GREEN < Burnout.YELLOW < Burnout.ORANGE < Burnout.RED
        assert int(Burnout.GREEN) == 0
        assert int(Burnout.RED) == 3

    def test_energy_ordering(self):
        assert Energy.DEPLETED < Energy.LOW < Energy.MEDIUM < Energy.HIGH
        assert int(Energy.DEPLETED) == 0
        assert int(Energy.HIGH) == 3

    def test_altitude_ordering(self):
        assert Altitude.GROUND < Altitude.TEN_K < Altitude.THIRTY_K < Altitude.FIFTY_K

    def test_burst_phase_ordering(self):
        assert BurstPhase.NONE < BurstPhase.DETECTED < BurstPhase.PROTECTED
        assert BurstPhase.PROTECTED < BurstPhase.WINDING < BurstPhase.EXIT_PREP

    def test_injection_profile_ordering(self):
        assert InjectionProfile.NONE < InjectionProfile.MICRODOSE
        assert InjectionProfile.MICRODOSE < InjectionProfile.PERCEPTUAL
        assert InjectionProfile.PERCEPTUAL < InjectionProfile.CLASSICAL
        assert InjectionProfile.CLASSICAL < InjectionProfile.MDMA

    def test_enums_are_int_comparable(self):
        assert Momentum.ROLLING == 3
        assert Burnout.ORANGE == 2
        assert Energy.HIGH == 3


# -------------------------------------------------------------------
# CognitiveObservation model
# -------------------------------------------------------------------

class TestCognitiveObservation:
    def test_default_construction(self):
        obs = CognitiveObservation()
        assert obs.state.momentum == Momentum.COLD_START
        assert obs.state.burnout == Burnout.GREEN
        assert obs.state.energy == Energy.MEDIUM
        assert obs.exchange_index == 0

    def test_baseline_matches_defaults(self):
        obs = CognitiveObservation()
        assert obs.state.momentum == BASELINE_STATE.momentum
        assert obs.state.burnout == BASELINE_STATE.burnout
        assert obs.state.energy == BASELINE_STATE.energy

    def test_telemetry_block_fields(self):
        obs = CognitiveObservation()
        assert obs.dynamics.tasks_completed == 0
        assert obs.dynamics.exchanges_without_break == 0
        assert obs.dynamics.frustration_signal == 0.0
        assert obs.dynamics.adrenaline_debt == 0

    def test_custom_values(self):
        obs = CognitiveObservation(
            exchange_index=42,
            state=StateBlock(momentum=Momentum.ROLLING, energy=Energy.HIGH),
            dynamics=DynamicsBlock(tasks_completed=5, exchange_velocity=0.8),
        )
        assert obs.exchange_index == 42
        assert obs.state.momentum == Momentum.ROLLING
        assert obs.dynamics.tasks_completed == 5

    def test_injection_block_defaults(self):
        obs = CognitiveObservation()
        assert obs.injection.profile == InjectionProfile.NONE
        assert obs.injection.alpha == 0.0
        assert obs.injection.phase == InjectionPhase.BASELINE

    def test_allostasis_block_defaults(self):
        obs = CognitiveObservation()
        assert obs.allostasis.load == 0.0
        assert obs.allostasis.trend == AllostasisTrend.STABLE

    def test_serialization_round_trip(self):
        obs = CognitiveObservation(
            exchange_index=10,
            state=StateBlock(momentum=Momentum.PEAK, burnout=Burnout.YELLOW),
            dynamics=DynamicsBlock(burst_phase=BurstPhase.PROTECTED),
        )
        data = obs.model_dump()
        restored = CognitiveObservation(**data)
        assert restored.exchange_index == 10
        assert restored.state.momentum == Momentum.PEAK
        assert restored.dynamics.burst_phase == BurstPhase.PROTECTED

    def test_json_round_trip(self):
        obs = CognitiveObservation(
            exchange_index=5,
            injection=InjectionBlock(profile=InjectionProfile.CLASSICAL, alpha=0.8),
        )
        json_str = obs.model_dump_json()
        restored = CognitiveObservation.model_validate_json(json_str)
        assert restored.injection.profile == InjectionProfile.CLASSICAL
        assert restored.injection.alpha == 0.8

    def test_validation_rejects_negative_exchange(self):
        with pytest.raises(Exception):
            CognitiveObservation(exchange_index=-1)

    def test_validation_rejects_out_of_range_alpha(self):
        with pytest.raises(Exception):
            InjectionBlock(alpha=1.5)


# -------------------------------------------------------------------
# MockUsdStage
# -------------------------------------------------------------------

class TestMockUsdStage:
    def test_author_and_read(self):
        stage = MockUsdStage()
        obs = CognitiveObservation(exchange_index=1)
        stage.author("/state", 1, obs)
        result = stage.read("/state", 1)
        assert result.exchange_index == 1

    def test_read_missing_returns_none(self):
        stage = MockUsdStage()
        assert stage.read("/state", 99) is None

    def test_read_previous_at_zero_returns_baseline(self):
        """Commandment 5: read_previous(path, 0) returns schema defaults."""
        stage = MockUsdStage()
        result = stage.read_previous("/state", 0)
        assert result is not None
        assert result.state.momentum == Momentum.COLD_START
        assert result.state.burnout == Burnout.GREEN
        assert result.state.energy == Energy.MEDIUM

    def test_read_previous_never_returns_none(self):
        """Commandment 5: NEVER returns None."""
        stage = MockUsdStage()
        result = stage.read_previous("/state", 5)
        assert result is not None

    def test_read_previous_reads_t_minus_1(self):
        """Commandment 4: read t-1 from authored history."""
        stage = MockUsdStage()
        obs = CognitiveObservation(
            exchange_index=3,
            state=StateBlock(momentum=Momentum.ROLLING),
        )
        stage.author("/state", 3, obs)
        result = stage.read_previous("/state", 4)
        assert result.state.momentum == Momentum.ROLLING

    def test_deep_copy_isolation(self):
        stage = MockUsdStage()
        obs = CognitiveObservation(exchange_index=1)
        stage.author("/state", 1, obs)
        result = stage.read("/state", 1)
        result.exchange_index = 999
        original = stage.read("/state", 1)
        assert original.exchange_index == 1

    def test_thresholds_defaults(self):
        stage = MockUsdStage()
        assert stage.get_threshold("building_task_threshold") == 3
        assert stage.get_threshold("rolling_coherence_threshold") == 0.7

    def test_thresholds_custom(self):
        stage = MockUsdStage(thresholds={"building_task_threshold": 5})
        assert stage.get_threshold("building_task_threshold") == 5
        assert stage.get_threshold("rolling_coherence_threshold") == 0.7

    def test_max_exchange_index(self):
        stage = MockUsdStage()
        assert stage.max_exchange_index() == -1
        stage.author("/state", 0, CognitiveObservation())
        stage.author("/state", 5, CognitiveObservation())
        assert stage.max_exchange_index() == 5

    def test_clear(self):
        stage = MockUsdStage()
        stage.author("/state", 0, CognitiveObservation())
        stage.clear()
        assert stage.read("/state", 0) is None
        assert stage.max_exchange_index() == -1

    def test_keys(self):
        stage = MockUsdStage()
        stage.author("/state", 0, CognitiveObservation())
        stage.author("/action", 0, CognitiveObservation())
        assert len(stage.keys()) == 2

    def test_read_previous_negative_index_returns_baseline(self):
        """Edge case: negative index treated as 0."""
        stage = MockUsdStage()
        result = stage.read_previous("/state", -1)
        assert result is not None
        assert result.state.momentum == Momentum.COLD_START
