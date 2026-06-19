"""Rolling 14-day median baseline for HRV and resting HR.

Until 14 days of priors exist, compute_baseline returns None and the mapping
falls back to sleep-only rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Optional, Sequence

from .schema import BiometricPrior

BASELINE_DAYS = 14


@dataclass(frozen=True)
class Baseline:
    hrv: Optional[float]
    rhr: Optional[float]


def compute_baseline(history: Sequence[BiometricPrior]) -> Optional[Baseline]:
    """Median HRV/RHR over the most recent BASELINE_DAYS daily priors.

    Returns None until at least BASELINE_DAYS priors exist (the sleep-only
    regime). Within the window, each component's median is taken over whichever
    values are present; a component with no values in the window is None and its
    rules degrade. `history` is assumed one-prior-per-day (idempotency upstream).
    """
    if len(history) < BASELINE_DAYS:
        return None
    window = list(history)[-BASELINE_DAYS:]
    hrvs = [p.hrv_ms for p in window if p.hrv_ms is not None]
    rhrs = [p.resting_hr for p in window if p.resting_hr is not None]
    return Baseline(
        hrv=median(hrvs) if hrvs else None,
        rhr=median(rhrs) if rhrs else None,
    )
