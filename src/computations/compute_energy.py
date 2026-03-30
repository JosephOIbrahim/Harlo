"""Pure function: compute energy state transition.

Commandment 8: Energy decrements SUSPEND during active burst (adrenaline masking).
Debt applies on burst exit.
"""

from __future__ import annotations

from src.schemas import (
    BurstPhase,
    CognitiveObservation,
    Energy,
    StateBlock,
)


def compute_energy(
    authored: CognitiveObservation,
    prev_state: StateBlock,
    energy_decrement_interval: float = 10,
) -> Energy:
    """Compute next energy level.

    Rules:
      - During active burst (DETECTED-EXIT_PREP): energy decrements suspended
      - On burst exit (prev was burst, now NONE): apply adrenaline_debt
      - Normal: decrement every N exchanges without break
      - Exercise recovery: if exercise_recency_days == 0, small energy boost
    """
    prev_energy = prev_state.energy
    dynamics = authored.dynamics
    burst = dynamics.burst_phase

    # Adrenaline masking: suspend decrements during burst (Commandment 8)
    if burst >= BurstPhase.DETECTED:
        return prev_energy

    # Burst exit: apply adrenaline debt
    if dynamics.adrenaline_debt > 0:
        debt_steps = min(dynamics.adrenaline_debt, int(prev_energy))
        return Energy(max(int(prev_energy) - debt_steps, Energy.DEPLETED))

    # Exercise recovery boost
    if authored.state.exercise_recency_days == 0 and prev_energy < Energy.HIGH:
        return Energy(min(int(prev_energy) + 1, Energy.HIGH))

    # Normal decrement based on session length without break
    if (dynamics.exchanges_without_break > 0
            and dynamics.exchanges_without_break % int(energy_decrement_interval) == 0):
        if prev_energy > Energy.DEPLETED:
            return Energy(prev_energy - 1)

    return prev_energy
