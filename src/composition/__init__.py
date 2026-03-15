"""Composition Engine — Merkle-backed LIVRPS layer resolution."""

from .merkle import MerkleTree
from .layer import ArcType, Layer
from .stage import MerkleStage
from .resolver import Resolution, resolve
from .conflicts import Conflict, detect_conflicts
from .audit import log_resolution, read_audit, read_audit_for_stage

__all__ = [
    "MerkleTree",
    "ArcType",
    "Layer",
    "MerkleStage",
    "Resolution",
    "resolve",
    "Conflict",
    "detect_conflicts",
    "log_resolution",
    "read_audit",
    "read_audit_for_stage",
]
