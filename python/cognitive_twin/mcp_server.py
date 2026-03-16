"""MCP server exposing Cognitive Twin tools to Claude Desktop.

Wraps the Twin's core functions (recall, store, ask, patterns, session)
as MCP tools over stdio transport.
"""

from __future__ import annotations

import json
import os
import time
import uuid

from mcp.server import FastMCP

# Resolve paths before anything else
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = str(DATA_DIR / "twin.db")

# Create server
server = FastMCP(
    name="cognitive-twin",
    instructions=(
        "Cognitive Twin v6.0 — biologically-architected AI memory. "
        "Use twin_recall to search memory, twin_store to save traces, "
        "twin_ask for full generation pipeline, twin_patterns for "
        "pattern detection, twin_session_status for session info."
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
def twin_store(message: str, tags: list[str] | None = None, domain: str | None = None) -> str:
    """Store a new trace in the Cognitive Twin's memory.

    Encodes the message using the semantic encoder (BGE + LSH → 2048-bit SDR)
    and persists it to the trace database.

    Args:
        message: The text content to store as a memory trace.
        tags: Optional list of tags for categorization.
        domain: Optional domain label (e.g. "technical", "personal").
    """
    _ensure_data_dir()

    try:
        from encoder import semantic_store
    except ImportError:
        from cognitive_twin.encoder import semantic_store

    trace_id = uuid.uuid4().hex[:16]

    try:
        semantic_store(
            db_path=DB_PATH,
            trace_id=trace_id,
            message=message,
            tags=tags,
            domain=domain,
            source="mcp",
        )
        return json.dumps({
            "status": "ok",
            "trace_id": trace_id,
            "message": message,
            "stored": True,
        })
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@server.tool()
def twin_ask(question: str) -> str:
    """Run the full Cognitive Twin generation pipeline.

    Pipeline: semantic recall → context injection → LLM generation →
    Aletheia GVR verification → response. Requires ANTHROPIC_API_KEY
    to be set in the environment.

    Args:
        question: The question or prompt to process.
    """
    _ensure_data_dir()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return json.dumps({
            "status": "error",
            "error": "ANTHROPIC_API_KEY not set. Set it in your environment to use twin_ask.",
        })

    try:
        try:
            from provider import get_provider
            from brainstem.generate import generate
        except ImportError:
            from cognitive_twin.provider import get_provider
            from cognitive_twin.brainstem.generate import generate

        provider = get_provider("claude")
        result = generate(
            query=question,
            provider=provider,
            db_path=DB_PATH,
            domain="general",
            encoder_type="semantic",
            recall_depth="normal",
        )
        return json.dumps({
            "status": "ok",
            "response": result.get("response", ""),
            "verification": result.get("verification", {}),
            "confidence": result.get("confidence", 0.0),
            "model": result.get("model", "unknown"),
            "context_traces": len(result.get("context_traces", [])),
        }, default=str)
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


if __name__ == "__main__":
    server.run(transport="stdio")
