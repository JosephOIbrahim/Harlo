"""biometric_prior.v1 — wire schema + capacity verdict types. Pure data.

The wire payload accepted at POST /v1/biometrics. The spec's field list is
exhaustive (no version field on the wire — the "v1" lives in SCHEMA / the
buffer kind / this module).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field

from harlo.engine.schemas import Energy

SCHEMA = "biometric_prior.v1"


class BiometricPrior(BaseModel):
    """A HealthKit-shaped daily capacity signal (biometric_prior.v1).

    `source` is REQUIRED (the spec gives the allowed values with no (opt)
    marker, unlike hrv_ms / resting_hr / workout_yesterday). Flagged for review.
    """

    captured_at: datetime
    sleep_minutes: int = Field(ge=0)
    hrv_ms: Optional[float] = None
    resting_hr: Optional[float] = None
    workout_yesterday: Optional[bool] = None
    source: Literal["shortcuts_relay", "manual"]

    @property
    def calendar_date(self) -> str:
        """YYYY-MM-DD — the idempotency key (one prior per calendar date)."""
        return self.captured_at.date().isoformat()


class Capacity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    DEPLETED = "depleted"


@dataclass(frozen=True)
class CapacityVerdict:
    """Result of mapping a prior → capacity → Energy seed.

    energy_seed is an engine Energy level. Per spec, capacity=DEPLETED seeds
    Energy.LOW (NOT Energy.DEPLETED) and raises directive_mode instead.
    """

    capacity: Capacity
    energy_seed: Energy
    directive_mode: bool
    pre_baseline: bool  # True when <14 days of history → sleep-only rules
