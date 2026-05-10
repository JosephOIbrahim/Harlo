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

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from harlo.usd_lite.stage import BrainStage

logger = logging.getLogger(__name__)


class Checkpoint:
    """Per-process dirty-set tracker.

    Mark prim paths dirty during a session; `flush()` persists the
    stage when called explicitly. Clears the dirty set on successful
    flush.

    Implementation note: ``_dirty`` is a ``dict[path, generation]`` so a
    ``mark_dirty(path)`` arriving during a ``flush()`` is distinguishable
    from the pre-flush mark of the same path.  Each ``mark_dirty`` bumps
    a monotonic counter and records the path's current generation; flush
    snapshots the counter, runs the write, and clears only entries whose
    generation is ``<= snapshot``.  This closes both the
    different-path-during-write and same-path-during-write TOCTOU windows.
    """

    def __init__(self) -> None:
        self._dirty: dict[str, int] = {}
        self._generation: int = 0

    def mark_dirty(self, prim_path: str) -> None:
        """Record that `prim_path` has been mutated."""
        self._generation += 1
        self._dirty[prim_path] = self._generation

    def is_dirty(self) -> bool:
        """True if any path is marked dirty since the last flush."""
        return bool(self._dirty)

    def dirty_paths(self) -> frozenset[str]:
        """Snapshot of currently-dirty paths (for testing/diagnostics)."""
        return frozenset(self._dirty.keys())

    def flush(self, stage: "BrainStage", target_path: str) -> bool:
        """Persist `stage` to `target_path` if any path is dirty.

        Returns True if a write occurred, False if nothing was dirty.
        Clears the dirty set on success.

        The current generation is snapshotted **before** the write so:

        * a concurrent ``mark_dirty`` (different path OR same path)
          arriving while the write is in flight stamps a generation
          ``> snapshot`` and is preserved for the next flush, closing the
          TOCTOU window between the dirty check and the clear; and

        * a failing ``write()`` does **not** discard the dirty record —
          the entire dirty mapping remains for the caller to retry.
        """
        if not self._dirty:
            return False
        # Lazy import so module import doesn't require [substrate].
        from harlo.usd_lite.persistence import write

        snapshot_gen = self._generation
        try:
            write(stage, target_path)
        except Exception:
            # The dirty record is the only ledger of "what needs persisting";
            # do NOT clear it on a failed write or the mutations are lost.
            logger.exception(
                "Checkpoint.flush failed; preserving %d dirty paths for retry",
                len(self._dirty),
            )
            raise
        # Clear only entries whose generation is at or before the snapshot.
        # Anything stamped during the write keeps a higher generation and
        # survives — even if it is the same path as a pre-flush mark.
        self._dirty = {
            path: gen
            for path, gen in self._dirty.items()
            if gen > snapshot_gen
        }
        return True

    def clear(self) -> None:
        """Drop all dirty markings without flushing. Use with care —
        intended for tests and explicit aborts."""
        self._dirty.clear()


# Module-level default Checkpoint for callers that don't need to
# manage their own. Per-process, not per-thread.
default_checkpoint: Checkpoint = Checkpoint()
