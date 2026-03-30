"""Prediction inference — load model, accept state+action, output prediction.

Sprint 1 Phase 4: Prediction from trained XGBoost model.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
from sklearn.multioutput import MultiOutputRegressor

from .schemas import (
    BurstPhase,
    Burnout,
    CognitiveObservation,
    Energy,
    Momentum,
)
from .train_predictor import (
    TARGET_NAMES,
    TARGET_RANGES,
    _encode_observation,
    _round_and_clamp,
)


class CognitivePredictor:
    """Load a trained model and predict next cognitive state."""

    def __init__(self, model_path: str = "models/cognitive_predictor_v1.joblib"):
        self._model: MultiOutputRegressor = joblib.load(model_path)

    def predict(
        self,
        window: list[CognitiveObservation],
    ) -> dict[str, int]:
        """Predict next state from a window of observations.

        Args:
            window: List of 3 consecutive CognitiveObservations.

        Returns:
            Dict with predicted values for momentum, burnout, energy, burst_phase.
        """
        if len(window) != 3:
            raise ValueError(f"Window must be exactly 3 observations, got {len(window)}")

        features: list[float] = []
        for obs in window:
            features.extend(_encode_observation(obs))

        X = np.array([features])
        y_raw = self._model.predict(X)
        y_pred = _round_and_clamp(y_raw)

        result = {}
        for i, name in enumerate(TARGET_NAMES):
            result[name] = int(y_pred[0, i])

        return result

    def predict_observation(
        self,
        window: list[CognitiveObservation],
    ) -> CognitiveObservation:
        """Predict and return a full observation with predicted state values.

        Uses the last observation in the window as the template,
        overriding state fields with predictions.
        """
        predictions = self.predict(window)
        last = window[-1].model_copy(deep=True)

        last.state.momentum = Momentum(predictions["momentum"])
        last.state.burnout = Burnout(predictions["burnout"])
        last.state.energy = Energy(predictions["energy"])
        last.dynamics.burst_phase = BurstPhase(predictions["burst_phase"])
        last.exchange_index += 1

        return last
