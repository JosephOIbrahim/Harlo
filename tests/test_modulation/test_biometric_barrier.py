"""Tests for the biometric_barrier (ADR-0001).

Two invariants under test:

  1. Every payload that reaches the Modulation Layer has passed
     `validate_biometric()`.
  2. Biometric data does not leak into traces / reflexes / bridge /
     elenchus — enforced by the compliance grep in CLAUDE.md and
     by the fact that the only public output type is
     `BiometricSample`, never a `TracePrim`.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from harlo.modulation.allostatic import AllostasisTracker
from harlo.modulation.biometric_barrier import (
    BiometricBarrierError,
    BiometricSample,
    validate_biometric,
)


def _sample(
    type_: str = "heart_rate",
    value: float = 72.0,
    sampled_at: datetime | None = None,
) -> dict:
    sampled_at = sampled_at or datetime.now(tz=timezone.utc)
    return {
        "type": type_,
        "value": value,
        "unit": "count/min" if "heart_rate" in type_ else "ms",
        "sampled_at": sampled_at.isoformat(),
        "source": {"device": "Apple Watch Series 10"},
    }


class TestValidate:
    def test_accepts_valid_payload(self) -> None:
        sample = validate_biometric(_sample())
        assert isinstance(sample, BiometricSample)
        assert sample.type == "heart_rate"
        assert sample.value == pytest.approx(72.0)

    def test_accepts_json_string(self) -> None:
        sample = validate_biometric(json.dumps(_sample()))
        assert sample.type == "heart_rate"

    def test_rejects_unknown_type(self) -> None:
        bad = _sample(type_="brain_voltage")
        with pytest.raises(BiometricBarrierError):
            validate_biometric(bad)

    def test_rejects_missing_required_field(self) -> None:
        bad = _sample()
        del bad["source"]
        with pytest.raises(BiometricBarrierError):
            validate_biometric(bad)

    def test_rejects_unparseable_json(self) -> None:
        with pytest.raises(BiometricBarrierError):
            validate_biometric("not json")


class TestFreshnessWindow:
    def test_fresh_sample_can_trigger_red(self) -> None:
        tracker = AllostasisTracker(hr_red_bpm=140.0)
        sample = validate_biometric(_sample(value=160.0))
        tracker.record_biometric(sample)
        assert tracker.should_force_red() is True

    def test_stale_sample_cannot_trigger_red(self) -> None:
        tracker = AllostasisTracker(
            hr_red_bpm=140.0, biometric_red_freshness_sec=300.0
        )
        stale = validate_biometric(
            _sample(
                value=180.0,
                sampled_at=datetime.now(tz=timezone.utc) - timedelta(minutes=10),
            )
        )
        tracker.record_biometric(stale)
        assert tracker.should_force_red() is False

    def test_stale_sample_still_contributes_to_depleted(self) -> None:
        tracker = AllostasisTracker(
            hr_red_bpm=100.0,
            biometric_red_freshness_sec=300.0,
        )
        stale = validate_biometric(
            _sample(
                value=120.0,
                sampled_at=datetime.now(tz=timezone.utc) - timedelta(minutes=10),
            )
        )
        tracker.record_biometric(stale)
        # Trend signal still elevates load even when not fresh.
        assert tracker.get_biometric_load() > 0.0


class TestIsolation:
    def test_biometric_sample_has_no_trace_methods(self) -> None:
        sample = validate_biometric(_sample())
        # Spec: BiometricSample is frozen and has no trace-write surface.
        assert not hasattr(sample, "to_trace")
        assert not hasattr(sample, "store_reflex")

    def test_age_seconds_handles_naive_datetime(self) -> None:
        naive = datetime.now().replace(tzinfo=None)
        sample = BiometricSample(
            type="heart_rate",
            value=80.0,
            unit="count/min",
            sampled_at=naive,
            ingested_at=datetime.now(tz=timezone.utc),
            source_device="Apple Watch Series 10",
        )
        # Should not raise.
        assert sample.age_seconds() >= 0.0


class TestRespiratoryRate:
    """Respiratory rate feeds the DEPLETED/load path (ADR-0001 roadmap #1).

    Only the EXCESS over a normal resting baseline counts — normal
    breathing (12-16 br/min) must never inflate stress load (unlike the
    naive mean/threshold HR formula). RR is a slow signal (Apple samples
    it mainly during sleep/rest), so it contributes to the DEPLETED trend
    but NEVER to the fresh-only RED motor-inhibition path.
    """

    def test_elevated_respiratory_rate_raises_load(self) -> None:
        tracker = AllostasisTracker()
        # 25 br/min — at the red mark (normal resting is 12-16).
        tracker.record_biometric(
            validate_biometric(_sample(type_="respiratory_rate", value=25.0))
        )
        assert tracker.get_biometric_load() >= 0.99

    def test_normal_respiratory_rate_contributes_no_load(self) -> None:
        tracker = AllostasisTracker()
        # 14 br/min — squarely normal; must add zero stress load.
        tracker.record_biometric(
            validate_biometric(_sample(type_="respiratory_rate", value=14.0))
        )
        assert tracker.get_biometric_load() == 0.0

    def test_respiratory_rate_scales_between_floor_and_red(self) -> None:
        # Default floor 16, red 25 → 20.5 br/min is the midpoint → ~0.5.
        tracker = AllostasisTracker()
        tracker.record_biometric(
            validate_biometric(_sample(type_="respiratory_rate", value=20.5))
        )
        assert tracker.get_biometric_load() == pytest.approx(0.5, abs=0.02)

    def test_high_respiratory_rate_can_deplete(self) -> None:
        tracker = AllostasisTracker()
        tracker.record_biometric(
            validate_biometric(_sample(type_="respiratory_rate", value=26.0))
        )
        assert tracker.is_depleted() is True

    def test_respiratory_rate_alone_does_not_force_red(self) -> None:
        # Slow signal — must not drive motor inhibition even when very high.
        tracker = AllostasisTracker()
        tracker.record_biometric(
            validate_biometric(_sample(type_="respiratory_rate", value=40.0))
        )
        assert tracker.should_force_red() is False
