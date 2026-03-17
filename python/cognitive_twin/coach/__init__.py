"""Coach.md — system prompt projection from Twin state.

Reads current state from HotStore and session manager, produces
an Anthropic XML system prompt block for Claude (the Actor).
No LLM client imports. Deterministic for same input state.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def project_coach(
    db_path: str,
    session_id: Optional[str] = None,
) -> str:
    """Project current Twin state as Anthropic XML system prompt.

    Reads from:
    - Hot Tier: last 5 traces for immediate context
    - Session manager: active session info
    - Patterns: count of detected patterns

    Args:
        db_path: Path to SQLite database.
        session_id: Optional session ID for session-specific context.

    Returns:
        Anthropic XML system prompt block string.
    """
    recent_traces = _get_recent_traces(db_path, limit=5)
    session_info = _get_session_info(db_path, session_id)
    pattern_count = _get_pattern_count(db_path)

    return _format_xml(
        recent_traces=recent_traces,
        session_info=session_info,
        pattern_count=pattern_count,
    )


def _get_recent_traces(db_path: str, limit: int = 5) -> list[dict]:
    """Get most recent hot traces."""
    if not Path(db_path).exists():
        return []

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(
            "SELECT trace_id, message, tags, domain, timestamp "
            "FROM hot_traces ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        rows = cursor.fetchall()
        return [
            {
                "trace_id": r[0],
                "message": r[1],
                "tags": json.loads(r[2]) if r[2] else [],
                "domain": r[3],
                "timestamp": r[4],
            }
            for r in rows
        ]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


def _get_session_info(db_path: str, session_id: Optional[str]) -> dict:
    """Get session info if available."""
    if not Path(db_path).exists():
        return {}

    conn = sqlite3.connect(db_path)
    try:
        if session_id:
            cursor = conn.execute(
                "SELECT session_id, exchange_count, domain, allostatic_tokens "
                "FROM sessions WHERE session_id = ? AND closed = 0",
                (session_id,),
            )
        else:
            cursor = conn.execute(
                "SELECT session_id, exchange_count, domain, allostatic_tokens "
                "FROM sessions WHERE closed = 0 "
                "ORDER BY last_active DESC LIMIT 1",
            )
        row = cursor.fetchone()
        if row:
            return {
                "session_id": row[0],
                "exchange_count": row[1],
                "domain": row[2],
                "allostatic_tokens": row[3],
            }
        return {}
    except sqlite3.OperationalError:
        return {}
    finally:
        conn.close()


def _get_pattern_count(db_path: str) -> int:
    """Get count of detected patterns."""
    if not Path(db_path).exists():
        return 0

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("SELECT COUNT(*) FROM patterns").fetchone()
        return row[0] if row else 0
    except sqlite3.OperationalError:
        return 0
    finally:
        conn.close()


def _format_xml(
    recent_traces: list[dict],
    session_info: dict,
    pattern_count: int,
) -> str:
    """Format Twin state as Anthropic XML system prompt block.

    Args:
        recent_traces: List of recent trace dicts.
        session_info: Session metadata dict.
        pattern_count: Number of detected patterns.

    Returns:
        Formatted XML string.
    """
    lines = ['<cognitive-twin-context version="8.0">']

    # Trust level (Phase 3 placeholder)
    lines.append("  <trust-level>0.0</trust-level>")

    # Session
    if session_info:
        lines.append("  <session>")
        lines.append(f'    <id>{session_info["session_id"]}</id>')
        lines.append(f'    <exchanges>{session_info["exchange_count"]}</exchanges>')
        lines.append(f'    <domain>{session_info["domain"]}</domain>')
        lines.append(
            f'    <allostatic-load>{session_info["allostatic_tokens"]}</allostatic-load>'
        )
        lines.append("  </session>")

    # Recent traces
    if recent_traces:
        lines.append("  <recent-traces>")
        for trace in recent_traces:
            tags_str = ", ".join(trace["tags"]) if trace["tags"] else ""
            lines.append(f"    <trace>")
            lines.append(f'      <domain>{trace["domain"]}</domain>')
            if tags_str:
                lines.append(f"      <tags>{tags_str}</tags>")
            lines.append(f'      <message>{trace["message"]}</message>')
            lines.append(f"    </trace>")
        lines.append("  </recent-traces>")

    # Patterns
    lines.append(f"  <patterns-detected>{pattern_count}</patterns-detected>")

    lines.append("</cognitive-twin-context>")
    return "\n".join(lines)
