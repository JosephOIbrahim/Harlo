"""Allostatic load tracking.

Rule 9: Allostatic load = token velocity + prompt frequency. Software only.
Rule 1: Zero-watt idle. Event-driven only.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field


# Window for tracking velocity (seconds)
_WINDOW_SEC = 300.0  # 5 minutes
_DEPLETION_THRESHOLD = 0.85
# Max expected tokens-per-second for normalization
_MAX_TOKEN_VELOCITY = 100.0
# Max expected prompts-per-minute for normalization
_MAX_PROMPT_FREQ = 20.0


@dataclass
class _PromptRecord:
    tokens: int
    ts: float


class AllostasisTracker:
    """Track token velocity and prompt frequency to compute allostatic load.

    Pure state tracking. Event-driven only. No polling. No background threads.
    """

    def __init__(self, window_sec: float = _WINDOW_SEC) -> None:
        self._window_sec = window_sec
        self._records: deque[_PromptRecord] = deque()

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
        """Check if the system is in a depleted state."""
        return self.get_load() >= _DEPLETION_THRESHOLD

    def reset(self) -> None:
        """Clear all tracked records."""
        self._records.clear()
