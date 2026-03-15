"""Config loading for the Cognitive Twin daemon."""

import os
from pathlib import Path

# Project root detection
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Data paths
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "twin.db"
SOCKET_PATH = DATA_DIR / "twind.sock"
AUDIT_LOG = DATA_DIR / "audit.log"
STAGES_DIR = DATA_DIR / "stages"
DEFERRED_DIR = DATA_DIR / "deferred_verifications"
TEMP_DIR = Path(os.environ.get("TMPDIR", "/dev/shm" if os.name != "nt" else os.environ.get("TEMP", ".")))

# Config paths
CONFIG_DIR = PROJECT_ROOT / "config"
PROFILE_PATH = CONFIG_DIR / "default_profile.yaml"
BARRIER_SCHEMA_PATH = CONFIG_DIR / "barrier_schema.json"
DEPTH_CONFIG_PATH = CONFIG_DIR / "verification_depth.yaml"

# Performance targets
COLD_START_MS = 50
HOT_RECALL_MS = 2
CLI_RELEASE_MS = 50
TEARDOWN_PREEMPT_MS = 10
DMN_BUDGET_S = 30

# Decay defaults
DEFAULT_LAMBDA = 0.05
DEFAULT_EPSILON = 0.01

# Encoder type: "lexical" (default, Rust hot path) or "semantic" (BGE + LSH)
ENCODER_TYPE = os.environ.get("TWIN_ENCODER_TYPE", "lexical")

# Session timeout in seconds (default 1800 = 30 minutes)
SESSION_TIMEOUT_S = int(os.environ.get("TWIN_SESSION_TIMEOUT", "1800"))

# Daemon settings
PID_FILE = DATA_DIR / "twind.pid"
DAEMON_IDLE_TIMEOUT_S = 30  # Exit after this many seconds idle (Rule 1)


def ensure_data_dirs():
    """Create data directories if they don't exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STAGES_DIR.mkdir(parents=True, exist_ok=True)
    DEFERRED_DIR.mkdir(parents=True, exist_ok=True)
