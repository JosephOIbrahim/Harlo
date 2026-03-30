"""Pure function: compute routing requirements.

Outputs capability requirements, NOT delegate names (Commandment 4).
The DAG says WHAT is needed. The registry decides WHO fulfills it.
"""

from __future__ import annotations

from src.schemas import (
    Burnout,
    BurstPhase,
    CognitiveObservation,
    Energy,
    Momentum,
    StateBlock,
)


# Signal → expert mapping
SIGNAL_EXPERT_MAP = {
    "frustrated": "validator",
    "stuck": "scaffolder",
    "depleted": "restorer",
    "exploring": "socratic",
    "focused": "direct",
    "directive": "direct",
}


def compute_routing(
    authored: CognitiveObservation,
    prev_state: StateBlock,
    has_valid_consent: bool = False,
) -> dict:
    """Compute routing requirements based on cognitive state.

    Returns dict with:
      - expert: str (signal-mapped expert type)
      - requirements: dict (capability requirements for delegate selection)

    Safety overrides:
      - burnout >= ORANGE and no consent → force restorer
      - RED → always force restorer (consent ignored)
    """
    state = authored.state
    dynamics = authored.dynamics

    # Determine expert from signals
    expert = _classify_expert(authored)

    # Base requirements
    requires_coding = dynamics.tasks_completed > 0 and dynamics.exchange_velocity > 0.5
    latency_max = "interactive"
    context_budget = "medium"

    # Adjust based on state
    if state.momentum >= Momentum.ROLLING:
        context_budget = "heavy"
    elif state.momentum <= Momentum.COLD_START:
        context_budget = "light"

    if dynamics.burst_phase >= BurstPhase.DETECTED:
        latency_max = "realtime"

    # Map expert to supported tasks
    task_map = {
        "validator": ["reasoning", "coaching"],
        "scaffolder": ["reasoning", "coaching"],
        "restorer": ["coaching"],
        "socratic": ["reasoning", "exploration"],
        "direct": ["reasoning", "implementation"],
    }
    supported_tasks = task_map.get(expert, ["reasoning"])

    # Safety overrides (Commandment 6: consent is OOB)
    if state.burnout == Burnout.RED:
        expert = "restorer"
        supported_tasks = ["coaching"]
        requires_coding = False
        context_budget = "light"

    elif state.burnout >= Burnout.ORANGE and not has_valid_consent:
        expert = "restorer"
        supported_tasks = ["coaching"]
        requires_coding = False

    return {
        "expert": expert,
        "requirements": {
            "requires_coding": requires_coding,
            "latency_max": latency_max,
            "context_budget": context_budget,
            "supported_tasks": supported_tasks,
        },
    }


def _classify_expert(authored: CognitiveObservation) -> str:
    """Classify the active expert from cognitive signals."""
    dynamics = authored.dynamics
    state = authored.state

    if dynamics.frustration_signal >= 0.7:
        return "frustrated"

    if state.energy == Energy.DEPLETED:
        return "depleted"

    if dynamics.topic_coherence < 0.4 and state.momentum <= Momentum.COLD_START:
        return "stuck"

    if dynamics.topic_coherence > 0.7 and dynamics.exchange_velocity > 0.6:
        if dynamics.burst_phase >= BurstPhase.DETECTED:
            return "focused"

    if dynamics.topic_coherence > 0.6:
        return "exploring"

    return "direct"
