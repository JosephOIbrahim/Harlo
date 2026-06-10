"""Pure function: compute burst phase transitions."""

from __future__ import annotations

from src.schemas import (
    BurstPhase,
    CognitiveObservation,
    DynamicsBlock,
)


def compute_burst(
    authored: CognitiveObservation,
    prev_dynamics: DynamicsBlock,
    burst_detect_velocity: float = 0.8,
    burst_detect_coherence: float = 0.85,
    burst_winding_exchange: float = 50,
    burst_exit_exchange: float = 70,
) -> BurstPhase:
    """Compute burst phase transition.

    NONE → DETECTED: high velocity + coherence
    DETECTED → PROTECTED: sustained (next exchange)
    PROTECTED → WINDING: session_exchange_count >= winding threshold
    WINDING → EXIT_PREP: session_exchange_count >= exit threshold
    EXIT_PREP → NONE: next exchange
    Any → NONE: coherence drops below detection threshold
    """
    prev_burst = prev_dynamics.burst_phase
    dynamics = authored.dynamics
    velocity = dynamics.exchange_velocity
    coherence = dynamics.topic_coherence
    session_count = dynamics.session_exchange_count

    # Exit conditions
    if prev_burst == BurstPhase.EXIT_PREP:
        return BurstPhase.NONE

    # Coherence drop breaks burst
    if prev_burst >= BurstPhase.DETECTED and coherence < burst_detect_coherence * 0.7:
        return BurstPhase.NONE

    # Progression
    if prev_burst == BurstPhase.NONE:
        if velocity >= burst_detect_velocity and coherence >= burst_detect_coherence:
            return BurstPhase.DETECTED
        return BurstPhase.NONE

    if prev_burst == BurstPhase.DETECTED:
        return BurstPhase.PROTECTED

    if prev_burst == BurstPhase.PROTECTED:
        if session_count >= burst_winding_exchange:
            return BurstPhase.WINDING
        return BurstPhase.PROTECTED

    if prev_burst == BurstPhase.WINDING:
        if session_count >= burst_exit_exchange:
            return BurstPhase.EXIT_PREP
        return BurstPhase.WINDING

    return prev_burst
