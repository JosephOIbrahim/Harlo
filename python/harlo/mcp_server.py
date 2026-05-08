"""MCP server exposing Harlo tools to Claude Desktop.

Wraps the Twin's core functions (recall, store, coach, patterns, session)
as MCP tools over stdio transport. v8.0: No LLM client code — the Actor
(Claude) reasons, the Twin (Observer) stores and projects.

Bridges into the v9 cognitive_engine (src/) via a lazy singleton: every
tool call runs through process_exchange to keep exchange_index monotonic
and the schedule state up to date. Engine failures degrade gracefully
to v8-only behavior — every tool body still works without the engine.
"""

from __future__ import annotations

import atexit
import json
import logging
import threading
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

# ─── v9 cognitive engine bridge ─────────────────────────────────────────
# Lazy singleton; first tool call initializes. Init failure → False
# sentinel, callers fall back to v8-only. Two locks: _engine_lock
# guards init (FastMCP can dispatch concurrent calls), _exchange_lock
# serializes process_exchange (pxr.Usd.Stage writes are not thread-safe;
# exchange_index must be monotonic).

_engine = None
_engine_lock = threading.Lock()
_exchange_lock = threading.Lock()


def _get_engine():
    """Lazy-initialize the v9 cognitive engine. Returns None on failure.

    Once init fails, the sentinel sticks for the process lifetime — callers
    stay in v8-only mode rather than retrying every call.
    """
    global _engine
    if _engine is not None:
        return _engine if _engine else None
    with _engine_lock:
        if _engine is None:
            try:
                # src/ is not pip-installed; ensure it's importable
                import sys as _sys
                _root = str(PROJECT_ROOT)
                if _root not in _sys.path:
                    _sys.path.insert(0, _root)
                from src.cognitive_engine import CognitiveEngine
                _engine = CognitiveEngine(
                    stage_dir=str(DATA_DIR / "stages"),
                )
                atexit.register(_engine.close)
                logging.getLogger(__name__).info(
                    "v9 cognitive engine initialized (stage_type=%s)",
                    _engine.stage_type,
                )
            except Exception as e:
                logging.getLogger(__name__).warning(
                    "v9 engine init failed, falling back to v8-only: %s", e,
                )
                _engine = False  # sentinel — don't retry on subsequent calls
    return _engine if _engine else None


def _enrich(tool_name: str, tool_input: dict, session_id: str = "live"):
    """Run a v9 exchange and return the engine response dict, or None.

    Serializes exchanges with _exchange_lock so concurrent MCP tools don't
    race on USD writes or exchange_index increments. Engine errors are
    logged and swallowed; callers continue with their v8 path.
    """
    eng = _get_engine()
    if eng is None:
        return None
    try:
        from harlo.clock import now_iso
        with _exchange_lock:
            return eng.process_exchange(
                tool_name, tool_input, session_id,
                current_time_iso=now_iso(),
            )
    except Exception as e:
        logging.getLogger(__name__).warning(
            "v9 process_exchange failed for %s: %s", tool_name, e,
        )
        return None


def _v9_block(enrichment) -> dict:
    """Project an _enrich() result into a stable shape for tool responses."""
    if enrichment is None:
        return {}
    return {
        "v9": {
            "exchange_index": enrichment.get("exchange_index"),
            "delegate_id": enrichment.get("delegate_id"),
            "expert": enrichment.get("expert"),
            "prediction": enrichment.get("prediction"),
        }
    }


