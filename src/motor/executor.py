"""Motor executor — atomic action execution.

Rule 24: ONE action at a time. Execute ONE atomic action, return to full
         cognitive loop.
Rule 26: Motor reflexes skip planning, NEVER skip Basal Ganglia.
Rule 28: RED state halts ALL motor activity.
Rule 32: Single failure = instant de-compilation (handled by motor_cerebellum).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from .premotor import PlannedAction, ActionPlan
from .basal_ganglia import gate, GateDecision, GateResult
from .consent import ConsentState


class ExecutionStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    GATED = "gated"         # Blocked by Basal Ganglia
    HALTED = "halted"       # RED state


@dataclass
class ExecutionResult:
    """Result of a single atomic action execution."""

    status: ExecutionStatus
    action: PlannedAction
    gate_result: Optional[GateResult] = None
    output: Optional[dict] = None
    error: Optional[str] = None
    executed_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        d: dict = {
            "status": self.status.value,
            "action": self.action.to_dict(),
            "executed_at": self.executed_at,
        }
        if self.gate_result is not None:
            d["gate_result"] = self.gate_result.to_dict()
        if self.output is not None:
            d["output"] = self.output
        if self.error is not None:
            d["error"] = self.error
        return d


# ------------------------------------------------------------------
# Action handlers registry
# ------------------------------------------------------------------

# Map action_type -> handler function.
# Handlers take (action, session_state) and return a dict output.
_HANDLERS: dict[str, Callable[[PlannedAction, dict], dict]] = {}


def register_handler(action_type: str, handler: Callable[[PlannedAction, dict], dict]) -> None:
    """Register a handler for an action type."""
    _HANDLERS[action_type] = handler


def _default_handler(action: PlannedAction, session_state: dict) -> dict:
    """Default handler — returns the action payload as acknowledgment."""
    return {
        "acknowledged": True,
        "action_type": action.action_type,
        "target": action.target,
    }


# ------------------------------------------------------------------
# Execution (Rule 24: ONE at a time)
# ------------------------------------------------------------------

def execute_one(
    action: PlannedAction,
    session_state: dict,
    consent_state: Optional[ConsentState] = None,
) -> ExecutionResult:
    """Execute ONE atomic action through the Basal Ganglia gate.

    Rule 24: Only one action. Returns to cognitive loop after.
    Rule 26: ALWAYS goes through Basal Ganglia, even for reflexes.
    Rule 28: RED state → immediate halt.

    Args:
        action: The planned action to execute.
        session_state: Current session state dict.
        consent_state: Consent tracker.

    Returns:
        ExecutionResult with status and output.
    """
    # Rule 28: RED kills motor
    if session_state.get("cognitive_state") == "RED":
        return ExecutionResult(
            status=ExecutionStatus.HALTED,
            action=action,
            error="RED state — all motor activity halted (Rule 28)",
        )

    # Rule 26: ALWAYS gate, even reflexes
    gate_result = gate(action, session_state, consent_state)

    if gate_result.decision != GateDecision.DISINHIBIT:
        return ExecutionResult(
            status=ExecutionStatus.GATED,
            action=action,
            gate_result=gate_result,
            error=gate_result.failure_reason,
        )

    # Execute the action
    handler = _HANDLERS.get(action.action_type, _default_handler)
    try:
        output = handler(action, session_state)
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            action=action,
            gate_result=gate_result,
            output=output,
        )
    except Exception as exc:
        return ExecutionResult(
            status=ExecutionStatus.FAILED,
            action=action,
            gate_result=gate_result,
            error=str(exc),
        )


def execute_plan_step(
    plan: ActionPlan,
    session_state: dict,
    consent_state: Optional[ConsentState] = None,
) -> Optional[ExecutionResult]:
    """Execute the current step of an action plan.

    Rule 24: ONE action at a time. Advances the plan by one step.

    Returns:
        ExecutionResult for the current step, or None if plan is complete.
    """
    step = plan.current_step()
    if step is None:
        return None

    result = execute_one(step, session_state, consent_state)

    # Only advance if successful
    if result.status == ExecutionStatus.SUCCESS:
        plan.advance()

    return result
