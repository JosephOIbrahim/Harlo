"""Inquiry Apoptosis — S5: TTL + exponential decay.

TTL range: 48h to 30d (per inquiry type).
Decay formula: e^(-3t/ttl).
Below 20% vitality = delete.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

from .types import InquiryType, TTL_HOURS

# S5: Deletion threshold
VITALITY_THRESHOLD = 0.20
# Decay steepness factor
DECAY_K = 3.0


@dataclass
class InquiryVitality:
    """Tracks the vitality (remaining life) of an inquiry."""
    inquiry_id: str
    inquiry_type: InquiryType
    created_at: float  # time.time()

    @property
    def ttl_hours(self) -> int:
        return TTL_HOURS[self.inquiry_type]

    @property
    def ttl_seconds(self) -> float:
        return self.ttl_hours * 3600.0

    def vitality(self, now: float | None = None) -> float:
        """Compute vitality as e^(-3t/ttl).

        Returns value in [0.0, 1.0].
        """
        if now is None:
            now = time.time()
        t = max(0.0, now - self.created_at)
        ttl = self.ttl_seconds
        if ttl <= 0:
            return 0.0
        return math.exp(-DECAY_K * t / ttl)

    def should_delete(self, now: float | None = None) -> bool:
        """S5: Below 20% vitality = delete."""
        return self.vitality(now) < VITALITY_THRESHOLD

    def remaining_hours(self, now: float | None = None) -> float:
        """Hours until vitality drops below threshold."""
        # Solve: e^(-3t/ttl) = 0.20
        # t = -ttl * ln(0.20) / 3
        if now is None:
            now = time.time()
        elapsed = max(0.0, now - self.created_at)
        ttl = self.ttl_seconds
        # Time at which vitality = threshold
        t_threshold = -ttl * math.log(VITALITY_THRESHOLD) / DECAY_K
        remaining_s = t_threshold - elapsed
        return max(0.0, remaining_s / 3600.0)


def sweep_expired(vitalities: list[InquiryVitality], now: float | None = None) -> tuple[list[str], list[InquiryVitality]]:
    """Sweep and return (expired_ids, surviving_vitalities)."""
    if now is None:
        now = time.time()
    expired: list[str] = []
    surviving: list[InquiryVitality] = []
    for v in vitalities:
        if v.should_delete(now):
            expired.append(v.inquiry_id)
        else:
            surviving.append(v)
    return expired, surviving
