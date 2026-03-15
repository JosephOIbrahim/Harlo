"""DMN Window — S6: Session-exit synthesis.

On session exit, the Twin enters a brief DMN window to synthesize
observations into potential inquiries. This runs in the background
(via daemon's DMNTeardown) and respects the 30s budget.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from .types import InquiryType


@dataclass
class Observation:
    """A behavioral observation collected during a session."""
    content: str
    category: InquiryType
    timestamp: float = field(default_factory=time.time)
    weight: float = 1.0


@dataclass
class SynthesisCandidate:
    """A potential inquiry generated during DMN synthesis."""
    inquiry_type: InquiryType
    hypothesis: str
    alt_hypothesis: str
    supporting_observations: list[str]
    confidence: float
    generated_at: float = field(default_factory=time.time)


@dataclass
class DMNWindow:
    """Manages the session-exit synthesis window.

    Collects observations during a session, then synthesizes
    them into inquiry candidates when the session ends.
    No polling, no sleep. Called once at session exit.
    """
    observations: list[Observation] = field(default_factory=list)
    session_start: float = field(default_factory=time.time)

    def add_observation(self, content: str, category: InquiryType, weight: float = 1.0) -> None:
        """Record an observation during the session."""
        self.observations.append(Observation(
            content=content,
            category=category,
            weight=weight,
        ))

    def synthesize(self, abort_check=None) -> list[SynthesisCandidate]:
        """Synthesize observations into inquiry candidates.

        Called at session exit. Respects abort_check (callable returning bool)
        for preemption support (Rule 19).

        Args:
            abort_check: Optional callable that returns True if synthesis
                         should abort (new CLI command preempting).
        """
        if not self.observations:
            return []

        # Group observations by category
        by_category: dict[InquiryType, list[Observation]] = {}
        for obs in self.observations:
            if abort_check and abort_check():
                return []
            by_category.setdefault(obs.category, []).append(obs)

        candidates: list[SynthesisCandidate] = []

        for category, obs_list in by_category.items():
            if abort_check and abort_check():
                break

            # Need minimum observations to form a candidate
            if len(obs_list) < 2:
                continue

            # Build candidate from observations
            contents = [o.content for o in obs_list]
            total_weight = sum(o.weight for o in obs_list)
            confidence = min(total_weight / 10.0, 1.0)

            candidates.append(SynthesisCandidate(
                inquiry_type=category,
                hypothesis=f"Observed {len(obs_list)} {category.value} signals",
                alt_hypothesis=f"Coincidental {category.value} signals",
                supporting_observations=contents,
                confidence=confidence,
            ))

        return candidates

    def to_teardown_context(self) -> dict:
        """Package state for DMNTeardown background thread."""
        return {
            "session_start": self.session_start,
            "observation_count": len(self.observations),
            "observations": [
                {
                    "content": o.content,
                    "category": o.category.value,
                    "weight": o.weight,
                    "timestamp": o.timestamp,
                }
                for o in self.observations
            ],
        }

    def clear(self) -> None:
        """Reset for a new session."""
        self.observations.clear()
        self.session_start = time.time()