def _v9_status_block(enrichment) -> dict:
    """Rich v9 view used by twin_session_status: engine health + last
    observation state + schedule + routing.

    Falls back to the slim _v9_block shape if anything in the rich view
    fails (defensive — status calls shouldn't crash on enrichment errors).
    """
    if enrichment is None:
        return {}

    eng = _get_engine()
    if eng is None:
        return _v9_block(enrichment)

    try:
        health = eng.get_health()
    except Exception:
        health = {}

    last_obs = None
    try:
        if eng._observations:
            last_obs = eng._observations[-1]
    except Exception:
        last_obs = None

    block = {
        "exchange_index": enrichment.get("exchange_index"),
        "engine": {
            "stage_type": health.get("stage_type"),
            "predictor": health.get("predictor"),
            "observations_logged": health.get("observations_logged"),
            "delegates_registered": health.get("delegates_registered"),
            "memory_queue_size": health.get("memory_queue_size"),
            "pending_save": health.get("pending_save"),
        },
        "routing": {
            "delegate_id": enrichment.get("delegate_id"),
            "expert": enrichment.get("expert"),
        },
        "prediction": enrichment.get("prediction"),
    }

    if last_obs is not None:
        try:
            block["state"] = {
                "momentum": last_obs.state.momentum.name,
                "burnout": last_obs.state.burnout.name,
                "energy": last_obs.state.energy.name,
                "altitude": last_obs.state.altitude.name,
            }
            block["dynamics"] = {
                "burst_phase": last_obs.dynamics.burst_phase.name,
                "session_exchange_count": last_obs.dynamics.session_exchange_count,
                "exchanges_without_break": last_obs.dynamics.exchanges_without_break,
            }
            block["schedule"] = {
                "kind": last_obs.schedule.kind.name,
                "override_reason": last_obs.schedule.override_reason,
            }
            block["allostasis"] = {
                "load": round(float(last_obs.allostasis.load), 4),
                "trend": last_obs.allostasis.trend.name,
            }
        except Exception:
            pass

    return {"v9": block}

# Create server
server = FastMCP(
    name="harlo",
    instructions=(
        "Harlo v8.0 — biologically-architected AI memory. "
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
    """Search the Harlo's memory for traces matching a query.

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
        from harlo.encoder import semantic_recall

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
        from harlo.federated_recall import query_past_experience as qpe

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
        from harlo.hot_store import HotStore
        _hot_store = HotStore(str(DATA_DIR / "twin.db"))
    return _hot_store


def _get_injection_store():
    """Lazy singleton for InjectionStore."""
    global _injection_store
    if _injection_store is None:
        from harlo.injection import InjectionStore
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
        from harlo.coach import project_coach
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
    """Detect patterns in the Harlo's stored traces.

    Runs all pattern detection algorithms: recurring themes (semantic
    clustering via SDR hamming distance), temporal patterns (co-occurrence
    within 24h windows), and allostatic load escalation across sessions.
    """
    _ensure_data_dir()

    try:
        from modulation.detector import PatternDetector
    except ImportError:
        from harlo.modulation.detector import PatternDetector

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
    """Get current session information from the Harlo.

    Returns v8 active session list (exchange count, allostatic load, domain,
    timing) plus a v9 block carrying the cognitive engine's full live state:
    momentum, burnout, energy, burst phase, schedule, allostatic load, and
    the active routing decision. Schedule reflects the current wall-clock
    against the authored /schedule/ on the cognitive twin stage.
    """
    _ensure_data_dir()
    enrichment = _enrich("twin_session_status", {})

    try:
        from session.manager import SessionManager
    except ImportError:
        from harlo.session.manager import SessionManager

    try:
        mgr = SessionManager(DB_PATH)
        active = mgr.list_active()
        response = {
            "status": "ok",
            "active_sessions": [s.to_dict() for s in active],
            "count": len(active),
        }
        response.update(_v9_status_block(enrichment))
        return json.dumps(response, default=str)
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
        from harlo.elenchus_v8 import ElenchusQueue
        from harlo.trust import TrustLedger

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
    enrichment = _enrich("trigger_cognitive_recalibration", {})

    try:
        from harlo.trust.recalibration import trigger_recalibration
        result = trigger_recalibration(str(DATA_DIR / "twin.db"))
        if isinstance(result, dict):
            result.update(_v9_block(enrichment))
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


def main():
    """Entry point for the harlo console script."""
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
