"""Health check — print CognitiveEngine status."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "python"))

import tempfile as _tf
_sandbox = _tf.mkdtemp(prefix="harlo-script-")
os.environ.setdefault("HARLO_STAGE_DIR", os.path.join(_sandbox, "stages"))
os.environ.setdefault("HARLO_BUFFER_DB", os.path.join(_sandbox, "observations.db"))

from harlo.engine.cognitive_engine import CognitiveEngine

engine = CognitiveEngine()
print(json.dumps(engine.get_health(), indent=2))
engine.close()
