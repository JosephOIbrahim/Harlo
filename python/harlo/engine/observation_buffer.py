"""Observation Buffer — SQLite priority queue for training observations.

Anchor partition (20% locked synthetic) + organic partition (80% surprise-weighted).
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .schemas import CognitiveObservation


@dataclass
class BufferedObservation:
    """An observation in the buffer with priority metadata."""
    obs_id: str
    observation: CognitiveObservation
    priority: float
    partition: str  # "anchor" or "organic"
    surprise_score: float = 0.0


class ObservationBuffer:
    """SQLite-backed priority queue for observations.

    Two partitions:
    - anchor (20%): locked synthetic observations for baseline
    - organic (80%): surprise-weighted observations from live sessions
    """

    def __init__(self, db_path: str = ":memory:", max_size: int = 10000):
        self._db_path = db_path
        self._max_size = max_size
        self._anchor_ratio = 0.20
        self._conn = sqlite3.connect(db_path)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create buffer table if it doesn't exist."""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS observation_buffer (
                obs_id TEXT PRIMARY KEY,
                observation_json TEXT NOT NULL,
                priority REAL NOT NULL DEFAULT 0.0,
                partition TEXT NOT NULL DEFAULT 'organic',
                surprise_score REAL NOT NULL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_buffer_priority
            ON observation_buffer(partition, priority DESC)
        """)
        self._conn.commit()

    def add(
        self,
        observation: CognitiveObservation,
        partition: str = "organic",
        surprise_score: float = 0.0,
    ) -> str:
        """Add an observation to the buffer.

        Priority is based on surprise score for organic, fixed for anchor.
        """
        obs_id = str(uuid.uuid4())[:8]
        priority = 1.0 if partition == "anchor" else surprise_score

        self._conn.execute(
            """INSERT INTO observation_buffer
               (obs_id, observation_json, priority, partition, surprise_score)
               VALUES (?, ?, ?, ?, ?)""",
            (obs_id, observation.model_dump_json(), priority, partition, surprise_score),
        )
        self._conn.commit()

        self._maybe_evict()
        return obs_id

    def add_anchor_batch(self, observations: list[CognitiveObservation]) -> int:
        """Add a batch of anchor observations."""
        count = 0
        for obs in observations:
            self.add(obs, partition="anchor", surprise_score=0.0)
            count += 1
        return count

    def sample(self, n: int = 100) -> list[BufferedObservation]:
        """Sample observations maintaining anchor/organic ratio."""
        n_anchor = max(1, int(n * self._anchor_ratio))
        n_organic = n - n_anchor

        results: list[BufferedObservation] = []

        # Anchor samples (highest priority)
        rows = self._conn.execute(
            """SELECT obs_id, observation_json, priority, partition, surprise_score
               FROM observation_buffer
               WHERE partition = 'anchor'
               ORDER BY RANDOM()
               LIMIT ?""",
            (n_anchor,),
        ).fetchall()

        for row in rows:
            results.append(BufferedObservation(
                obs_id=row[0],
                observation=CognitiveObservation.model_validate_json(row[1]),
                priority=row[2],
                partition=row[3],
                surprise_score=row[4],
            ))

        # Organic samples (priority-weighted)
        rows = self._conn.execute(
            """SELECT obs_id, observation_json, priority, partition, surprise_score
               FROM observation_buffer
               WHERE partition = 'organic'
               ORDER BY priority DESC
               LIMIT ?""",
            (n_organic,),
        ).fetchall()

        for row in rows:
            results.append(BufferedObservation(
                obs_id=row[0],
                observation=CognitiveObservation.model_validate_json(row[1]),
                priority=row[2],
                partition=row[3],
                surprise_score=row[4],
            ))

        return results

    def _maybe_evict(self) -> None:
        """Evict lowest-priority organic observations if over max_size."""
        count = self._conn.execute(
            "SELECT COUNT(*) FROM observation_buffer"
        ).fetchone()[0]

        if count > self._max_size:
            excess = count - self._max_size
            self._conn.execute(
                """DELETE FROM observation_buffer WHERE obs_id IN (
                    SELECT obs_id FROM observation_buffer
                    WHERE partition = 'organic'
                    ORDER BY priority ASC
                    LIMIT ?
                )""",
                (excess,),
            )
            self._conn.commit()

    def size(self) -> dict[str, int]:
        """Return buffer size by partition."""
        result = {"anchor": 0, "organic": 0, "total": 0}
        rows = self._conn.execute(
            "SELECT partition, COUNT(*) FROM observation_buffer GROUP BY partition"
        ).fetchall()
        for row in rows:
            result[row[0]] = row[1]
        result["total"] = sum(v for k, v in result.items() if k != "total")
        return result

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()
