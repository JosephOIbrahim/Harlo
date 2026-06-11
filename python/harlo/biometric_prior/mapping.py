"""biometric_prior → capacity → Energy seed.

Severity-first evaluation. The spec lists the rows best-to-worst for
readability, but they MUST be evaluated worst-to-best: the `low` row
(sleep<=330) is a superset of `depleted` (sleep<270), so depleted is checked
first or it never fires. `medium` is the else/default — which mirrors the
spec's own "missing prior → default MEDIUM" rule. `low` is also checked before
`high` so an elevated resting HR (strain) overrides good sleep.
"""

from __future__ import annotations

from typing import Optional

from harlo.engine.schemas import Energy

from .baseline import Baseline
from .schema import BiometricPrior, Capacity, CapacityVerdict

SLEEP_HIGH = 420
SLEEP_LOW_CEILING = 330  # sleep <= 330 → low; medium is 330 < sleep < 420
SLEEP_DEPLETED = 270
RHR_STRAIN_DELTA = 5.0
HRV_DEPLETED_FACTOR = 0.85


def classify(prior: BiometricPrior, baseline: Optional[Baseline]) -> CapacityVerdict:
    """Map a prior (+ optional baseline) to a capacity verdict.

    Missing optional fields and a missing baseline both degrade the
    baseline-dependent terms to sleep-only.
    """
    sleep = prior.sleep_minutes
    hrv = prior.hrv_ms
    rhr = prior.resting_hr
    pre_baseline = baseline is None
    have_hrv_base = hrv is not None and baseline is not None and baseline.hrv is not None
    have_rhr_base = rhr is not None and baseline is not None and baseline.rhr is not None

    # 1. depleted — needs full HRV+baseline evidence (never fires pre-baseline)
    if sleep < SLEEP_DEPLETED and have_hrv_base and hrv < baseline.hrv * HRV_DEPLETED_FACTOR:
        return CapacityVerdict(Capacity.DEPLETED, Energy.LOW, True, pre_baseline)

    # 2. low — short sleep (<=330), or resting HR elevated vs baseline (strain)
    if sleep <= SLEEP_LOW_CEILING or (have_rhr_base and rhr >= baseline.rhr + RHR_STRAIN_DELTA):
        return CapacityVerdict(Capacity.LOW, Energy.LOW, False, pre_baseline)

    # 3. high — long sleep AND (HRV >= baseline, or HRV unavailable → sleep-only)
    if sleep >= SLEEP_HIGH:
        if not have_hrv_base or hrv >= baseline.hrv:
            return CapacityVerdict(Capacity.HIGH, Energy.HIGH, False, pre_baseline)
        # long sleep but HRV below baseline → not peak; falls to medium default

    # 4. medium — the else/default
    return CapacityVerdict(Capacity.MEDIUM, Energy.MEDIUM, False, pre_baseline)
