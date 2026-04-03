"""Session lifecycle manager — SQLite-backed session persistence.

Sessions are implicit: created on first interaction, closed explicitly
or by timeout. Each session tracks exchange count, conversation history,
domain, encoder type, and cumulative allostatic token count.

Storage: SQLite sessions table in the shared twin.db database.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Optional

# Maximum conversation history entries (messages, not exchanges)
_MAX_HISTORY_MESSAGES = 100


@dataclass
class Session:
    """A single Twin session."""

    session_id: str
    started_at: int
    last_active: int
    exchange_count: int = 0
    domain: str = "general"
    encoder_type: str = "semantic"
    closed: bool = False
    history_json: str = "[]"
    allostatic_tokens: int = 0

    @property
    def history(self) -> list[dict]:
        """Deserialize conversation history."""
        return json.loads(self.history_json)

    def set_history(self, history: list[dict]) -> None:
        """Serialize and store conversation history, enforcing the cap."""
        if len(history) > _MAX_HISTORY_MESSAGES:
            history = history[-_MAX_HISTORY_MESSAGES:]
        self.history_json = json.dumps(history)

    def is_expired(self, timeout_s: int, now: int | None = None) -> bool:
        """Check if this session has exceeded the timeout."""
        if self.closed:
            return True
        ts = now if now is not None else int(time.time())
        return (ts - self.last_active) > timeout_s

    def to_dict(self) -> dict:
        """Serialize session to a plain dict."""
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "last_active": self.last_active,
            "exchange_count": self.exchange_count,
            "domain": self.domain,
            "encoder_type": self.encoder_type,
            "closed": self.closed,
            "allostatic_tokens": self.allostatic_tokens,
            "history_length": len(self.history),
        }


def _ensure_sessions_table(conn: sqlite3.Connection) -> None:
    """Create the sessions table if it does not exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            started_at INTEGER NOT NULL,
            last_active INTEGER NOT NULL,
            exchange_count INTEGER NOT NULL DEFAULT 0,
            domain TEXT NOT NULL DEFAULT 'general',
            encoder_type TEXT NOT NULL DEFAULT 'semantic',
            closed INTEGER NOT NULL DEFAULT 0,
            history_json TEXT NOT NULL DEFAULT '[]',
            allostatic_tokens INTEGER NOT NULL DEFAULT 0
        )
    """)


class SessionManager:
    """Manages session lifecycle: create, retrieve, update, close, expire."""

    def __init__(self, db_path: str, timeout_s: int = 1800) -> None:
        """Initialize the session manager.

        Args:
            db_path: Path to the SQLite database file.
            timeout_s: Session timeout in seconds (default 1800 = 30 min).
        """
        self._db_path = db_path
        self._timeout_s = timeout_s
        self._init_db()

    def _init_db(self) -> None:
        """Ensure the sessions table exists."""
        conn = self._connect()
        try:
            _ensure_sessions_table(conn)
            conn.commit()
        finally:
            conn.close()

    def _connect(self) -> sqlite3.Connection:
        """Open a connection to the database."""
        return sqlite3.connect(self._db_path)

    def create(
        self,
        domain: str = "general",
        encoder_type: str = "semantic",
        now: int | None = None,
    ) -> Session:
        """Create a new session with a fresh UUID.

        Args:
            domain: Active domain for this session.
            encoder_type: Encoder type for this session.
            now: Override timestamp for testing.

        Returns:
            The newly created Session.
        """
        ts = now if now is not None else int(time.time())
        session = Session(
            session_id=uuid.uuid4().hex[:16],
            started_at=ts,
            last_active=ts,
            domain=domain,
            encoder_type=encoder_type,
        )
        conn = self._connect()
        try:
            conn.execute(
                """INSERT INTO sessions
                   (session_id, started_at, last_active, exchange_count,
                    domain, encoder_type, closed, history_json, allostatic_tokens)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session.session_id, session.started_at, session.last_active,
                    session.exchange_count, session.domain, session.encoder_type,
                    int(session.closed), session.history_json, session.allostatic_tokens,
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return session

    def get(self, session_id: str) -> Session | None:
        """Load a session from the database.

        Args:
            session_id: The session identifier.

        Returns:
            Session if found, None otherwise.
        """
        conn = self._connect()
        try:
            row = conn.execute(
                """SELECT session_id, started_at, last_active, exchange_count,
                          domain, encoder_type, closed, history_json, allostatic_tokens
                   FROM sessions WHERE session_id = ?""",
                (session_id,),
            ).fetchone()
            if row is None:
                return None
            return Session(
                session_id=row[0],
                started_at=row[1],
                last_active=row[2],
                exchange_count=row[3],
                domain=row[4],
                encoder_type=row[5],
                closed=bool(row[6]),
                history_json=row[7],
                allostatic_tokens=row[8],
            )
        finally:
            conn.close()

    def get_or_create(
        self,
        session_id: str | None = None,
        domain: str = "general",
        encoder_type: str = "semantic",
        now: int | None = None,
    ) -> Session:
        """Get an existing session or create a new one.

        Args:
            session_id: Optional session ID to look up.
            domain: Domain for new session creation.
            encoder_type: Encoder type for new session creation.
            now: Override timestamp for testing.

        Returns:
            Existing or newly created Session.
        """
        if session_id:
            session = self.get(session_id)
            if session and not session.closed:
                ts = now if now is not None else int(time.time())
                if not session.is_expired(self._timeout_s, now=ts):
                    return session
        return self.create(domain=domain, encoder_type=encoder_type, now=now)

    def update(self, session: Session) -> None:
        """Persist session state back to the database.

        Args:
            session: The session to persist.
        """
        conn = self._connect()
        try:
            conn.execute(
                """UPDATE sessions SET
                    last_active = ?, exchange_count = ?, domain = ?,
                    encoder_type = ?, closed = ?, history_json = ?,
                    allostatic_tokens = ?
                   WHERE session_id = ?""",
                (
                    session.last_active, session.exchange_count, session.domain,
                    session.encoder_type, int(session.closed), session.history_json,
                    session.allostatic_tokens, session.session_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def record_exchange(
        self,
        session_id: str,
        query: str,
        response: str,
        tokens: int = 0,
        now: int | None = None,
    ) -> Session | None:
        """Record an exchange within a session.

        Updates exchange count, conversation history, last_active timestamp,
        and cumulative allostatic token count.

        Args:
            session_id: The session to update.
            query: The user's query.
            response: The Twin's response.
            tokens: Number of tokens consumed in this exchange.
            now: Override timestamp for testing.

        Returns:
            Updated Session, or None if session not found.
        """
        session = self.get(session_id)
        if session is None or session.closed:
            return None

        ts = now if now is not None else int(time.time())
        session.exchange_count += 1
        session.last_active = ts
        session.allostatic_tokens += tokens

        history = session.history
        history.append({"role": "user", "content": query})
        history.append({"role": "assistant", "content": response})
        session.set_history(history)

        self.update(session)
        return session

    def close(self, session_id: str, trigger_dmn: bool = True) -> Session | None:
        """Close a session and optionally trigger DMN teardown.

        Args:
            session_id: The session to close.
            trigger_dmn: Whether to fire DMN teardown synthesis.

        Returns:
            Closed Session, or None if not found.
        """
        session = self.get(session_id)
        if session is None:
            return None
        if session.closed:
            return session  # Already closed, idempotent

        session.closed = True
        session.last_active = int(time.time())
        self.update(session)

        if trigger_dmn:
            self._trigger_dmn_teardown(session)

        return session

    def close_expired(self, now: int | None = None) -> list[str]:
        """Find and close all sessions past timeout.

        Args:
            now: Override timestamp for testing.

        Returns:
            List of session IDs that were closed.
        """
        ts = now if now is not None else int(time.time())
        cutoff = ts - self._timeout_s

        conn = self._connect()
        try:
            rows = conn.execute(
                """SELECT session_id FROM sessions
                   WHERE closed = 0 AND last_active < ?""",
                (cutoff,),
            ).fetchall()
        finally:
            conn.close()

        closed_ids = []
        for (sid,) in rows:
            self.close(sid, trigger_dmn=True)
            closed_ids.append(sid)
        return closed_ids

    def list_active(self, now: int | None = None) -> list[Session]:
        """Return all non-closed, non-expired sessions.

        Args:
            now: Override timestamp for testing.

        Returns:
            List of active Sessions.
        """
        ts = now if now is not None else int(time.time())
        cutoff = ts - self._timeout_s

        conn = self._connect()
        try:
            rows = conn.execute(
                """SELECT session_id, started_at, last_active, exchange_count,
                          domain, encoder_type, closed, history_json, allostatic_tokens
                   FROM sessions
                   WHERE closed = 0 AND last_active >= ?""",
                (cutoff,),
            ).fetchall()
        finally:
            conn.close()

        return [
            Session(
                session_id=r[0], started_at=r[1], last_active=r[2],
                exchange_count=r[3], domain=r[4], encoder_type=r[5],
                closed=bool(r[6]), history_json=r[7], allostatic_tokens=r[8],
            )
            for r in rows
        ]

    def _trigger_dmn_teardown(self, session: Session) -> None:
        """Fire DMN teardown synthesis for a closing session."""
        try:
            from ..daemon.dmn_teardown import get_teardown

            teardown = get_teardown()
            context = {
                "session_id": session.session_id,
                "domain": session.domain,
                "exchange_count": session.exchange_count,
                "history": session.history,
                "allostatic_tokens": session.allostatic_tokens,
            }

            def _synthesis(ctx, abort_check=None):
                """Placeholder synthesis — returns context for potential DMN processing."""
                return ctx

            teardown.start(_synthesis, context)
        except Exception:
            pass  # DMN teardown is best-effort; don't fail session close
