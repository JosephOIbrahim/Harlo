#!/usr/bin/env python
"""Teardown for pin_schedule.py: remove the experiment sublayer from
harlo.usda's subLayerPaths and verify by stage read-back.

The experiment_schedule.usda FILE is left on disk (it is an experiment
artifact); only its composition arc is removed. Does not touch
composition/resolver.py or usd_lite/composer.py.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pin_schedule import EXPERIMENT_LAYER, default_stage_dir


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage-dir", type=Path, default=default_stage_dir())
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
    target = str(args.stage_dir / EXPERIMENT_LAYER)

    root_layer = Sdf.Layer.FindOrOpen(str(root_path))
    if root_layer is None:
        print(f"FAILED: could not open {root_path}", file=sys.stderr)
        return 1

    paths = list(root_layer.subLayerPaths)
    if target not in paths:
        print("not pinned (idempotent no-op)")
    else:
        paths.remove(target)
        root_layer.subLayerPaths = paths
        root_layer.Save()
        print("unpinned")

    # ---- read-back verification ----------------------------------------
    stage = Usd.Stage.Open(str(root_path))
    if stage is None:
        print("FAILED: stage would not open after unpin", file=sys.stderr)
        return 1
    stack_ids = [lyr.identifier for lyr in stage.GetLayerStack()]
    final_paths = list(Sdf.Layer.FindOrOpen(str(root_path)).subLayerPaths)

    ok = True
    if target in stack_ids or target in final_paths:
        print("VERIFY FAILED: experiment layer still in the stack", file=sys.stderr)
        ok = False
    if not any("schedule.usda" in p for p in final_paths):
        print("VERIFY FAILED: schedule.usda missing from subLayerPaths", file=sys.stderr)
        ok = False
    if not stage.GetPrimAtPath("/schedule"):
        print("VERIFY FAILED: /schedule prim no longer composes", file=sys.stderr)
        ok = False

    if not ok:
        return 1
    print("UNPINNED + VERIFIED. subLayerPaths (strongest first):")
    for i, p in enumerate(final_paths):
        print(f"  [{i}] {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
