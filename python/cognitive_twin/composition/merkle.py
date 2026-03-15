"""Merkle Tree with O(log n) partial updates.

Rule 6: Composition stages use Merkle Tree hashing.
Partial branch O(log n). Not full-file SHA256 O(n).
"""

from __future__ import annotations

import hashlib
import math


def _sha256(data: str) -> str:
    """SHA-256 hash of a string, returned as hex digest."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _combine(left: str, right: str) -> str:
    """Hash two child hashes into a parent hash."""
    return _sha256(left + right)


class MerkleTree:
    """Merkle tree stored as a flat array with O(log n) partial updates.

    Internal representation: a complete binary tree stored in a 1-indexed
    array where node 1 is the root, and for node i the children are 2i
    and 2i+1.  Leaf nodes start at index `self._leaf_offset`.
    """

    def __init__(self, leaves: list[str] | None = None) -> None:
        if leaves is None:
            leaves = []
        self._leaf_count = len(leaves)
        if self._leaf_count == 0:
            self._size = 0
            self._leaf_offset = 0
            self._nodes: list[str] = []
            return
        # Round up to next power of 2 for a complete binary tree.
        self._capacity = 1 << math.ceil(math.log2(self._leaf_count)) if self._leaf_count > 1 else 1
        self._size = 2 * self._capacity  # total nodes (1-indexed, index 0 unused)
        self._leaf_offset = self._capacity  # first leaf index
        self._nodes = [""] * self._size
        # Place leaves.
        for i, leaf in enumerate(leaves):
            self._nodes[self._leaf_offset + i] = leaf
        # Fill unused leaf slots with empty hash.
        empty = _sha256("")
        for i in range(self._leaf_count, self._capacity):
            self._nodes[self._leaf_offset + i] = empty
        # Build tree bottom-up.
        for i in range(self._leaf_offset - 1, 0, -1):
            self._nodes[i] = _combine(self._nodes[2 * i], self._nodes[2 * i + 1])

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_root(self) -> str:
        """Return the Merkle root hash."""
        if self._size == 0:
            return _sha256("")
        return self._nodes[1]

    def update_leaf(self, index: int, new_hash: str) -> str:
        """Update a single leaf and recompute only the affected branch.

        Runs in O(log n) time — only the path from the leaf to the root
        is recomputed, not the entire tree.
        """
        if index < 0 or index >= self._leaf_count:
            raise IndexError(f"Leaf index {index} out of range [0, {self._leaf_count})")
        pos = self._leaf_offset + index
        self._nodes[pos] = new_hash
        # Walk up to root, recomputing parents.
        pos //= 2
        while pos >= 1:
            self._nodes[pos] = _combine(self._nodes[2 * pos], self._nodes[2 * pos + 1])
            pos //= 2
        return self._nodes[1]

    def get_proof(self, index: int) -> list[tuple[str, str]]:
        """Return a Merkle proof (audit path) for the leaf at *index*.

        Each element is (sibling_hash, side) where side is 'L' or 'R'
        indicating which side the sibling is on.
        """
        if index < 0 or index >= self._leaf_count:
            raise IndexError(f"Leaf index {index} out of range [0, {self._leaf_count})")
        proof: list[tuple[str, str]] = []
        pos = self._leaf_offset + index
        while pos > 1:
            if pos % 2 == 0:
                sibling = self._nodes[pos + 1]
                proof.append((sibling, "R"))
            else:
                sibling = self._nodes[pos - 1]
                proof.append((sibling, "L"))
            pos //= 2
        return proof

    @staticmethod
    def verify_proof(leaf_hash: str, proof: list[tuple[str, str]], root: str) -> bool:
        """Verify a Merkle proof against a known root hash."""
        current = leaf_hash
        for sibling_hash, side in proof:
            if side == "R":
                current = _combine(current, sibling_hash)
            else:
                current = _combine(sibling_hash, current)
        return current == root

    @property
    def leaf_count(self) -> int:
        return self._leaf_count
