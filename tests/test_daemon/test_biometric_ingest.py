"""Tests for the daemon `biometric_ingest` router endpoint."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from harlo.daemon.router import _handle_biometric_ingest, route_command


def _sample(value: float = 72.0, minutes_ago: int = 0) -> dict:
    ts = datetime.now(tz=timezone.utc) - timedelta(minutes=minutes_ago)
    return {
        "type": "heart_rate",
        "value": value,
        "unit": "count/min",
        "sampled_at": ts.isoformat(),
        "source": {"device": "Apple Watch Series 10"},
    }


@pytest.fixture(autouse=True)
def reset_tracker():
    """Reset the module-level tracker between tests so we don't carry
    state across cases."""
    import harlo.daemon.router as router

    router._tracker_singleton = None
    yield
    router._tracker_singleton = None


def test_accepts_single_valid_sample() -> None:
    resp = _handle_biometric_ingest({"samples": [_sample()]})
    assert resp["status"] == "ok"
    assert resp["result"]["accepted"] == 1
    assert resp["result"]["rejected"] == []


def test_rejects_invalid_payload() -> None:
    bad = _sample()
    del bad["source"]
    resp = _handle_biometric_ingest({"samples": [bad]})
    assert resp["result"]["accepted"] == 0
    assert len(resp["result"]["rejected"]) == 1


def test_force_red_only_for_fresh_samples() -> None:
    stale_panic = _sample(value=180.0, minutes_ago=10)
    resp = _handle_biometric_ingest({"samples": [stale_panic]})
    assert resp["result"]["force_red"] is False


def test_force_red_true_for_fresh_panic() -> None:
    resp = _handle_biometric_ingest({"samples": [_sample(value=180.0)]})
    assert resp["result"]["force_red"] is True


def test_route_command_dispatches_biometric_ingest() -> None:
    resp = route_command("biometric_ingest", {"samples": [_sample()]})
    assert resp["status"] == "ok"
    assert resp["result"]["accepted"] == 1


def test_unknown_command_returns_error() -> None:
    resp = route_command("definitely_not_a_command", {})
    assert resp["status"] == "error"


def test_samples_must_be_a_list() -> None:
    resp = _handle_biometric_ingest({"samples": "not a list"})
    assert resp["status"] == "error"
