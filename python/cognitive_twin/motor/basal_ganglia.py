"""Basal Ganglia — 5-check inhibition gate for motor actions.

Rule 23: DEFAULT IS INHIBIT ALL. Every action requires ALL five checks to pass.
Rule 25: Level 3 (LOCKED) NEVER opens — gate returns LOCKED immediately.
Rule 26: Motor reflexes skip planning, NEVER skip Basal Ganglia.
Rule 28: RED state halts ALL motor activity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .premotor import PlannedAction
from .consent import ConsentLevel, ConsentState, effective_consent_level
from .scope import Scope, validate_scope


class GateDecision(Enum):
    DISINHIBIT = "disinhibit"  # All checks pass — action may proceed
    INHIBIT = "inhibit"        # One or more checks failed
    ESCALATE = "escalate"      # Needs higher consent
    LOCKED = "locked"          # Level 3 — NEVER opens


@dataclass
class GateResult:
    """Result of the 5-check inhibition gate."""

    decision: GateDecision
    checks: dict[str, bool] = field(default_factory=dict)
    failure_reason: Optional[str] = None

    def to_dict(self) -> dict:
        d: dict = {
            "decision": self.decision.value,
            "checks": self.checks,
        }
        if self.failure_reason is not None:
            d["failure_reason"] = self.failure_reason
        return d


# ------------------------------------------------------------------
# The five checks
# ------------------------------------------------------------------

def _check_anchor(action: PlannedAction, session_state: dict) -> tuple[bool, Optional[str]]:
    """Check 1: Anchor alignment.

    Verify the action's intent is anchored to a legitimate cognitive goal.
    """
    cognitive_state = session_state.get("cognitive_state", "")

    # Rule 28: RED state halts ALL motor activity
    if cognitive_state == "RED":
        return False, "RED state — all motor activity halted (Rule 28)"

    # Action must have a description (minimal anchor requirement)
    if not action.description:
        return False, "Action has no description — cannot verify anchor"

    return True, None


def _check_consent(
    action: PlannedAction,
    session_state: dict,
    consent_state: ConsentState,
) -> tuple[bool, Optional[str]]:
    """Check 2: Consent level.

    Rule 25: LOCKED never passes.
    Rule 27: DEPLETED promotes SESSION to PER_ACTION.
    Rule 29: Irreversible promotes lower levels.
    """
    is_depleted = session_state.get("is_depleted", False)

    level = effective_consent_level(
        ConsentLevel(action.consent_level),
        is_depleted=is_depleted,
        is_irreversible=not action.reversible,
    )

    # Rule 25: LOCKED never opens
    if level == ConsentLevel.LOCKED:
        return False, "LOCKED consent — gate NEVER opens (Rule 25)"

    action_id = f"{action.action_type}:{action.target}"
    if not consent_state.has_consent(level, action_id):
        return False, f"Missing consent for level {level.name} (action: {action_id})"

    return True, None


def _check_elenchus(action: PlannedAction, session_state: dict) -> tuple[bool, Optional[str]]:
    """Check 3: Elenchus verification state.

    The action's underlying intent must have been verified.
    """
    elenchus_state = session_state.get("elenchus_state", "")

    if elenchus_state == "spec_gamed":
        return False, "Elenchus detected spec-gaming — action blocked"

    if elenchus_state == "unprovable":
        return False, "Elenchus state is UNPROVABLE — action blocked"

    # Verified or no elenchus context (autonomous actions)
    return True, None


def _check_reversibility(action: PlannedAction, session_state: dict) -> tuple[bool, Optional[str]]:
    """Check 4: Reversibility.

    Rule 29: Irreversible actions at high consent levels require extra scrutiny.
    Irreversible + LOCKED = always blocked (handled by consent check).
    """
    if not action.reversible:
        level = ConsentLevel(action.consent_level)
        # Rule 29: Level 1 + irreversible was already promoted to Level 2
        # But if somehow an irreversible LOCKED action arrives, block it
        if level == ConsentLevel.LOCKED:
            return False, "Irreversible LOCKED action — permanently blocked"

        # Warn but pass — consent check already escalated the level
        if not action.side_effects:
            return True, None

        # Side effects on irreversible action — extra scrutiny
        max_side_effects = session_state.get("max_irreversible_side_effects", 3)
        if len(action.side_effects) > max_side_effects:
            return False, (
                f"Irreversible action has {len(action.side_effects)} side effects "
                f"(max {max_side_effects})"
            )

    return True, None


def _check_scope(action: PlannedAction, session_state: dict) -> tuple[bool, Optional[str]]:
    """Check 5: Scope validation.

    Ensure the action targets resources within declared boundaries.
    """
    scope_data = session_state.get("scope")
    if scope_data is None:
        # No scope declared — conservative: only AUTONOMOUS passes
        if ConsentLevel(action.consent_level) == ConsentLevel.AUTONOMOUS:
            return True, None
        return False, "No scope declared — non-autonomous action blocked"

    scope = Scope.from_dict(scope_data) if isinstance(scope_data, dict) else scope_data
    result = validate_scope(action.action_type, action.target, action.payload, scope)

    if not result.passed:
        return False, f"Scope violation: {result.reason}"

    return True, None


# ------------------------------------------------------------------
# Main gate function
# ------------------------------------------------------------------

def gate(
    action: PlannedAction,
    session_state: dict,
    consent_state: Optional[ConsentState] = None,
) -> GateResult:
    """Run the 5-check inhibition gate.

    DEFAULT: INHIBIT (Rule 23).
    ALL five checks must pass for DISINHIBIT.
    ANY failure results in INHIBIT, ESCALATE, or LOCKED.

    The five checks:
    1. Anchor alignment
    2. Consent level
    3. Elenchus verification
    4. Reversibility
    5. Scope validation

    Args:
        action: The planned action to gate.
        session_state: Dict with cognitive_state, is_depleted, elenchus_state,
                       scope, etc.
        consent_state: ConsentState tracker. If None, a fresh (no-grant) state
                       is used — which means only AUTONOMOUS actions can pass.

    Returns:
        GateResult with decision and per-check results.
    """
    if consent_state is None:
        consent_state = ConsentState()

    checks: dict[str, bool] = {}
    first_failure: Optional[str] = None

    # --- Check 1: Anchor ---
    anchor_ok, anchor_reason = _check_anchor(action, session_state)
    checks["anchor"] = anchor_ok
    if not anchor_ok and first_failure is None:
        first_failure = anchor_reason

    # --- Check 2: Consent ---
    consent_ok, consent_reason = _check_consent(action, session_state, consent_state)
    checks["consent"] = consent_ok
    if not consent_ok and first_failure is None:
        first_failure = consent_reason

    # --- Check 3: Elenchus ---
    elenchus_ok, elenchus_reason = _check_elenchus(action, session_state)
    checks["elenchus"] = elenchus_ok
    if not elenchus_ok and first_failure is None:
        first_failure = elenchus_reason

    # --- Check 4: Reversibility ---
    rev_ok, rev_reason = _check_reversibility(action, session_state)
    checks["reversibility"] = rev_ok
    if not rev_ok and first_failure is None:
        first_failure = rev_reason

    # --- Check 5: Scope ---
    scope_ok, scope_reason = _check_scope(action, session_state)
    checks["scope"] = scope_ok
    if not scope_ok and first_failure is None:
        first_failure = scope_reason

    # --- Decision ---
    all_passed = all(checks.values())

    if all_passed:
        return GateResult(decision=GateDecision.DISINHIBIT, checks=checks)

    # Rule 25: If consent was LOCKED, return LOCKED
    level = ConsentLevel(action.consent_level)
    effective = effective_consent_level(
        level,
        is_depleted=session_state.get("is_depleted", False),
        is_irreversible=not action.reversible,
    )
    if effective == ConsentLevel.LOCKED or level == ConsentLevel.LOCKED:
        return GateResult(
            decision=GateDecision.LOCKED,
            checks=checks,
            failure_reason=first_failure or "LOCKED — gate NEVER opens",
        )

    # If consent check failed but others passed, suggest escalation
    if not consent_ok and all(v for k, v in checks.items() if k != "consent"):
        return GateResult(
            decision=GateDecision.ESCALATE,
            checks=checks,
            failure_reason=first_failure,
        )

    # Default: INHIBIT
    return GateResult(
        decision=GateDecision.INHIBIT,
        checks=checks,
        failure_reason=first_failure,
    )
