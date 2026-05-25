"""Evaluators: drift schema, lead-time, deflection/overshoot, observation density.

Implements the four metrics from 03_HANDOFF.md Phase 3, under the v1 constraints
of D38/D39/D46:

- The reference predictor has target leakage and no horizon (D38), so per-window
  `predicted ≈ actual` and drift ≈ 0. This is reported honestly, not hidden.
- No deflection claim is asserted in v1 (D39): deflection/overshoot rates are
  None unless an explicit scaffolding signal is supplied (which the real corpus
  lacks — scaffolding_requirements is absent, D20).
- Commandment 5: the overshoot baseline is computed BEFORE the deflection rate.

The Cassandra classification heuristic (Article 3) is implemented as a pure,
well-defined function and exercised by a hand-authored fixture — proving the
*mechanism*, not a multiplier (the v2 claim).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.schemas import Burnout

from .extractor import Session, Window

CRASH_LEVEL = int(Burnout.RED)  # 3 — "crash" threshold for Cassandra attribution
TARGETS = ("momentum", "burnout", "energy", "burst_phase")


# ---------------------------------------------------------------------------
# Cassandra classification heuristic (Article 3 — well-defined mechanism)
# ---------------------------------------------------------------------------

def classify_window(predicted: dict, actual: dict, scaffolding_fired: bool) -> str:
    """Classify one window's burnout prediction vs outcome (Article 3).

    - predicted crash, no crash, scaffolding fired  -> trajectory_deflection
    - predicted crash, no crash, no scaffolding      -> model_overshoot
    - predicted crash, crash                          -> true_positive
    - no predicted crash, crash                       -> missed_crash
    - otherwise                                       -> true_negative
    """
    predicted_crash = predicted["burnout"] >= CRASH_LEVEL
    actual_crash = actual["burnout"] >= CRASH_LEVEL
    if predicted_crash and not actual_crash:
        return "trajectory_deflection" if scaffolding_fired else "model_overshoot"
    if predicted_crash and actual_crash:
        return "true_positive"
    if not predicted_crash and actual_crash:
        return "missed_crash"
    return "true_negative"


def classify_trajectory(
    windows: tuple[Window, ...],
    scaffolding_by_index: Optional[dict[int, bool]] = None,
) -> list[tuple[int, Optional[str]]]:
    """Classify each window. v1 default (no scaffolding signal) -> None per window."""
    out: list[tuple[int, Optional[str]]] = []
    for w in windows:
        if scaffolding_by_index is None or w.index not in scaffolding_by_index or w.predicted is None:
            out.append((w.index, None))  # D39: no deflection claim without a signal
        else:
            out.append((w.index, classify_window(w.predicted, w.actual, scaffolding_by_index[w.index])))
    return out


# ---------------------------------------------------------------------------
# Drift schema
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DriftRow:
    exchange_index: int          # temporal key (Commandment 3)
    actual: dict[str, int]
    predicted: Optional[dict[str, int]]
    drift: Optional[dict[str, int]]   # predicted - actual per target (None if no predictor)
    signal_proxy: int            # observation-density gap at this window (higher = sparser)
    lead_time: None = None       # undefined in v1 (no horizon, D38)
    deflection_flag: None = None
    overshoot_baseline_flag: None = None


def compute_drift_schema(session: Session) -> list[DriftRow]:
    rows: list[DriftRow] = []
    for w in session.windows:
        gap = w.observations[2].exchange_index - w.observations[1].exchange_index
        drift = None
        if w.predicted is not None:
            drift = {t: w.predicted[t] - w.actual[t] for t in TARGETS}
        rows.append(
            DriftRow(
                exchange_index=w.observations[2].exchange_index,
                actual=w.actual,
                predicted=w.predicted,
                drift=drift,
                signal_proxy=gap,
            )
        )
    return rows


# ---------------------------------------------------------------------------
# Observation density (gap-based signal-weakness proxy)
# ---------------------------------------------------------------------------

def compute_observation_density(session: Session, weak_gap_threshold: int = 2) -> dict:
    """Gap-based proxy: large exchange_index gaps => sparse cadence => weak signal."""
    exch = [o.exchange_index for o in session.observations]
    gaps = [exch[i] - exch[i - 1] for i in range(1, len(exch))]
    if not gaps:
        return {"gaps": 0, "mean_gap": None, "max_gap": None,
                "weak_signal_fraction": None, "threshold": weak_gap_threshold}
    weak = [g for g in gaps if g > weak_gap_threshold]
    return {
        "gaps": len(gaps),
        "mean_gap": round(sum(gaps) / len(gaps), 4),
        "max_gap": max(gaps),
        "weak_signal_fraction": round(len(weak) / len(gaps), 4),
        "threshold": weak_gap_threshold,
    }


# ---------------------------------------------------------------------------
# Lead-time distribution (undefined in v1 — no horizon)
# ---------------------------------------------------------------------------

def compute_lead_time_distribution(session: Session) -> dict:
    """v1: lead time is undefined (no horizon, D38). Report actual state-transition
    counts descriptively so the artifact is still informative."""
    transitions = {t: 0 for t in TARGETS}
    windows = session.windows
    for i in range(1, len(windows)):
        prev, cur = windows[i - 1].actual, windows[i].actual
        for t in TARGETS:
            if prev[t] != cur[t]:
                transitions[t] += 1
    return {
        "status": "undefined_v1",
        "reason": "no forecasting horizon in reference predictor (D38); lead time requires a t+horizon forecast",
        "actual_transition_counts": transitions,
    }


# ---------------------------------------------------------------------------
# Deflection / overshoot (Commandment 5: overshoot computed BEFORE deflection)
# ---------------------------------------------------------------------------

def compute_overshoot_baseline(
    windows: tuple[Window, ...],
    scaffolding_by_index: Optional[dict[int, bool]] = None,
) -> dict:
    """Overshoot = predicted-crash, NO scaffolding, no actual crash, over all
    predicted-crash-without-scaffolding windows. v1: None (no scaffolding signal)."""
    if scaffolding_by_index is None:
        return {"status": "not_asserted_v1", "rate": None,
                "reason": "scaffolding_requirements absent (D20); no un-scaffolded crash-prediction set"}
    denom = num = 0
    for w in windows:
        if w.predicted is None:
            continue
        fired = scaffolding_by_index.get(w.index, False)
        if w.predicted["burnout"] >= CRASH_LEVEL and not fired:
            denom += 1
            if w.actual["burnout"] < CRASH_LEVEL:
                num += 1
    return {"status": "computed", "rate": (num / denom) if denom else None,
            "numerator": num, "denominator": denom}


def compute_deflection_rate(
    windows: tuple[Window, ...],
    scaffolding_by_index: Optional[dict[int, bool]] = None,
) -> dict:
    """Deflection = predicted-crash, scaffolding fired, no actual crash, over all
    predicted-crash-with-scaffolding windows. v1: None (no scaffolding signal)."""
    if scaffolding_by_index is None:
        return {"status": "not_asserted_v1", "rate": None,
                "reason": "no deflection claim asserted in v1 (D39); scaffolding signal unavailable (D20)"}
    denom = num = 0
    for w in windows:
        if w.predicted is None:
            continue
        fired = scaffolding_by_index.get(w.index, False)
        if w.predicted["burnout"] >= CRASH_LEVEL and fired:
            denom += 1
            if w.actual["burnout"] < CRASH_LEVEL:
                num += 1
    return {"status": "computed", "rate": (num / denom) if denom else None,
            "numerator": num, "denominator": denom}


# ---------------------------------------------------------------------------
# Top-level session evaluation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EvaluationResult:
    session_id: str
    partition: str
    drift_rows: list[DriftRow]
    observation_density: dict
    lead_time: dict
    overshoot_baseline: dict   # computed BEFORE deflection (Commandment 5)
    deflection: dict
    classifications: list[tuple[int, Optional[str]]]
    leakage_note: str


def evaluate_session(
    session: Session,
    scaffolding_by_index: Optional[dict[int, bool]] = None,
) -> EvaluationResult:
    drift_rows = compute_drift_schema(session)
    # Commandment 5: overshoot baseline FIRST, then deflection.
    overshoot = compute_overshoot_baseline(session.windows, scaffolding_by_index)
    deflection = compute_deflection_rate(session.windows, scaffolding_by_index)
    leak = "none"
    if drift_rows and all(r.drift is not None for r in drift_rows):
        if all(all(v == 0 for v in r.drift.values()) for r in drift_rows):
            leak = "confirmed: predicted == actual for all windows (target leakage, D38)"
        else:
            leak = "partial: some non-zero drift despite leakage"
    return EvaluationResult(
        session_id=session.session_id,
        partition=session.partition,
        drift_rows=drift_rows,
        observation_density=compute_observation_density(session),
        lead_time=compute_lead_time_distribution(session),
        overshoot_baseline=overshoot,
        deflection=deflection,
        classifications=classify_trajectory(session.windows, scaffolding_by_index),
        leakage_note=leak,
    )
