"""DelegateRegistry — capability-matching delegate selection.

Commandment 4: The registry never hardcodes which delegate handles what.
It matches capabilities to requirements.
"""

from __future__ import annotations

from typing import Optional

from .delegate_base import DelegateCapabilities, HdCognitiveDelegate


# Latency ordering: lower index = faster
LATENCY_ORDER = {"realtime": 0, "interactive": 1, "batch": 2}

# Context budget → minimum effective tokens
CONTEXT_BUDGET_TOKENS = {
    "light": 10_000,
    "medium": 50_000,
    "heavy": 150_000,
}


class DelegateRegistry:
    """Manages registered delegates and selects by capability matching.

    Selection logic:
    1. Filter: requires_coding → must have 'code_generation' in supported_tasks
    2. Filter: supported_tasks must overlap with requirements
    3. Filter: context_budget → effective_context >= minimum
    4. Prefer: matching or faster latency_class
    5. Tiebreak: lower latency, then higher context
    """

    def __init__(self) -> None:
        self._delegates: dict[str, HdCognitiveDelegate] = {}

    def register(self, delegate: HdCognitiveDelegate) -> None:
        """Register a delegate."""
        self._delegates[delegate.get_delegate_id()] = delegate

    def unregister(self, delegate_id: str) -> None:
        """Remove a delegate from the registry."""
        self._delegates.pop(delegate_id, None)

    def get(self, delegate_id: str) -> Optional[HdCognitiveDelegate]:
        """Get a specific delegate by ID."""
        return self._delegates.get(delegate_id)

    def list_delegates(self) -> list[DelegateCapabilities]:
        """Return capabilities of all registered delegates."""
        return [d.get_capabilities() for d in self._delegates.values()]

    def select(self, requirements: dict) -> HdCognitiveDelegate:
        """Select the best delegate matching the given requirements.

        Args:
            requirements: Dict with optional keys:
                - requires_coding: bool
                - latency_max: str ("realtime", "interactive", "batch")
                - context_budget: str ("light", "medium", "heavy")
                - supported_tasks: list[str]

        Returns:
            Best matching delegate. Falls back to first registered if no match.

        Raises:
            ValueError: If no delegates are registered.
        """
        if not self._delegates:
            raise ValueError("No delegates registered")

        candidates = list(self._delegates.values())

        # Filter: requires_coding
        if requirements.get("requires_coding", False):
            coding_candidates = [
                d for d in candidates
                if "code_generation" in d.get_capabilities().supported_tasks
            ]
            if coding_candidates:
                candidates = coding_candidates

        # Filter: supported_tasks overlap
        required_tasks = requirements.get("supported_tasks", [])
        if required_tasks:
            task_candidates = [
                d for d in candidates
                if any(t in d.get_capabilities().supported_tasks for t in required_tasks)
            ]
            if task_candidates:
                candidates = task_candidates

        # Filter: context_budget
        budget = requirements.get("context_budget", "medium")
        min_tokens = CONTEXT_BUDGET_TOKENS.get(budget, 50_000)
        context_candidates = [
            d for d in candidates
            if d.get_capabilities().effective_context >= min_tokens
        ]
        if context_candidates:
            candidates = context_candidates

        # Filter: latency
        max_latency = requirements.get("latency_max", "batch")
        max_latency_idx = LATENCY_ORDER.get(max_latency, 2)
        latency_candidates = [
            d for d in candidates
            if LATENCY_ORDER.get(d.get_capabilities().latency_class, 2) <= max_latency_idx
        ]
        if latency_candidates:
            candidates = latency_candidates

        # Sort: lower latency first, then higher context
        candidates.sort(key=lambda d: (
            LATENCY_ORDER.get(d.get_capabilities().latency_class, 2),
            -d.get_capabilities().effective_context,
        ))

        return candidates[0]
