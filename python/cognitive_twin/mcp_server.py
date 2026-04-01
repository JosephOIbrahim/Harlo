"""MCP server exposing Cognitive Twin tools to Claude Desktop.

Wraps the Twin's core functions (recall, store, coach, patterns, session)
as MCP tools over stdio transport. v8.0: No LLM client code — the Actor
(Claude) reasons, the Twin (Observer) stores and projects.
"""

from __future__ import annotations

import json
import time
import uuid

from mcp.server import FastMCP

# Resolve paths before anything else
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = str(DATA_DIR / "twin.db")
TRUST_DELTA_VERIFIED = 0.02
TRUST_DELTA_REJECTED = -0.05

# Create server
server = FastMCP(
    name="cognitive-twin",
    instructions=(
        "Cognitive Twin v8.0 — biologically-architected AI memory. "
        "Use twin_recall to search memory, twin_store to save traces, "
        "twin_coach for coaching context, twin_patterns for pattern "
        "detection, twin_session_status for session info."
    ),
)


def _ensure_data_dir():
    """Ensure the data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


@server.tool()
def twin_recall(query: str, depth: str = "normal") -> str:
    """Search the Cognitive Twin's memory for traces matching a query.

    Uses semantic SDR encoding (BGE + LSH) to find relevant stored traces
    via hamming distance. Returns context string, matching traces, and
    confidence score.

    Args:
        query: The search query text.
        depth: "normal" (top 5) or "deep" (top 15) recall depth.
    """
    _ensure_data_dir()

    try:
        from encoder import semantic_recall
    except ImportError:
        from cognitive_twin.encoder import semantic_recall

    try:
        result = semantic_recall(DB_PATH, query, depth=depth)
        return json.dumps({
            "status": "ok",
            "context": result.get("context", ""),
            "traces": result.get("traces", []),
            "confidence": result.get("confidence", 0.0),
            "trace_count": len(result.get("traces", [])),
        }, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@server.tool()
def query_past_experience(query: str, limit: int = 10) -> str:
    """Federated recall across Hot and Warm memory tiers.

    Searches both the Hot Tier (FTS5 plaintext, immediate) and Warm Tier
    (SDR Hamming, semantic) simultaneously, merging and deduplicating results.
    Satisfies both "what did I just say?" and "what patterns exist?" queries.

    Args:
        query: Search query text.
        limit: Maximum results to return (default 10).
    """
    _ensure_data_dir()

    try:
        from cognitive_twin.federated_recall import query_past_experience as qpe

        results = qpe(str(DATA_DIR / "twin.db"), query, limit=limit)
        return json.dumps({
            "status": "ok",
            "results": [
                {
                    "trace_id": r.trace_id,
                    "message": r.message,
                    "score": r.score,
                    "tier": r.tier,
                    "domain": r.domain,
                    "tags": r.tags,
                }
                for r in results
            ],
            "count": len(results),
        }, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


_hot_store = None
_injection_store = None


def _get_hot_store():
    """Lazy singleton for HotStore. No model loading."""
    global _hot_store
    if _hot_store is None:
        from cognitive_twin.hot_store import HotStore
        _hot_store = HotStore(str(DATA_DIR / "twin.db"))
    return _hot_store


def _get_injection_store():
    """Lazy singleton for InjectionStore."""
    global _injection_store
    if _injection_store is None:
        from cognitive_twin.injection import InjectionStore
        _injection_store = InjectionStore(str(DATA_DIR / "twin.db"))
    return _injection_store


@server.tool()
def twin_store(
    message: str,
    tags: list[str] | None = None,
    domain: str | None = None,
    injection_state: dict | None = None,
) -> str:
    """Store a memory trace. Zero-encoding hot path (<2ms).

    Writes to the Hot Tier (L1) immediately with no model loading or SDR
    encoding. Traces are promoted to Warm Tier (L2) asynchronously by the
    Observer process.

    Optionally stores an injection state transition alongside the trace.

    Args:
        message: The text content to store as a memory trace.
        tags: Optional list of tags for categorization.
        domain: Optional domain label (e.g. "technical", "personal").
        injection_state: Optional injection state dict with keys:
            profile (str), s_nm (float), alpha (float),
            exchange_count (int), transition (str), session_id (str).
    """
    _ensure_data_dir()

    try:
        hot = _get_hot_store()
        trace_id = hot.store(
            message=message,
            tags=tags or [],
            domain=domain or "general",
        )

        result = {
            "status": "stored",
            "trace_id": trace_id,
            "tier": "hot",
            "encoded": False,
        }

        # Store injection state if provided
        if injection_state is not None:
            inj = _get_injection_store()
            inj_trace_id = inj.store(
                profile=injection_state["profile"],
                s_nm=injection_state["s_nm"],
                alpha=injection_state["alpha"],
                exchange_count=injection_state["exchange_count"],
                transition=injection_state["transition"],
                session_id=injection_state.get("session_id", ""),
            )
            result["injection_trace_id"] = inj_trace_id

        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@server.tool()
def twin_coach(session_id: str | None = None) -> str:
    """Get coaching context for the current session.

    Returns a structured system prompt block built from the Twin's current
    state: recent traces, session info, trust level, and pending patterns.
    The Actor (Claude) uses this to inform its reasoning.

    Args:
        session_id: Optional session ID for session-specific context.
    """
    _ensure_data_dir()

    try:
        from cognitive_twin.coach import project_coach
        result = project_coach(
            db_path=str(DATA_DIR / "twin.db"),
            session_id=session_id,
        )
        return json.dumps({
            "status": "ok",
            "coach_block": result,
        })
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@server.tool()
def twin_patterns() -> str:
    """Detect patterns in the Cognitive Twin's stored traces.

    Runs all pattern detection algorithms: recurring themes (semantic
    clustering via SDR hamming distance), temporal patterns (co-occurrence
    within 24h windows), and allostatic load escalation across sessions.
    """
    _ensure_data_dir()

    try:
        from modulation.detector import PatternDetector
    except ImportError:
        from cognitive_twin.modulation.detector import PatternDetector

    try:
        detector = PatternDetector(DB_PATH)
        patterns = detector.detect_all()
        return json.dumps({
            "status": "ok",
            "patterns": [p.to_dict() for p in patterns],
            "count": len(patterns),
        }, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@server.tool()
def twin_session_status() -> str:
    """Get current session information from the Cognitive Twin.

    Returns all active (non-closed, non-expired) sessions with their
    exchange count, allostatic token load, active domain, and timing.
    """
    _ensure_data_dir()

    try:
        from session.manager import SessionManager
    except ImportError:
        from cognitive_twin.session.manager import SessionManager

    try:
        mgr = SessionManager(DB_PATH)
        active = mgr.list_active()
        return json.dumps({
            "status": "ok",
            "active_sessions": [s.to_dict() for s in active],
            "count": len(active),
        }, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@server.tool()
def resolve_verifications(verdicts: list[dict]) -> str:
    """Resolve pending Elenchus verification claims.

    The Actor evaluates pending claims and submits boolean verdicts.
    Each verdict dict must have 'claim_id' (str) and 'verdict' (bool).

    Args:
        verdicts: List of {"claim_id": str, "verdict": bool} dicts.
    """
    _ensure_data_dir()

    try:
        from cognitive_twin.elenchus_v8 import ElenchusQueue
        from cognitive_twin.trust import TrustLedger

        queue = ElenchusQueue(str(DATA_DIR / "twin.db"))
        ledger = TrustLedger(str(DATA_DIR / "twin.db"))
        results = []
        for v in verdicts:
            claim = queue.resolve(v["claim_id"], v["verdict"])
            delta = 0.0
            if claim is not None:
                delta = TRUST_DELTA_VERIFIED if v["verdict"] else TRUST_DELTA_REJECTED
                ledger.update(delta)
            results.append({
                "claim_id": v["claim_id"],
                "resolved": claim is not None,
                "status": claim.status if claim else "not_found",
                "trust_delta": delta,
            })
        return json.dumps({
            "status": "ok",
            "resolved": results,
            "remaining_pending": queue.pending_count(),
            "trust_score": ledger.get_score(),
        })
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@server.tool()
def trigger_cognitive_recalibration() -> str:
    """Trigger cognitive recalibration — reset intake and trust.

    Clears the cognitive profile and resets trust score to 0.0.
    Use when the user indicates a major life or role change.
    Re-triggerable: can be called multiple times.
    """
    _ensure_data_dir()

    try:
        from cognitive_twin.trust.recalibration import trigger_recalibration
        result = trigger_recalibration(str(DATA_DIR / "twin.db"))
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


def main():
    """Entry point for the cognitive-twin console script."""
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
