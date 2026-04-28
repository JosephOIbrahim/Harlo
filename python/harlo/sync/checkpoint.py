"""Checkpoint sync strategy.

Deferred persistence: callers mark prim paths dirty during the session;
`flush()` writes the stage explicitly. Best for high-write-rate prims
where per-mutation persistence would dominate cost (TracePrim,
CompositionLayerPrim, SkillPrim, intake/multiplier prims, InquiryPrim
per D4).

This module imports `harlo.usd_lite.persistence` lazily so importing
`harlo.sync` does not require the [substrate] extra.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from harlo.usd_lite.stage import BrainStage


class Checkpoint:
    """Per-process dirty-set tracker.

    Mark prim paths dirty during a session; `flush()` persists the
    stage when called explicitly. Clears the dirty set on successful
    flush.
    """

    def __init__(self) -> None:
        self._dirty: set[str] = set()

    def mark_dirty(self, prim_path: str) -> None:
        """Record that `prim_path` has been mutated."""
        self._dirty.add(prim_path)

    def is_dirty(self) -> bool:
        """True if any path is marked dirty since the last flush."""
        return bool(self._dirty)

    def dirty_paths(self) -> frozenset[str]:
        """Snapshot of currently-dirty paths (for testing/diagnostics)."""
        return frozenset(self._dirty)

    def flush(self, stage: "BrainStage", target_path: str) -> bool:
        """Persist `stage` to `target_path` if any path is dirty.

        Returns True if a write occurred, False if nothing was dirty.
        Clears the dirty set on success.
        """
        if not self._dirty:
            return False
        # Lazy import so module import doesn't require [substrate].
        from harlo.usd_lite.persistence import write
        write(stage, target_path)
        self._dirty.clear()
        return True

    def clear(self) -> None:
        """Drop all dirty markings without flushing. Use with care —
        intended for tests and explicit aborts."""
        self._dirty.clear()


# Module-level default Checkpoint for callers that don't need to
# manage their own. Per-process, not per-thread.
default_checkpoint: Checkpoint = Checkpoint()
