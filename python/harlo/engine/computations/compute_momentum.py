"""Pure function: compute momentum state transition.

Commandment 2: Pure function. NO internal counters.
Accumulators (tasks_completed, session_exchange_count) are authored externally.
"""

from __future__ import annotations

from src.schemas import (
    Burnout,
    BurstPhase,
    CognitiveObservation,
    Momentum,
    StateBlock,
)


def compute_momentum(
    authored: CognitiveObservation,
    prev_state: StateBlock,
    building_task_threshold: float = 3,
    rolling_coherence_threshold: float = 0.7,
    rolling_velocity_threshold: float = 0.5,
    peak_exchange_threshold: float = 50,
) -> Momentum:
    """Compute next momentum state from authored observation and previous state.

    Transitions:
      CRASHED  → COLD_START: always (session continues)
      COLD_START → BUILDING: tasks_completed >= threshold
      BUILDING → ROLLING: coherence >= threshold AND velocity >= threshold
      ROLLING → PEAK: session_exchange_count >= threshold AND in burst
      PEAK → CRASHED: burnout >= ORANGE
      Any → CRASHED: burnout == RED (exogenous override)
      Any above COLD_START → one step down: low coherence or high frustration
    """
    prev_momentum = prev_state.momentum
    burnout = authored.state.burnout
    dynamics = authored.dynamics

    # RED always crashes (Commandment 7) — check both authored AND previous
    if burnout == Burnout.RED or prev_state.burnout == Burnout.RED:
        return Momentum.CRASHED

    # ORANGE crashes from PEAK
    if burnout >= Burnout.ORANGE and prev_momentum == Momentum.PEAK:
        return Momentum.CRASHED

    # Degradation: frustration or low coherence can drop momentum
    if dynamics.frustration_signal >= 0.8 and prev_momentum > Momentum.COLD_START:
        return Momentum(max(prev_momentum - 1, Momentum.COLD_START))

    if dynamics.topic_coherence < 0.3 and prev_momentum > Momentum.BUILDING:
        return Momentum(max(prev_momentum - 1, Momentum.COLD_START))

    # Promotion paths
    if prev_momentum == Momentum.CRASHED:
        return Momentum.COLD_START

    if prev_momentum == Momentum.COLD_START:
        if dynamics.tasks_completed >= building_task_threshold:
            return Momentum.BUILDING
        return Momentum.COLD_START

    if prev_momentum == Momentum.BUILDING:
        if (dynamics.topic_coherence >= rolling_coherence_threshold
                and dynamics.exchange_velocity >= rolling_velocity_threshold):
            return Momentum.ROLLING
        return Momentum.BUILDING

    if prev_momentum == Momentum.ROLLING:
        if (dynamics.session_exchange_count >= peak_exchange_threshold
                and dynamics.burst_phase >= BurstPhase.PROTECTED):
            return Momentum.PEAK
        return Momentum.ROLLING

    # PEAK stays PEAK unless degraded above
    return prev_momentum
