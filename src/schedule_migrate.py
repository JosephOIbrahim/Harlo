"""Schedule sublayer migration — move /schedule/ off harlo.usda onto schedule.usda.

The daemon authors per-exchange to harlo.usda. Hand-edits to /schedule/ on the
root layer race against that save. Solution: park /schedule/ on a dedicated
sublayer the daemon never authors to.

migrate_inline() is idempotent and callable both from the bootstrap path
(CognitiveStage.__init__) and the standalone CLI (scripts/migrate_schedule_sublayer.py).
"""

from __future__ import annotations

import os
from typing import Optional

from . import usd_bootstrap  # noqa: F401 — ensures pxr is importable

from pxr import Sdf, Usd


def migrate_inline(stage_dir: str, root_layer: Optional["Sdf.Layer"] = None) -> dict:
    """Ensure /schedule/ lives on schedule.usda, not harlo.usda. Idempotent.

    Returns a dict: {"status": str, "migrated": bool, "schedule_path": str?}.

    Cases handled:
    - already_migrated: schedule.usda is wired AND root has no /schedule/ prim
    - migrated (pre-migration): root has /schedule/ → copy to sched, remove from root
    - migrated (no schedule yet): no /schedule/ on root → author empty skeleton
      onto schedule.usda
    - migrated (partial recovery): sched.usda already wired but root still has
      /schedule/ → copy root → sched (sched wins on conflict via overlay), then
      remove from root
    """
    root_path = os.path.join(stage_dir, "harlo.usda")
    sched_path = os.path.join(stage_dir, "schedule.usda")

    if root_layer is None:
        if not os.path.exists(root_path):
            return {"status": "no_root", "migrated": False}
        root_layer = Sdf.Layer.FindOrOpen(root_path)
        if root_layer is None:
            return {"status": "no_root", "migrated": False}

    sched_already_subbed = any(
        os.path.normpath(p) == os.path.normpath(sched_path)
        for p in root_layer.subLayerPaths
    )
    has_root_schedule = root_layer.GetPrimAtPath("/schedule") is not None

    if sched_already_subbed and not has_root_schedule:
        return {
            "status": "already_migrated",
            "migrated": False,
            "schedule_path": sched_path,
        }

    if os.path.exists(sched_path):
        sched_layer = Sdf.Layer.FindOrOpen(sched_path)
    else:
        sched_layer = Sdf.Layer.CreateNew(sched_path)

    if has_root_schedule:
        # Copy /schedule subtree spec-level from root to sched.
        if sched_layer.GetPrimAtPath("/schedule") is not None:
            del sched_layer.pseudoRoot.nameChildren["schedule"]
        Sdf.CopySpec(root_layer, "/schedule", sched_layer, "/schedule")
    elif sched_layer.GetPrimAtPath("/schedule") is None:
        # Fresh skeleton via the existing helper — open sched_layer as a Stage.
        sched_stage = Usd.Stage.Open(sched_layer)
        from .schedule import author_empty_skeleton
        author_empty_skeleton(sched_stage)
        # author_empty_skeleton calls stage.DefinePrim, which authors to root
        # layer of THIS stage = sched_layer.

    if not sched_already_subbed:
        paths = list(root_layer.subLayerPaths)
        paths.insert(0, sched_path)
        root_layer.subLayerPaths = paths

    if has_root_schedule:
        del root_layer.pseudoRoot.nameChildren["schedule"]

    sched_layer.Save()
    root_layer.Save()
    return {"status": "migrated", "migrated": True, "schedule_path": sched_path}
