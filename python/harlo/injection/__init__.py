"""Injection state persistence — SQLite store for Digital Injection Framework state.

Stores injection state transitions (profile activation/deactivation) as
independently queryable records. Separate from hot_traces to maintain
clean type separation and enable injection-specific pattern detection.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class InjectionTrace:
    """A single injection state transition record."""

    trace_id: str
    profile: str            # "none" | "microdose" | "perceptual" | "classical" | "mdma"
    s_nm: float             # Neuromodulatory signal strength (0.000 - 0.025)
    alpha: float            # Current pharmacokinetic alpha (0.0 - 1.0)
    exchange_count: int     # Exchange number when transition occurred
    transition: str         # "activated" | "deactivated" | "red_override"
    session_id: str         # Link to active session
    timestamp: float        # Unix timestamp


_VALID_PROFILES = {"none", "microdose", "perceptual", "classical", "mdma"}
_VALID_TRANSITIONS = {"activated", "deactivated", "red_override"}

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS injection_traces (
    trace_id        TEXT PRIMARY KEY,
    profile         TEXT NOT NULL,
    s_nm            REAL NOT NULL,
    alpha           REAL NOT NULL,
    exchange_count  INTEGER NOT NULL,
    transition      TEXT NOT NULL,
    session_id      TEXT NOT NULL DEFAULT '',
    timestamp       REAL NOT NULL
)
"""

_CREATE_INDEX_SESSION = """
CREATE INDEX IF NOT EXISTS idx_injection_session
    ON injection_traces(session_id)
"""

_CREATE_INDEX_PROFILE = """
CREATE INDEX IF NOT EXISTS idx_injection_profile
    ON injection_traces(profile)
"""

_CREATE_INDEX_TIMESTAMP = """
CREATE INDEX IF NOT EXISTS idx_injection_timestamp
    ON injection_traces(timestamp)
"""


class InjectionStore:
    """SQLite persistence for injection state transitions."""

    def __init__(self, db_path: str) -> None:
        """Initialize InjectionStore with database path."""
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create injection_traces table and indexes if needed."""
        self._conn.execute(_CREATE_TABLE)
        self._conn.execute(_CREATE_INDEX_SESSION)
        self._conn.execute(_CREATE_INDEX_PROFILE)
        self._conn.execute(_CREATE_INDEX_TIMESTAMP)
        self._conn.commit()

    def store(
        self,
        profile: str,
        s_nm: float,
        alpha: float,
        exchange_count: int,
        transition: str,
        session_id: str = "",
        trace_id: Optional[str] = None,
        timestamp: Optional[float] = None,
    ) -> str:
        """Store an injection state transition.

        Args:
            profile: Injection profile name.
            s_nm: Neuromodulatory signal strength.
            alpha: Pharmacokinetic alpha value.
            exchange_count: Exchange number at transition.
            transition: Type of transition.
            session_id: Associated session ID.
            trace_id: Optional explicit ID (generated if None).
            timestamp: Optional explicit timestamp (now if None).

        Returns:
            The trace_id of the stored injection trace.

        Raises:
            ValueError: If profile or transition is invalid.
        """
        if profile not in _VALID_PROFILES:
            raise ValueError(f"Invalid profile: {profile!r}. Must be one of {_VALID_PROFILES}")
        if transition not in _VALID_TRANSITIONS:
            raise ValueError(f"Invalid transition: {transition!r}. Must be one of {_VALID_TRANSITIONS}")
        if not (0.0 <= s_nm <= 0.025):
            raise ValueError(f"s_nm must be in [0.0, 0.025], got {s_nm}")
        if not (0.0 <= alpha <= 1.0):
            raise ValueError(f"alpha must be in [0.0, 1.0], got {alpha}")

        if trace_id is None:
            trace_id = uuid.uuid4().hex[:16]
        if timestamp is None:
            timestamp = time.time()

        self._conn.execute(
            "INSERT INTO injection_traces "
            "(trace_id, profile, s_nm, alpha, exchange_count, transition, session_id, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (trace_id, profile, s_nm, alpha, exchange_count, transition, session_id, timestamp),
        )
        self._conn.commit()
        return trace_id

    def get_recent(self, limit: int = 10) -> list[InjectionTrace]:
        """Get most recent injection traces, newest first."""
        cursor = self._conn.execute(
            "SELECT trace_id, profile, s_nm, alpha, exchange_count, transition, session_id, timestamp "
            "FROM injection_traces ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        return [self._row_to_trace(row) for row in cursor.fetchall()]

    def get_by_profile(self, profile: str, limit: int = 50) -> list[InjectionTrace]:
        """Get injection traces filtered by profile."""
        cursor = self._conn.execute(
            "SELECT trace_id, profile, s_nm, alpha, exchange_count, transition, session_id, timestamp "
            "FROM injection_traces WHERE profile = ? ORDER BY timestamp DESC LIMIT ?",
            (profile, limit),
        )
        return [self._row_to_trace(row) for row in cursor.fetchall()]

    def get_by_session(self, session_id: str) -> list[InjectionTrace]:
        """Get all injection traces for a session."""
        cursor = self._conn.execute(
            "SELECT trace_id, profile, s_nm, alpha, exchange_count, transition, session_id, timestamp "
            "FROM injection_traces WHERE session_id = ? ORDER BY timestamp ASC",
            (session_id,),
        )
        return [self._row_to_trace(row) for row in cursor.fetchall()]

    def get_activation_count(self, profile: str, since_timestamp: float = 0.0) -> int:
        """Count activations of a specific profile since a timestamp."""
        row = self._conn.execute(
            "SELECT COUNT(*) FROM injection_traces "
            "WHERE profile = ? AND transition = 'activated' AND timestamp >= ?",
            (profile, since_timestamp),
        ).fetchone()
        return row[0] if row else 0

    def get_profile_frequency(self, limit_sessions: int = 10) -> dict[str, int]:
        """Count activation frequency per profile across recent sessions."""
        cursor = self._conn.execute(
            "SELECT profile, COUNT(*) as cnt FROM injection_traces "
            "WHERE transition = 'activated' "
            "GROUP BY profile ORDER BY cnt DESC"
        )
        return {row[0]: row[1] for row in cursor.fetchall()}

    def count(self) -> int:
        """Total number of injection traces."""
        row = self._conn.execute("SELECT COUNT(*) FROM injection_traces").fetchone()
        return row[0] if row else 0

    def search(self, query: str, limit: int = 10) -> list[InjectionTrace]:
        """Search injection traces by profile name or transition type."""
        cursor = self._conn.execute(
            "SELECT trace_id, profile, s_nm, alpha, exchange_count, transition, session_id, timestamp "
            "FROM injection_traces "
            "WHERE profile LIKE ? OR transition LIKE ? "
            "ORDER BY timestamp DESC LIMIT ?",
            (f"%{query}%", f"%{query}%", limit),
        )
        return [self._row_to_trace(row) for row in cursor.fetchall()]

    @staticmethod
    def _row_to_trace(row: tuple) -> InjectionTrace:
        """Convert a database row to an InjectionTrace dataclass."""
        return InjectionTrace(
            trace_id=row[0],
            profile=row[1],
            s_nm=row[2],
            alpha=row[3],
            exchange_count=row[4],
            transition=row[5],
            session_id=row[6],
            timestamp=row[7],
        )
