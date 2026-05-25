"""PVH command-line entry point.

Runs the full read-only pipeline: extract trajectories -> evaluate -> emit
artifacts (pvh_metrics.json + evidence_artifact.md).

    python -m harness.path_d.pvh.cli --output harness/path_d/pvh/outputs/run_001/

Read-only on data/ and models/ (Article 1). v1 scope per D35/D39.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.predict import CognitivePredictor

from .evaluators import evaluate_session
from .extractor import iter_sessions
from .reporters import write_evidence_artifact, write_pvh_metrics


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pvh",
        description="Predictive Validation Harness (read-only methodology validator, v1).",
    )
    parser.add_argument("--db", default="data/observations.db",
                        help="Observation database (read-only).")
    parser.add_argument("--model", default="models/cognitive_predictor_v1.joblib",
                        help="Reference predictor (read-only).")
    parser.add_argument("--output", default="harness/path_d/pvh/outputs/run_001/",
                        help="Directory for emitted artifacts.")
    parser.add_argument("--no-predictor", action="store_true",
                        help="Skip model load (predicted fields stay null).")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)

    predictor = None if args.no_predictor else CognitivePredictor(args.model)

    sessions = list(iter_sessions(args.db, predictor=predictor))
    results = [evaluate_session(s) for s in sessions]

    metrics_path = outdir / "pvh_metrics.json"
    artifact_path = outdir / "evidence_artifact.md"
    write_pvh_metrics(results, metrics_path)
    write_evidence_artifact(results, artifact_path)

    total_windows = sum(len(r.drift_rows) for r in results)
    print(f"PVH v1: {len(results)} session(s), {total_windows} window(s)")
    print(f"  metrics:  {metrics_path}")
    print(f"  evidence: {artifact_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
