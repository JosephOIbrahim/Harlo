"""XGBoost Predictor Training — Sprint 1 Phase 4.

Commandment 10: Ordinal encoding for progressive states (GREEN=0..RED=3).
One-Hot for nominals (action_type, context). XGBRegressor with reg:squarederror.
MultiOutputRegressor wrapping. Round predictions to nearest valid integer.
Drop exchange_index and session_id from features.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.multioutput import MultiOutputRegressor
from xgboost import XGBRegressor

from .schemas import (
    ActionType,
    AllostasisTrend,
    BurstPhase,
    Burnout,
    CognitiveObservation,
    ContextLevel,
    Energy,
    InjectionPhase,
    InjectionProfile,
    Momentum,
    SleepQuality,
)


# -------------------------------------------------------------------
# Feature encoding
# -------------------------------------------------------------------

# Nominal fields that need one-hot encoding
NOMINAL_ACTION_TYPES = list(ActionType)
NOMINAL_INJECTION_PROFILES = list(InjectionProfile)

# Ordinal targets to predict
TARGET_NAMES = ["momentum", "burnout", "energy", "burst_phase"]
TARGET_RANGES = {
    "momentum": (0, 4),
    "burnout": (0, 3),
    "energy": (0, 3),
    "burst_phase": (0, 4),
}


def _encode_observation(obs: CognitiveObservation) -> list[float]:
    """Encode a single observation into a feature vector.

    Commandment 10: Ordinal for progressive states, One-Hot for nominals.
    Drops exchange_index and session_id.
    """
    features: list[float] = []

    # Ordinal state features
    features.append(float(int(obs.state.momentum)))
    features.append(float(int(obs.state.burnout)))
    features.append(float(int(obs.state.energy)))
    features.append(float(int(obs.state.altitude)))
    features.append(float(obs.state.exercise_recency_days))
    features.append(float(int(obs.state.sleep_quality)))
    features.append(float(int(obs.state.context)))

    # One-hot action_type (Commandment 10: one-hot for nominals)
    for at in NOMINAL_ACTION_TYPES:
        features.append(1.0 if obs.action.action_type == at else 0.0)

    # Dynamics (continuous + ordinal)
    features.append(obs.dynamics.exchange_velocity)
    features.append(obs.dynamics.topic_coherence)
    features.append(float(obs.dynamics.session_exchange_count))
    features.append(float(int(obs.dynamics.burst_phase)))
    features.append(obs.dynamics.tangent_budget_remaining)
    features.append(float(obs.dynamics.exchanges_without_break))
    features.append(float(obs.dynamics.adrenaline_debt))
    features.append(float(obs.dynamics.tasks_completed))
    features.append(obs.dynamics.frustration_signal)

    # Injection (ordinal profile + continuous alpha + ordinal phase)
    # One-hot injection profile (nominal)
    for ip in NOMINAL_INJECTION_PROFILES:
        features.append(1.0 if obs.injection.profile == ip else 0.0)
    features.append(obs.injection.alpha)
    features.append(float(int(obs.injection.phase)))

    # Allostasis (continuous)
    features.append(obs.allostasis.load)
    features.append(float(int(obs.allostasis.trend)))
    features.append(float(obs.allostasis.sessions_24h))
    features.append(obs.allostasis.override_ratio_7d)

    return features


def _encode_targets(obs: CognitiveObservation) -> list[float]:
    """Encode prediction targets (ordinal state values)."""
    return [
        float(int(obs.state.momentum)),
        float(int(obs.state.burnout)),
        float(int(obs.state.energy)),
        float(int(obs.dynamics.burst_phase)),
    ]


def _build_sliding_window(
    trajectory: list[CognitiveObservation],
    window_size: int = 3,
) -> tuple[list[list[float]], list[list[float]]]:
    """Build 3-step sliding window features and targets.

    Input: observations at [t-2, t-1, t] → predict state at t.
    Commandment 10: Drop exchange_index and session_id.
    """
    X: list[list[float]] = []
    y: list[list[float]] = []

    for i in range(window_size - 1, len(trajectory)):
        window_features: list[float] = []
        for j in range(window_size):
            obs = trajectory[i - (window_size - 1) + j]
            window_features.extend(_encode_observation(obs))

        targets = _encode_targets(trajectory[i])
        X.append(window_features)
        y.append(targets)

    return X, y


def load_trajectories(jsonl_path: str) -> list[list[CognitiveObservation]]:
    """Load trajectories from JSONL file."""
    trajectories = []
    with open(jsonl_path) as f:
        for line in f:
            traj_data = json.loads(line)
            traj = [CognitiveObservation(**obs) for obs in traj_data]
            trajectories.append(traj)
    return trajectories


def prepare_dataset(
    trajectories: list[list[CognitiveObservation]],
    window_size: int = 3,
) -> tuple[np.ndarray, np.ndarray]:
    """Prepare full dataset from trajectories."""
    all_X: list[list[float]] = []
    all_y: list[list[float]] = []

    for traj in trajectories:
        if len(traj) < window_size:
            continue
        X, y = _build_sliding_window(traj, window_size)
        all_X.extend(X)
        all_y.extend(y)

    return np.array(all_X), np.array(all_y)


def train_model(
    X: np.ndarray,
    y: np.ndarray,
    test_size: float = 0.1,
    val_size: float = 0.1,
    seed: int = 42,
) -> tuple[MultiOutputRegressor, dict]:
    """Train XGBoost multi-output regressor.

    Commandment 10: XGBRegressor with reg:squarederror.
    MultiOutputRegressor wrapping. Round predictions to nearest valid integer.

    Returns: (model, metrics_dict)
    """
    # 80/10/10 split
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed,
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val,
        test_size=val_size / (1 - test_size),
        random_state=seed,
    )

    base_model = XGBRegressor(
        objective="reg:squarederror",
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        random_state=seed,
        verbosity=0,
    )

    model = MultiOutputRegressor(base_model)
    model.fit(X_train, y_train)

    # Evaluate
    y_pred_raw = model.predict(X_test)
    y_pred = _round_and_clamp(y_pred_raw)

    metrics = _compute_metrics(y_test, y_pred)

    # Validation metrics
    y_val_pred_raw = model.predict(X_val)
    y_val_pred = _round_and_clamp(y_val_pred_raw)
    val_metrics = _compute_metrics(y_val, y_val_pred)
    metrics["val_metrics"] = val_metrics

    metrics["dataset_stats"] = {
        "train_size": len(X_train),
        "val_size": len(X_val),
        "test_size": len(X_test),
        "feature_count": X.shape[1],
    }

    return model, metrics


def _round_and_clamp(predictions: np.ndarray) -> np.ndarray:
    """Round predictions to nearest valid integer and clamp to valid range.

    Commandment 10: Round predictions to nearest valid integer class.
    """
    result = np.round(predictions).astype(int)
    for i, name in enumerate(TARGET_NAMES):
        lo, hi = TARGET_RANGES[name]
        result[:, i] = np.clip(result[:, i], lo, hi)
    return result


def _compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Compute per-field accuracy, rare-class accuracy, and MAE."""
    metrics: dict = {}

    for i, name in enumerate(TARGET_NAMES):
        true_col = y_true[:, i].astype(int)
        pred_col = y_pred[:, i].astype(int)

        # Per-field accuracy
        accuracy = np.mean(true_col == pred_col)
        metrics[f"{name}_accuracy"] = round(float(accuracy), 4)

        # MAE
        mae = np.mean(np.abs(true_col - pred_col))
        metrics[f"{name}_mae"] = round(float(mae), 4)

        # Rare-class accuracy (classes that appear <5% of the time)
        lo, hi = TARGET_RANGES[name]
        for cls_val in range(lo, hi + 1):
            mask = true_col == cls_val
            count = mask.sum()
            pct = count / len(true_col)
            if 0 < pct < 0.05:
                if count > 0:
                    cls_acc = np.mean(pred_col[mask] == cls_val)
                    metrics[f"{name}_rare_class_{cls_val}_accuracy"] = round(float(cls_acc), 4)
                    metrics[f"{name}_rare_class_{cls_val}_count"] = int(count)

    return metrics


def save_model(model: MultiOutputRegressor, path: str) -> None:
    """Save model to disk."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)


def main():
    """CLI entry point for training."""
    import argparse
    parser = argparse.ArgumentParser(description="Train cognitive state predictor")
    parser.add_argument("--data", type=str, default="data/trajectories_10k.jsonl")
    parser.add_argument("--output", type=str, default="models/cognitive_predictor_v1.joblib")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    print("Loading trajectories...")
    trajectories = load_trajectories(args.data)
    print(f"Loaded {len(trajectories)} trajectories")

    print("Preparing dataset...")
    X, y = prepare_dataset(trajectories)
    print(f"Dataset: {X.shape[0]} samples, {X.shape[1]} features")

    print("Training model...")
    model, metrics = train_model(X, y, seed=args.seed)

    print("Saving model...")
    save_model(model, args.output)

    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
