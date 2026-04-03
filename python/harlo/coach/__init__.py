"""Coach Core — system prompt projection from Twin state.

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
    - Injection store: recent injection state history

    Args:
        db_path: Path to SQLite database.
        session_id: Optional session ID for session-specific context.

    Returns:
        Anthropic XML system prompt block string.
    """
    recent_traces = _get_recent_traces(db_path, limit=5)
    session_info = _get_session_info(db_path, session_id)
    pattern_count = _get_pattern_count(db_path)
    trust_score = _get_trust_score(db_path)
    pending_claims = _get_pending_claims(db_path)
    injection_history = _get_injection_history(db_path)

    return _format_xml(
        recent_traces=recent_traces,
        session_info=session_info,
        pattern_count=pattern_count,
        trust_score=trust_score,
        pending_claims=pending_claims,
        injection_history=injection_history,
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


def _get_trust_score(db_path: str) -> float:
    """Get current trust score."""
    try:
        from harlo.trust import TrustLedger
        ledger = TrustLedger(db_path)
        return ledger.get_score()
    except Exception:
        return 0.0


def _get_pending_claims(db_path: str) -> list[dict]:
    """Get pending Elenchus claims for Coach injection."""
    try:
        from harlo.elenchus_v8 import ElenchusQueue
        queue = ElenchusQueue(db_path)
        claims = queue.get_pending(limit=5)
        return [
            {"claim_id": c.claim_id, "claim_text": c.claim_text}
            for c in claims
        ]
    except Exception:
        return []


def _get_injection_history(db_path: str) -> list[dict]:
    """Get recent injection state transitions."""
    if not Path(db_path).exists():
        return []

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(
            "SELECT profile, alpha, exchange_count, transition, session_id, timestamp "
            "FROM injection_traces ORDER BY timestamp DESC LIMIT 10",
        )
        rows = cursor.fetchall()
        return [
            {
                "profile": r[0],
                "alpha": r[1],
                "exchange_count": r[2],
                "transition": r[3],
                "session_id": r[4],
                "timestamp": r[5],
            }
            for r in rows
        ]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


def _format_xml(
    recent_traces: list[dict],
    session_info: dict,
    pattern_count: int,
    trust_score: float = 0.0,
    pending_claims: list[dict] | None = None,
    injection_history: list[dict] | None = None,
) -> str:
    """Format Twin state as Anthropic XML system prompt block.

    Args:
        recent_traces: List of recent trace dicts.
        session_info: Session metadata dict.
        pattern_count: Number of detected patterns.

    Returns:
        Formatted XML string.
    """
    lines = ['<harlo-context version="8.0">']

    # Trust level
    lines.append(f"  <trust-level>{trust_score:.2f}</trust-level>")

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

    # Pending claims
    if pending_claims:
        lines.append("  <pending-verifications>")
        for claim in pending_claims:
            lines.append(f'    <claim id="{claim["claim_id"]}">')
            lines.append(f'      {claim["claim_text"]}')
            lines.append(f"    </claim>")
        lines.append("  </pending-verifications>")

    # Injection history (only when there IS history)
    if injection_history:
        lines.append("  <injection-history>")

        # Last 3 sessions summary
        activations = [h for h in injection_history if h["transition"] == "activated"]
        if activations:
            recent_profiles = [a["profile"] for a in activations[:3]]
            recent_exchanges = [str(a["exchange_count"]) for a in activations[:3]]
            summaries = [
                f'{p} ({e} exc)' for p, e in zip(recent_profiles, recent_exchanges)
            ]
            lines.append(f"    <recent-sessions>{', '.join(summaries)}</recent-sessions>")

            # Most frequent profile
            freq: dict[str, int] = {}
            for a in activations:
                freq[a["profile"]] = freq.get(a["profile"], 0) + 1
            most_freq = max(freq, key=freq.get)  # type: ignore[arg-type]
            lines.append(
                f"    <most-frequent-profile>"
                f"{most_freq} (used {freq[most_freq]} of last {len(activations)} activations)"
                f"</most-frequent-profile>"
            )

        # Current/last injection state
        last = injection_history[0]
        lines.append(
            f'    <last-injection profile="{last["profile"]}" '
            f'transition="{last["transition"]}" '
            f'alpha="{last["alpha"]:.2f}" '
            f'exchange="{last["exchange_count"]}"/>'
        )

        lines.append("  </injection-history>")

    # Patterns
    lines.append(f"  <patterns-detected>{pattern_count}</patterns-detected>")

    lines.append("</harlo-context>")
    return "\n".join(lines)
