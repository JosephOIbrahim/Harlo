"""Read-only constraint test (Commandment 2 / Article 1 + D33).

Running the extractor must produce ZERO mutations to the observation DB.
Runs against a temp fixture DB, never data/observations.db.
"""

from __future__ import annotations

import os
import sqlite3

from harness.path_d.pvh.extractor import iter_sessions


def _count(db: str) -> int:
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return conn.execute("SELECT COUNT(*) FROM observation_buffer").fetchone()[0]
    finally:
        conn.close()


def test_extractor_does_not_mutate_db(obs_db):
    db = obs_db([{"session_id": "s", "exchange_index": i} for i in range(5)])

    before_mtime = os.stat(db).st_mtime_ns
    before_count = _count(db)

    sessions = list(iter_sessions(db))  # no predictor: pure read

    after_mtime = os.stat(db).st_mtime_ns
    after_count = _count(db)

    assert after_count == before_count == 5
    assert after_mtime == before_mtime, "extractor mutated the observation DB"
    assert len(sessions) == 1
    assert sessions[0].metadata.window_count == 3  # 5 obs -> 3 windows


def test_no_wal_sidecars_created(obs_db):
    """Read-only access must not create -wal/-shm sidecar files."""
    db = obs_db([{"session_id": "s", "exchange_index": i} for i in range(4)])
    list(iter_sessions(db))
    assert not os.path.exists(db + "-wal")
    assert not os.path.exists(db + "-shm")
