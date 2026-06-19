"""Config loading for the Harlo daemon.

Resolves data and config paths in a platform-aware way:

- macOS installed (bundled in Harlo.app or HARLO_DATA_DIR set):
  user state under ~/Library/Application Support/Harlo/.
- Linux installed (HARLO_DATA_DIR set):
  honors XDG_DATA_HOME or HARLO_DATA_DIR.
- Dev mode (running from source tree, no env var):
  PROJECT_ROOT/data — preserves legacy behavior so contributors
  don't need to configure anything.

Config files (schemas, default profile) stay co-located with the
source / app bundle — they ship with the code, not the user state.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


def _detect_data_dir() -> Path:
    """Resolve the per-user data directory.

    Order:
      1. HARLO_DATA_DIR env override (any platform).
      2. macOS: ~/Library/Application Support/Harlo
      3. Linux: $XDG_DATA_HOME/harlo or ~/.local/share/harlo
      4. Dev fallback: PROJECT_ROOT/data (only if it exists — i.e.
         we're running from source).
      5. Otherwise: best-effort platform default (will be created).
    """
    override = os.environ.get("HARLO_DATA_DIR")
    if override:
        return Path(override).expanduser()

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Harlo"

    if sys.platform.startswith("linux"):
        xdg = os.environ.get("XDG_DATA_HOME")
        if xdg:
            return Path(xdg).expanduser() / "harlo"
        legacy = PROJECT_ROOT / "data"
        if legacy.exists():
            return legacy
        return Path.home() / ".local" / "share" / "harlo"

    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "Harlo"

    return PROJECT_ROOT / "data"


DATA_DIR = _detect_data_dir()
DB_PATH = DATA_DIR / "twin.db"
# HARLO_SOCKET_PATH lets the command socket live OUTSIDE DATA_DIR — specifically
# in the App Group container shared with the sandboxed HarloHealthBridge, the one
# path both the sandboxed bridge and the (non-sandboxed) daemon can reach
# (ADR-0001 Phase 5B). twin.db and all other state stay in DATA_DIR.
SOCKET_PATH = (
    Path(os.environ["HARLO_SOCKET_PATH"]).expanduser()
    if os.environ.get("HARLO_SOCKET_PATH")
    else DATA_DIR / "twind.sock"
)
AUDIT_LOG = DATA_DIR / "audit.log"
STAGES_DIR = DATA_DIR / "stages"
DEFERRED_DIR = DATA_DIR / "deferred_verifications"
REFLEX_DIR = DATA_DIR / "reflexes"
HEALTHKIT_ANCHOR_PATH = DATA_DIR / "healthkit_anchor.bin"
AGENTS_DIR = DATA_DIR / "agents"
AGENTS_QUEUE_DIR = AGENTS_DIR / "queue"
AGENTS_OUTPUTS_DIR = AGENTS_DIR / "outputs"
TEMP_DIR = Path(os.environ.get("TMPDIR", "/dev/shm" if os.name != "nt" else os.environ.get("TEMP", ".")))

CONFIG_DIR = PROJECT_ROOT / "config"
PROFILE_PATH = CONFIG_DIR / "default_profile.yaml"
BARRIER_SCHEMA_PATH = CONFIG_DIR / "barrier_schema.json"
DEPTH_CONFIG_PATH = CONFIG_DIR / "verification_depth.yaml"
INTAKE_FORM_SCHEMA_PATH = CONFIG_DIR / "intake_form_schema.json"
BIOMETRIC_SAMPLE_SCHEMA_PATH = CONFIG_DIR / "biometric_sample_schema.json"

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
    REFLEX_DIR.mkdir(parents=True, exist_ok=True)
    AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    AGENTS_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    AGENTS_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
