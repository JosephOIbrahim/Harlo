"""CognitiveEngine — integration singleton between Sprint 1/3 and live MCP.

On each MCP tool call that touches cognitive state:
1. Evaluate the computation DAG
2. Route to appropriate delegate via capability requirements
3. Emit CognitiveObservation
4. Run prediction (if enabled)

Commandment 2: Existing MCP server works — extend, don't break.
Commandment 5: Every MCP call emits a CognitiveObservation.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

from .computations.compute_routing import compute_routing
from .consent import ConsentManager
from .delegate_base import DelegateResult, TaskContext
from .delegate_claude import HdClaude
from .delegate_claude_code import HdClaudeCode
from .delegate_registry import DelegateRegistry
from .mock_cogexec import evaluate_dag
from .mock_usd_stage import MockUsdStage
from .observation_buffer import ObservationBuffer
from .schemas import (
    ActionBlock,
    ActionType,
    AllostasisBlock,
    CognitiveObservation,
    DynamicsBlock,
    StateBlock,
)

logger = logging.getLogger(__name__)


class CognitiveEngine:
    """Singleton that lives alongside the MCP server.

    On each MCP tool call:
    1. Author exchange data to stage
    2. Evaluate computation DAG
    3. Route to delegate via capabilities
    4. Emit CognitiveObservation to buffer
    5. Run prediction (async-safe)
    """

    def __init__(
        self,
        buffer_db_path: str = ":memory:",
        model_path: Optional[str] = None,
        observation_logging: bool = True,
        prediction_enabled: bool = True,
    ) -> None:
        self.stage = MockUsdStage()
        self.registry = DelegateRegistry()
        self.consent_manager = ConsentManager()
        self.exchange_index = 0
        self._observation_logging = observation_logging
        self._prediction_enabled = prediction_enabled
        self._observations: list[CognitiveObservation] = []

        # Register delegates
        claude = HdClaude()
        claude_code = HdClaudeCode()
        self.registry.register(claude)
        self.registry.register(claude_code)

        # Create sublayers
        self.stage.create_delegate_sublayer("claude_code")
        self.stage.create_delegate_sublayer("claude")

        # Observation buffer
        self._buffer = ObservationBuffer(db_path=buffer_db_path)

        # Predictor (optional, graceful fallback)
        self._predictor = None
        if prediction_enabled and model_path:
            try:
                from .predict import CognitivePredictor
                self._predictor = CognitivePredictor(model_path)
            except Exception as e:
                logger.warning(f"Predictor not loaded: {e}")

    def process_exchange(
        self,
        tool_name: str,
        tool_input: dict,
        session_id: str = "live",
    ) -> dict:
        """Process a single exchange through the cognitive engine.

        Called by MCP server on each tool invocation.
        Returns enriched context dict.
        """
        self.exchange_index += 1
        idx = self.exchange_index

        # 1. Author exchange data to stage
        obs = self._build_authored_observation(tool_name, tool_input, session_id, idx)

        # 2. Evaluate full DAG
        resolved = evaluate_dag(self.stage, obs, idx)
        self._observations.append(resolved)

        # 3. Route via capabilities
        has_consent = self.consent_manager.has_valid_consent("override", idx)
        routing = compute_routing(resolved, resolved.state, has_valid_consent=has_consent)
        delegate = self.registry.select(routing["requirements"])

        # 4. Delegate cycle
        ctx = TaskContext(
            task_type=routing["expert"],
            signal_class=tool_name,
            requires_coding=routing["requirements"].get("requires_coding", False),
            context_budget=routing["requirements"].get("context_budget", "medium"),
            exchange_index=idx,
        )
        computed = {
            "momentum": int(resolved.state.momentum),
            "burnout": int(resolved.state.burnout),
            "energy": int(resolved.state.energy),
            "burst": int(resolved.dynamics.burst_phase),
            "allostasis": {"load": resolved.allostasis.load},
        }
        delegate.sync(self.stage.compose(), computed, ctx)
        result = delegate.execute(tool_name)

        # Commit to sublayer
        for path, value in result.proposed_mutations.items():
            self.stage.author_to_sublayer(delegate.get_delegate_id(), path, idx, value)

        # 5. Emit observation
        if self._observation_logging:
            self._buffer.add(resolved, partition="organic", surprise_score=0.5)

        # 6. Prediction
        prediction = None
        if self._predictor and len(self._observations) >= 3:
            try:
                window = self._observations[-3:]
                prediction = self._predictor.predict(window)
                self.stage.author("/prediction/forecast", idx, prediction)
            except Exception as e:
                logger.warning(f"Prediction failed: {e}")

        return {
            "cognitive_context": result.response,
            "delegate_id": delegate.get_delegate_id(),
            "expert": routing["expert"],
            "exchange_index": idx,
            "prediction": prediction,
            "observation_logged": self._observation_logging,
        }

    def _build_authored_observation(
        self, tool_name: str, tool_input: dict,
        session_id: str, exchange_index: int,
    ) -> CognitiveObservation:
        """Build an authored observation from MCP tool call context."""
        # Estimate dynamics from tool input
        message = tool_input.get("message", tool_input.get("query", ""))
        msg_len = len(message) if isinstance(message, str) else 0

        return CognitiveObservation(
            session_id=session_id,
            observation_index=exchange_index,
            exchange_index=exchange_index,
            state=StateBlock(exercise_recency_days=1),
            action=ActionBlock(action_type=ActionType.QUERY),
            dynamics=DynamicsBlock(
                exchange_velocity=min(msg_len / 500.0, 1.0),
                topic_coherence=0.7,
                session_exchange_count=exchange_index,
                exchanges_without_break=exchange_index,
                tasks_completed=max(exchange_index // 3, 0),
            ),
            allostasis=AllostasisBlock(sessions_24h=1),
        )

    def get_buffer_stats(self) -> dict:
        """Get observation buffer statistics."""
        return self._buffer.size()

    def get_exchange_count(self) -> int:
        """Get total exchange count."""
        return self.exchange_index

    def close(self) -> None:
        """Clean up resources."""
        self._buffer.close()
