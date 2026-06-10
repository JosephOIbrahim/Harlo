#!/usr/bin/env python
"""Pin /schedule/ for an experiment window via a sublayer at position 0.

USD subLayers are STRONGEST-FIRST: inserting the experiment layer at
position 0 — ahead of schedule.usda — makes its /schedule/ opinions win
composition. The live read path (cognitive_stage -> load_schedule_from_stage)
reads the composed stage, so the pin takes effect without touching
composition/resolver.py or usd_lite/composer.py (neither is imported here,
and neither runs on the schedule path).

Creates experiment_schedule.usda (an empty `over "schedule"` for the
operator to author pin values into) if absent, inserts it, saves, and
verifies by re-opening the stage and checking the layer stack.

Teardown: unpin_schedule.py.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

EXPERIMENT_LAYER = "experiment_schedule.usda"


def default_stage_dir() -> Path:
    root = os.environ.get(
        "HARLO_DATA_DIR", str(Path.home() / "Library/Application Support/Harlo")
    )
    return Path(root) / "stages"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--stage-dir",
        type=Path,
        default=default_stage_dir(),
        help="stage directory containing harlo.usda (default: DATA_ROOT/stages)",
    )
    args = ap.parse_args()

    try:
        from pxr import Sdf, Usd
    except ImportError:
        print("FAILED: pxr (OpenUSD) not importable in this venv", file=sys.stderr)
        return 1

    root_path = args.stage_dir / "harlo.usda"
    if not root_path.exists():
        print(f"FAILED: no harlo.usda at {args.stage_dir}", file=sys.stderr)
        return 1
    exp_path = args.stage_dir / EXPERIMENT_LAYER

    # Create the experiment layer if absent: a bare `over "schedule"` the
    # operator authors pin values into. An over with no opinions composes
    # as a no-op, so pinning before authoring is safe.
    if not exp_path.exists():
        layer = Sdf.Layer.CreateNew(str(exp_path))
        prim = Sdf.PrimSpec(layer, "schedule", Sdf.SpecifierOver)
        layer.comment = (
            "memory-uplift experiment pin layer - author /schedule/ "
            "overrides here; remove via unpin_schedule.py"
        )
        del prim  # held by the layer; named var only for clarity
        layer.Save()
        print(f"created {exp_path}")

    root_layer = Sdf.Layer.FindOrOpen(str(root_path))
    if root_layer is None:
        print(f"FAILED: could not open {root_path}", file=sys.stderr)
        return 1

    paths = list(root_layer.subLayerPaths)
    target = str(exp_path)
    if target in paths:
        if paths.index(target) == 0:
            print("already pinned at position 0 (idempotent no-op)")
        else:
            paths.remove(target)
            paths.insert(0, target)
            root_layer.subLayerPaths = paths
            root_layer.Save()
            print("re-pinned to position 0")
    else:
        paths.insert(0, target)
        root_layer.subLayerPaths = paths
        root_layer.Save()
        print("pinned at position 0")

    # ---- read-back verification on a fresh stage ----------------------
    stage = Usd.Stage.Open(str(root_path))
    if stage is None:
        print("FAILED: stage would not open after pin", file=sys.stderr)
        return 1
    stack_ids = [lyr.identifier for lyr in stage.GetLayerStack()]
    final_paths = list(Sdf.Layer.FindOrOpen(str(root_path)).subLayerPaths)

    ok = True
    if target not in stack_ids:
        print("VERIFY FAILED: experiment layer absent from layer stack", file=sys.stderr)
        ok = False
    if not final_paths or final_paths[0] != target:
        print(f"VERIFY FAILED: position 0 is {final_paths[:1]}, not the experiment layer", file=sys.stderr)
        ok = False
    if not any("schedule.usda" in p and EXPERIMENT_LAYER not in p for p in final_paths):
        print("VERIFY FAILED: schedule.usda missing from subLayerPaths — pin clobbered the stack", file=sys.stderr)
        ok = False
    if not stage.GetPrimAtPath("/schedule"):
        print("VERIFY FAILED: /schedule prim no longer composes", file=sys.stderr)
        ok = False

    if not ok:
        return 1
    print("PINNED + VERIFIED. subLayerPaths (strongest first):")
    for i, p in enumerate(final_paths):
        print(f"  [{i}] {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
