"""Motor cerebellum — action pattern learning and de-compilation.

Rule 32: Motor reflex zero-tolerance. Single failure = instant de-compilation.
         A failed reflex is immediately removed from the reflex cache and
         flagged so it cannot be re-compiled without full GVR.

Rule 12: Only VERIFIED resolutions become reflexes (enforced at compilation).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ActionPattern:
    """A learned motor pattern (reflex)."""

    pattern_id: str
    action_type: str
    target_pattern: str    # glob or prefix for matching targets
    success_count: int = 0
    failure_count: int = 0
    last_used: float = 0.0
    compiled: bool = True
    decompiled_at: Optional[float] = None
    decompile_reason: Optional[str] = None

    def to_dict(self) -> dict:
        d: dict = {
            "pattern_id": self.pattern_id,
            "action_type": self.action_type,
            "target_pattern": self.target_pattern,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_used": self.last_used,
            "compiled": self.compiled,
        }
        if self.decompiled_at is not None:
            d["decompiled_at"] = self.decompiled_at
        if self.decompile_reason is not None:
            d["decompile_reason"] = self.decompile_reason
        return d

    @classmethod
    def from_dict(cls, data: dict) -> ActionPattern:
        return cls(
            pattern_id=data["pattern_id"],
            action_type=data["action_type"],
            target_pattern=data["target_pattern"],
            success_count=data.get("success_count", 0),
            failure_count=data.get("failure_count", 0),
            last_used=data.get("last_used", 0.0),
            compiled=data.get("compiled", True),
            decompiled_at=data.get("decompiled_at"),
            decompile_reason=data.get("decompile_reason"),
        )


class MotorCerebellum:
    """Track and learn from motor action outcomes.

    Rule 32: Single failure = instant de-compilation.
    """

    def __init__(self) -> None:
        self._patterns: dict[str, ActionPattern] = {}

    # ------------------------------------------------------------------
    # Pattern management
    # ------------------------------------------------------------------

    def register_pattern(self, pattern: ActionPattern) -> None:
        """Register a new action pattern (reflex)."""
        self._patterns[pattern.pattern_id] = pattern

    def get_pattern(self, pattern_id: str) -> Optional[ActionPattern]:
        """Look up a pattern by ID."""
        return self._patterns.get(pattern_id)

    def find_pattern(self, action_type: str, target: str) -> Optional[ActionPattern]:
        """Find a compiled pattern matching the action type and target."""
        for pattern in self._patterns.values():
            if not pattern.compiled:
                continue
            if pattern.action_type != action_type:
                continue
            # Simple prefix match on target
            if target.startswith(pattern.target_pattern) or pattern.target_pattern == "*":
                return pattern
        return None

    # ------------------------------------------------------------------
    # Learning (Rule 32: zero-tolerance)
    # ------------------------------------------------------------------

    def record_success(self, pattern_id: str) -> None:
        """Record a successful execution of a pattern."""
        pattern = self._patterns.get(pattern_id)
        if pattern is None or not pattern.compiled:
            return
        pattern.success_count += 1
        pattern.last_used = time.time()

    def record_failure(self, pattern_id: str, reason: str) -> None:
        """Record a failed execution — triggers instant de-compilation.

        Rule 32: Single failure = instant de-compilation.
        The pattern is marked as decompiled and cannot be used until
        re-verified through full GVR.
        """
        pattern = self._patterns.get(pattern_id)
        if pattern is None:
            return

        pattern.failure_count += 1
        pattern.last_used = time.time()

        # Rule 32: instant de-compilation on ANY failure
        self._decompile(pattern, reason)

    def _decompile(self, pattern: ActionPattern, reason: str) -> None:
        """De-compile a pattern — remove from active reflexes.

        Rule 32: Zero-tolerance. Once decompiled, requires full GVR
        re-verification before re-compilation.
        """
        pattern.compiled = False
        pattern.decompiled_at = time.time()
        pattern.decompile_reason = reason

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_compiled_patterns(self) -> list[ActionPattern]:
        """Return all currently compiled (active) patterns."""
        return [p for p in self._patterns.values() if p.compiled]

    def get_decompiled_patterns(self) -> list[ActionPattern]:
        """Return all decompiled patterns (need re-verification)."""
        return [p for p in self._patterns.values() if not p.compiled]

    def to_dict(self) -> dict:
        return {
            "patterns": {pid: p.to_dict() for pid, p in self._patterns.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> MotorCerebellum:
        cerebellum = cls()
        for pid, pdata in data.get("patterns", {}).items():
            cerebellum._patterns[pid] = ActionPattern.from_dict(pdata)
        return cerebellum
