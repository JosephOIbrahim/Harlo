"""First Real Session — 10-exchange simulated production session.

Verifies everything works end-to-end with the CognitiveEngine.
This is the Sprint 5 acceptance test.
"""

from __future__ import annotations

import json
import os
import sys

# Ensure src/ is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cognitive_engine import CognitiveEngine


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
