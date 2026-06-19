"""biometric_prior — HealthKit-shaped capacity signal → Energy seed (v1).

Phase 1: pure-logic layer (schema, mapping, baseline). No I/O, no server.
HealthKit itself is OUT of scope; this is the shape both manual injection and
the future Shortcuts relay POST to /v1/biometrics.
"""

from .baseline import BASELINE_DAYS, Baseline, compute_baseline
from .mapping import classify
from .schema import SCHEMA, BiometricPrior, Capacity, CapacityVerdict

__all__ = [
    "SCHEMA",
    "BiometricPrior",
    "Capacity",
    "CapacityVerdict",
    "Baseline",
    "BASELINE_DAYS",
    "compute_baseline",
    "classify",
]
