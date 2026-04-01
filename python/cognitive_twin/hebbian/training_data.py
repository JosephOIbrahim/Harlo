"""Elenchus training data pipeline — JSONL with profile features.

Patch 5: cognitive_profile_features (full float vector) alongside hash.
Patch 8: O(1) log rotation at max_rows (10,000).

Rule 11: NO reasoning traces in dataset.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..usd_lite.prims import CognitiveProfilePrim

_DEFAULT_DATA_DIR = Path("data")
_DEFAULT_FILENAME = "elenchus_training.jsonl"
_MAX_ROWS = 10_000
_MAX_ROTATED_FILES = 3


def _profile_hash(profile: Optional[CognitiveProfilePrim]) -> str:
    """Compute deterministic hash of cognitive profile state."""
    if profile is None:
        return hashlib.sha256(b"no_profile").hexdigest()
    m = profile.multipliers
    raw = json.dumps({
        "surprise_threshold": m.surprise_threshold,
        "reconstruction_threshold": m.reconstruction_threshold,
        "hebbian_alpha": m.hebbian_alpha,
        "allostatic_threshold": m.allostatic_threshold,
        "detail_orientation": m.detail_orientation,
    }, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _profile_features(profile: Optional[CognitiveProfilePrim]) -> dict:
    """Extract cognitive profile features as float dict.

    Patch 5: Non-empty when profile exists; empty dict {} when no profile.
    Never null, never missing key.
    """
    if profile is None:
        return {}
    m = profile.multipliers
    return {
        "surprise_threshold": m.surprise_threshold,
        "reconstruction_threshold": m.reconstruction_threshold,
        "hebbian_alpha": m.hebbian_alpha,
        "allostatic_threshold": m.allostatic_threshold,
        "detail_orientation": m.detail_orientation,
    }


def record_verification(
    intent_hash: str,
    output_hash: str,
    verification_state: str,
    cycle_count: int,
    domain: str = "general",
    confidence_score: float = 0.0,
    retrieval_path: str = "SYSTEM_1",
    profile: Optional[CognitiveProfilePrim] = None,
    data_dir: Optional[Path] = None,
) -> dict:
    """Record a verification event to the training data JSONL.

    Rule 11: NO reasoning traces in this function or its output.

    Returns the row dict that was written.
    """
    if data_dir is None:
        data_dir = _DEFAULT_DATA_DIR

    row = {
        "intent_hash": intent_hash,
        "output_hash": output_hash,
        "verification_state": verification_state,
        "cycle_count": cycle_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "domain": domain,
        "confidence_score": confidence_score,
        "retrieval_path": retrieval_path,
        "cognitive_profile_hash": _profile_hash(profile),
        "cognitive_profile_features": _profile_features(profile),
    }

    data_dir.mkdir(parents=True, exist_ok=True)
    filepath = data_dir / _DEFAULT_FILENAME

    # Check rotation before writing
    _maybe_rotate(filepath, data_dir)

    # Append the row
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")

    return row


def _count_lines(filepath: Path) -> int:
    """Count lines in a file without reading all content into memory."""
    if not filepath.exists():
        return 0
    count = 0
    with open(filepath, "r", encoding="utf-8") as f:
        for _ in f:
            count += 1
    return count


def _maybe_rotate(filepath: Path, data_dir: Path) -> None:
    """Rotate the training data file if it exceeds max_rows.

    Patch 8: O(1) amortized. Rename current file, start fresh.
    Retain at most MAX_ROTATED_FILES old files.
    """
    if not filepath.exists():
        return

    line_count = _count_lines(filepath)
    if line_count < _MAX_ROWS:
        return

    # Rotate: rename to timestamped file (microseconds for uniqueness)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%f")
    rotated_name = f"elenchus_training.{ts}.jsonl"
    rotated_path = data_dir / rotated_name
    filepath.replace(rotated_path)  # replace() works cross-platform

    # Cleanup: retain at most MAX_ROTATED_FILES
    rotated_files = sorted(data_dir.glob("elenchus_training.*.jsonl"))
    excess = len(rotated_files) - _MAX_ROTATED_FILES
    if excess > 0:
        for old_file in rotated_files[:excess]:
            old_file.unlink()


def get_row_count(data_dir: Optional[Path] = None) -> int:
    """Get current row count in the active training data file."""
    if data_dir is None:
        data_dir = _DEFAULT_DATA_DIR
    filepath = data_dir / _DEFAULT_FILENAME
    return _count_lines(filepath)
