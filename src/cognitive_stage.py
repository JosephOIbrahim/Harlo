"""CognitiveStage — real pxr.Usd.Stage for cognitive state.

Drop-in replacement for MockUsdStage. Same method signatures.
State lives in .usda files on disk. Human-readable. Git-trackable.

Commandment 4: Same interface as MockUsdStage.
Commandment 5: .usda files in data/stages/.
Commandment 6: read_previous(path, 0) returns defaults. NEVER None.
Commandment 7: Time samples use Usd.TimeCode(exchange_index).
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from typing import Any, Optional

from . import usd_bootstrap  # noqa: F401 — ensures pxr is importable

from pxr import Sdf, Usd

from .schemas import BASELINE_OBSERVATION, CognitiveObservation


class CognitiveStage:
    """Real USD stage for cognitive state. Drop-in for MockUsdStage.

    Stores CognitiveObservation objects as JSON strings in USD time samples.
    Delegate sublayers are real .usda files composed via USD sublayer mechanics.
    """

    def __init__(
        self,
        stage_dir: Optional[str] = None,
        thresholds: Optional[dict[str, float]] = None,
        in_memory: bool = False,
    ) -> None:
        self._stage_dir = stage_dir or os.path.join("data", "stages")
        self._in_memory = in_memory
        self._sublayer_priority: list[str] = []
        self._sublayer_stages: dict[str, Usd.Stage] = {}

        # Thresholds (same as MockUsdStage)
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

        if in_memory:
            self._stage = Usd.Stage.CreateInMemory()
        else:
            os.makedirs(self._stage_dir, exist_ok=True)
            os.makedirs(os.path.join(self._stage_dir, "delegates"), exist_ok=True)
            root_path = os.path.join(self._stage_dir, "cognitive_twin.usda")
            if os.path.exists(root_path):
                self._stage = Usd.Stage.Open(root_path)
            else:
                self._stage = Usd.Stage.CreateNew(root_path)
                self._init_hierarchy()
                self._stage.GetRootLayer().Save()

        self._init_hierarchy()

    def _init_hierarchy(self) -> None:
        """Create canonical prim structure."""
        for path in [
            "/state", "/state/momentum", "/state/burnout", "/state/energy",
            "/state/injection", "/state/allostatic",
            "/routing", "/sessions", "/delegates", "/prediction",
            "/memory", "/projects",
        ]:
            if not self._stage.GetPrimAtPath(path).IsValid():
                self._stage.DefinePrim(path, "Scope")

    # ─── Core API (matches MockUsdStage interface exactly) ────────────

    def get_threshold(self, name: str) -> float:
        """Get a stage-level threshold by name."""
        return self._thresholds[name]

    def author(self, prim_path: str, exchange_index: int, value: Any) -> None:
        """Write a value to the stage at (prim_path, exchange_index).

        Stores value as JSON string in a time sample on a 'data' attribute.
        """
        prim = self._ensure_prim(prim_path)
        attr = self._ensure_data_attr(prim)
        serialized = self._serialize(value)
        attr.Set(serialized, Usd.TimeCode(float(exchange_index)))

    def read(self, prim_path: str, exchange_index: int) -> Any:
        """Read a value from the stage. Returns None if not found."""
        prim = self._stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            return None
        attr = prim.GetAttribute("data")
        if not attr.IsValid():
            return None
        val = attr.Get(Usd.TimeCode(float(exchange_index)))
        if val is None:
            return None
        return self._deserialize(val)

    def read_previous(self, prim_path: str, exchange_index: int) -> Any:
        """Read value at exchange_index - 1.

        Commandment 6: At exchange_index == 0, returns schema defaults.
        NEVER returns None. NEVER throws KeyError.
        """
        if exchange_index <= 0:
            return self._get_baseline(prim_path)
        prev = self.read(prim_path, exchange_index - 1)
        if prev is not None:
            return prev
        return self._get_baseline(prim_path)

    def _get_baseline(self, prim_path: str) -> Any:
        """Return schema default baseline. NEVER None."""
        return BASELINE_OBSERVATION.model_copy(deep=True)

    # ─── Delegate sublayers (real .usda files) ────────────────────────

    def create_delegate_sublayer(self, delegate_id: str) -> None:
        """Create an isolated write layer for a delegate."""
        if delegate_id not in self._sublayer_stages:
            if self._in_memory:
                sub_stage = Usd.Stage.CreateInMemory()
            else:
                layer_path = os.path.join(
                    self._stage_dir, "delegates", f"{delegate_id}.usda"
                )
                if os.path.exists(layer_path):
                    sub_stage = Usd.Stage.Open(layer_path)
                else:
                    sub_stage = Usd.Stage.CreateNew(layer_path)
                    sub_stage.GetRootLayer().Save()

                # Add as sublayer to root
                root_layer = self._stage.GetRootLayer()
                if layer_path not in root_layer.subLayerPaths:
                    root_layer.subLayerPaths.append(layer_path)

            self._sublayer_stages[delegate_id] = sub_stage
            if delegate_id not in self._sublayer_priority:
                self._sublayer_priority.append(delegate_id)

    def set_sublayer_priority(self, priority: list[str]) -> None:
        """Set sublayer composition priority. Last = strongest."""
        self._sublayer_priority = list(priority)

    def author_to_sublayer(
        self, delegate_id: str, prim_path: str,
        exchange_index: int, value: Any,
    ) -> None:
        """Write to a delegate's sublayer."""
        if delegate_id not in self._sublayer_stages:
            self.create_delegate_sublayer(delegate_id)
        sub_stage = self._sublayer_stages[delegate_id]
        prim = sub_stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            prim = sub_stage.DefinePrim(prim_path, "Scope")
        attr = prim.GetAttribute("data")
        if not attr.IsValid():
            attr = prim.CreateAttribute("data", Sdf.ValueTypeNames.String)
        serialized = self._serialize(value)
        attr.Set(serialized, Usd.TimeCode(float(exchange_index)))

    def read_from_sublayer(
        self, delegate_id: str, prim_path: str, exchange_index: int,
    ) -> Any:
        """Read from a specific delegate sublayer."""
        sub_stage = self._sublayer_stages.get(delegate_id)
        if sub_stage is None:
            return None
        prim = sub_stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            return None
        attr = prim.GetAttribute("data")
        if not attr.IsValid():
            return None
        val = attr.Get(Usd.TimeCode(float(exchange_index)))
        if val is None:
            return None
        return self._deserialize(val)

    def compose(self) -> dict:
        """Compose base + all sublayers. Returns dict keyed by (path, index).

        Mimics MockUsdStage.compose() for compatibility.
        """
        composed: dict[tuple[str, int], Any] = {}

        # Base stage entries
        self._collect_time_samples(self._stage, composed)

        # Sublayers in priority order (last = strongest)
        for delegate_id in self._sublayer_priority:
            sub_stage = self._sublayer_stages.get(delegate_id)
            if sub_stage:
                self._collect_time_samples(sub_stage, composed)

        return composed

    def _collect_time_samples(self, stage: Usd.Stage, target: dict) -> None:
        """Collect all time-sampled data from a stage into target dict."""
        for prim in stage.TraverseAll():
            attr = prim.GetAttribute("data")
            if attr.IsValid():
                time_samples = attr.GetTimeSamples()
                for ts in time_samples:
                    val = attr.Get(Usd.TimeCode(ts))
                    if val is not None:
                        key = (str(prim.GetPath()), int(ts))
                        target[key] = self._deserialize(val)

    # ─── Persistence ──────────────────────────────────────────────────

    def save(self) -> None:
        """Persist all layers to disk."""
        if not self._in_memory:
            self._stage.GetRootLayer().Save()
            for sub_stage in self._sublayer_stages.values():
                sub_stage.GetRootLayer().Save()

    def export_flat(self, output_path: str) -> None:
        """Export flattened stage to a single .usda file."""
        self._stage.Export(output_path)

    def get_usda_text(self) -> str:
        """Return the root .usda as text."""
        return self._stage.GetRootLayer().ExportToString()

    # ─── Compat methods from MockUsdStage ─────────────────────────────

    def keys(self) -> list[tuple[str, int]]:
        """Return all stored keys from base stage."""
        result: list[tuple[str, int]] = []
        for prim in self._stage.TraverseAll():
            attr = prim.GetAttribute("data")
            if attr.IsValid():
                for ts in attr.GetTimeSamples():
                    result.append((str(prim.GetPath()), int(ts)))
        return result

    def max_exchange_index(self) -> int:
        """Return highest exchange_index in base stage, or -1 if empty."""
        indices = []
        for prim in self._stage.TraverseAll():
            attr = prim.GetAttribute("data")
            if attr.IsValid():
                samples = attr.GetTimeSamples()
                if samples:
                    indices.append(int(max(samples)))
        return max(indices) if indices else -1

    def clear(self) -> None:
        """Clear all data. For in-memory stages, recreates."""
        if self._in_memory:
            self._stage = Usd.Stage.CreateInMemory()
            self._init_hierarchy()
            for did in list(self._sublayer_stages):
                self._sublayer_stages[did] = Usd.Stage.CreateInMemory()
        else:
            # Clear all prims except hierarchy
            for prim in list(self._stage.TraverseAll()):
                attr = prim.GetAttribute("data")
                if attr.IsValid():
                    attr.Clear()
            for sub_stage in self._sublayer_stages.values():
                for prim in list(sub_stage.TraverseAll()):
                    attr = prim.GetAttribute("data")
                    if attr.IsValid():
                        attr.Clear()

    @property
    def usd_stage(self) -> Usd.Stage:
        """Access the raw USD stage."""
        return self._stage

    # ─── Serialization ────────────────────────────────────────────────

    @staticmethod
    def _serialize(value: Any) -> str:
        """Serialize a Python value to JSON string for USD storage."""
        if isinstance(value, CognitiveObservation):
            return value.model_dump_json()
        elif isinstance(value, dict):
            return json.dumps(value, default=str)
        else:
            return json.dumps(value, default=str)

    @staticmethod
    def _deserialize(raw: str) -> Any:
        """Deserialize from JSON string. Attempts CognitiveObservation first."""
        if not isinstance(raw, str):
            return raw
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and "schema_name" in data:
                return CognitiveObservation(**data)
            return data
        except (json.JSONDecodeError, TypeError, ValueError):
            return raw

    def _ensure_prim(self, prim_path: str):
        """Get or create a prim at the given path."""
        prim = self._stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            prim = self._stage.DefinePrim(prim_path, "Scope")
        return prim

    def _ensure_data_attr(self, prim):
        """Ensure prim has a 'data' string attribute."""
        attr = prim.GetAttribute("data")
        if not attr.IsValid():
            attr = prim.CreateAttribute("data", Sdf.ValueTypeNames.String)
        return attr
