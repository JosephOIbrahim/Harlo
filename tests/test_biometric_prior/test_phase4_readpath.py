"""Phase 4 — read path: Energy seed at session init.

seed_block() reads today's prior, classifies per the mapping, and surfaces the
seed (incl. directive_mode). Absent prior → None (unchanged default behavior —
regressed explicitly).
"""

from __future__ import annotations

from harlo.biometric_prior.persistence import BufferUsdStore
from harlo.biometric_prior.readpath import seed_block
from harlo.biometric_prior.schema import BiometricPrior
from harlo.engine.observation_buffer import ObservationBuffer

TODAY = "2026-06-10"


def _store():
    return BufferUsdStore(ObservationBuffer(":memory:"), stage=None)


def _prior(date, sleep, hrv=None, rhr=None, source="manual"):
    return BiometricPrior(captured_at=f"{date}T07:00:00", sleep_minutes=sleep,
                          hrv_ms=hrv, resting_hr=rhr, source=source)


def test_seed_low_for_short_sleep():
    store = _store()
    store.upsert(_prior(TODAY, sleep=300))  # <330 → low (pre-baseline)
    seed = seed_block(today=TODAY, store=store)
    assert seed is not None
    assert seed["energy"] == "LOW"
    assert seed["capacity"] == "low"
    assert seed["directive_mode"] is False
    assert seed["pre_baseline"] is True


def test_seed_medium_at_330_boundary():
    # Gate-1-approved mapping: 330<=sleep<420 → medium. (Note: Gate 4's
    # round-trip text says 330→LOW, which contradicts this boundary — surfaced
    # for the architect, not auto-resolved.)
    store = _store()
    store.upsert(_prior(TODAY, sleep=330))
    assert seed_block(today=TODAY, store=store)["energy"] == "MEDIUM"


def test_seed_high_for_long_sleep():
    store = _store()
    store.upsert(_prior(TODAY, sleep=450))  # 450 → high (sleep-only)
    seed = seed_block(today=TODAY, store=store)
    assert seed["energy"] == "HIGH" and seed["capacity"] == "high"


def test_seed_depleted_sets_directive_with_baseline():
    store = _store()
    # 14 prior days establishing an HRV baseline of 50, then a depleted today.
    for d in range(1, 15):
        store.upsert(_prior(f"2026-05-{d:02d}", sleep=400, hrv=50.0, rhr=60.0))
    store.upsert(_prior(TODAY, sleep=250, hrv=40.0, rhr=60.0))  # <270 & hrv<42.5
    seed = seed_block(today=TODAY, store=store)
    assert seed["capacity"] == "depleted"
    assert seed["energy"] == "LOW"
    assert seed["directive_mode"] is True
    assert seed["pre_baseline"] is False


def test_absent_prior_returns_none_regression():
    # No prior for today → None → session startup unchanged (default MEDIUM).
    store = _store()
    store.upsert(_prior("2026-06-09", sleep=330))  # yesterday only
    assert seed_block(today=TODAY, store=store) is None


def test_empty_store_never_blocks():
    assert seed_block(today=TODAY, store=_store()) is None
