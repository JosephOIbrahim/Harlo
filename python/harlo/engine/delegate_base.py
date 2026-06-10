"""HdCognitiveDelegate — Hydra-pattern delegate interface.

The 'Hd' prefix is a naming convention borrowed from USD Hydra, NOT an import.
All classes here are pure Python. Zero Pixar library dependencies.

Commandment 4: Capability-requirement routing separates WHAT from HOW.
The DAG outputs what's needed (capabilities). The Bridge selects who fulfills it.
The DAG never names a specific LLM.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DelegateCapabilities:
    """What a delegate can do."""
    delegate_id: str
    supported_tasks: list[str]
    latency_class: str          # "realtime", "interactive", "batch"
    context_window: int
    compression_factor: float = 1.0

    @property
    def effective_context(self) -> int:
        """Context window after compression."""
        return int(self.context_window * self.compression_factor)


@dataclass
class TaskContext:
    """What the current exchange needs."""
    task_type: str
    signal_class: str
    requires_coding: bool = False
    context_budget: str = "medium"
    exchange_index: int = 0


@dataclass
class DelegateResult:
    """What a delegate returns after execution."""
    response: str
    proposed_mutations: dict = field(default_factory=dict)
    observation_data: dict = field(default_factory=dict)
    tokens_used: int = 0


class HdCognitiveDelegate(ABC):
    """Base class for cognitive delegates.

    Hydra-pattern: any model implementing this interface
    can consume the composed cognitive stage.
    The stage never names a specific LLM.
    """

    @abstractmethod
    def get_delegate_id(self) -> str:
        """Return unique delegate identifier."""

    @abstractmethod
    def get_capabilities(self) -> DelegateCapabilities:
        """Return this delegate's capability declaration."""

    @abstractmethod
    def sync(self, stage_view: dict, computed_values: dict, context: TaskContext) -> None:
        """Pull state from composed stage. Prepare for execution."""

    @abstractmethod
    def execute(self, task: str) -> DelegateResult:
        """Produce output from synced cognitive state."""

    @abstractmethod
    def commit_resources(self, result: DelegateResult) -> dict:
        """Propose state mutations back to stage. Returns authored changes."""

    def get_status(self) -> str:
        """Return delegate operational status."""
        return "active"
