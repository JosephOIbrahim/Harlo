"""Biometric barrier — the separate ingestion path for HealthKit.

Rule 9 + ADR-0001: biometric signals enrich the Modulation Layer's
allostatic load but NEVER enter the trace, reflex, or composition
pipelines. They have different lifetime, consent, and retention than
core memory, so they get their own schema and their own validator.

A compliance grep enforces isolation:

    grep -rn "biometric" python/harlo/elenchus/ python/harlo/bridge/

MUST return 0 results.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import jsonschema

from harlo.daemon.config import BIOMETRIC_SAMPLE_SCHEMA_PATH


_schema_cache: dict[str, Any] | None = None


def _load_schema() -> dict[str, Any]:
    global _schema_cache
    if _schema_cache is None:
        _schema_cache = json.loads(
            BIOMETRIC_SAMPLE_SCHEMA_PATH.read_text(encoding="utf-8")
        )
    return _schema_cache


@dataclass(frozen=True)
class BiometricSample:
    """A validated HealthKit sample, immutable past the barrier.

    Wall-clock timestamps are kept verbatim (Rule 22 fuzzing applies
    only on the trace path, which biometrics never take).
    """

    type: str
    value: float
    unit: str
    sampled_at: datetime
    ingested_at: datetime
    source_device: str
    source_bundle_id: str | None = None
    confidence: float | None = None

    def age_seconds(self, now: datetime | None = None) -> float:
        """Wall-clock age of the sample. Used by the freshness window."""
        now = now or datetime.now(tz=timezone.utc)
        if self.sampled_at.tzinfo is None:
            sampled = self.sampled_at.replace(tzinfo=timezone.utc)
        else:
            sampled = self.sampled_at
        return max(0.0, (now - sampled).total_seconds())


class BiometricBarrierError(ValueError):
    """Raised when a payload fails biometric validation."""


def validate_biometric(raw: str | dict[str, Any]) -> BiometricSample:
    """Validate one biometric payload against the schema, return a
    `BiometricSample`.

    The payload comes from the HarloHealthBridge XPC service. The
    barrier is the ONLY entry point — no other module is allowed to
    construct a `BiometricSample` from arbitrary input.

    Raises:
        BiometricBarrierError: on JSON parse error or schema violation.
    """
    if isinstance(raw, str):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise BiometricBarrierError(f"invalid JSON: {exc}") from exc
    else:
        payload = raw

    try:
        jsonschema.validate(instance=payload, schema=_load_schema())
    except jsonschema.ValidationError as exc:
        raise BiometricBarrierError(f"schema violation: {exc.message}") from exc

    sampled_at = _parse_iso(payload["sampled_at"])
    ingested_at = _parse_iso(payload.get("ingested_at")) if payload.get("ingested_at") else datetime.now(tz=timezone.utc)
    source = payload["source"]
    return BiometricSample(
        type=payload["type"],
        value=float(payload["value"]),
        unit=payload["unit"],
        sampled_at=sampled_at,
        ingested_at=ingested_at,
        source_device=source["device"],
        source_bundle_id=source.get("bundle_id"),
        confidence=payload.get("confidence"),
    )


def _parse_iso(value: str) -> datetime:
    """Parse an RFC3339 / ISO-8601 timestamp into a tz-aware datetime.

    Accepts the Z suffix that HealthKit emits.
    """
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


__all__ = [
    "BiometricBarrierError",
    "BiometricSample",
    "validate_biometric",
]
