"""Threshold mean-reversion for inquiry penalties.

Prevents penalty accumulation from permanently silencing inquiry types.
Penalties decay toward zero over time using exponential mean-reversion.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field


# Mean-reversion half-life in hours
REVERSION_HALF_LIFE_H = 24.0
# Derived decay constant
_LAMBDA = math.log(2) / REVERSION_HALF_LIFE_H


@dataclass
class PenaltyRecord:
    """A penalty applied to an inquiry type or topic."""
    key: str
    penalty: float
    applied_at: float  # time.time()

    def current_penalty(self, now: float | None = None) -> float:
        """Compute decayed penalty at time `now`."""
        if now is None:
            now = time.time()
        elapsed_h = max(0.0, (now - self.applied_at) / 3600.0)
        return self.penalty * math.exp(-_LAMBDA * elapsed_h)


@dataclass
class PenaltyLedger:
    """Tracks and decays penalties for inquiry keys."""
    records: list[PenaltyRecord] = field(default_factory=list)

    def add_penalty(self, key: str, amount: float, ts: float | None = None) -> None:
        """Add a penalty for a key."""
        if ts is None:
            ts = time.time()
        self.records.append(PenaltyRecord(key=key, penalty=amount, applied_at=ts))

    def effective_penalty(self, key: str, now: float | None = None) -> float:
        """Sum of all decayed penalties for a key."""
        if now is None:
            now = time.time()
        return sum(
            r.current_penalty(now)
            for r in self.records
            if r.key == key
        )

    def prune_negligible(self, threshold: float = 0.01, now: float | None = None) -> int:
        """Remove penalties that have decayed below threshold. Returns count removed."""
        if now is None:
            now = time.time()
        before = len(self.records)
        self.records = [
            r for r in self.records
            if r.current_penalty(now) >= threshold
        ]
        return before - len(self.records)
