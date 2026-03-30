"""Engine configuration for Sprint 3 CognitiveEngine."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

ENGINE_ENABLED = True
OBSERVATION_LOGGING = True
PREDICTION_ENABLED = True
BUFFER_DB_PATH = str(PROJECT_ROOT / "data" / "observations.db")
MODEL_PATH = str(PROJECT_ROOT / "models" / "cognitive_predictor_v1.joblib")
OBSERVATION_DIR = str(PROJECT_ROOT / "data" / "observations")
