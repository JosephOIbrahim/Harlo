"""Tests for the composite RED check (Rule 28 + ADR-0001).

Verifies that the basal_ganglia inhibits motor when:
  - cognitive_state == "RED", OR
  - session_state["biometric_force_red"] is True (fresh biometric panic).

Stale biometric samples MUST NOT drive RED — that's tested at the
AllostasisTracker layer in test_modulation/test_biometric_barrier.py.
"""

from __future__ import annotations

from harlo.motor.basal_ganglia import _check_anchor
from harlo.motor.premotor import PlannedAction


def _action() -> PlannedAction:
    return PlannedAction(
        action_type="send_message",
        description="reply to user",
        target="local",
        payload={},
        consent_level=1,
        reversible=True,
    )


def test_explicit_red_inhibits() -> None:
    ok, reason = _check_anchor(_action(), {"cognitive_state": "RED"})
    assert ok is False
    assert "RED" in (reason or "")


def test_biometric_force_red_inhibits() -> None:
    ok, reason = _check_anchor(
        _action(),
        {"cognitive_state": "NORMAL", "biometric_force_red": True},
    )
    assert ok is False
    assert "biometric" in (reason or "").lower()
    assert "ADR-0001" in (reason or "")


def test_normal_state_allows() -> None:
    ok, reason = _check_anchor(
        _action(),
        {"cognitive_state": "NORMAL", "biometric_force_red": False},
    )
    assert ok is True
    assert reason is None


def test_missing_biometric_key_defaults_to_allow() -> None:
    ok, _ = _check_anchor(_action(), {"cognitive_state": "NORMAL"})
    assert ok is True
