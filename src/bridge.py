"""Bridge — Full exchange loop coordinator.

Sprint 1 Phase 5: Connects MockCogExec, HdClaude, ObservationBuffer.
Runs a complete simulated session with all systems integrated.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from .delegate_base import TaskContext
from .delegate_claude import HdClaude
from .mock_cogexec import evaluate_dag
from .mock_usd_stage import MockUsdStage
from .observation_buffer import ObservationBuffer
from .predict import CognitivePredictor
from .schemas import (
    ActionBlock,
    ActionType,
    AllostasisBlock,
    BurstPhase,
    Burnout,
    CognitiveObservation,
    DynamicsBlock,
    Energy,
    InjectionBlock,
    Momentum,
    StateBlock,
)
from .validator import validate_trajectory


@dataclass
class ExchangeResult:
    """Result of a single exchange in the bridge loop."""
    exchange_index: int
    observation: CognitiveObservation
    delegate_tokens: int
    prediction: Optional[dict[str, int]] = None


@dataclass
class SessionResult:
    """Result of a complete bridge session."""
    session_id: str
    exchanges: list[ExchangeResult] = field(default_factory=list)
    total_tokens: int = 0
    violations: list[str] = field(default_factory=list)
    observations_buffered: int = 0
    final_state: Optional[CognitiveObservation] = None


class Bridge:
    """Full exchange loop coordinator.

    Connects:
    - MockUsdStage: state storage
    - MockCogExec (evaluate_dag): state computation
    - HdClaude: delegate for generating actions
    - ObservationBuffer: priority queue for training
    - CognitivePredictor: optional next-state prediction
    """

    def __init__(
        self,
        seed: int = 42,
        predictor_path: Optional[str] = None,
        buffer_max_size: int = 5000,
    ):
        self._rng = random.Random(seed)
        self._stage = MockUsdStage()
        self._delegate = HdClaude()
        self._buffer = ObservationBuffer(db_path=":memory:", max_size=buffer_max_size)
        self._predictor: Optional[CognitivePredictor] = None
        if predictor_path:
            self._predictor = CognitivePredictor(predictor_path)

    def run_session(
        self,
        session_id: str = "bridge-session",
        num_exchanges: int = 50,
        validate: bool = True,
    ) -> SessionResult:
        """Run a complete exchange loop session.

        For each exchange:
        1. Generate authored observation (simulate user input)
        2. Evaluate through MockCogExec DAG
        3. Sync state to delegate
        4. Execute delegate response
        5. Buffer observation
        6. Optionally predict next state
        """
        result = SessionResult(session_id=session_id)
        observations: list[CognitiveObservation] = []

        # Accumulators (authored by bridge, Commandment 2)
        tasks_completed = 0
        exchanges_without_break = 0
        adrenaline_debt = 0

        for i in range(num_exchanges):
            # Simulate dynamics
            velocity = self._rng.uniform(0.3, 0.9)
            coherence = self._rng.uniform(0.5, 0.95)
            frustration = self._rng.uniform(0.0, 0.4)

            if self._rng.random() < velocity * 0.3:
                tasks_completed += 1
            exchanges_without_break += 1
            if self._rng.random() < 0.05:
                exchanges_without_break = 0

            # Build authored observation
            obs = CognitiveObservation(
                session_id=session_id,
                observation_index=i,
                exchange_index=i,
                dynamics=DynamicsBlock(
                    exchange_velocity=velocity,
                    topic_coherence=coherence,
                    session_exchange_count=i,
                    exchanges_without_break=exchanges_without_break,
                    adrenaline_debt=adrenaline_debt,
                    tasks_completed=tasks_completed,
                    frustration_signal=frustration,
                ),
                state=StateBlock(exercise_recency_days=1),
                allostasis=AllostasisBlock(sessions_24h=1),
            )

            # Evaluate through DAG
            resolved = evaluate_dag(self._stage, obs, i)
            observations.append(resolved)

            # Sync to delegate and execute
            ctx = TaskContext(
                task_type="simulation",
                signal_class="bridge",
                exchange_index=i,
            )
            computed = {
                "momentum": int(resolved.state.momentum),
                "burnout": int(resolved.state.burnout),
                "energy": int(resolved.state.energy),
                "burst": int(resolved.dynamics.burst_phase),
                "allostasis": {"load": resolved.allostasis.load},
            }
            self._delegate.sync({}, computed, ctx)
            delegate_response = self._delegate.execute("bridge_exchange")

            # Buffer observation
            surprise = abs(velocity - 0.5) + abs(coherence - 0.7)
            self._buffer.add(resolved, partition="organic", surprise_score=surprise)
            result.observations_buffered += 1

            # Predict next state if predictor available and we have enough history
            prediction = None
            if self._predictor and len(observations) >= 3:
                window = observations[-3:]
                prediction = self._predictor.predict(window)

            # Track adrenaline
            if resolved.dynamics.burst_phase >= BurstPhase.DETECTED:
                adrenaline_debt += 1
            elif adrenaline_debt > 0:
                adrenaline_debt = 0

            exchange_result = ExchangeResult(
                exchange_index=i,
                observation=resolved,
                delegate_tokens=delegate_response.tokens_used,
                prediction=prediction,
            )
            result.exchanges.append(exchange_result)
            result.total_tokens += delegate_response.tokens_used

        # Validate trajectory
        if validate and observations:
            result.violations = validate_trajectory(observations)

        result.final_state = observations[-1] if observations else None
        return result

    def get_buffer_stats(self) -> dict:
        """Get observation buffer statistics."""
        return self._buffer.size()

    def get_delegate_resources(self) -> dict:
        """Get delegate resource usage."""
        return {
            "delegate_id": self._delegate.get_delegate_id(),
            "exchanges": self._delegate._exchange_count,
        }

    def close(self) -> None:
        """Clean up resources."""
        self._buffer.close()
