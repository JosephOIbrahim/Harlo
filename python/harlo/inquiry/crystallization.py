"""Trace Crystallization — S7.

3+ observations below threshold -> decay rate becomes lambda/10.
Max 50 crystallized traces.
Eviction by lowest preservation_score.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

MAX_CRYSTALLIZED = 50
MIN_OBSERVATIONS_TO_CRYSTALLIZE = 3
DECAY_DIVISOR = 10  # Crystallized traces decay at lambda/10


@dataclass
class CrystallizedTrace:
    """A trace that has been crystallized due to repeated sub-threshold observation."""
    trace_id: str
    topic_key: str
    observations: list[str]
    observation_count: int
    original_decay_rate: float
    crystallized_decay_rate: float
    preservation_score: float
    crystallized_at: float = field(default_factory=time.time)

    @property
    def is_valid(self) -> bool:
        return self.observation_count >= MIN_OBSERVATIONS_TO_CRYSTALLIZE


@dataclass
class CrystallizationStore:
    """Manages the crystallized trace pool (max 50)."""
    traces: list[CrystallizedTrace] = field(default_factory=list)

    def attempt_crystallize(
        self,
        trace_id: str,
        topic_key: str,
        observations: list[str],
        decay_rate: float,
        *,
        threshold: int | None = None,
        depth_weight: float | None = None,
        preservation_score: float | None = None,
    ) -> CrystallizedTrace | None:
        """Attempt to crystallize a trace.

        S7: 3+ observations below threshold -> decay rate lambda/10.

        ``preservation_score`` is computed from the constitutional formula
        ``(len(observations) / threshold) * depth_weight``.  Pass
        ``threshold`` and ``depth_weight`` as keyword arguments and the
        engine will compute the score deterministically.

        ``preservation_score=`` is retained as a legacy keyword for the
        existing test suite; new callers should use the formula path so the
        score is reproducible from inputs.

        Returns the crystallized trace, or None if requirements not met.
        """
        if len(observations) < MIN_OBSERVATIONS_TO_CRYSTALLIZE:
            return None

        if threshold is not None and depth_weight is not None:
            # S7 literal (CLAUDE.md): preservation_score = (obs/threshold) * depth_weight.
            # Computed in-engine so eviction is deterministic and callers
            # cannot inject arbitrary scores.
            if threshold <= 0:
                raise ValueError("threshold must be positive")
            score = (len(observations) / threshold) * depth_weight
        elif preservation_score is not None:
            # Legacy path; prefer the formula keyword pair for new code.
            score = preservation_score
        else:
            raise ValueError(
                "attempt_crystallize requires (threshold, depth_weight) "
                "or preservation_score"
            )

        # Check if already crystallized
        for existing in self.traces:
            if existing.trace_id == trace_id:
                existing.observations = observations
                existing.observation_count = len(observations)
                existing.preservation_score = score
                return existing

        crystallized = CrystallizedTrace(
            trace_id=trace_id,
            topic_key=topic_key,
            observations=observations,
            observation_count=len(observations),
            original_decay_rate=decay_rate,
            crystallized_decay_rate=decay_rate / DECAY_DIVISOR,
            preservation_score=score,
        )

        if len(self.traces) >= MAX_CRYSTALLIZED:
            self._evict_lowest()

        self.traces.append(crystallized)
        return crystallized

    def _evict_lowest(self) -> None:
        """Evict the trace with the lowest preservation_score."""
        if not self.traces:
            return
        worst_idx = min(range(len(self.traces)), key=lambda i: self.traces[i].preservation_score)
        self.traces.pop(worst_idx)

    def get_decay_rate(self, trace_id: str, default_rate: float) -> float:
        """Get effective decay rate for a trace (crystallized or default)."""
        for t in self.traces:
            if t.trace_id == trace_id:
                return t.crystallized_decay_rate
        return default_rate

    def count(self) -> int:
        return len(self.traces)
