"""Mock HdClaude delegate — Sync/Execute/CommitResources.

Sprint 1 Phase 5: Simulates Claude's role in the exchange loop.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .schemas import (
    ActionBlock,
    ActionType,
    CognitiveObservation,
)


@dataclass
class DelegateResponse:
    """Response from the mock Claude delegate."""
    action: ActionBlock
    content: str
    tokens_used: int


class HdClaude:
    """Mock delegate simulating Claude's behavior in the exchange loop.

    Implements Sync/Execute/CommitResources pattern:
    - sync(): Receive current cognitive state
    - execute(): Generate a response action
    - commit_resources(): Report token usage
    """

    def __init__(self, seed: int = 42):
        import random
        self._rng = random.Random(seed)
        self._synced_state: Optional[CognitiveObservation] = None
        self._exchange_count = 0

    def sync(self, observation: CognitiveObservation) -> None:
        """Sync current cognitive state to the delegate."""
        self._synced_state = observation

    def execute(self) -> DelegateResponse:
        """Generate a response based on synced state.

        Returns an action appropriate to the current cognitive state.
        """
        if self._synced_state is None:
            return DelegateResponse(
                action=ActionBlock(action_type=ActionType.QUERY),
                content="[no state synced]",
                tokens_used=10,
            )

        state = self._synced_state.state
        self._exchange_count += 1

        # Simple heuristic response based on state
        action_type = ActionType.DIRECTIVE
        content = "Proceeding with task."
        tokens = self._rng.randint(50, 500)

        return DelegateResponse(
            action=ActionBlock(action_type=action_type, detail=content),
            content=content,
            tokens_used=tokens,
        )

    def commit_resources(self) -> dict:
        """Report resource usage."""
        return {
            "exchanges": self._exchange_count,
            "delegate": "HdClaude-mock-v1",
        }
