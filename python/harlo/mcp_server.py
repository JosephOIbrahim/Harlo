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

# Resolve paths via the single source of truth (Rule: no divergent
# state directories between CLI and MCP entry points).
from harlo.daemon.config import DATA_DIR, DB_PATH as _DB_PATH, PROJECT_ROOT

DB_PATH = str(_DB_PATH)
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

# First-call-per-process banner gate. Daemon respawn resets the flag.
_banner_shown = False
_banner_lock = threading.Lock()


def _consume_banner() -> str:
    """Return HARLO_BANNER once per process; empty string thereafter."""
    global _banner_shown
    if _banner_shown:
        return ""
    with _banner_lock:
        if _banner_shown:
            return ""
        try:
            import sys as _sys
            _root = str(PROJECT_ROOT)
            if _root not in _sys.path:
                _sys.path.insert(0, _root)
            from src.branding import HARLO_BANNER
            _banner_shown = True
            return HARLO_BANNER
        except Exception:
            _banner_shown = True
            return ""


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
        "Use recall to search memory, store to save traces, "
        "coach for coaching context, patterns for pattern "
        "detection, status for session info. "
        "In user-facing prose, refer to 'Harlo' — never the tool names."
    ),
)


def _ensure_data_dir():
    """Ensure the data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


@server.tool(name="recall")
def twin_recall(query: str, depth: str = "normal") -> str:
    """Search the Harlo's memory for traces matching a query.

    Uses semantic SDR encoding (BGE + LSH) to find relevant stored traces
    via hamming distance. Returns context string, matching traces, and
    confidence score. The recall runs through the v9 engine so the
    exchange_index advances and schedule state stays current.

    Args:
        query: The search query text.
        depth: "normal" (top 5) or "deep" (top 15) recall depth.
    """
    _ensure_data_dir()
    enrichment = _enrich("twin_recall", {"query": query, "depth": depth})

    try:
        try:
            try:
                from encoder import semantic_recall
            except ImportError:
                from harlo.encoder import semantic_recall
            result = semantic_recall(DB_PATH, query, depth=depth)
        except ImportError:
            # Lean-bundle degrade: sentence_transformers is excluded from the
            # bundle on purpose. Route to the Rust lexical encoder, which
            # returns an identically-shaped dict (context/confidence/traces).
            from harlo import hippocampus
            result = hippocampus.py_recall(query, depth, str(DB_PATH))
        response = {
            "status": "ok",
            "context": result.get("context", ""),
            "traces": result.get("traces", []),
            "confidence": result.get("confidence", 0.0),
            "trace_count": len(result.get("traces", [])),
        }
        response.update(_v9_block(enrichment))
        return json.dumps(response, default=str)
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
    enrichment = _enrich("query_past_experience", {"query": query, "limit": limit})

    try:
        from harlo.federated_recall import query_past_experience as qpe

        results = qpe(str(DATA_DIR / "twin.db"), query, limit=limit)
        response = {
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
        }
        response.update(_v9_block(enrichment))
        return json.dumps(response, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@server.tool(name="persist_stage")
def persist_stage() -> str:
    """Persist the current cognitive state to a USD .usda file.

    Explicit persist entrypoint for the USD-proof trial verifier
    (`wave1_harness.check_populated_hierarchy`). Assembles a BrainStage from
    in-process state and writes via `harlo.usd_lite.persistence.write`. The
    v9 engine init path is NOT modified — persistence is an operation invoked
    at known times, not a side-effect of init.

    Returns a JSON object with: path (the .usda file written), tier_counts
    (session/entity/decision prim counts), decision_deferred (bool), and
    decision_deferred_reason (str).
    """
    _ensure_data_dir()
    enrichment = _enrich("persist_stage", {})
    try:
        from harlo.usd_lite.persistence import persist_current_brain
        result = persist_current_brain(DB_PATH, DATA_DIR / "stages")
        response = {"status": "ok", **result}
        response.update(_v9_block(enrichment))
        return json.dumps(response, default=str)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": f"{type(e).__name__}: {e}",
        })


_hot_store = None
_injection_store = None
# Guards the lazy init of _hot_store and _injection_store.  FastMCP can
# dispatch concurrent tool calls; without this lock two threads can both
# see None, both construct a fresh store, and the second write clobbers
# the first — leaving the first thread holding a stale reference to a
# connection that the second instance will eventually close, causing
# silent trace loss.
_store_lock = threading.Lock()


def _get_hot_store():
    """Lazy singleton for HotStore. No model loading."""
    global _hot_store
    if _hot_store is None:
        with _store_lock:
            if _hot_store is None:
                from harlo.hot_store import HotStore
                _hot_store = HotStore(str(DATA_DIR / "twin.db"))
    return _hot_store


def _get_injection_store():
    """Lazy singleton for InjectionStore."""
    global _injection_store
    if _injection_store is None:
        with _store_lock:
            if _injection_store is None:
                from harlo.injection import InjectionStore
                _injection_store = InjectionStore(str(DATA_DIR / "twin.db"))
    return _injection_store


@server.tool(name="store")
def twin_store(
    message: str,
    tags: list[str] | None = None,
    domain: str | None = None,
    injection_state: dict | None = None,
) -> str:
    """Store a memory trace. Zero-encoding hot path (<2ms).

    Writes to the v8 Hot Tier (L1) immediately with no model loading or SDR
    encoding (traces promoted to Warm Tier asynchronously by the Observer).
    The same call also drives a v9 process_exchange so the cognitive engine
    records a CognitiveObservation for this exchange — different stores,
    different concepts (v8 = the user-facing memory, v9 = engine telemetry).

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
    enrichment = _enrich(
        "twin_store",
        {"message": message, "tags": tags or [], "domain": domain or "general"},
    )

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

        result.update(_v9_block(enrichment))
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@server.tool(name="coach")
def twin_coach(session_id: str | None = None) -> str:
    """Get coaching context for the current session.

    Drives the full v9 cognitive exchange (author → DAG → route → delegate
    → observe → predict → save) and returns:
      - coach_block (v8): structured system prompt from twin.db with recent
        traces, trust level, and pending patterns
      - cognitive_context (v9): delegate-derived advisory string when the
        routed expert produces one
      - v9: live engine state — momentum/burnout/energy/burst, schedule
        kind (with override_reason), allostatic load, active routing
        (delegate_id, expert), and latest prediction. Schedule reflects
        the wall-clock against the authored /schedule/ on the stage —
        FAMILY hours route to restorer regardless of consent (mirrors
        the burnout RED safety pattern); OFF_HOURS reduces context budget.

    Args:
        session_id: Optional session ID for session-specific context.
    """
    _ensure_data_dir()
    enrichment = _enrich(
        "twin_coach",
        {"session_id": session_id} if session_id else {},
        session_id=session_id or "live",
    )

    try:
        from harlo.coach import project_coach
        result = project_coach(
            db_path=str(DATA_DIR / "twin.db"),
            session_id=session_id,
        )
        response = {
            "status": "ok",
            "coach_block": result,
        }
        if enrichment is not None:
            ctx = enrichment.get("cognitive_context") or ""
            if ctx:
                response["cognitive_context"] = ctx
        response.update(_v9_status_block(enrichment))
        return json.dumps(response, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@server.tool(name="patterns")
def twin_patterns() -> str:
    """Detect patterns in the Harlo's stored traces.

    Runs all pattern detection algorithms: recurring themes (semantic
    clustering via SDR hamming distance), temporal patterns (co-occurrence
    within 24h windows), and allostatic load escalation across sessions.
    """
    _ensure_data_dir()
    enrichment = _enrich("twin_patterns", {})

    try:
        try:
            from modulation.detector import PatternDetector
        except ImportError:
            from harlo.modulation.detector import PatternDetector
        detector = PatternDetector(DB_PATH)
        patterns = detector.detect_all()
        response = {
            "status": "ok",
            "patterns": [p.to_dict() for p in patterns],
            "count": len(patterns),
        }
        response.update(_v9_block(enrichment))
        return json.dumps(response, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@server.tool(name="status")
def twin_session_status() -> str:
    """Get current session information from the Harlo.

    Returns v8 active session list (exchange count, allostatic load, domain,
    timing) plus a v9 block carrying the cognitive engine's full live state:
    momentum, burnout, energy, burst phase, schedule, allostatic load, and
    the active routing decision. Schedule reflects the current wall-clock
    against the authored /schedule/ on the cognitive twin stage.

    On the first call after daemon spawn, the response carries a `banner`
    field with the HARLO ASCII boot banner. Render it verbatim, monospaced,
    above the rest of the response. Subsequent calls in the same daemon
    lifetime omit the field.
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
        response: dict = {}
        banner = _consume_banner()
        if banner:
            response["banner"] = banner
        response["status"] = "ok"
        response["active_sessions"] = [s.to_dict() for s in active]
        response["count"] = len(active)
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
    enrichment = _enrich("resolve_verifications", {"count": len(verdicts)})

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
        response = {
            "status": "ok",
            "resolved": results,
            "remaining_pending": queue.pending_count(),
            "trust_score": ledger.get_score(),
        }
        response.update(_v9_block(enrichment))
        return json.dumps(response)
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


@server.tool()
def stage_reload(force: bool = False) -> str:
    """Reload the cognitive twin stage from disk.

    Use after editing /schedule/ on disk via an external script (or any
    out-of-band stage write) when you want the daemon to absorb the change
    immediately, instead of waiting for the auto-detect that runs at the
    start of every process_exchange.

    The auto-detect is mtime-based — this explicit tool also supports a
    force=True mode for cases where mtime didn't advance but content did
    (e.g., file replaced atomically with the same mtime, clock skew, or
    you've just observed a clobber and want a guaranteed barrier).

    Returns JSON: {"status": "ok", "reloaded": bool, "reason": str}.
    """
    eng = _get_engine()
    if eng is None:
        return json.dumps({"status": "engine unavailable"})
    try:
        with _exchange_lock:
            sched_result = eng.reload_schedule(force=force)
            root_result = eng.reload_if_disk_changed(force=force)
        reloaded = bool(sched_result.get("reloaded") or root_result.get("reloaded"))
        reasons = []
        if sched_result.get("reloaded"):
            reasons.append(f"schedule: {sched_result.get('reason', '')}")
        if root_result.get("reloaded"):
            reasons.append(f"root: {root_result.get('reason', '')}")
        if not reloaded:
            # Surface whichever reason is most informative; default to schedule's.
            reason = sched_result.get("reason") or root_result.get("reason") or "no change"
        else:
            reason = "; ".join(reasons) if reasons else "absorbed external change"
        return json.dumps({"status": "ok", "reloaded": reloaded, "reason": reason})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


def _print_version() -> None:
    """Print the colored HARLO banner + version on stdout. CLI --version path."""
    import sys as _sys
    try:
        _root = str(PROJECT_ROOT)
        if _root not in _sys.path:
            _sys.path.insert(0, _root)
        from src.branding import HARLO_BANNER
    except Exception:
        HARLO_BANNER = "HARLO"
    try:
        from importlib.metadata import version as _v
        ver = _v("harlo")
    except Exception:
        ver = "unknown"
    # ANSI true-color (\033[38;2;R;G;Bm) — #FFB300
    if _sys.stdout.isatty():
        _sys.stdout.write(f"\033[38;2;255;179;0m{HARLO_BANNER}\033[0m\n")
    else:
        _sys.stdout.write(f"{HARLO_BANNER}\n")
    _sys.stdout.write(f"  harlo v{ver}\n")


def main():
    """Entry point for the harlo console script."""
    import sys as _sys
    if len(_sys.argv) > 1 and _sys.argv[1] in ("--version", "-V"):
        _print_version()
        return
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
