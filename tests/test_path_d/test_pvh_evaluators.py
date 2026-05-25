"""Evaluator tests, including the Cassandra fixture (Commandment 6).

What the Cassandra fixture proves in v1: the attribution *mechanism* is
well-defined and correctly flags an averted crash as deflection (not model
error). It does NOT prove a multiplier (D39) — the real corpus carries no
scaffolding signal, so v1 asserts no deflection rate.
"""

from __future__ import annotations

from harness.path_d.pvh.extractor import MISSING_FIELDS, Session, SessionMeta, Window
from harness.path_d.pvh.evaluators import (
    classify_trajectory,
    classify_window,
    compute_deflection_rate,
    compute_observation_density,
    compute_overshoot_baseline,
    evaluate_session,
)
from src.schemas import Burnout, CognitiveObservation


def _state(burnout, momentum=0, energy=2, burst_phase=0):
    return {"momentum": momentum, "burnout": burnout, "energy": energy, "burst_phase": burst_phase}


def _obs(exch):
    return CognitiveObservation(session_id="cassandra", exchange_index=exch, observation_index=exch)


def _session(windows, observations, session_id="s", partition="organic"):
    meta = SessionMeta(
        obs_count=len(observations),
        window_count=len(windows),
        below_window_threshold=len(observations) < 3,
        missing_fields=MISSING_FIELDS,
        dropped_rows=0,
        ordering_warnings=(),
        created_at_range=(None, None),
    )
    return Session(session_id=session_id, partition=partition,
                   observations=tuple(observations), windows=tuple(windows), metadata=meta)


# --- the well-defined heuristic -------------------------------------------

def test_classify_window_cases():
    assert classify_window(_state(3), _state(1), True) == "trajectory_deflection"
    assert classify_window(_state(3), _state(1), False) == "model_overshoot"
    assert classify_window(_state(3), _state(3), True) == "true_positive"
    assert classify_window(_state(0), _state(3), False) == "missed_crash"
    assert classify_window(_state(0), _state(0), False) == "true_negative"


def test_cassandra_fixture_averted_crash_is_deflection_not_model_error():
    """Commandment 6: a 5-obs synthetic trajectory with a known averted crash
    must be flagged deflection-success, not model-error."""
    obs = [_obs(i) for i in range(5)]  # 5 observations -> 3 windows (idx 2,3,4)
    # Window at index 3 is the averted crash: predicted RED, actual YELLOW.
    windows = (
        Window(index=2, observations=(obs[0], obs[1], obs[2]),
               actual=_state(1), predicted=_state(1)),
        Window(index=3, observations=(obs[1], obs[2], obs[3]),
               actual=_state(1), predicted=_state(int(Burnout.RED))),  # predicted crash
        Window(index=4, observations=(obs[2], obs[3], obs[4]),
               actual=_state(1), predicted=_state(1)),
    )
    scaffolding_fired = {3: True}
    cls = dict(classify_trajectory(windows, scaffolding_fired))
    assert cls[3] == "trajectory_deflection", "averted crash misclassified"

    # Contrast: identical prediction, no scaffolding -> model_overshoot (model error)
    cls_unscaffolded = dict(classify_trajectory(windows, {3: False}))
    assert cls_unscaffolded[3] == "model_overshoot"


def test_v1_no_scaffolding_yields_no_classification():
    obs = [_obs(i) for i in range(5)]
    windows = (
        Window(index=2, observations=(obs[0], obs[1], obs[2]), actual=_state(1), predicted=_state(3)),
    )
    # v1 default: no scaffolding map -> no classification (D39)
    cls = dict(classify_trajectory(windows, None))
    assert cls[2] is None


# --- Commandment 5: overshoot before deflection; rates ---------------------

def test_overshoot_and_deflection_rates_with_scaffolding():
    obs = [_obs(i) for i in range(4)]
    windows = (
        # predicted crash, scaffolding fired, no actual crash -> deflection
        Window(index=2, observations=(obs[0], obs[1], obs[2]), actual=_state(1), predicted=_state(3)),
        # predicted crash, NO scaffolding, no actual crash -> overshoot
        Window(index=3, observations=(obs[1], obs[2], obs[3]), actual=_state(1), predicted=_state(3)),
    )
    scaffolding = {2: True, 3: False}
    overshoot = compute_overshoot_baseline(windows, scaffolding)
    deflection = compute_deflection_rate(windows, scaffolding)
    assert overshoot["denominator"] == 1 and overshoot["rate"] == 1.0
    assert deflection["denominator"] == 1 and deflection["rate"] == 1.0


def test_v1_rates_not_asserted_without_signal():
    sess = _session(
        windows=(Window(index=2, observations=(_obs(0), _obs(1), _obs(2)),
                        actual=_state(1), predicted=_state(1)),),
        observations=[_obs(i) for i in range(3)],
    )
    result = evaluate_session(sess)  # no scaffolding map
    assert result.overshoot_baseline["status"] == "not_asserted_v1"
    assert result.deflection["status"] == "not_asserted_v1"
    assert result.overshoot_baseline["rate"] is None
    assert result.deflection["rate"] is None


# --- leakage + drift -------------------------------------------------------

def test_leakage_note_confirmed_when_predicted_equals_actual():
    windows = tuple(
        Window(index=i, observations=(_obs(i - 2), _obs(i - 1), _obs(i)),
               actual=_state(1), predicted=_state(1))
        for i in range(2, 5)
    )
    sess = _session(windows, [_obs(i) for i in range(5)])
    result = evaluate_session(sess)
    assert "confirmed" in result.leakage_note
    for row in result.drift_rows:
        assert all(v == 0 for v in row.drift.values())


# --- observation density ---------------------------------------------------

def test_observation_density_gap_flagging():
    # exchange indices 0,1,2,5 -> gaps [1,1,3]; gap 3 > threshold 2 -> weak
    obs = [_obs(i) for i in (0, 1, 2, 5)]
    sess = _session(windows=(), observations=obs)
    d = compute_observation_density(sess, weak_gap_threshold=2)
    assert d["gaps"] == 3
    assert d["max_gap"] == 3
    assert d["weak_signal_fraction"] == round(1 / 3, 4)
