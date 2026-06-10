"""CognitiveEngine — production-hardened integration singleton.

Wires Sprint 1-4 components to the live MCP server.
Every component fails independently. Nothing crashes the MCP server.

Commandment 2: MCP server MUST NOT crash.
Commandment 4: Every try/except logs the exception.
"""

from __future__ import annotations

import json
import logging
import os
from collections import deque
from typing import Any, Optional

from . import engine_config
from .schemas import ScheduleBlock, ScheduleKind

logger = logging.getLogger(__name__)


class CognitiveEngine:
    """Production cognitive engine. Lives alongside the MCP server.

    On each MCP tool call:
    1. Author exchange data to stage
    2. Evaluate computation DAG
    3. Route to delegate via capabilities
    4. Emit CognitiveObservation to buffer
    5. Run prediction

    Every step has independent error handling.
    Failure in any step does not affect others.
    """

    def __init__(
        self,
        buffer_db_path: Optional[str] = None,
        model_path: Optional[str] = None,
        observation_logging: Optional[bool] = None,
        prediction_enabled: Optional[bool] = None,
        use_real_usd: Optional[bool] = None,
        stage_dir: Optional[str] = None,
        in_memory: bool = False,
    ) -> None:
        self.exchange_index = 0
        self.stage_type = "unknown"
        self._observation_logging = (
            observation_logging if observation_logging is not None
            else engine_config.OBSERVATION_LOGGING
        )
        self._prediction_enabled = (
            prediction_enabled if prediction_enabled is not None
            else engine_config.PREDICTION_ENABLED
        )
        self._observations: list = []
        self._pending_save = False
        self._memory_queue: deque = deque(maxlen=100)

        # --- Stage (graceful fallback) ---
        self.stage = self._init_stage(use_real_usd, stage_dir, in_memory)

        # --- Registry + Delegates ---
        self.registry = self._init_registry()

        # --- Consent ---
        self.consent_manager = self._init_consent()

        # --- Observation buffer ---
        # If in_memory mode and no explicit buffer path, use in-memory buffer
        if in_memory and buffer_db_path is None:
            buffer_db_path = ":memory:"
        self._buffer = self._init_buffer(buffer_db_path)

        # --- Predictor ---
        self._predictor = self._init_predictor(model_path)

        # --- External-write detection baseline ---
        # Track the on-disk mtime so the next exchange can absorb out-of-band
        # edits to /schedule/ (or any other prim) before they get clobbered
        # by stage.save(). See reload_if_disk_changed() for the full contract.
        self._stage_disk_path: Optional[str] = None
        self._last_disk_mtime: float = 0.0
        self._refresh_disk_mtime_baseline()

        logger.info(
            f"CognitiveEngine initialized: stage={self.stage_type}, "
            f"predictor={'yes' if self._predictor else 'no'}, "
            f"observations={self._observation_logging}"
        )

    # ─── Component initialization (each with fallback) ────────────

    def _init_stage(self, use_real_usd, stage_dir, in_memory):
        """Initialize stage. Falls back to MockUsdStage on failure."""
        try:
            from .stage_factory import create_stage
            stage = create_stage(
                use_real_usd=use_real_usd,
                stage_dir=stage_dir or engine_config.STAGE_DIR,
                in_memory=in_memory,
            )
            # Detect type
            try:
                from .cognitive_stage import CognitiveStage
                if isinstance(stage, CognitiveStage):
                    self.stage_type = "real_usd"
                else:
                    self.stage_type = "mock"
            except ImportError:
                self.stage_type = "mock"

            # Create delegate sublayers
            stage.create_delegate_sublayer("claude_code")
            stage.create_delegate_sublayer("claude")
            return stage

        except Exception as e:
            logger.warning(f"Stage init failed, using MockUsdStage: {e}")
            from .mock_usd_stage import MockUsdStage
            stage = MockUsdStage()
            stage.create_delegate_sublayer("claude_code")
            stage.create_delegate_sublayer("claude")
            self.stage_type = "mock"
            return stage

    def _init_registry(self):
        """Initialize delegate registry."""
        from .delegate_claude import HdClaude
        from .delegate_claude_code import HdClaudeCode
        from .delegate_registry import DelegateRegistry

        registry = DelegateRegistry()
        registry.register(HdClaude())
        registry.register(HdClaudeCode())
        return registry

    def _init_consent(self):
        """Initialize consent manager."""
        from .consent import ConsentManager
        return ConsentManager()

    def _init_buffer(self, db_path):
        """Initialize observation buffer."""
        try:
            from .observation_buffer import ObservationBuffer
            path = db_path or engine_config.BUFFER_DB_PATH
            return ObservationBuffer(db_path=path)
        except Exception as e:
            logger.warning(f"ObservationBuffer init failed: {e}")
            from .observation_buffer import ObservationBuffer
            return ObservationBuffer(db_path=":memory:")

    def _init_predictor(self, model_path):
        """Initialize predictor. Returns None if unavailable."""
        if not self._prediction_enabled:
            return None
        path = model_path or engine_config.MODEL_PATH
        if not os.path.exists(path):
            logger.warning(f"Predictor model not found at {path}")
            return None
        try:
            from .predict import CognitivePredictor
            return CognitivePredictor(path)
        except Exception as e:
            logger.warning(f"Predictor not loaded: {e}")
            return None

    # ─── Core exchange processing ─────────────────────────────────

    def process_exchange(
        self,
        tool_name: str,
        tool_input: dict,
        session_id: str = "live",
        current_time_iso: Optional[str] = None,
    ) -> Optional[dict]:
        """Process a single exchange. Returns enriched context or None.

        current_time_iso is T3 (UTC ISO 8601 µs, Z suffix) per
        docs/temporal-models.md. When provided, /schedule/ is evaluated and
        attached to the observation, modulating routing and predictor.
        When None, schedule defaults to WORK (current behavior).

        Every step fails independently. MCP server continues regardless.
        """
        if not engine_config.ENGINE_ENABLED:
            return None

        # 0. Absorb external /schedule/ edits before authoring. Save() at the
        # end of this exchange would otherwise clobber any out-of-band write.
        try:
            self.reload_if_disk_changed()
        except Exception as e:
            logger.warning(f"reload_if_disk_changed at exchange entry: {e}")

        self.exchange_index += 1
        idx = self.exchange_index

        # 1. Author exchange data
        resolved = None
        try:
            obs = self._build_authored_observation(tool_name, tool_input, session_id, idx)
            from .mock_cogexec import evaluate_dag
            resolved = evaluate_dag(self.stage, obs, idx)

            # Schedule evaluation (post-DAG so the field survives).
            # Engine remains clock-free: current_time_iso is INPUT, not a clock read.
            if current_time_iso is not None:
                try:
                    resolved.schedule = self._evaluate_schedule(current_time_iso)
                except Exception as e:
                    logger.warning(f"Schedule evaluation failed: {e}")

            self._observations.append(resolved)
        except Exception as e:
            logger.error(f"DAG evaluation failed at exchange {idx}: {e}")
            return self._fallback_response(idx, tool_name)

        # 2. Route via capabilities
        delegate = None
        result = None
        computed = {}
        try:
            from .computations.compute_routing import compute_routing
            has_consent = self.consent_manager.has_valid_consent("override", idx)
            routing = compute_routing(resolved, resolved.state, has_valid_consent=has_consent)
            delegate = self.registry.select(routing["requirements"])

            ctx = self._build_task_context(routing, tool_name, idx)
            computed = self._extract_computed(resolved)
            delegate.sync(self.stage.compose(), computed, ctx)
            result = delegate.execute(tool_name)

            for path, value in result.proposed_mutations.items():
                self.stage.author_to_sublayer(delegate.get_delegate_id(), path, idx, value)
        except Exception as e:
            logger.error(f"Delegate cycle failed at exchange {idx}: {e}")

        # 3. Emit observation
        if self._observation_logging and resolved:
            try:
                self._buffer.add(resolved, partition="organic", surprise_score=0.5)
            except Exception as e:
                logger.error(f"Observation logging failed at exchange {idx}: {e}")
                if len(self._memory_queue) < 100:
                    self._memory_queue.append(resolved)
                    logger.warning("Observation queued in memory")

        # 4. Prediction (skipped during OFF_HOURS per schedule rule)
        prediction = None
        schedule_kind = (
            resolved.schedule.kind if resolved is not None else ScheduleKind.WORK
        )
        if (
            self._predictor
            and len(self._observations) >= 3
            and schedule_kind != ScheduleKind.OFF_HOURS
        ):
            try:
                window = self._observations[-3:]
                prediction = self._predictor.predict(window)
                self.stage.author("/prediction/forecast", idx, prediction)
            except Exception as e:
                logger.error(f"Prediction failed at exchange {idx}: {e}")

        # 5. Save stage
        try:
            if hasattr(self.stage, 'save'):
                self.stage.save()
                self._refresh_disk_mtime_baseline()
            self._pending_save = False
        except Exception as e:
            logger.warning(f"Stage save failed (file locked?): {e}")
            self._pending_save = True

        # 6. Flush memory queue
        self._flush_memory_queue()

        return {
            "cognitive_context": result.response if result else "",
            "delegate_id": delegate.get_delegate_id() if delegate else "none",
            "expert": routing.get("expert", "unknown") if 'routing' in dir() else "unknown",
            "exchange_index": idx,
            "prediction": prediction,
            "observation_logged": self._observation_logging,
        }

    # ─── Helpers ──────────────────────────────────────────────────

    def _build_authored_observation(self, tool_name, tool_input, session_id, idx):
        """Build observation from MCP tool call context."""
        from .schemas import (
            ActionBlock, ActionType, AllostasisBlock,
            CognitiveObservation, DynamicsBlock, StateBlock,
        )
        message = tool_input.get("message", tool_input.get("query", ""))
        msg_len = len(message) if isinstance(message, str) else 0

        return CognitiveObservation(
            session_id=session_id,
            observation_index=idx,
            exchange_index=idx,
            state=StateBlock(exercise_recency_days=1),
            action=ActionBlock(action_type=ActionType.QUERY),
            dynamics=DynamicsBlock(
                exchange_velocity=min(msg_len / 500.0, 1.0),
                topic_coherence=0.7,
                session_exchange_count=idx,
                exchanges_without_break=idx,
                tasks_completed=max(idx // 3, 0),
            ),
            allostasis=AllostasisBlock(sessions_24h=1),
        )

    def _build_task_context(self, routing, tool_name, idx):
        """Build TaskContext from routing result."""
        from .delegate_base import TaskContext
        return TaskContext(
            task_type=routing["expert"],
            signal_class=tool_name,
            requires_coding=routing["requirements"].get("requires_coding", False),
            context_budget=routing["requirements"].get("context_budget", "medium"),
            exchange_index=idx,
        )

    def _extract_computed(self, resolved):
        """Extract computed values dict from resolved observation."""
        return {
            "momentum": int(resolved.state.momentum),
            "burnout": int(resolved.state.burnout),
            "energy": int(resolved.state.energy),
            "burst": int(resolved.dynamics.burst_phase),
            "allostasis": {"load": resolved.allostasis.load},
        }

    def _fallback_response(self, idx, tool_name):
        """Return minimal response when engine fails."""
        return {
            "cognitive_context": "",
            "delegate_id": "none",
            "expert": "unknown",
            "exchange_index": idx,
            "prediction": None,
            "observation_logged": False,
        }

    def _flush_memory_queue(self):
        """Drain memory queue to DB when possible."""
        while self._memory_queue:
            try:
                obs = self._memory_queue[0]
                self._buffer.add(obs, partition="organic", surprise_score=0.5)
                self._memory_queue.popleft()
            except Exception:
                break

    # ─── External-write detection ─────────────────────────────────

    def _refresh_disk_mtime_baseline(self) -> None:
        """Capture current on-disk mtime as the daemon's known-fresh baseline.

        Called after engine init and after every successful stage.save() so the
        baseline always reflects "the disk content the daemon currently has in
        memory." A subsequent mtime that exceeds this baseline means an
        out-of-band writer has modified the file since.
        """
        try:
            usd_stage = getattr(self.stage, "usd_stage", None)
            if usd_stage is None:
                return
            layer = usd_stage.GetRootLayer()
            path = getattr(layer, "realPath", "") or ""
            if not path or not os.path.exists(path):
                return
            self._stage_disk_path = path
            self._last_disk_mtime = os.path.getmtime(path)
        except Exception as e:
            logger.debug(f"_refresh_disk_mtime_baseline: {e}")

    def reload_if_disk_changed(self, force: bool = False) -> dict:
        """Detect and absorb external writes to the stage file.

        Returns {"reloaded": bool, "reason": str}. Safe to call any time.
        No-op for in-memory stages, missing files, or disk that hasn't
        advanced past the baseline (unless force=True).

        Race window: an external writer that modifies disk DURING an
        in-flight exchange (between author and save) will be clobbered by
        that exchange's save and not detectable on the next call (daemon's
        save updates mtime, masking the loss). The stage_reload MCP tool
        with force=True is the explicit recovery for that case.
        """
        path = self._stage_disk_path
        if path is None or not os.path.exists(path):
            return {"reloaded": False, "reason": "no on-disk stage"}
        try:
            current_mtime = os.path.getmtime(path)
        except OSError as e:
            return {"reloaded": False, "reason": f"stat failed: {e}"}
        if not force and current_mtime <= self._last_disk_mtime:
            return {"reloaded": False, "reason": "disk unchanged"}
        usd_stage = getattr(self.stage, "usd_stage", None)
        if usd_stage is None:
            return {"reloaded": False, "reason": "no usd stage"}
        try:
            layer = usd_stage.GetRootLayer()
            ok = layer.Reload(force=False)
        except Exception as e:
            return {"reloaded": False, "reason": f"reload failed: {e}"}
        if not ok:
            return {"reloaded": False, "reason": "layer dirty (in-flight write?)"}
        self._last_disk_mtime = current_mtime
        return {"reloaded": True, "reason": "absorbed external change"}

    def reload_schedule(self, force: bool = False) -> dict:
        """Reload schedule.usda sublayer from disk.

        /schedule/ now lives on a dedicated sublayer the daemon never authors
        to (see src/schedule_migrate.py). External edits land directly on
        schedule.usda and are absorbed via Sdf.Layer.Reload — no race against
        the daemon's per-exchange root save.

        Returns {"reloaded": bool, "reason": str}.
        """
        try:
            usd_stage = getattr(self.stage, "usd_stage", None)
            if usd_stage is None:
                return {"reloaded": False, "reason": "no usd stage"}
            stage_dir = getattr(self.stage, "_stage_dir", None)
            if stage_dir is None:
                return {"reloaded": False, "reason": "no stage_dir"}
            sched_path = os.path.join(stage_dir, "schedule.usda")
            if not os.path.exists(sched_path):
                return {"reloaded": False, "reason": "no schedule.usda"}
            from pxr import Sdf
            sched_layer = Sdf.Layer.FindOrOpen(sched_path)
            if sched_layer is None:
                return {"reloaded": False, "reason": "could not open schedule.usda"}
            ok = sched_layer.Reload(force=force)
        except Exception as e:
            return {"reloaded": False, "reason": f"reload failed: {e}"}
        if not ok:
            return {"reloaded": False, "reason": "layer dirty or unchanged"}
        return {"reloaded": True, "reason": "absorbed external change"}

    def _evaluate_schedule(self, current_time_iso: str) -> ScheduleBlock:
        """Load /schedule/ from the underlying USD stage and evaluate.

        Returns ScheduleBlock(kind=WORK) if the stage doesn't expose a real
        USD stage (mock fallback) or if /schedule/ is unconfigured.
        """
        usd_stage = getattr(self.stage, "usd_stage", None)
        if usd_stage is None:
            return ScheduleBlock()
        from .schedule import evaluate_schedule, load_schedule_from_stage
        return evaluate_schedule(load_schedule_from_stage(usd_stage), current_time_iso)

    # ─── Health + Status ──────────────────────────────────────────

    def get_health(self) -> dict:
        """Production health check."""
        obs_count = 0
        try:
            stats = self._buffer.size()
            obs_count = stats.get("total", 0)
        except Exception:
            pass

        usda_exists = False
        try:
            usda_path = os.path.join(engine_config.STAGE_DIR, "harlo.usda")
            usda_exists = os.path.exists(usda_path)
        except Exception:
            pass

        return {
            "engine": "active" if engine_config.ENGINE_ENABLED else "disabled",
            "stage_type": self.stage_type,
            "stage_file": usda_exists,
            "predictor": self._predictor is not None,
            "observations_logged": obs_count,
            "exchange_index": self.exchange_index,
            "delegates_registered": len(self.registry.list_delegates()),
            "memory_queue_size": len(self._memory_queue),
            "pending_save": self._pending_save,
        }

    def get_buffer_stats(self) -> dict:
        """Get observation buffer statistics."""
        try:
            return self._buffer.size()
        except Exception:
            return {"anchor": 0, "organic": 0, "total": 0}

    def get_exchange_count(self) -> int:
        """Get total exchange count."""
        return self.exchange_index

    def close(self) -> None:
        """Clean up resources."""
        try:
            self._flush_memory_queue()
            if hasattr(self.stage, 'save'):
                self.stage.save()
        except Exception as e:
            logger.warning(f"Cleanup save failed: {e}")
        try:
            self._buffer.close()
        except Exception:
            pass
