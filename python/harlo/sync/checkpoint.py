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

        The dirty set is **snapshotted before** the write so that:

        * a concurrent ``mark_dirty`` arriving while the write is in
          flight is preserved (it stays in ``self._dirty`` and will be
          flushed on the next call), closing the TOCTOU window between
          the dirty check and the clear; and

        * a failing ``write()`` does **not** discard the dirty record —
          the snapshotted paths remain dirty for the caller to retry.
        """
        if not self._dirty:
            return False
        # Lazy import so module import doesn't require [substrate].
        from harlo.usd_lite.persistence import write

        snapshot = set(self._dirty)
        try:
            write(stage, target_path)
        except Exception:
            # The dirty record is the only ledger of "what needs persisting";
            # do NOT clear it on a failed write or the mutations are lost.
            logger.exception(
                "Checkpoint.flush failed; preserving %d dirty paths for retry",
                len(snapshot),
            )
            raise
        # Clear only the paths we actually attempted to persist.  Paths
        # marked dirty after the snapshot are kept for the next flush.
        self._dirty -= snapshot
        return True

    def clear(self) -> None:
        """Drop all dirty markings without flushing. Use with care —
        intended for tests and explicit aborts."""
        self._dirty.clear()


# Module-level default Checkpoint for callers that don't need to
# manage their own. Per-process, not per-thread.
default_checkpoint: Checkpoint = Checkpoint()
