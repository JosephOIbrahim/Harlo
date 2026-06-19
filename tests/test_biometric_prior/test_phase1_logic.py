"""Phase 1 — biometric_prior pure logic: schema, mapping, baseline.

Table-driven over every mapping row, boundary values, missing-field
degradation, and pre-baseline behaviour. No I/O, no server.

Baseline fixture: hrv median 50.0, rhr median 60.0 → derived thresholds
hrv*0.85 = 42.5 (depleted), rhr+5 = 65 (strain).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from harlo.biometric_prior import (
    Baseline,
    BiometricPrior,
    Capacity,
    classify,
    compute_baseline,
)
from harlo.engine.schemas import Energy

BASE = Baseline(hrv=50.0, rhr=60.0)


def _prior(sleep, hrv=None, rhr=None, workout=None, source="manual",
           at="2026-06-10T07:00:00"):
    return BiometricPrior(
        captured_at=at, sleep_minutes=sleep, hrv_ms=hrv,
        resting_hr=rhr, workout_yesterday=workout, source=source,
    )


# (id, prior, baseline, expected_capacity, expected_energy, expected_directive)
CASES = [
    # --- with baseline: full rules ---
    ("high",              _prior(450, hrv=55, rhr=58), BASE, Capacity.HIGH,     Energy.HIGH,   False),
    ("high_boundary_420", _prior(420, hrv=50, rhr=58), BASE, Capacity.HIGH,     Energy.HIGH,   False),
    ("medium",            _prior(375, hrv=55, rhr=58), BASE, Capacity.MEDIUM,   Energy.MEDIUM, False),
    ("medium_floor_331",  _prior(331, hrv=55, rhr=58), BASE, Capacity.MEDIUM,   Energy.MEDIUM, False),
    ("medium_ceil_419",   _prior(419, hrv=55, rhr=58), BASE, Capacity.MEDIUM,   Energy.MEDIUM, False),
    ("low_ceiling_330",   _prior(330, hrv=55, rhr=58), BASE, Capacity.LOW,      Energy.LOW,    False),
    ("low_sleep",         _prior(300, hrv=55, rhr=58), BASE, Capacity.LOW,      Energy.LOW,    False),
    ("low_sleep_bnd_329", _prior(329, hrv=55, rhr=58), BASE, Capacity.LOW,      Energy.LOW,    False),
    ("low_rhr_strain",    _prior(450, hrv=55, rhr=65), BASE, Capacity.LOW,      Energy.LOW,    False),  # rhr>=base+5 overrides high
    ("rhr_below_strain",  _prior(450, hrv=55, rhr=64), BASE, Capacity.HIGH,     Energy.HIGH,   False),  # 64<65 → high
    ("depleted",          _prior(250, hrv=40, rhr=58), BASE, Capacity.DEPLETED, Energy.LOW,    True),
    ("depleted_needs_hrv",_prior(250, hrv=45, rhr=58), BASE, Capacity.LOW,      Energy.LOW,    False),  # 45>=42.5 → not depleted
    ("depleted_sleep_270",_prior(270, hrv=40, rhr=58), BASE, Capacity.LOW,      Energy.LOW,    False),  # 270 not <270 → low
    ("hi_sleep_low_hrv",  _prior(450, hrv=45, rhr=58), BASE, Capacity.MEDIUM,   Energy.MEDIUM, False),  # gap → medium default
    # --- with baseline: missing-field degradation ---
    ("missing_hrv_high",  _prior(450, hrv=None, rhr=58), BASE, Capacity.HIGH,   Energy.HIGH,   False),  # sleep-only high
    ("missing_rhr_low",   _prior(300, hrv=55, rhr=None), BASE, Capacity.LOW,    Energy.LOW,    False),
    ("missing_all_opt",   _prior(400, hrv=None, rhr=None), BASE, Capacity.MEDIUM, Energy.MEDIUM, False),
    # --- pre-baseline: sleep-only (no depleted possible) ---
    ("pre_high",          _prior(450, hrv=55, rhr=58), None, Capacity.HIGH,     Energy.HIGH,   False),
    ("pre_medium",        _prior(375, hrv=55, rhr=58), None, Capacity.MEDIUM,   Energy.MEDIUM, False),
    ("pre_low",           _prior(300, hrv=55, rhr=58), None, Capacity.LOW,      Energy.LOW,    False),
    ("pre_no_depleted",   _prior(250, hrv=10, rhr=58), None, Capacity.LOW,      Energy.LOW,    False),  # depleted needs baseline
]


@pytest.mark.parametrize("case", CASES, ids=[c[0] for c in CASES])
def test_classify(case):
    _id, prior, baseline, cap, energy, directive = case
    v = classify(prior, baseline)
    assert v.capacity == cap, f"{_id}: capacity got {v.capacity}"
    assert v.energy_seed == energy, f"{_id}: energy got {v.energy_seed}"
    assert v.directive_mode == directive, f"{_id}: directive got {v.directive_mode}"


def test_depleted_seeds_low_not_energy_depleted():
    # Spec: capacity=DEPLETED → Energy.LOW + directive, NOT Energy.DEPLETED.
    v = classify(_prior(250, hrv=40), BASE)
    assert v.capacity == Capacity.DEPLETED
    assert v.energy_seed == Energy.LOW
    assert v.directive_mode is True


def test_pre_baseline_flag_set():
    assert classify(_prior(400), None).pre_baseline is True
    assert classify(_prior(400, hrv=55, rhr=58), BASE).pre_baseline is False


# --- baseline tracker ---
def _hist(n, hrv=50.0, rhr=60.0):
    return [_prior(400, hrv=hrv, rhr=rhr, at=f"2026-05-{d:02d}T07:00:00")
            for d in range(1, n + 1)]


def test_baseline_none_before_14_days():
    assert compute_baseline(_hist(13)) is None


def test_baseline_at_14_days():
    b = compute_baseline(_hist(14, hrv=50, rhr=60))
    assert b is not None
    assert b.hrv == 50.0 and b.rhr == 60.0


def test_baseline_is_median_of_window():
    hist = [_prior(400, hrv=float(40 + i), rhr=60.0, at=f"2026-05-{i + 1:02d}T07:00:00")
            for i in range(14)]  # hrv 40..53 → median (46+47)/2
    assert compute_baseline(hist).hrv == 46.5


def test_baseline_skips_missing_components():
    hist = _hist(14, hrv=50, rhr=60)
    hist[0] = _prior(400, hrv=None, rhr=None, at="2026-05-01T07:00:00")
    assert compute_baseline(hist).hrv == 50.0  # median over the 13 present


def test_baseline_rolls_to_last_14():
    # 20 days; last 14 all hrv=70, earlier ones hrv=10 → median 70.
    hist = (_hist(6, hrv=10.0)
            + [_prior(400, hrv=70.0, rhr=60.0, at=f"2026-05-{d:02d}T07:00:00")
               for d in range(7, 21)])
    assert compute_baseline(hist).hrv == 70.0


# --- schema ---
def test_schema_calendar_date():
    assert _prior(400, at="2026-06-10T23:30:00").calendar_date == "2026-06-10"


def test_schema_requires_sleep_minutes():
    with pytest.raises(ValidationError):
        BiometricPrior(captured_at="2026-06-10T07:00:00", source="manual")


def test_schema_rejects_bad_source():
    with pytest.raises(ValidationError):
        _prior(400, source="garmin")


def test_schema_rejects_negative_sleep():
    with pytest.raises(ValidationError):
        _prior(-5)
