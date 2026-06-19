"""Allostatic load tracking.

Rule 9 (v6.1): Allostatic load = token velocity + prompt frequency,
plus OPTIONAL opt-in biometric signals via the biometric_barrier per
ADR-0001. Biometric signals stay in the Modulation Layer; they never
enter traces or reflexes.

Rule 1: Zero-watt idle. Event-driven only.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .biometric_barrier import BiometricSample


# Window for tracking velocity (seconds)
_WINDOW_SEC = 300.0  # 5 minutes
_DEPLETION_THRESHOLD = 0.85
# Max expected tokens-per-second for normalization
_MAX_TOKEN_VELOCITY = 100.0
# Max expected prompts-per-minute for normalization
_MAX_PROMPT_FREQ = 20.0

# Biometric window — slower trends than token velocity. Sample is
# retained for DEPLETED trend detection up to this many seconds.
_BIOMETRIC_WINDOW_SEC = 1800.0  # 30 minutes
# Freshness window — only samples younger than this can flip RED.
# Default 5 min; configurable from default_profile.yaml per Rule 9.
_BIOMETRIC_RED_FRESHNESS_SEC = 300.0
# Personal HR / HRV thresholds default to a population-level guess
# until the intake form calibrates them per user.
_DEFAULT_HR_RED_BPM = 140.0  # sustained high-HR for inhibition
_DEFAULT_HRV_RED_MS = 20.0   # low HRV under stress
# Respiratory rate (breaths/min). Normal resting is 12-16; only the EXCESS
# above the floor adds load, saturating at the red mark. RR is a slow signal
# (Apple samples it mainly during sleep/rest), so it feeds DEPLETED via
# get_biometric_load — never the fresh-only RED motor-inhibition path.
_DEFAULT_RR_FLOOR_BPM = 16.0
_DEFAULT_RR_RED_BPM = 25.0


@dataclass
class _PromptRecord:
    tokens: int
    ts: float


@dataclass
class _BiometricRecord:
    """One biometric sample retained in the Modulation Layer.

    `wall_at` is the source-device wall-clock time used for the
    freshness window (Apple Watch latency means we must distinguish
    when the body experienced this vs. when we received it).
    `monotonic_at` is for ordering only.
    """

    type: str
    value: float
    wall_at: datetime
    monotonic_at: float


class AllostasisTracker:
    """Track token velocity and prompt frequency to compute allostatic load.

    Pure state tracking. Event-driven only. No polling. No background threads.
    """

    def __init__(
        self,
        window_sec: float = _WINDOW_SEC,
        biometric_window_sec: float = _BIOMETRIC_WINDOW_SEC,
        biometric_red_freshness_sec: float = _BIOMETRIC_RED_FRESHNESS_SEC,
        hr_red_bpm: float = _DEFAULT_HR_RED_BPM,
        hrv_red_ms: float = _DEFAULT_HRV_RED_MS,
        rr_floor_bpm: float = _DEFAULT_RR_FLOOR_BPM,
        rr_red_bpm: float = _DEFAULT_RR_RED_BPM,
    ) -> None:
        self._window_sec = window_sec
        self._biometric_window_sec = biometric_window_sec
        self._biometric_red_freshness_sec = biometric_red_freshness_sec
        self._hr_red_bpm = hr_red_bpm
        self._hrv_red_ms = hrv_red_ms
        self._rr_floor_bpm = rr_floor_bpm
        self._rr_red_bpm = rr_red_bpm
        self._records: deque[_PromptRecord] = deque()
        self._biometric: deque[_BiometricRecord] = deque()

    def record_prompt(self, tokens: int, ts: float | None = None) -> None:
        """Record a prompt event with token count.

        Args:
            tokens: Number of tokens in this prompt.
            ts: Timestamp (seconds since epoch). Defaults to time.monotonic().
        """
        if ts is None:
            ts = time.monotonic()
        self._records.append(_PromptRecord(tokens=tokens, ts=ts))
        self._prune(ts)

    def _prune(self, now: float) -> None:
        """Remove records outside the tracking window."""
        cutoff = now - self._window_sec
        while self._records and self._records[0].ts < cutoff:
            self._records.popleft()

    def _now(self) -> float:
        return time.monotonic()

    def get_load(self) -> float:
        """Compute current allostatic load as 0.0 to 1.0.

        Load = 0.5 * normalized_token_velocity + 0.5 * normalized_prompt_frequency
        """
        now = self._now()
        self._prune(now)

        if not self._records:
            return 0.0

        elapsed = now - self._records[0].ts
        if elapsed <= 0:
            elapsed = 1.0

        # Token velocity: tokens per second
        total_tokens = sum(r.tokens for r in self._records)
        token_velocity = total_tokens / elapsed
        norm_velocity = min(token_velocity / _MAX_TOKEN_VELOCITY, 1.0)

        # Prompt frequency: prompts per minute
        prompt_count = len(self._records)
        prompt_freq = (prompt_count / elapsed) * 60.0
        norm_freq = min(prompt_freq / _MAX_PROMPT_FREQ, 1.0)

        load = 0.5 * norm_velocity + 0.5 * norm_freq
        return min(load, 1.0)

    def is_depleted(self) -> bool:
        """Check if the system is in a depleted state.

        Composite of software signals (tokens + prompt frequency) and,
        if any biometric samples have arrived, biometric stress load.
        Stale biometric samples DO contribute to DEPLETED (slow trend);
        they only fail the freshness check for RED transitions.
        """
        software_load = self.get_load()
        biometric_load = self.get_biometric_load()
        composite = max(software_load, biometric_load)
        return composite >= _DEPLETION_THRESHOLD

    def record_biometric(self, sample: "BiometricSample") -> None:
        """Ingest one validated biometric sample.

        The sample MUST have been through `biometric_barrier.validate_biometric`.
        This is the only contract — we don't re-validate.
        """
        now_mono = self._now()
        self._biometric.append(
            _BiometricRecord(
                type=sample.type,
                value=sample.value,
                wall_at=sample.sampled_at,
                monotonic_at=now_mono,
            )
        )
        self._prune_biometric(now_mono)

    def _prune_biometric(self, now_mono: float) -> None:
        cutoff = now_mono - self._biometric_window_sec
        while self._biometric and self._biometric[0].monotonic_at < cutoff:
            self._biometric.popleft()

    def get_biometric_load(self) -> float:
        """Normalized biometric stress signal in [0.0, 1.0].

        Returns 0.0 when there is no biometric data — i.e., the user
        has not opted into HealthKit. Equally returns 0.0 when only
        non-stress sample types (e.g., step_count) are present.
        """
        now_mono = self._now()
        self._prune_biometric(now_mono)
        if not self._biometric:
            return 0.0

        hr_values = [r.value for r in self._biometric if r.type == "heart_rate"]
        hrv_values = [
            r.value for r in self._biometric
            if r.type == "heart_rate_variability_sdnn"
        ]

        hr_score = 0.0
        if hr_values:
            mean_hr = sum(hr_values) / len(hr_values)
            hr_score = min(max(mean_hr / self._hr_red_bpm, 0.0), 1.0)

        hrv_score = 0.0
        if hrv_values:
            mean_hrv = sum(hrv_values) / len(hrv_values)
            # Lower HRV = higher stress. Invert and normalize.
            if mean_hrv <= 0:
                hrv_score = 1.0
            else:
                hrv_score = min(max(self._hrv_red_ms / mean_hrv, 0.0), 1.0)

        # Respiratory rate: only the EXCESS over the normal resting floor
        # counts, ramping linearly to 1.0 at the red mark. Normal breathing
        # (<= floor) contributes zero — RR has a high physiological baseline,
        # so the mean/threshold shape used for HR would wrongly inflate load.
        rr_values = [r.value for r in self._biometric if r.type == "respiratory_rate"]
        rr_score = 0.0
        if rr_values:
            mean_rr = sum(rr_values) / len(rr_values)
            span = self._rr_red_bpm - self._rr_floor_bpm
            if span > 0:
                rr_score = min(max((mean_rr - self._rr_floor_bpm) / span, 0.0), 1.0)

        return max(hr_score, hrv_score, rr_score)

    def should_force_red(self, now: datetime | None = None) -> bool:
        """Whether biometric data, within the freshness window, indicates
        a RED-triggering state.

        Stale samples (older than `biometric_red_freshness_sec` wall-clock)
        are excluded — Apple Watch latency means we cannot trust them
        to drive motor inhibition.
        """
        if not self._biometric:
            return False
        now = now or datetime.now(tz=timezone.utc)
        fresh_hr: list[float] = []
        fresh_hrv: list[float] = []
        for r in self._biometric:
            wall = r.wall_at if r.wall_at.tzinfo else r.wall_at.replace(tzinfo=timezone.utc)
            age = (now - wall).total_seconds()
            if age > self._biometric_red_freshness_sec:
                continue
            if r.type == "heart_rate":
                fresh_hr.append(r.value)
            elif r.type == "heart_rate_variability_sdnn":
                fresh_hrv.append(r.value)
        if fresh_hr and (sum(fresh_hr) / len(fresh_hr)) >= self._hr_red_bpm:
            return True
        if fresh_hrv and (sum(fresh_hrv) / len(fresh_hrv)) <= self._hrv_red_ms:
            return True
        return False

    def reset(self) -> None:
        """Clear all tracked records."""
        self._records.clear()
        self._biometric.clear()
