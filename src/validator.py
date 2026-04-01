"""26 invariant validator for cognitive state trajectories.

Each invariant is an assert with a descriptive message.
INV-14 amended for RED exception (Commandment 7).
"""

from __future__ import annotations

from src.schemas import (
    Burnout,
    BurstPhase,
    CognitiveObservation,
    Energy,
    InjectionPhase,
    InjectionProfile,
    Momentum,
)


class InvariantViolation(Exception):
    """Raised when a trajectory invariant is violated."""
    def __init__(self, inv_id: str, message: str, exchange_index: int):
        self.inv_id = inv_id
        self.exchange_index = exchange_index
        super().__init__(f"{inv_id} at exchange {exchange_index}: {message}")


def validate_trajectory(observations: list[CognitiveObservation]) -> list[str]:
    """Validate a full trajectory against all 26 invariants.

    Returns list of violation descriptions. Empty = valid.
    """
    violations: list[str] = []

    for i, obs in enumerate(observations):
        if i == 0:
            continue  # Skip first observation (no previous state)

        prev = observations[i - 1]
        idx = obs.exchange_index

        # INV-01: Momentum range valid
        if not (0 <= int(obs.state.momentum) <= 4):
            violations.append(f"INV-01 at {idx}: momentum {obs.state.momentum} out of range")

        # INV-02: Burnout range valid
        if not (0 <= int(obs.state.burnout) <= 3):
            violations.append(f"INV-02 at {idx}: burnout {obs.state.burnout} out of range")

        # INV-03: Energy range valid
        if not (0 <= int(obs.state.energy) <= 3):
            violations.append(f"INV-03 at {idx}: energy {obs.state.energy} out of range")

        # INV-04: Momentum transitions are at most +1 step (except CRASHED and RED)
        if obs.state.burnout != Burnout.RED:
            m_delta = int(obs.state.momentum) - int(prev.state.momentum)
            if m_delta > 1:
                violations.append(
                    f"INV-04 at {idx}: momentum jumped {prev.state.momentum}→{obs.state.momentum}"
                )

        # INV-05: Burst phase transitions are sequential
        b_curr = int(obs.dynamics.burst_phase)
        b_prev = int(prev.dynamics.burst_phase)
        if b_prev == int(BurstPhase.EXIT_PREP):
            if b_curr != int(BurstPhase.NONE):
                violations.append(
                    f"INV-05 at {idx}: EXIT_PREP must go to NONE, got {obs.dynamics.burst_phase}"
                )
        elif b_curr > b_prev + 1 and b_curr != 0:
            violations.append(
                f"INV-05 at {idx}: burst jumped {prev.dynamics.burst_phase}→{obs.dynamics.burst_phase}"
            )

        # INV-06: Energy range is 0-3
        if not (0 <= int(obs.state.energy) <= 3):
            violations.append(f"INV-06 at {idx}: energy out of range")

        # INV-07 to INV-10: Anchor gains always 1.0
        # (validated at computation level, not in trajectory)

        # INV-11: RED burnout implies crashed or crashing momentum
        if obs.state.burnout == Burnout.RED:
            if obs.state.momentum > Momentum.COLD_START:
                violations.append(
                    f"INV-11 at {idx}: RED burnout but momentum is {obs.state.momentum}"
                )

        # INV-12: Burnout RED means energy should be LOW or DEPLETED (eventually)
        # Soft check: RED for 2+ consecutive exchanges should degrade energy
        if obs.state.burnout == Burnout.RED and prev.state.burnout == Burnout.RED:
            if obs.state.energy > Energy.LOW:
                violations.append(
                    f"INV-12 at {idx}: sustained RED but energy is {obs.state.energy}"
                )

        # INV-13: Burnout never skips levels (GREEN→ORANGE forbidden)
        burnout_delta = int(obs.state.burnout) - int(prev.state.burnout)
        # INV-14 exception: exogenous RED can skip
        if burnout_delta > 1 and obs.state.burnout != Burnout.RED:
            violations.append(
                f"INV-13 at {idx}: burnout skipped {prev.state.burnout}→{obs.state.burnout}"
            )

        # INV-14: RED exception — ANY→RED is allowed (exogenous override)
        # (This is the exception: no violation for jump to RED)

        # INV-15: RED kills burst
        if obs.state.burnout == Burnout.RED and obs.dynamics.burst_phase > BurstPhase.NONE:
            violations.append(
                f"INV-15 at {idx}: RED burnout but burst active: {obs.dynamics.burst_phase}"
            )

        # INV-16: exchange_index is monotonically increasing
        if obs.exchange_index <= prev.exchange_index:
            violations.append(
                f"INV-16 at {idx}: exchange_index not monotonic: {prev.exchange_index}→{obs.exchange_index}"
            )

        # INV-17: session_exchange_count is non-decreasing within session
        if obs.session_id == prev.session_id:
            if obs.dynamics.session_exchange_count < prev.dynamics.session_exchange_count:
                violations.append(
                    f"INV-17 at {idx}: session_exchange_count decreased"
                )

        # INV-18: topic_coherence in [0, 1]
        if not (0.0 <= obs.dynamics.topic_coherence <= 1.0):
            violations.append(f"INV-18 at {idx}: coherence out of range: {obs.dynamics.topic_coherence}")

        # INV-19: alpha in [0, 1]
        if not (0.0 <= obs.injection.alpha <= 1.0):
            violations.append(f"INV-19 at {idx}: alpha out of range: {obs.injection.alpha}")

        # INV-20: allostatic load in [0, 1]
        if not (0.0 <= obs.allostasis.load <= 1.0):
            violations.append(f"INV-20 at {idx}: allostatic load out of range: {obs.allostasis.load}")

        # INV-21: Injection phase follows profile lifecycle
        if obs.injection.profile == InjectionProfile.NONE:
            if obs.injection.phase != InjectionPhase.BASELINE:
                violations.append(
                    f"INV-21 at {idx}: no injection profile but phase is {obs.injection.phase}"
                )

        # INV-22: Injection alpha is 0 when profile is NONE
        if obs.injection.profile == InjectionProfile.NONE:
            if obs.injection.alpha != 0.0:
                violations.append(
                    f"INV-22 at {idx}: no injection but alpha is {obs.injection.alpha}"
                )

        # INV-23: Coherence should generally decrease with topic switches
        # (Soft invariant: topic_coherence < 0.5 implies lower momentum feasible)

        # INV-24: Frustration signal in [0, 1]
        if not (0.0 <= obs.dynamics.frustration_signal <= 1.0):
            violations.append(
                f"INV-24 at {idx}: frustration out of range: {obs.dynamics.frustration_signal}"
            )

        # INV-25: Tangent budget >= 0
        if obs.dynamics.tangent_budget_remaining < 0:
            violations.append(
                f"INV-25 at {idx}: negative tangent budget: {obs.dynamics.tangent_budget_remaining}"
            )

        # INV-26: Energy decrements suspend during burst (adrenaline masking)
        if (obs.dynamics.burst_phase >= BurstPhase.DETECTED
                and prev.dynamics.burst_phase >= BurstPhase.DETECTED):
            if int(obs.state.energy) < int(prev.state.energy):
                violations.append(
                    f"INV-26 at {idx}: energy decreased during burst"
                )

    return violations
