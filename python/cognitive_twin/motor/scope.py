"""Scope validation — ensure actions stay within declared boundaries.

Actions must target resources within the declared scope. Scope violations
trigger INHIBIT in the Basal Ganglia gate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Scope:
    """Defines the allowed boundaries for motor actions."""

    allowed_targets: set[str] = field(default_factory=set)
    allowed_action_types: set[str] = field(default_factory=set)
    blocked_targets: set[str] = field(default_factory=set)
    max_payload_size: int = 1_000_000  # bytes

    def to_dict(self) -> dict:
        return {
            "allowed_targets": sorted(self.allowed_targets),
            "allowed_action_types": sorted(self.allowed_action_types),
            "blocked_targets": sorted(self.blocked_targets),
            "max_payload_size": self.max_payload_size,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Scope:
        return cls(
            allowed_targets=set(data.get("allowed_targets", [])),
            allowed_action_types=set(data.get("allowed_action_types", [])),
            blocked_targets=set(data.get("blocked_targets", [])),
            max_payload_size=data.get("max_payload_size", 1_000_000),
        )


@dataclass
class ScopeCheckResult:
    """Result of a scope validation check."""

    passed: bool
    reason: Optional[str] = None


def validate_scope(
    action_type: str,
    target: str,
    payload: dict,
    scope: Scope,
) -> ScopeCheckResult:
    """Validate that an action falls within the declared scope.

    Checks (in order):
    1. Target is not in blocked list.
    2. If allowed_targets is non-empty, target must be in it.
    3. If allowed_action_types is non-empty, action_type must be in it.
    4. Payload size is within limit.

    Returns:
        ScopeCheckResult with passed=True if all checks pass.
    """
    # 1. Blocked targets
    if target in scope.blocked_targets:
        return ScopeCheckResult(
            passed=False,
            reason=f"Target {target!r} is explicitly blocked",
        )

    # 2. Allowed targets (if specified)
    if scope.allowed_targets and target not in scope.allowed_targets:
        return ScopeCheckResult(
            passed=False,
            reason=f"Target {target!r} not in allowed targets",
        )

    # 3. Allowed action types (if specified)
    if scope.allowed_action_types and action_type not in scope.allowed_action_types:
        return ScopeCheckResult(
            passed=False,
            reason=f"Action type {action_type!r} not in allowed action types",
        )

    # 4. Payload size
    import json
    try:
        payload_bytes = len(json.dumps(payload).encode("utf-8"))
    except (TypeError, ValueError):
        payload_bytes = 0

    if payload_bytes > scope.max_payload_size:
        return ScopeCheckResult(
            passed=False,
            reason=f"Payload size {payload_bytes} exceeds max {scope.max_payload_size}",
        )

    return ScopeCheckResult(passed=True)
