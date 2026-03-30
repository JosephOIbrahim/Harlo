"""Mock USD Stage — dict-based storage keyed by (prim_path, exchange_index).

Commandment 3: exchange_index is a monotonic integer. The ONLY temporal key.
Commandment 4: State machines read t-1 from authored history. No self-query cycles.
Commandment 5: At exchange_index == 0, read_previous() returns schema default baseline.
               NEVER returns None. NEVER throws KeyError.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Optional

from .schemas import (
    BASELINE_OBSERVATION,
    CognitiveObservation,
)


class MockUsdStage:
    """Dict-based USD stage mock for cognitive state simulation.

    Storage is keyed by (prim_path: str, exchange_index: int).
    Supports author(), read(), read_previous() with schema-default baselines.
    Supports stage-level threshold configuration.
    """

    def __init__(self, thresholds: Optional[dict[str, float]] = None) -> None:
        self._store: dict[tuple[str, int], Any] = {}
        self._thresholds: dict[str, float] = {
            "building_task_threshold": 3,
            "rolling_coherence_threshold": 0.7,
            "rolling_velocity_threshold": 0.5,
            "peak_exchange_threshold": 50,
            "burst_detect_velocity": 0.8,
            "burst_detect_coherence": 0.85,
            "burst_winding_exchange": 50,
            "burst_exit_exchange": 70,
            "energy_decrement_interval": 10,
            "tangent_base_budget": 4.0,
            "context_promote_threshold": 4.2,
            "context_demote_threshold": 3.8,
            "frustration_burnout_threshold": 0.7,
            "burnout_exchange_yellow": 20,
            "burnout_exchange_orange": 40,
        }
        if thresholds:
            self._thresholds.update(thresholds)

    def get_threshold(self, name: str) -> float:
        """Get a stage-level threshold by name."""
        return self._thresholds[name]

    def author(self, prim_path: str, exchange_index: int, value: Any) -> None:
        """Write a value to the stage at (prim_path, exchange_index)."""
        self._store[(prim_path, exchange_index)] = deepcopy(value)

    def read(self, prim_path: str, exchange_index: int) -> Any:
        """Read a value from the stage. Returns None if not found."""
        key = (prim_path, exchange_index)
        val = self._store.get(key)
        return deepcopy(val) if val is not None else None

    def read_previous(self, prim_path: str, exchange_index: int) -> Any:
        """Read the value at exchange_index - 1.

        Commandment 5: At exchange_index == 0, returns schema default baseline.
        NEVER returns None. NEVER throws KeyError.
        """
        if exchange_index <= 0:
            return self._get_baseline(prim_path)

        prev = self.read(prim_path, exchange_index - 1)
        if prev is not None:
            return prev

        return self._get_baseline(prim_path)

    def _get_baseline(self, prim_path: str) -> Any:
        """Return the schema default baseline for a prim path.

        Commandment 5: NEVER None. NEVER KeyError.
        """
        return BASELINE_OBSERVATION.model_copy(deep=True)

    def keys(self) -> list[tuple[str, int]]:
        """Return all stored keys."""
        return list(self._store.keys())

    def max_exchange_index(self) -> int:
        """Return the highest exchange_index in the store, or -1 if empty."""
        if not self._store:
            return -1
        return max(idx for _, idx in self._store.keys())

    def clear(self) -> None:
        """Clear all stored data."""
        self._store.clear()
