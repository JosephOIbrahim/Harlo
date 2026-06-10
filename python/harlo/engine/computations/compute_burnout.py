"""Pure function: compute burnout state transition.

Commandment 7: RED event is an exogenous override: ANY → RED.
Sequential burnout: GREEN → YELLOW → ORANGE → RED (never skips, except RED override).
INV-14 exception: exogenous_red=True bypasses sequential rule.
"""

from __future__ import annotations

from src.schemas import (
    Burnout,
    CognitiveObservation,
    StateBlock,
)


def compute_burnout(
    authored: CognitiveObservation,
    prev_state: StateBlock,
    exogenous_red: bool = False,
    frustration_burnout_threshold: float = 0.7,
    burnout_exchange_yellow: float = 20,
    burnout_exchange_orange: float = 40,
) -> Burnout:
    """Compute next burnout state.

    Rules:
      - exogenous_red=True → ANY → RED immediately (Commandment 7, INV-14 exception)
      - Sequential only: GREEN→YELLOW→ORANGE→RED (never skip)
      - Escalation: frustration >= threshold OR long session without break
      - De-escalation: low frustration AND recent break can reduce by 1
    """
    if exogenous_red:
        return Burnout.RED

    prev_burnout = prev_state.burnout
    dynamics = authored.dynamics
    frustration = dynamics.frustration_signal
    exchanges_no_break = dynamics.exchanges_without_break

    # Escalation check
    should_escalate = False
    if frustration >= frustration_burnout_threshold:
        should_escalate = True
    elif prev_burnout == Burnout.GREEN and exchanges_no_break >= burnout_exchange_yellow:
        should_escalate = True
    elif prev_burnout == Burnout.YELLOW and exchanges_no_break >= burnout_exchange_orange:
        should_escalate = True
    elif prev_burnout == Burnout.ORANGE and frustration >= 0.9:
        should_escalate = True

    if should_escalate and prev_burnout < Burnout.RED:
        return Burnout(prev_burnout + 1)

    # De-escalation: low frustration + recent break
    if frustration < 0.2 and exchanges_no_break < 5 and prev_burnout > Burnout.GREEN:
        return Burnout(prev_burnout - 1)

    return prev_burnout
