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
