"""Δ9 regression — warm-tier decay elapsed term is DAYS, not raw Unix seconds.

Mirrors crates/hippocampus/src/decay.rs::test_decay_unit_is_days for the
Python degrade-path encoder (_compute_lazy_decay). Fed realistic Unix epochs
— the case the prior 1,140 tests never exercised — strength must track
e^(-λ·days). Pre-fix (seconds) these FAIL: e^(-0.05·86400) ≈ 0 for a
one-day-old trace.
"""

import math

from harlo.encoder import _compute_lazy_decay

CREATED = 1_700_000_000  # realistic Unix epoch (~2023-11)
DAY = 86_400


def test_one_day_old_trace_survives():
    s1 = _compute_lazy_decay(1.0, 0.05, CREATED, [], CREATED + DAY)
    assert abs(s1 - math.exp(-0.05 * 1)) < 1e-6, f"1 day -> {s1}"
    # The contract: a day-old trace must stay well above the apoptosis floor.
    assert s1 > 0.9, f"a day-old trace must survive: {s1}"


def test_decay_tracks_days():
    s14 = _compute_lazy_decay(1.0, 0.05, CREATED, [], CREATED + 14 * DAY)
    assert abs(s14 - math.exp(-0.05 * 14)) < 1e-6, f"14 days -> {s14}"
    s90 = _compute_lazy_decay(1.0, 0.05, CREATED, [], CREATED + 90 * DAY)
    assert abs(s90 - math.exp(-0.05 * 90)) < 1e-6, f"90 days -> {s90}"
