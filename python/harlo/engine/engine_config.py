"""Engine configuration for CognitiveEngine.

D56/D81 (CTO review): harlo.daemon.config is the single path authority.
The pre-promotion src/engine_config.py defaulted STAGE_DIR/BUFFER_DB_PATH/
MODEL_PATH into the repo tree, so installed runs wrote state into the
source checkout. All state now lives under DATA_DIR (platform-aware:
~/Library/Application Support/Harlo on installed macOS), with env
overrides for tests/dev and a source-checkout fallback for the trained
predictor model (which ships via git-lfs in the repo, not in wheels).
"""

import os
from pathlib import Path

from harlo.daemon.config import DATA_DIR

# Source-checkout root — resolves to the repo root when running from a
# git checkout (python/harlo/engine/ → up 3). Inside site-packages this
# points somewhere meaningless; the pyproject.toml guard below keeps the
# fallback from ever firing there.
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Master kill switch — False = pre-Sprint 3 behavior
ENGINE_ENABLED = os.environ.get("ENGINE_ENABLED", "1") == "1"

# Component toggles (each can be disabled independently)
OBSERVATION_LOGGING = os.environ.get("OBSERVATION_LOGGING", "1") == "1"
PREDICTION_ENABLED = os.environ.get("PREDICTION_ENABLED", "1") == "1"
GRACEFUL_FALLBACK = True

# Sprint 4: Toggle between real USD and dict mock.
# True by default (Commandment 3). Falls back to mock if pxr unavailable.
USE_REAL_USD = os.environ.get("USE_REAL_USD", "1") == "1"


def _default_model_path() -> str:
    """Resolve the predictor model: env override → source tree → DATA_DIR.

    Source-checkout takes precedence over DATA_DIR so a freshly
    retrained repo model is never shadowed by a stale installed copy;
    installed machines have no source checkout, so they resolve to
    DATA_DIR. The model is git-lfs (385 KB) and not packaged in wheels;
    predictor init degrades gracefully (predictor=None) when absent.
    """
    env = os.environ.get("HARLO_MODEL_PATH")
    if env:
        return env
    src_model = PROJECT_ROOT / "models" / "cognitive_predictor_v1.joblib"
    if (PROJECT_ROOT / "pyproject.toml").exists() and src_model.exists():
        return str(src_model)
    data_model = DATA_DIR / "models" / "cognitive_predictor_v1.joblib"
    if data_model.exists():
        return str(data_model)
    # Canonical install location, even when absent — predictor degrades.
    return str(data_model)


# Paths — DATA_DIR-rooted (D81), env-overridable.
STAGE_DIR = os.environ.get("HARLO_STAGE_DIR", str(DATA_DIR / "stages"))
BUFFER_DB_PATH = os.environ.get("HARLO_BUFFER_DB", str(DATA_DIR / "observations.db"))
MODEL_PATH = _default_model_path()
OBSERVATION_DIR = str(DATA_DIR / "observations")

# Logging
LOG_LEVEL = os.environ.get("COGTWIN_LOG_LEVEL", "INFO")
