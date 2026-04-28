"""Path C migration — USD-Lite text format → real OpenUSD format.

Read-tolerant on input (handles both old and new formats).
Idempotent (running on the new format is a no-op).

Usage:
    python -m harlo.migrate_path_c INPUT [--output OUTPUT] [--dry-run] [--report REPORT_JSON]

Exit codes:
    0  success (including no-op)
    1  input format unrecognized
    2  parse error
    3  write error
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class MigrationReport:
    """Report produced by `migrate()`."""
    input_path: str = ""
    output_path: str = ""
    input_format: str = "unknown"  # "old" | "new" | "unknown"
    prims_migrated: dict[str, int] = field(default_factory=dict)
    codec_conversions: int = 0
    dry_run: bool = False
    error: Optional[str] = None
    exit_code: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def _detect_format(input_path: str) -> str:
    """Return 'old' | 'new' | 'unknown' based on file content.

    Strategy:
      1. If pxr is importable and the file opens as a real USD stage
         AND has a typed BrainStage prim with Harlo-namespaced attrs,
         it's the new format.
      2. Else, if the file starts with the old USD-Lite signature
         (`#usda 1.0` followed by `def BrainStage "Brain"` and at
         least one `def TracePrim`/`def AssociationPrim` declaration),
         it's the old format.
      3. Else, unknown.
    """
    p = Path(input_path)
    if not p.exists():
        return "unknown"

    # Try pxr-based detection first (new format)
    try:
        from pxr import Usd
        stage = Usd.Stage.Open(str(p))
        if stage is not None:
            brain = stage.GetPrimAtPath("/Brain")
            if brain.IsValid() and brain.GetTypeName() == "BrainStage":
                # New format if the typed BrainStage exists.
                return "new"
    except ImportError:
        pass
    except Exception:
        # Real-USD parser may reject; fall through to old-format check.
        pass

    # Old-format detection: text-pattern matching.
    try:
        text = p.read_text(encoding="utf-8")
    except Exception:
        return "unknown"

    lines = text.splitlines()
    if not lines or not lines[0].startswith("#usda"):
        return "unknown"

    # Old format has `def BrainStage "Brain"` and `*Prim` typeNames
    # not present in real USD (only in USD-Lite emitter output).
    has_brain = any('def BrainStage "Brain"' in ln for ln in lines)
    has_prim_types = any(
        ln.lstrip().startswith(("def TracePrim ", "def AssociationPrim ",
                                 "def CompositionPrim ", "def ElenchusPrim "))
        for ln in lines
    )
    if has_brain and has_prim_types:
        return "old"

    return "unknown"


def _count_prims(stage) -> dict[str, int]:
    """Count prims by typeName in a BrainStage object."""
    counts: dict[str, int] = {}

    def bump(name: str, n: int = 1) -> None:
        counts[name] = counts.get(name, 0) + n

    bump("BrainStage", 1)
    bump("AssociationPrim", 1)
    bump("TracePrim", len(stage.association.traces))
    bump("CompositionPrim", 1)
    bump("CompositionLayerPrim", len(stage.composition.layers))
    # Provenance count: layers with non-None provenance
    prov = sum(1 for L in stage.composition.layers.values() if L.provenance is not None)
    if prov:
        bump("Provenance", prov)
    bump("ElenchusPrim", 1)
    if stage.elenchus.gate_status is not None:
        bump("GateStatusPrim", 1)
    if stage.elenchus.merkle_root is not None:
        bump("MerkleRootPrim", 1)
    if stage.session is not None:
        bump("SessionPrim", 1)
    bump("InquiryContainerPrim", 1)
    bump("InquiryPrim", len(stage.inquiry.active))
    bump("MotorContainerPrim", 1)
    bump("MotorPrim", len(stage.motor.pending))
    bump("SkillsContainerPrim", 1)
    bump("SkillPrim", len(stage.skills.domains))
    bump("CognitiveProfilePrim", 1)
    bump("MultipliersPrim", 1)
    bump("IntakeHistoryPrim", 1)
    return counts


def _count_codec_conversions(stage) -> int:
    """Count codec-blocker conversions performed during migration.

    Each TracePrim contributes 5 (sdr + 2 hebbian masks + co_acts +
    competitions). Each CompositionLayerPrim contributes 1 (opinion).
    IntakeHistoryPrim contributes 1 (answer_embeddings).
    """
    n = 0
    n += 5 * len(stage.association.traces)
    n += len(stage.composition.layers)
    n += 1  # IntakeHistoryPrim's answer_embeddings
    return n


def migrate(
    input_path: str,
    output_path: Optional[str] = None,
    dry_run: bool = False,
) -> MigrationReport:
    """Migrate a USD-Lite file to real-USD format.

    See module docstring for details.
    """
    report = MigrationReport(
        input_path=input_path,
        output_path=output_path or (input_path + ".migrated.usda"),
        dry_run=dry_run,
    )

    fmt = _detect_format(input_path)
    report.input_format = fmt

    if fmt == "unknown":
        report.error = (
            f"Input format unrecognized at {input_path!r}. "
            "Expected old USD-Lite (#usda 1.0 + def BrainStage + def TracePrim) "
            "or new real-USD (typed BrainStage at /Brain)."
        )
        report.exit_code = 1
        return report

    if fmt == "new":
        # Idempotent: already migrated. Don't touch output_path.
        return report

    # Old format → migrate
    try:
        from .usd_lite.serializer import parse
        text = Path(input_path).read_text(encoding="utf-8")
        stage_obj = parse(text)
    except Exception as exc:
        report.error = f"parse error: {exc}"
        report.exit_code = 2
        return report

    report.prims_migrated = _count_prims(stage_obj)
    report.codec_conversions = _count_codec_conversions(stage_obj)

    if dry_run:
        return report

    try:
        from .usd_lite.persistence import write
        write(stage_obj, report.output_path)
    except Exception as exc:
        report.error = f"write error: {exc}"
        report.exit_code = 3
        return report

    return report


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="harlo.migrate_path_c",
        description="Migrate USD-Lite .usda files to real-USD Path C format.",
    )
    parser.add_argument("input", help="Path to input .usda file (old or new format)")
    parser.add_argument("--output", default=None,
                        help="Path to write the new-format file (default: <input>.migrated.usda)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Detect format and count prims; do not write output")
    parser.add_argument("--report", default=None,
                        help="Write the MigrationReport as JSON to this path")
    args = parser.parse_args(argv)

    report = migrate(args.input, args.output, args.dry_run)

    # Emit report to stdout (human-readable) and optional JSON file
    print(f"input:  {report.input_path}")
    print(f"format: {report.input_format}")
    if report.input_format == "new":
        print("no-op: already migrated")
    elif report.input_format == "old":
        print(f"output: {report.output_path}{'  (dry-run)' if report.dry_run else ''}")
        total_prims = sum(report.prims_migrated.values())
        print(f"prims migrated: {total_prims}")
        for tn, n in sorted(report.prims_migrated.items()):
            print(f"  {tn}: {n}")
        print(f"codec conversions: {report.codec_conversions}")
    if report.error:
        print(f"ERROR: {report.error}", file=sys.stderr)

    if args.report:
        Path(args.report).write_text(json.dumps(report.to_dict(), indent=2))

    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
