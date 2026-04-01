"""Health check — print CognitiveEngine status."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cognitive_engine import CognitiveEngine

engine = CognitiveEngine()
print(json.dumps(engine.get_health(), indent=2))
engine.close()
