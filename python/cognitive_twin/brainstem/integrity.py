"""Merkle integrity verification for composition stages.

Verifies that a stage's Merkle root hasn't been tampered with
by recomputing from the stored layers and comparing.

Absorbed from bridge/ in Phase 4.
"""

from __future__ import annotations

from ..composition.stage import MerkleStage


def verify_merkle_root(stage_id: str, expected_root: str) -> bool:
    """Verify the Merkle root of a stage hasn't been tampered with.

    Loads the stage from disk, recomputes its Merkle root from
    the constituent layers, and compares against *expected_root*.
    """
    try:
        stage = MerkleStage.load(stage_id)
    except (FileNotFoundError, OSError):
        return False

    actual_root = stage.get_merkle_root()
    return actual_root == expected_root
