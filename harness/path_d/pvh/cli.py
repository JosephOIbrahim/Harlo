"""PVH command-line entry point.

Phase 0 stub. Real implementation lands in Phase 5 (integration), per
harness/path_d/03_HANDOFF.md. Entry point: `python -m harness.path_d.pvh.cli`.
"""

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pvh",
        description="Predictive Validation Harness (read-only analytic harness).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="harness/path_d/pvh/outputs/run_001/",
        help="Directory for emitted artifacts (pvh_metrics.json, evidence_artifact.md).",
    )
    return parser


def main(argv=None):
    raise NotImplementedError("PVH CLI is a Phase 0 stub; implemented in Phase 5.")


if __name__ == "__main__":
    main()
