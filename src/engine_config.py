"""Engine configuration for CognitiveEngine — Sprint 5 production."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

# Master kill switch — False = pre-Sprint 3 behavior
ENGINE_ENABLED = os.environ.get("ENGINE_ENABLED", "1") == "1"

# Component toggles (each can be disabled independently)
OBSERVATION_LOGGING = os.environ.get("OBSERVATION_LOGGING", "1") == "1"
PREDICTION_ENABLED = os.environ.get("PREDICTION_ENABLED", "1") == "1"
GRACEFUL_FALLBACK = True

# Sprint 4: Toggle between real USD and dict mock.
# True by default (Commandment 3). Falls back to mock if pxr unavailable.
USE_REAL_USD = os.environ.get("USE_REAL_USD", "1") == "1"

# Paths
STAGE_DIR = str(PROJECT_ROOT / "data" / "stages")
BUFFER_DB_PATH = str(PROJECT_ROOT / "data" / "observations.db")
MODEL_PATH = str(PROJECT_ROOT / "models" / "cognitive_predictor_v1.joblib")
OBSERVATION_DIR = str(PROJECT_ROOT / "data" / "observations")

# Logging
LOG_LEVEL = os.environ.get("COGTWIN_LOG_LEVEL", "INFO")
