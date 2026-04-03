"""Hot Tier schema definitions for SQLite + FTS5.

Provides DDL statements and schema creation for the zero-encoding
Hot Tier (L1) trace store.
"""

from __future__ import annotations

import sqlite3

# Table name constants
TABLE_HOT_TRACES = "hot_traces"
TABLE_HOT_TRACES_FTS = "hot_traces_fts"

CREATE_HOT_TRACES = """
CREATE TABLE IF NOT EXISTS hot_traces (
    trace_id    TEXT PRIMARY KEY,
    message     TEXT NOT NULL,
    tags        TEXT NOT NULL DEFAULT '[]',
    domain      TEXT NOT NULL DEFAULT 'general',
    timestamp   REAL NOT NULL,
    encoded     INTEGER NOT NULL DEFAULT 0
)
"""

CREATE_HOT_TRACES_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS hot_traces_fts USING fts5(
    message,
    tags,
    domain,
    content='hot_traces',
    content_rowid='rowid'
)
"""

CREATE_TRIGGER_INSERT = """
CREATE TRIGGER IF NOT EXISTS hot_traces_ai AFTER INSERT ON hot_traces BEGIN
    INSERT INTO hot_traces_fts(rowid, message, tags, domain)
    VALUES (new.rowid, new.message, new.tags, new.domain);
END
"""

CREATE_TRIGGER_DELETE = """
CREATE TRIGGER IF NOT EXISTS hot_traces_ad AFTER DELETE ON hot_traces BEGIN
    INSERT INTO hot_traces_fts(hot_traces_fts, rowid, message, tags, domain)
    VALUES ('delete', old.rowid, old.message, old.tags, old.domain);
END
"""

CREATE_TRIGGER_UPDATE = """
CREATE TRIGGER IF NOT EXISTS hot_traces_au AFTER UPDATE ON hot_traces BEGIN
    INSERT INTO hot_traces_fts(hot_traces_fts, rowid, message, tags, domain)
    VALUES ('delete', old.rowid, old.message, old.tags, old.domain);
    INSERT INTO hot_traces_fts(rowid, message, tags, domain)
    VALUES (new.rowid, new.message, new.tags, new.domain);
END
"""

CREATE_INDEX_PENDING = """
CREATE INDEX IF NOT EXISTS idx_hot_traces_pending
    ON hot_traces(encoded) WHERE encoded = 0
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create Hot Tier tables, FTS5 index, triggers, and indexes.

    Idempotent: safe to call multiple times on the same database.

    Args:
        conn: Active SQLite connection.
    """
    conn.execute(CREATE_HOT_TRACES)
    conn.execute(CREATE_HOT_TRACES_FTS)
    conn.execute(CREATE_TRIGGER_INSERT)
    conn.execute(CREATE_TRIGGER_DELETE)
    conn.execute(CREATE_TRIGGER_UPDATE)
    conn.execute(CREATE_INDEX_PENDING)
    conn.commit()
