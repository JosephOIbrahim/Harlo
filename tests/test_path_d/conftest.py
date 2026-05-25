"""Fixtures for path_d (PVH) tests.

All fixtures build a TEMPORARY observation database (tmp_path). Per D33,
path_d tests never touch the canonical data/observations.db.
"""

from __future__ import annotations

import sqlite3
import uuid

import pytest

from src.schemas import CognitiveObservation

_SCHEMA = """
CREATE TABLE observation_buffer (
    obs_id TEXT PRIMARY KEY,
    observation_json TEXT NOT NULL,
    priority REAL NOT NULL DEFAULT 0.0,
    partition TEXT NOT NULL DEFAULT 'organic',
    surprise_score REAL NOT NULL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


def _make_obs(session_id: str, exchange_index: int, observation_index=None) -> CognitiveObservation:
    oi = observation_index if observation_index is not None else exchange_index
    return CognitiveObservation(
        session_id=session_id,
        exchange_index=exchange_index,
        observation_index=oi,
    )


@pytest.fixture
def obs_db(tmp_path):
    """Factory: build a temp observation_buffer DB and return its path.

    rows: list of dicts with keys session_id, exchange_index,
          optional observation_index, partition, created_at, obs_id.
    raw_extra: list of (obs_id, raw_json_string, partition, created_at) for
               injecting malformed rows.
    """
    def _build(rows, name="obs.db", raw_extra=None):
        path = tmp_path / name
        conn = sqlite3.connect(str(path))
        conn.execute(_SCHEMA)
        for r in rows:
            obs = _make_obs(r["session_id"], r["exchange_index"], r.get("observation_index"))
            conn.execute(
                "INSERT INTO observation_buffer (obs_id, observation_json, partition, created_at) VALUES (?,?,?,?)",
                (
                    r.get("obs_id", str(uuid.uuid4())[:8]),
                    obs.model_dump_json(),
                    r.get("partition", "organic"),
                    r.get("created_at"),
                ),
            )
        for oid, raw_json, part, cat in (raw_extra or []):
            conn.execute(
                "INSERT INTO observation_buffer (obs_id, observation_json, partition, created_at) VALUES (?,?,?,?)",
                (oid, raw_json, part, cat),
            )
        conn.commit()
        conn.close()
        return str(path)

    return _build
