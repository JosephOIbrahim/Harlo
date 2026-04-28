"""Write-through sync strategy.

Synchronous persistence: caller blocks until the .usda file is written.
Best for low-write-rate, consistency-critical prims (SessionPrim,
GateStatusPrim, MerkleRootPrim, MotorPrim per D4).

This module imports `harlo.usd_lite.persistence` lazily inside its
function body so importing `harlo.sync` does not require the
[substrate] extra. Constitution Law 3.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from harlo.usd_lite.stage import BrainStage


def persist(stage: "BrainStage", target_path: str) -> None:
    """Synchronously write `stage` to `target_path` via the persistence
    layer.

    Currently writes the entire stage (no per-prim partial-write
    optimization). Future surgery may narrow to subtree writes once
    the persistence layer supports them.
    """
    # Lazy import so importing this module does not require [substrate].
    from harlo.usd_lite.persistence import write
    write(stage, target_path)


def persist_prim(stage: "BrainStage", prim_path: str, target_path: str) -> None:
    """Persist after a mutation affecting `prim_path`.

    Today this is equivalent to `persist(stage, target_path)` — the
    `prim_path` argument is recorded for future per-subtree write
    optimization but otherwise unused.
    """
    # Argument is recorded for future use; currently full-stage write.
    _ = prim_path
    persist(stage, target_path)
