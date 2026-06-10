"""Pure function: compute allostatic load and trend."""

from __future__ import annotations

from src.schemas import (
    AllostasisBlock,
    AllostasisTrend,
    Burnout,
    CognitiveObservation,
    Energy,
    SleepQuality,
)


def compute_allostasis(
    authored: CognitiveObservation,
    prev_allostasis: AllostasisBlock,
) -> AllostasisBlock:
    """Compute allostatic load composite.

    Weights from spec:
      w_freq=0.20, w_intense=0.15, w_crisis=0.25,
      w_comply=0.15, w_recover=0.15, w_sleep=0.10

    Returns updated AllostasisBlock with load and trend.
    """
    state = authored.state
    dynamics = authored.dynamics
    prev_load = prev_allostasis.load

    # Component scores (0-1 each)
    # Frequency: normalized exchange velocity
    freq_score = min(dynamics.exchange_velocity, 1.0)

    # Intensity: frustration signal
    intensity_score = dynamics.frustration_signal

    # Crisis: burnout severity normalized
    crisis_score = int(state.burnout) / 3.0

    # Compliance: override ratio
    comply_score = authored.allostasis.override_ratio_7d

    # Recovery: inverse of exercise recency (0 days = good recovery = low score)
    recovery_score = min(state.exercise_recency_days / 7.0, 1.0)

    # Sleep: poor sleep = higher load
    sleep_score = 0.0 if state.sleep_quality == SleepQuality.GOOD else 1.0

    load = (
        0.20 * freq_score
        + 0.15 * intensity_score
        + 0.25 * crisis_score
        + 0.15 * comply_score
        + 0.15 * recovery_score
        + 0.10 * sleep_score
    )
    load = min(max(load, 0.0), 1.0)

    # Trend detection
    delta = load - prev_load
    if abs(delta) < 0.05:
        trend = AllostasisTrend.STABLE
    elif delta > 0.2:
        trend = AllostasisTrend.SPIKE
    elif delta > 0:
        trend = AllostasisTrend.RISING
    else:
        trend = AllostasisTrend.FALLING

    return AllostasisBlock(
        load=round(load, 4),
        trend=trend,
        sessions_24h=authored.allostasis.sessions_24h,
        override_ratio_7d=authored.allostasis.override_ratio_7d,
    )
