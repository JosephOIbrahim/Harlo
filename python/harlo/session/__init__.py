"""Session lifecycle management for the Harlo.

Provides implicit session tracking: sessions are created on first
interaction and closed explicitly or by timeout. Each session persists
conversation history, exchange count, domain, and allostatic load
state in SQLite.
"""

from .manager import Session, SessionManager

__all__ = ["Session", "SessionManager"]
