"""C3 — persisted modulation state → Motor Cortex gate wire.

Proves the previously-inert ADR-0001 biometric RED path now reaches the
Basal Ganglia: ingest persists derived state → apply_to_session_state
surfaces it → _check_anchor inhibits. Also enforces Rule 9 (only derived
scalars persisted) and ADR-0001 freshness (stale RED expires).
"""

from __future__ import annotations

import json

from harlo.modulation.state import (
    RED_FRESHNESS_SEC,
    ModulationState,
    apply_to_session_state,
    read_modulation_state,
    write_modulation_state,
)
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


def test_write_read_roundtrip(tmp_path):
    p = tmp_path / "modulation_state.json"
    st = ModulationState(
        is_depleted=True,
        biometric_force_red=True,
        biometric_load=0.9,
        cognitive_state="RED",
        updated_at=123.0,
    )
    write_modulation_state(st, path=p)
    got = read_modulation_state(p)
    assert got.is_depleted is True
    assert got.biometric_force_red is True
    assert got.cognitive_state == "RED"


def test_read_missing_returns_safe_defaults(tmp_path):
    got = read_modulation_state(tmp_path / "nope.json")
    assert got.biometric_force_red is False
    assert got.cognitive_state == "NORMAL"


def test_persisted_file_has_no_raw_biometric_fields(tmp_path):
    # Rule 9 / ADR-0001: only derived scalars cross this boundary.
    p = tmp_path / "modulation_state.json"
    write_modulation_state(
        ModulationState(biometric_load=0.5, updated_at=1.0), path=p
    )
    raw = json.loads(p.read_text(encoding="utf-8"))
    assert set(raw.keys()) <= {
        "is_depleted",
        "biometric_force_red",
        "biometric_load",
        "cognitive_state",
        "updated_at",
    }
    for forbidden in ("heart_rate", "value", "sampled_at", "hrv", "type", "unit", "source"):
        assert forbidden not in raw


def test_fresh_force_red_reaches_session_state_and_inhibits_gate(tmp_path):
    p = tmp_path / "s.json"
    now = 1000.0
    write_modulation_state(
        ModulationState(
            biometric_force_red=True, cognitive_state="RED", updated_at=now
        ),
        path=p,
    )
    ss = apply_to_session_state({}, path=p, now=now + 10)  # within freshness
    assert ss["biometric_force_red"] is True
    # Biometric panic does NOT escalate the whole system to RED — it scopes
    # to motor inhibition via the dedicated flag.
    assert ss.get("cognitive_state") != "RED"
    # End-to-end: the gate's anchor check now inhibits (Rule 28 + ADR-0001).
    ok, reason = _check_anchor(_action(), ss)
    assert ok is False
    assert "biometric" in (reason or "").lower()
    assert "ADR-0001" in (reason or "")


def test_stale_force_red_is_expired_but_depleted_persists(tmp_path):
    p = tmp_path / "s.json"
    now = 1000.0
    write_modulation_state(
        ModulationState(
            is_depleted=True,
            biometric_force_red=True,
            cognitive_state="RED",
            updated_at=now,
        ),
        path=p,
    )
    ss = apply_to_session_state({}, path=p, now=now + RED_FRESHNESS_SEC + 1)
    assert ss["biometric_force_red"] is False  # ADR-0001 freshness expiry
    assert ss["is_depleted"] is True           # DEPLETED may persist when stale
    ok, _reason = _check_anchor(_action(), ss)
    assert ok is True                          # no longer RED → anchor passes
