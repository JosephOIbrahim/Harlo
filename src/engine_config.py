"""Engine configuration for CognitiveEngine."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

ENGINE_ENABLED = True
OBSERVATION_LOGGING = True
PREDICTION_ENABLED = True
BUFFER_DB_PATH = str(PROJECT_ROOT / "data" / "observations.db")
MODEL_PATH = str(PROJECT_ROOT / "models" / "cognitive_predictor_v1.joblib")
OBSERVATION_DIR = str(PROJECT_ROOT / "data" / "observations")
STAGE_DIR = str(PROJECT_ROOT / "data" / "stages")

# Sprint 4: Toggle between real USD stage and dict mock.
# Set USE_REAL_USD=1 env var or change default here.
# Requires Python 3.12 + USD 26.03 built at C:\USD\26.03-exec.
USE_REAL_USD = os.environ.get("USE_REAL_USD", "0") == "1"
