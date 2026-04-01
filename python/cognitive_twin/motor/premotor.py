"""Premotor cortex — action plan generation and persistence.

Rule 31: Action plan is stored in the Composition stage.
Rule 24: ONE action at a time — current_step_index tracks progress.
Rule 29: Reversibility metadata drives consent escalation.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Optional

from .consent import ConsentLevel, get_consent_level, effective_consent_level


@dataclass
class PlannedAction:
    """A single atomic action in a plan."""

    action_type: str
    description: str
    target: str
    payload: dict
    consent_level: int
    reversible: bool
    side_effects: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "action_type": self.action_type,
            "description": self.description,
            "target": self.target,
            "payload": self.payload,
            "consent_level": self.consent_level,
            "reversible": self.reversible,
            "side_effects": self.side_effects,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PlannedAction:
        return cls(
            action_type=data["action_type"],
            description=data["description"],
            target=data["target"],
            payload=data["payload"],
            consent_level=data["consent_level"],
            reversible=data["reversible"],
            side_effects=data.get("side_effects", []),
        )


@dataclass
class ActionPlan:
    """A sequence of planned actions. Rule 31: persisted in Composition stage."""

    plan_id: str
    intent: str
    steps: list[PlannedAction]
    current_step_index: int = 0
    created_at: float = field(default_factory=time.time)
    completed: bool = False

    # ------------------------------------------------------------------
    # Navigation (Rule 24: one at a time)
    # ------------------------------------------------------------------

    def current_step(self) -> Optional[PlannedAction]:
        """Return the current step, or None if plan is exhausted."""
        if self.current_step_index >= len(self.steps):
            return None
        return self.steps[self.current_step_index]

    def advance(self) -> Optional[PlannedAction]:
        """Advance to the next step. Returns the new current step or None."""
        self.current_step_index += 1
        if self.current_step_index >= len(self.steps):
            self.completed = True
            return None
        return self.steps[self.current_step_index]

    def is_complete(self) -> bool:
        return self.completed or self.current_step_index >= len(self.steps)

    # ------------------------------------------------------------------
    # Serialisation (Rule 31: stored in Composition stage)
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "intent": self.intent,
            "steps": [s.to_dict() for s in self.steps],
            "current_step_index": self.current_step_index,
            "created_at": self.created_at,
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ActionPlan:
        return cls(
            plan_id=data["plan_id"],
            intent=data["intent"],
            steps=[PlannedAction.from_dict(s) for s in data["steps"]],
            current_step_index=data.get("current_step_index", 0),
            created_at=data.get("created_at", 0.0),
            completed=data.get("completed", False),
        )


# ------------------------------------------------------------------
# Plan creation
# ------------------------------------------------------------------

def create_plan(intent: str, raw_steps: list[dict], *, is_depleted: bool = False) -> ActionPlan:
    """Build an ActionPlan from raw step dicts.

    Each raw step should have: action_type, description, target, payload,
    reversible, side_effects.

    Consent levels are computed automatically with Rule 27/29 adjustments.
    """
    canonical = json.dumps({"intent": intent, "steps": raw_steps}, sort_keys=True)
    plan_id = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    planned: list[PlannedAction] = []
    for raw in raw_steps:
        base_level = get_consent_level(raw.get("action_type", "unknown"))
        is_irreversible = not raw.get("reversible", True)
        level = effective_consent_level(
            base_level,
            is_depleted=is_depleted,
            is_irreversible=is_irreversible,
        )
        planned.append(PlannedAction(
            action_type=raw["action_type"],
            description=raw.get("description", ""),
            target=raw.get("target", ""),
            payload=raw.get("payload", {}),
            consent_level=int(level),
            reversible=raw.get("reversible", True),
            side_effects=raw.get("side_effects", []),
        ))

    return ActionPlan(plan_id=plan_id, intent=intent, steps=planned)
