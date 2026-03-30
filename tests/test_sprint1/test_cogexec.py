"""Tests for Sprint 1 Phase 2: MockCogExec DAG and computation functions.

Minimum 3 test cases per computation. Covers:
- DAG topological ordering
- Each computation function (momentum, burnout, energy, injection, context, burst, allostasis)
- 20-exchange trajectory evaluation
"""

import math

import networkx as nx
import pytest

from src.schemas import (
    ActionBlock,
    ActionType,
    AllostasisBlock,
    AllostasisTrend,
    BurstPhase,
    Burnout,
    CognitiveObservation,
    ContextLevel,
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
from src.mock_cogexec import build_dag, evaluate_dag
from src.computations.compute_momentum import compute_momentum
from src.computations.compute_burnout import compute_burnout
from src.computations.compute_energy import compute_energy
from src.computations.compute_injection_gain import compute_injection_gain, compute_anchor_gain
from src.computations.compute_context_budget import compute_context_budget
from src.computations.compute_burst import compute_burst
from src.computations.compute_allostasis import compute_allostasis


# -------------------------------------------------------------------
# DAG structure
# -------------------------------------------------------------------

class TestDAG:
    def test_dag_is_acyclic(self):
        dag = build_dag()
        assert nx.is_directed_acyclic_graph(dag)

    def test_dag_topological_order(self):
        dag = build_dag()
        order = list(nx.topological_sort(dag))
        assert order.index("burst") < order.index("energy")
        assert order.index("energy") < order.index("momentum")
        assert order.index("momentum") < order.index("burnout")
        assert order.index("burnout") < order.index("allostasis")

    def test_dag_has_all_nodes(self):
        dag = build_dag()
        expected = {"burst", "energy", "momentum", "burnout", "allostasis",
                    "injection_gain", "context_budget"}
        assert set(dag.nodes) == expected

    def test_independent_nodes(self):
        dag = build_dag()
        assert list(dag.predecessors("injection_gain")) == []
        assert list(dag.predecessors("context_budget")) == []


# -------------------------------------------------------------------
# compute_momentum
# -------------------------------------------------------------------

class TestComputeMomentum:
    def test_crashed_promotes_to_cold_start(self):
        obs = CognitiveObservation()
        prev = StateBlock(momentum=Momentum.CRASHED)
        assert compute_momentum(obs, prev) == Momentum.COLD_START

    def test_cold_start_to_building(self):
        obs = CognitiveObservation(
            dynamics=DynamicsBlock(tasks_completed=3),
        )
        prev = StateBlock(momentum=Momentum.COLD_START)
        assert compute_momentum(obs, prev) == Momentum.BUILDING

    def test_building_to_rolling(self):
        obs = CognitiveObservation(
            dynamics=DynamicsBlock(topic_coherence=0.8, exchange_velocity=0.6),
        )
        prev = StateBlock(momentum=Momentum.BUILDING)
        assert compute_momentum(obs, prev) == Momentum.ROLLING

    def test_rolling_to_peak_requires_burst(self):
        obs = CognitiveObservation(
            dynamics=DynamicsBlock(
                session_exchange_count=55,
                burst_phase=BurstPhase.PROTECTED,
            ),
        )
        prev = StateBlock(momentum=Momentum.ROLLING)
        assert compute_momentum(obs, prev) == Momentum.PEAK

    def test_red_burnout_crashes_any_momentum(self):
        obs = CognitiveObservation(state=StateBlock(burnout=Burnout.RED))
        prev = StateBlock(momentum=Momentum.PEAK)
        assert compute_momentum(obs, prev) == Momentum.CRASHED

    def test_frustration_degrades_momentum(self):
        obs = CognitiveObservation(
            dynamics=DynamicsBlock(frustration_signal=0.9),
        )
        prev = StateBlock(momentum=Momentum.ROLLING)
        assert compute_momentum(obs, prev) == Momentum.BUILDING

    def test_cold_start_stays_without_tasks(self):
        obs = CognitiveObservation(dynamics=DynamicsBlock(tasks_completed=1))
        prev = StateBlock(momentum=Momentum.COLD_START)
        assert compute_momentum(obs, prev) == Momentum.COLD_START


# -------------------------------------------------------------------
# compute_burnout
# -------------------------------------------------------------------

class TestComputeBurnout:
    def test_exogenous_red_overrides(self):
        """Commandment 7: ANY → RED when exogenous_red=True."""
        obs = CognitiveObservation()
        prev = StateBlock(burnout=Burnout.GREEN)
        assert compute_burnout(obs, prev, exogenous_red=True) == Burnout.RED

    def test_exogenous_red_from_any_level(self):
        for level in Burnout:
            obs = CognitiveObservation()
            prev = StateBlock(burnout=level)
            assert compute_burnout(obs, prev, exogenous_red=True) == Burnout.RED

    def test_sequential_escalation(self):
        obs = CognitiveObservation(
            dynamics=DynamicsBlock(frustration_signal=0.8),
        )
        prev = StateBlock(burnout=Burnout.GREEN)
        assert compute_burnout(obs, prev) == Burnout.YELLOW

    def test_no_skip_levels(self):
        """Burnout never skips: GREEN can only go to YELLOW, not ORANGE."""
        obs = CognitiveObservation(
            dynamics=DynamicsBlock(frustration_signal=0.95),
        )
        prev = StateBlock(burnout=Burnout.GREEN)
        result = compute_burnout(obs, prev)
        assert result == Burnout.YELLOW  # only one step up

    def test_de_escalation(self):
        obs = CognitiveObservation(
            dynamics=DynamicsBlock(frustration_signal=0.1, exchanges_without_break=2),
        )
        prev = StateBlock(burnout=Burnout.YELLOW)
        assert compute_burnout(obs, prev) == Burnout.GREEN

    def test_green_stays_green(self):
        obs = CognitiveObservation(
            dynamics=DynamicsBlock(frustration_signal=0.3, exchanges_without_break=5),
        )
        prev = StateBlock(burnout=Burnout.GREEN)
        assert compute_burnout(obs, prev) == Burnout.GREEN


# -------------------------------------------------------------------
# compute_energy
# -------------------------------------------------------------------

class TestComputeEnergy:
    def test_burst_suspends_decrement(self):
        """Commandment 8: energy decrements suspended during burst."""
        obs = CognitiveObservation(
            dynamics=DynamicsBlock(
                burst_phase=BurstPhase.PROTECTED,
                exchanges_without_break=20,
            ),
        )
        prev = StateBlock(energy=Energy.HIGH)
        assert compute_energy(obs, prev) == Energy.HIGH

    def test_adrenaline_debt_on_burst_exit(self):
        """Commandment 8: debt applies on burst exit."""
        obs = CognitiveObservation(
            dynamics=DynamicsBlock(
                burst_phase=BurstPhase.NONE,
                adrenaline_debt=2,
            ),
        )
        prev = StateBlock(energy=Energy.HIGH)
        assert compute_energy(obs, prev) == Energy.LOW

    def test_exercise_recovery_boost(self):
        obs = CognitiveObservation(
            state=StateBlock(exercise_recency_days=0),
            dynamics=DynamicsBlock(burst_phase=BurstPhase.NONE),
        )
        prev = StateBlock(energy=Energy.MEDIUM)
        assert compute_energy(obs, prev) == Energy.HIGH

    def test_normal_decrement(self):
        obs = CognitiveObservation(
            state=StateBlock(exercise_recency_days=3),
            dynamics=DynamicsBlock(
                exchanges_without_break=10,
                burst_phase=BurstPhase.NONE,
            ),
        )
        prev = StateBlock(energy=Energy.HIGH)
        assert compute_energy(obs, prev) == Energy.MEDIUM

    def test_depleted_stays_depleted(self):
        obs = CognitiveObservation(
            state=StateBlock(exercise_recency_days=5),
            dynamics=DynamicsBlock(
                exchanges_without_break=10,
                burst_phase=BurstPhase.NONE,
            ),
        )
        prev = StateBlock(energy=Energy.DEPLETED)
        assert compute_energy(obs, prev) == Energy.DEPLETED


# -------------------------------------------------------------------
# compute_injection_gain
# -------------------------------------------------------------------

class TestComputeInjectionGain:
    def test_anchor_always_1(self):
        """Commandment 6: anchor gain = 1.0 ALWAYS."""
        obs = CognitiveObservation(
            injection=InjectionBlock(
                profile=InjectionProfile.CLASSICAL,
                alpha=1.0,
                phase=InjectionPhase.PLATEAU,
            ),
        )
        for domain in ["SAFETY", "CONSENT", "KNOWLEDGE", "CONSTITUTIONAL"]:
            assert compute_injection_gain(obs, domain) == 1.0

    def test_anchor_gain_function_always_1(self):
        assert compute_anchor_gain("SAFETY") == 1.0
        assert compute_anchor_gain("anything") == 1.0

    def test_no_injection_returns_1(self):
        obs = CognitiveObservation()
        assert compute_injection_gain(obs) == 1.0

    def test_microdose_gain(self):
        obs = CognitiveObservation(
            injection=InjectionBlock(
                profile=InjectionProfile.MICRODOSE,
                alpha=1.0,
                phase=InjectionPhase.PLATEAU,
            ),
        )
        gain = compute_injection_gain(obs)
        assert 1.0 < gain <= 1.2

    def test_classical_gain_high_alpha(self):
        obs = CognitiveObservation(
            injection=InjectionBlock(
                profile=InjectionProfile.CLASSICAL,
                alpha=1.0,
                phase=InjectionPhase.PLATEAU,
            ),
        )
        gain = compute_injection_gain(obs)
        assert gain > 1.5

    def test_baseline_phase_returns_1(self):
        obs = CognitiveObservation(
            injection=InjectionBlock(
                profile=InjectionProfile.CLASSICAL,
                alpha=0.5,
                phase=InjectionPhase.BASELINE,
            ),
        )
        assert compute_injection_gain(obs) == 1.0


# -------------------------------------------------------------------
# compute_context_budget
# -------------------------------------------------------------------

class TestComputeContextBudget:
    def test_promote_payload_to_reference(self):
        """Commandment 9: promote at >4.2x."""
        obs = CognitiveObservation()
        prev = StateBlock(context=ContextLevel.PAYLOAD)
        assert compute_context_budget(obs, prev, token_ratio=4.5) == ContextLevel.REFERENCE

    def test_demote_reference_to_payload(self):
        """Commandment 9: demote at <3.8x."""
        obs = CognitiveObservation()
        prev = StateBlock(context=ContextLevel.REFERENCE)
        assert compute_context_budget(obs, prev, token_ratio=3.5) == ContextLevel.PAYLOAD

    def test_hysteresis_no_oscillation(self):
        """Between 3.8 and 4.2: no change (hysteresis)."""
        obs = CognitiveObservation()
        prev_payload = StateBlock(context=ContextLevel.PAYLOAD)
        prev_ref = StateBlock(context=ContextLevel.REFERENCE)
        # 4.0 is in the deadband
        assert compute_context_budget(obs, prev_payload, token_ratio=4.0) == ContextLevel.PAYLOAD
        assert compute_context_budget(obs, prev_ref, token_ratio=4.0) == ContextLevel.REFERENCE


# -------------------------------------------------------------------
# compute_burst
# -------------------------------------------------------------------

class TestComputeBurst:
    def test_none_to_detected(self):
        obs = CognitiveObservation(
            dynamics=DynamicsBlock(exchange_velocity=0.9, topic_coherence=0.9),
        )
        prev = DynamicsBlock(burst_phase=BurstPhase.NONE)
        assert compute_burst(obs, prev) == BurstPhase.DETECTED

    def test_detected_to_protected(self):
        obs = CognitiveObservation(
            dynamics=DynamicsBlock(exchange_velocity=0.9, topic_coherence=0.9),
        )
        prev = DynamicsBlock(burst_phase=BurstPhase.DETECTED)
        assert compute_burst(obs, prev) == BurstPhase.PROTECTED

    def test_coherence_drop_breaks_burst(self):
        obs = CognitiveObservation(
            dynamics=DynamicsBlock(exchange_velocity=0.9, topic_coherence=0.3),
        )
        prev = DynamicsBlock(burst_phase=BurstPhase.PROTECTED)
        assert compute_burst(obs, prev) == BurstPhase.NONE

    def test_exit_prep_returns_to_none(self):
        obs = CognitiveObservation(
            dynamics=DynamicsBlock(exchange_velocity=0.9, topic_coherence=0.9),
        )
        prev = DynamicsBlock(burst_phase=BurstPhase.EXIT_PREP)
        assert compute_burst(obs, prev) == BurstPhase.NONE


# -------------------------------------------------------------------
# compute_allostasis
# -------------------------------------------------------------------

class TestComputeAllostasis:
    def test_zero_load_at_baseline(self):
        obs = CognitiveObservation()
        prev = AllostasisBlock()
        result = compute_allostasis(obs, prev)
        assert result.load < 0.1

    def test_high_load_under_stress(self):
        obs = CognitiveObservation(
            state=StateBlock(
                burnout=Burnout.RED,
                exercise_recency_days=7,
                sleep_quality=SleepQuality.POOR,
            ),
            dynamics=DynamicsBlock(
                exchange_velocity=1.0,
                frustration_signal=1.0,
            ),
            allostasis=AllostasisBlock(override_ratio_7d=1.0),
        )
        prev = AllostasisBlock()
        result = compute_allostasis(obs, prev)
        assert result.load > 0.8

    def test_trend_detection(self):
        obs = CognitiveObservation(
            state=StateBlock(burnout=Burnout.ORANGE),
            dynamics=DynamicsBlock(frustration_signal=0.9),
        )
        prev = AllostasisBlock(load=0.1)
        result = compute_allostasis(obs, prev)
        assert result.trend in (AllostasisTrend.RISING, AllostasisTrend.SPIKE)


# -------------------------------------------------------------------
# Full DAG evaluation: 20-exchange trajectory
# -------------------------------------------------------------------

class TestFullDAGEvaluation:
    def test_20_exchange_trajectory(self):
        """Evaluate 20 exchanges through the full DAG."""
        stage = MockUsdStage()
        results = []

        for i in range(20):
            # Simulate gradual session progression
            tasks = min(i, 5)
            velocity = min(i * 0.05, 1.0)
            coherence = 0.9 if i < 15 else 0.5
            frustration = 0.0 if i < 12 else min((i - 12) * 0.15, 1.0)

            obs = CognitiveObservation(
                exchange_index=i,
                session_id="test-session",
                dynamics=DynamicsBlock(
                    tasks_completed=tasks,
                    exchange_velocity=velocity,
                    topic_coherence=coherence,
                    session_exchange_count=i,
                    exchanges_without_break=i,
                    frustration_signal=frustration,
                ),
                state=StateBlock(exercise_recency_days=1),
            )

            result = evaluate_dag(stage, obs, i)
            results.append(result)

        # Verify trajectory properties
        assert results[0].state.momentum in (Momentum.COLD_START, Momentum.CRASHED)
        # Should see some momentum progression
        momentums = [r.state.momentum for r in results]
        assert max(momentums) >= Momentum.BUILDING
        # All results should be valid observations
        for r in results:
            assert isinstance(r, CognitiveObservation)
            assert r.state.burnout in list(Burnout)
            assert r.state.energy in list(Energy)

    def test_red_event_during_trajectory(self):
        """Commandment 7: RED event crashes everything."""
        stage = MockUsdStage()

        # Build some momentum first
        for i in range(5):
            obs = CognitiveObservation(
                exchange_index=i,
                dynamics=DynamicsBlock(tasks_completed=5, exchange_velocity=0.6, topic_coherence=0.8),
            )
            evaluate_dag(stage, obs, i)

        # Exogenous RED at exchange 5
        obs = CognitiveObservation(
            exchange_index=5,
            dynamics=DynamicsBlock(tasks_completed=5),
        )
        result = evaluate_dag(stage, obs, 5, exogenous_red=True)
        assert result.state.burnout == Burnout.RED

    def test_dag_authors_to_stage(self):
        """Verify DAG writes results back to stage."""
        stage = MockUsdStage()
        obs = CognitiveObservation(exchange_index=0)
        evaluate_dag(stage, obs, 0)
        stored = stage.read("/state", 0)
        assert stored is not None
