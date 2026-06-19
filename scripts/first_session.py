"""First Real Session — 10-exchange simulated production session.

Verifies everything works end-to-end with the CognitiveEngine.
This is the Sprint 5 acceptance test.
"""

from __future__ import annotations

import json
import os
import sys

# Make the in-tree package importable without an install (mirrors
# lint.yml's PYTHONPATH=python); harmless when harlo is installed.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "python"))

# Demo/acceptance script: sandbox engine state so runs never mutate
# the live DATA_DIR (engine paths are DATA_DIR-rooted since D56/D81).
import tempfile as _tf
_sandbox = _tf.mkdtemp(prefix="harlo-script-")
os.environ.setdefault("HARLO_STAGE_DIR", os.path.join(_sandbox, "stages"))
os.environ.setdefault("HARLO_BUFFER_DB", os.path.join(_sandbox, "observations.db"))

from harlo.engine.cognitive_engine import CognitiveEngine


def main():
    print("=== HARLO — FIRST SESSION ===\n")

    # Initialize engine (will use mock if USD unavailable)
    engine = CognitiveEngine()
    print(f"Engine initialized: stage={engine.stage_type}")
    print(f"Health: {json.dumps(engine.get_health(), indent=2)}\n")

    # 10 exchanges simulating a real session
    exchanges = [
        ("twin_coach", {"context": "session_start"}),
        ("twin_store", {"message": "Working on Harlo patent filing"}),
        ("twin_coach", {"context": "architecture_question"}),
        ("twin_coach", {"context": "deep_work"}),
        ("twin_coach", {"context": "deep_work"}),
        ("twin_coach", {"context": "deep_work"}),
        ("twin_store", {"message": "Decided on XGBoost over HMM for prediction"}),
        ("twin_coach", {"context": "energy_check"}),
        ("twin_patterns", {}),
        ("twin_coach", {"context": "session_end"}),
    ]

    for i, (tool, input_data) in enumerate(exchanges):
        print(f"--- Exchange {i+1}: {tool} ---")
        result = engine.process_exchange(tool, input_data, session_id="first-session")
        if result:
            print(f"  delegate: {result['delegate_id']}, expert: {result['expert']}")
            if result.get("prediction"):
                print(f"  prediction: {result['prediction']}")
        else:
            print("  (engine disabled or failed)")

    # Final health check
    print("\n=== VERIFICATION ===")
    health = engine.get_health()
    print(json.dumps(health, indent=2))

    # Assertions
    ok = True
    if health["exchange_index"] != 10:
        print(f"FAIL: Expected 10 exchanges, got {health['exchange_index']}")
        ok = False
    if health["observations_logged"] < 10:
        print(f"FAIL: Expected >=10 observations, got {health['observations_logged']}")
        ok = False
    if health["delegates_registered"] != 2:
        print(f"FAIL: Expected 2 delegates, got {health['delegates_registered']}")
        ok = False

    if ok:
        print("\nFIRST SESSION: ALL CHECKS PASSED")
    else:
        print("\nFIRST SESSION: SOME CHECKS FAILED")
        sys.exit(1)

    engine.close()


if __name__ == "__main__":
    main()
