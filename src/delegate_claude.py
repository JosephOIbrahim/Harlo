"""HdClaude — Interactive reasoning delegate.

Connects via the existing MCP server. Claude calls tools,
the twin evaluates state and returns enriched context.
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
from .schemas import (
    Burnout,
    Energy,
    Momentum,
)


class HdClaude(HdCognitiveDelegate):
    """Interactive reasoning delegate.

    For MCP-based delegates, 'execute' returns the enriched cognitive
    context that will be injected into Claude's system prompt via twin_coach.
    Claude itself does the reasoning — we provide the state.
    """

    def __init__(self) -> None:
        self._cognitive_context: str = ""
        self._stage_view: dict = {}
        self._computed: dict = {}
        self._context: Optional[TaskContext] = None
        self._exchange_count: int = 0

    def get_delegate_id(self) -> str:
        return "claude"

    def get_capabilities(self) -> DelegateCapabilities:
        return DelegateCapabilities(
            delegate_id="claude",
            supported_tasks=[
                "reasoning", "coaching", "architecture",
                "exploration", "writing", "analysis",
            ],
            latency_class="interactive",
            context_window=200_000,
            compression_factor=1.0,
        )

    def sync(self, stage_view: dict, computed_values: dict, context: TaskContext) -> None:
        """Package cognitive state into enriched context."""
        self._stage_view = stage_view
        self._computed = computed_values
        self._context = context
        self._cognitive_context = self._build_coach_block(
            stage_view, computed_values, context
        )

    def execute(self, task: str) -> DelegateResult:
        """Return enriched cognitive context for system prompt injection."""
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

    def _build_coach_block(self, stage_view: dict, computed: dict,
                           context: TaskContext) -> str:
        """Build structured cognitive context from computed values."""
        momentum = computed.get("momentum", 1)
        burnout = computed.get("burnout", 0)
        energy = computed.get("energy", 2)
        burst = computed.get("burst", 0)
        allostasis = computed.get("allostasis", {})
        load = allostasis.get("load", 0.0) if isinstance(allostasis, dict) else 0.0

        momentum_name = Momentum(momentum).name if isinstance(momentum, int) else str(momentum)
        burnout_name = Burnout(burnout).name if isinstance(burnout, int) else str(burnout)
        energy_name = Energy(energy).name if isinstance(energy, int) else str(energy)

        lines = [
            "+== COGNITIVE STATE ==================================+",
            f"| Momentum: {momentum_name:<12} Energy: {energy_name:<12} |",
            f"| Burnout:  {burnout_name:<12} Burst:  {burst:<12} |",
            f"| Load:     {load:<12.3f} Exchange: {context.exchange_index:<8} |",
            f"| Task:     {context.task_type:<12} Signal: {context.signal_class:<10} |",
            "+====================================================+",
        ]
        return "\n".join(lines)

    def _build_mutations(self) -> dict:
        """Build proposed state mutations."""
        return {
            "/delegate/claude/exchange_count": self._exchange_count,
            "/delegate/claude/status": "active",
        }

    def _build_observation_data(self) -> dict:
        """Build observation data for emission."""
        return {
            "delegate_id": "claude",
            "exchange_count": self._exchange_count,
            "context_length": len(self._cognitive_context),
        }
