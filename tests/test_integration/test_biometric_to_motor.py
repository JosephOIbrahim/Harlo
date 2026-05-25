"""End-to-end: biometric_ingest router → AllostasisTracker → basal_ganglia.

Unit tests at each layer pass, but the wiring between them is where
bugs hide. This test sends a fresh-panic HR sample via the actual
router entry point, confirms force_red propagates, then runs a real
PlannedAction through `_check_anchor` to confirm inhibition.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from harlo.daemon.router import _handle_biometric_ingest, route_command
from harlo.motor.basal_ganglia import _check_anchor
from harlo.motor.premotor import PlannedAction


def _sample(value: float, minutes_ago: int = 0, type_: str = "heart_rate") -> dict:
    ts = datetime.now(tz=timezone.utc) - timedelta(minutes=minutes_ago)
    unit = "count/min" if "heart_rate" in type_ and "variability" not in type_ else "ms"
    return {
        "type": type_,
        "value": value,
        "unit": unit,
        "sampled_at": ts.isoformat(),
        "source": {"device": "Apple Watch Series 10"},
    }


def _action() -> PlannedAction:
    return PlannedAction(
        action_type="send_message",
        description="reply",
        target="local",
        payload={},
        consent_level=1,
        reversible=True,
    )


@pytest.fixture(autouse=True)
def reset_tracker():
    import harlo.daemon.router as router

    router._tracker_singleton = None
    yield
    router._tracker_singleton = None


class TestFreshPanicInhibitsMotor:
    def test_fresh_high_hr_triggers_force_red_and_inhibits(self):
        resp = route_command(
            "biometric_ingest", {"samples": [_sample(180.0)]}
        )
        assert resp["status"] == "ok"
        assert resp["result"]["force_red"] is True

        session_state = {
            "cognitive_state": "NORMAL",
            "biometric_force_red": resp["result"]["force_red"],
        }
        ok, reason = _check_anchor(_action(), session_state)
        assert ok is False
        assert "biometric" in (reason or "").lower()

    def test_fresh_normal_hr_does_not_inhibit(self):
        resp = route_command(
            "biometric_ingest", {"samples": [_sample(72.0)]}
        )
        assert resp["result"]["force_red"] is False
        ok, _ = _check_anchor(
            _action(),
            {"cognitive_state": "NORMAL", "biometric_force_red": False},
        )
        assert ok is True


class TestStaleSampleDoesNotInhibit:
    """The plan's headline invariant: 5-20 min Apple Watch latency
    must NOT drive motor inhibition (would mean any old panic spike
    locks Harlo indefinitely)."""

    def test_15_minute_old_panic_does_not_trigger_red(self):
        resp = route_command(
            "biometric_ingest", {"samples": [_sample(180.0, minutes_ago=15)]}
        )
        assert resp["result"]["force_red"] is False, \
            "stale (>5 min) sample MUST NOT drive RED — ADR-0001"
        ok, _ = _check_anchor(
            _action(),
            {"cognitive_state": "NORMAL", "biometric_force_red": False},
        )
        assert ok is True


class TestStillContributesToDepletedTrend:
    """Stale samples can't drive RED but should still count toward
    DEPLETED (slow trend over the modulation window)."""

    def test_stale_panic_inflates_load_for_depleted(self):
        resp = route_command(
            "biometric_ingest", {"samples": [_sample(180.0, minutes_ago=15)]}
        )
        # Load reflects trend even when freshness gate denies RED.
        assert resp["result"]["biometric_load"] > 0.0


class TestMultipleSamplesInOneCall:
    def test_mixed_validity(self):
        good = _sample(72.0)
        bad = _sample(72.0)
        del bad["source"]
        resp = route_command(
            "biometric_ingest", {"samples": [good, bad, good]}
        )
        assert resp["result"]["accepted"] == 2
        assert len(resp["result"]["rejected"]) == 1


class TestRule28NeverBypassed:
    """No matter what the biometric subsystem says, an explicit
    cognitive_state=RED always wins. Belt-and-suspenders for Rule 28."""

    def test_explicit_red_still_wins_when_biometrics_say_otherwise(self):
        # Empty bio state but explicit RED still locks the gate.
        ok, reason = _check_anchor(
            _action(),
            {"cognitive_state": "RED", "biometric_force_red": False},
        )
        assert ok is False
        assert "RED" in (reason or "")
