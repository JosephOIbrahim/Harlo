"""HdClaudeCode — Implementation delegate.

Handles code generation, debugging, file manipulation tasks.
Pure Python. Zero Pixar library dependencies.
"""

from __future__ import annotations

from typing import Optional

from .delegate_base import (
    DelegateCapabilities,
    DelegateResult,
    HdCognitiveDelegate,
    TaskContext,
)
from .schemas import Burnout, Energy, Momentum


class HdClaudeCode(HdCognitiveDelegate):
    """Implementation delegate for code-centric tasks.

    Provides enriched context tuned for implementation:
    orientation markers, progress tracking, file context.
    """

    def __init__(self) -> None:
        self._cognitive_context: str = ""
        self._stage_view: dict = {}
        self._computed: dict = {}
        self._context: Optional[TaskContext] = None
        self._exchange_count: int = 0

    def get_delegate_id(self) -> str:
        return "claude_code"

    def get_capabilities(self) -> DelegateCapabilities:
        return DelegateCapabilities(
            delegate_id="claude_code",
            supported_tasks=[
                "implementation", "code_generation",
                "debugging", "file_manipulation", "testing",
            ],
            latency_class="batch",
            context_window=200_000,
            compression_factor=1.0,
        )

    def sync(self, stage_view: dict, computed_values: dict, context: TaskContext) -> None:
        """Package cognitive state for implementation context."""
        self._stage_view = stage_view
        self._computed = computed_values
        self._context = context
        self._cognitive_context = self._build_implementation_block(
            stage_view, computed_values, context
        )

    def execute(self, task: str) -> DelegateResult:
        """Return implementation-tuned cognitive context."""
        self._exchange_count += 1
        return DelegateResult(
            response=self._cognitive_context,
            proposed_mutations=self._build_mutations(),
            observation_data=self._build_observation_data(),
            tokens_used=len(self._cognitive_context) // 4,
        )

    def commit_resources(self, result: DelegateResult) -> dict:
        """Write session state back to delegate sublayer."""
        return result.proposed_mutations

    def _build_implementation_block(self, stage_view: dict, computed: dict,
                                     context: TaskContext) -> str:
        """Build implementation-tuned context."""
        momentum = computed.get("momentum", 1)
        energy = computed.get("energy", 2)
        burnout = computed.get("burnout", 0)

        momentum_name = Momentum(momentum).name if isinstance(momentum, int) else str(momentum)
        energy_name = Energy(energy).name if isinstance(energy, int) else str(energy)

        lines = [
            "+== IMPLEMENTATION CONTEXT ===========================+",
            f"| Momentum: {momentum_name:<12} Energy: {energy_name:<12} |",
            f"| Exchange: {context.exchange_index:<8} Task: {context.task_type:<14} |",
            "+====================================================+",
        ]
        return "\n".join(lines)

    def _build_mutations(self) -> dict:
        return {
            "/delegate/claude_code/exchange_count": self._exchange_count,
            "/delegate/claude_code/status": "active",
        }

    def _build_observation_data(self) -> dict:
        return {
            "delegate_id": "claude_code",
            "exchange_count": self._exchange_count,
            "context_length": len(self._cognitive_context),
        }
