"""Consent gradient — 4-level consent model for motor actions.

Rule 25: Level 3 (LOCKED) NEVER opens. Financial, irreversible, other people's data.
Rule 27: DEPLETED state downgrades motor: Level 1 becomes Level 2.
Rule 29: Level 1 + irreversible = Level 2. Level 2 stays Level 2.
         NEVER Level 2 + irreversible = Level 3.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Optional


class ConsentLevel(IntEnum):
    """Consent levels ordered by severity."""
    AUTONOMOUS = 0   # Read-only, no side effects
    SESSION = 1      # Web search, public APIs
    PER_ACTION = 2   # Send messages, write files
    LOCKED = 3       # Financial, irreversible, other people's data — NEVER opens


# ------------------------------------------------------------------
# Action-type to consent-level mapping
# ------------------------------------------------------------------

_ACTION_CONSENT_MAP: dict[str, ConsentLevel] = {
    "read": ConsentLevel.AUTONOMOUS,
    "query": ConsentLevel.AUTONOMOUS,
    "inspect": ConsentLevel.AUTONOMOUS,
    "web_search": ConsentLevel.SESSION,
    "api_read": ConsentLevel.SESSION,
    "cache_lookup": ConsentLevel.SESSION,
    "write_file": ConsentLevel.PER_ACTION,
    "send_message": ConsentLevel.PER_ACTION,
    "api_write": ConsentLevel.PER_ACTION,
    "delete": ConsentLevel.PER_ACTION,
    "financial": ConsentLevel.LOCKED,
    "irreversible_delete": ConsentLevel.LOCKED,
    "third_party_data": ConsentLevel.LOCKED,
}


def get_consent_level(action_type: str) -> ConsentLevel:
    """Return the consent level for an action type.

    Unknown action types default to PER_ACTION (conservative).
    """
    return _ACTION_CONSENT_MAP.get(action_type, ConsentLevel.PER_ACTION)


def effective_consent_level(
    base_level: ConsentLevel,
    *,
    is_depleted: bool = False,
    is_irreversible: bool = False,
) -> ConsentLevel:
    """Compute effective consent level after rule adjustments.

    Rule 25: LOCKED never changes — it is always LOCKED.
    Rule 27: DEPLETED promotes SESSION (1) to PER_ACTION (2).
    Rule 29: Irreversible promotes AUTONOMOUS (0) or SESSION (1) to PER_ACTION (2).
             PER_ACTION stays PER_ACTION. NEVER promotes to LOCKED.

    Returns:
        The adjusted ConsentLevel.
    """
    # Rule 25: LOCKED is immutable
    if base_level == ConsentLevel.LOCKED:
        return ConsentLevel.LOCKED

    level = base_level

    # Rule 29: irreversible caps — Level 1 + irreversible = Level 2
    # Level 0 + irreversible also becomes Level 2
    if is_irreversible and level < ConsentLevel.PER_ACTION:
        level = ConsentLevel.PER_ACTION

    # Rule 27: DEPLETED promotes SESSION to PER_ACTION
    if is_depleted and level == ConsentLevel.SESSION:
        level = ConsentLevel.PER_ACTION

    # Rule 29 guard: NEVER promote to LOCKED
    if level > ConsentLevel.PER_ACTION:
        level = ConsentLevel.PER_ACTION

    return level


def is_locked(level: ConsentLevel) -> bool:
    """Rule 25: check if consent level is LOCKED (never opens)."""
    return level == ConsentLevel.LOCKED


class ConsentState:
    """Track per-session consent grants."""

    def __init__(self) -> None:
        self._session_granted: bool = False
        self._per_action_grants: dict[str, bool] = {}

    def grant_session(self) -> None:
        """Grant session-level consent."""
        self._session_granted = True

    def revoke_session(self) -> None:
        """Revoke session-level consent."""
        self._session_granted = False
        self._per_action_grants.clear()

    def grant_action(self, action_id: str) -> None:
        """Grant consent for a specific action."""
        self._per_action_grants[action_id] = True

    def has_consent(self, level: ConsentLevel, action_id: Optional[str] = None) -> bool:
        """Check if consent is granted for a level.

        Rule 25: LOCKED always returns False.
        """
        if level == ConsentLevel.LOCKED:
            return False  # NEVER opens
        if level == ConsentLevel.AUTONOMOUS:
            return True  # No consent needed
        if level == ConsentLevel.SESSION:
            return self._session_granted
        if level == ConsentLevel.PER_ACTION:
            if action_id is None:
                return False
            return self._per_action_grants.get(action_id, False)
        return False
