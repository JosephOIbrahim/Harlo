"""SQLite connection pooling for the Python layer.

Provides a thread-local singleton connection per database path,
avoiding the overhead of opening/closing connections per call.
Connections are cached per-thread (sqlite3 requirement).
"""

from __future__ import annotations

import sqlite3
import threading
from typing import Optional


_thread_local = threading.local()


def get_connection(db_path: str) -> sqlite3.Connection:
    """Get a cached SQLite connection for the given database path.

    Returns the same connection for repeated calls with the same path
    within the same thread. Creates a new connection on first call.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        A sqlite3.Connection instance.
    """
    cache_key = f"_conn_{db_path}"

    conn = getattr(_thread_local, cache_key, None)
    if conn is not None:
        try:
            conn.execute("SELECT 1")
            return conn
        except sqlite3.ProgrammingError:
            # Connection was closed; create a new one
            pass

    conn = sqlite3.connect(db_path)
    setattr(_thread_local, cache_key, conn)
    return conn


def close_connection(db_path: str) -> None:
    """Close and remove the cached connection for a database path.

    Args:
        db_path: Path to the SQLite database file.
    """
    cache_key = f"_conn_{db_path}"
    conn = getattr(_thread_local, cache_key, None)
    if conn is not None:
        try:
            conn.close()
        except sqlite3.ProgrammingError:
            pass
        delattr(_thread_local, cache_key)


def close_all() -> None:
    """Close all cached connections in the current thread."""
    for attr in list(vars(_thread_local)):
        if attr.startswith("_conn_"):
            conn = getattr(_thread_local, attr)
            try:
                conn.close()
            except (sqlite3.ProgrammingError, AttributeError):
                pass
            delattr(_thread_local, attr)
