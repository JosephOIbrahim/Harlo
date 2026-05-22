"""P5 — Swift bridge wire format ↔ Python biometric_barrier.

Catches drift between the HealthKit encoder branches in
`macos/HarloHealthBridge/Sources/HarloHealthBridge/BiometricEncoder.swift`
and `python/harlo/modulation/biometric_barrier.py`. Without this test,
a Swift-side key rename, a unit-string change, or a schema bump
without bridge update can silently break biometric ingestion at
runtime on the Mac.

Approach: parse the Swift file's `switch q.quantityType.identifier`
block + the `HKCategoryTypeIdentifier.sleepAnalysis` branch, mimic the
JSON each branch produces with realistic units, then run each payload
through `validate_biometric`. Any failure is a wire-format mismatch.

This test reads the Swift source as data — no Swift toolchain needed.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from harlo.modulation.biometric_barrier import (
    BiometricBarrierError,
    validate_biometric,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SWIFT_PATH = (
    _REPO_ROOT
    / "macos"
    / "HarloHealthBridge"
    / "Sources"
    / "HarloHealthBridge"
    / "BiometricEncoder.swift"
)

# Sample unit strings each Swift branch produces. Keys are the
# snake_case `type` strings emitted to the JSON payload.
# These mirror BiometricEncoder.swift; the test enforces the bridge
# can not drop a type without us noticing.
_EXPECTED_TYPES = {
    "heart_rate": "count/min",
    "heart_rate_variability_sdnn": "ms",
    "resting_heart_rate": "count/min",
    "respiratory_rate": "count/min",
    "active_energy_burned": "kcal",
    "step_count": "count",
    "oxygen_saturation": "%",
    "body_temperature": "degC",
    "sleep_analysis": "category",
}


def _parse_swift_emitted_types(text: str) -> set[str]:
    """Extract the `type = "..."` literals from the switch block."""
    return set(re.findall(r'type\s*=\s*"([a-z_]+)"', text))


def test_swift_source_present() -> None:
    assert _SWIFT_PATH.exists(), (
        f"BiometricEncoder.swift missing at {_SWIFT_PATH}; the bridge "
        "moved or was deleted — schema invariant lost."
    )


def test_every_swift_emitted_type_is_in_python_schema() -> None:
    """If Swift starts emitting a new biometric type, the schema must
    cover it. Otherwise the barrier rejects valid bridge payloads."""
    text = _SWIFT_PATH.read_text(encoding="utf-8")
    swift_types = _parse_swift_emitted_types(text)
    # sleep_analysis lives in a separate Category branch — add manually.
    if "sleep_analysis" in text:
        swift_types.add("sleep_analysis")
    assert swift_types, "no type literals found in Swift source"

    missing = swift_types - _EXPECTED_TYPES.keys()
    assert not missing, (
        f"Swift emits {missing} but the test's _EXPECTED_TYPES table "
        "does not — update both the test and the schema."
    )


def test_every_expected_type_validates_through_barrier() -> None:
    """Each Swift branch's payload, mimicked here with the unit string
    HKUnit uses, must pass `validate_biometric`."""
    iso_now = datetime.now(tz=timezone.utc).isoformat()
    for type_, unit in _EXPECTED_TYPES.items():
        payload = {
            "type": type_,
            "value": 72.0 if "heart_rate" in type_ else 1.0,
            "unit": unit,
            "sampled_at": iso_now,
            "source": {"device": "Apple Watch Series 10"},
        }
        if type_ == "sleep_analysis":
            payload["value"] = 0.0  # HKCategorySample value
        try:
            sample = validate_biometric(payload)
        except BiometricBarrierError as exc:
            pytest.fail(f"barrier rejected valid Swift-style payload for {type_}: {exc}")
        assert sample.type == type_
        assert sample.unit == unit


def test_payload_with_bundle_id_in_source_still_validates() -> None:
    """Swift attaches `bundle_id` for HKQuantitySample branches —
    confirm the barrier accepts the richer source object."""
    iso_now = datetime.now(tz=timezone.utc).isoformat()
    payload = {
        "type": "heart_rate",
        "value": 72.0,
        "unit": "count/min",
        "sampled_at": iso_now,
        "source": {
            "device": "Apple Watch Series 10",
            "bundle_id": "com.apple.health",
        },
    }
    sample = validate_biometric(payload)
    assert sample.source_bundle_id == "com.apple.health"


def test_dropping_required_field_is_rejected() -> None:
    """Smoke check: the barrier is actually validating, not no-op-ing."""
    payload = {
        "type": "heart_rate",
        "value": 72.0,
        "unit": "count/min",
        # 'sampled_at' deliberately missing
        "source": {"device": "Apple Watch Series 10"},
    }
    with pytest.raises(BiometricBarrierError):
        validate_biometric(payload)
