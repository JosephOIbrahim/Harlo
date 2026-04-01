"""Merkle hash computation over /Association/Traces subtree.

Computes a deterministic Merkle root over base traces (not effective SDRs
with Hebbian masks).  This ensures Hebbian learning does not trigger
false-positive corruption detection (Patch 4).
"""

from __future__ import annotations

import hashlib

from ..composition.merkle import MerkleTree
from ..usd_lite.hex_sdr import sdr_to_hex
from ..usd_lite.prims import TracePrim


def _trace_leaf_hash(trace: TracePrim) -> str:
    """Compute a deterministic leaf hash for a single trace.

    Uses base SDR only (not effective SDR with Hebbian masks).
    Hash input: trace_id + content_hash + sdr_hex.
    """
    sdr_hex = sdr_to_hex(trace.sdr)
    raw = f"{trace.trace_id}:{trace.content_hash}:{sdr_hex}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compute_trace_merkle(traces: dict[str, TracePrim]) -> str:
    """Compute Merkle hash over /Association/Traces subtree.

    1. Sort traces by trace_id (deterministic order)
    2. Hash each trace using base SDR only
    3. Build Merkle tree from leaf hashes
    4. Return root hash

    Empty traces → SHA256 of empty string (consistent with MerkleTree).
    """
    if not traces:
        return hashlib.sha256(b"").hexdigest()

    sorted_ids = sorted(traces.keys())
    leaf_hashes = [_trace_leaf_hash(traces[tid]) for tid in sorted_ids]
    tree = MerkleTree(leaf_hashes)
    return tree.get_root()
