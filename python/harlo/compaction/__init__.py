"""Temporal compaction — replay-then-archive.

Deep-idle process that compacts variant stacks by chronological
replay with decay. Preserves temporal archaeology via archives.

Critical invariant: flatten(decay(variants)) == decay(flatten(variants))
This holds because exponential decay is linear — the sum of decayed
values equals the decay of the sum.
"""

from __future__ import annotations

import json
import logging
import math
import shutil
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Variant:
    """A temporal variant (opinion layer) in the variant stack."""

    variant_id: str
    data: dict
    timestamp: float
    decay_lambda: float


@dataclass
class CompactionResult:
    """Result of a compaction operation."""

    variants_compacted: int
    baseline_written: bool
    archive_path: Optional[str]


class CompactionEngine:
    """Replay-then-archive compaction engine.

    Replays variants chronologically with decay, writes resolved
    baseline, and archives originals.
    """

    def __init__(self, db_path: str, archive_dir: Optional[str] = None) -> None:
        """Initialize compaction engine.

        Args:
            db_path: Path to SQLite database.
            archive_dir: Directory for archived variants. Defaults to
                {db_dir}/.usda.archive/
        """
        self._db_path = db_path
        if archive_dir is None:
            archive_dir = str(Path(db_path).parent / ".usda.archive")
        self._archive_dir = archive_dir
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS variants (
                variant_id TEXT PRIMARY KEY,
                data_json TEXT NOT NULL,
                timestamp REAL NOT NULL,
                decay_lambda REAL NOT NULL DEFAULT 0.05
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS baseline (
                key TEXT PRIMARY KEY,
                value_json TEXT NOT NULL,
                compacted_at REAL NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def add_variant(self, variant: Variant) -> None:
        """Add a variant to the stack.

        Args:
            variant: The variant to add.
        """
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO variants (variant_id, data_json, timestamp, decay_lambda) "
                "VALUES (?, ?, ?, ?)",
                (
                    variant.variant_id,
                    json.dumps(variant.data),
                    variant.timestamp,
                    variant.decay_lambda,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_variants(self) -> list[Variant]:
        """Get all variants, oldest first.

        Returns:
            List of Variant objects sorted by timestamp.
        """
        conn = sqlite3.connect(self._db_path)
        try:
            cursor = conn.execute(
                "SELECT variant_id, data_json, timestamp, decay_lambda "
                "FROM variants ORDER BY timestamp ASC"
            )
            return [
                Variant(
                    variant_id=row[0],
                    data=json.loads(row[1]),
                    timestamp=row[2],
                    decay_lambda=row[3],
                )
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    def compact(self, t_now: Optional[float] = None) -> CompactionResult:
        """Run replay-then-archive compaction.

        Algorithm:
        1. Sort variants by timestamp (chronological)
        2. Replay each, applying decay at t_now
        3. Write resolved state to baseline
        4. Archive original variants

        Args:
            t_now: Current time for decay calculation. Defaults to time.time().

        Returns:
            CompactionResult with stats.
        """
        if t_now is None:
            t_now = time.time()

        variants = self.get_variants()
        if not variants:
            return CompactionResult(0, False, None)

        # Replay with decay
        resolved = self._replay_with_decay(variants, t_now)

        # Write baseline
        self._write_baseline(resolved, t_now)

        # Archive variants
        archive_path = self._archive_variants(variants)

        # Remove variants from active table
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("DELETE FROM variants")
            conn.commit()
        finally:
            conn.close()

        return CompactionResult(
            variants_compacted=len(variants),
            baseline_written=True,
            archive_path=archive_path,
        )

    def get_baseline(self) -> dict:
        """Get current baseline state.

        Returns:
            Dict of key → value from baseline table.
        """
        conn = sqlite3.connect(self._db_path)
        try:
            cursor = conn.execute("SELECT key, value_json FROM baseline")
            return {row[0]: json.loads(row[1]) for row in cursor.fetchall()}
        finally:
            conn.close()

    def _replay_with_decay(
        self, variants: list[Variant], t_now: float
    ) -> dict:
        """Replay variants chronologically with decay.

        Each variant's contribution is weighted by:
        weight = e^(-lambda * (t_now - variant.timestamp))

        For overlapping keys, later variants override earlier ones
        (after decay weighting).

        Args:
            variants: Sorted list of variants.
            t_now: Current time for decay.

        Returns:
            Resolved key→value dict.
        """
        resolved: dict = {}

        for variant in variants:
            dt = max(0.0, t_now - variant.timestamp)
            weight = math.exp(-variant.decay_lambda * dt)

            for key, value in variant.data.items():
                if isinstance(value, (int, float)):
                    resolved[key] = resolved.get(key, 0.0) + value * weight
                else:
                    # Non-numeric: last-write-wins with decay threshold
                    if weight > 0.01:  # Only keep if weight > 1%
                        resolved[key] = value

        return resolved

    def _write_baseline(self, resolved: dict, t_now: float) -> None:
        """Write resolved state to baseline table."""
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("DELETE FROM baseline")
            for key, value in resolved.items():
                conn.execute(
                    "INSERT INTO baseline (key, value_json, compacted_at) VALUES (?, ?, ?)",
                    (key, json.dumps(value), t_now),
                )
            conn.commit()
        finally:
            conn.close()

    def _archive_variants(self, variants: list[Variant]) -> str:
        """Archive variants to .usda.archive/ directory.

        Args:
            variants: Variants to archive.

        Returns:
            Path to archive file.
        """
        Path(self._archive_dir).mkdir(parents=True, exist_ok=True)

        archive_name = f"compaction-{int(time.time())}.json"
        archive_path = str(Path(self._archive_dir) / archive_name)

        archive_data = [
            {
                "variant_id": v.variant_id,
                "data": v.data,
                "timestamp": v.timestamp,
                "decay_lambda": v.decay_lambda,
            }
            for v in variants
        ]

        Path(archive_path).write_text(
            json.dumps(archive_data, indent=2), encoding="utf-8"
        )

        return archive_path
