"""Command routing for the Cognitive Twin daemon.

Routes incoming commands to the appropriate subsystem.
"""

import json


def route_command(command: str, args: dict) -> dict:
    """Route a command to its handler and return the result.

    Args:
        command: The command name (e.g., "recall", "store", "status")
        args: Command arguments as a dictionary

    Returns:
        Result dictionary with at minimum a "status" key.
    """
    router = {
        "ask": _handle_ask,
        "detect": _handle_detect,
        "health": _handle_health,
        "recall": _handle_recall,
        "session_close": _handle_session_close,
        "session_list": _handle_session_list,
        "session_start": _handle_session_start,
        "session_status": _handle_session_status,
        "store": _handle_store,
        "consolidate": _handle_consolidate,
        "trace": _handle_trace,
        "status": _handle_status,
        "ping": _handle_ping,
        "resolve": _handle_resolve,
        "compose": _handle_compose,
        "conflicts": _handle_conflicts,
        "audit": _handle_audit,
        "verify": _handle_verify,
        "stuck": _handle_stuck,
        "deferred": _handle_deferred,
        "reflect": _handle_reflect,
        "inquire": _handle_inquire,
        "boundaries": _handle_boundaries,
        "profile": _handle_profile,
        "modulate": _handle_modulate,
        "mode": _handle_mode,
        "plan": _handle_plan,
        "consent": _handle_consent,
        "execute": _handle_execute,
        "undo": _handle_undo,
        "motor_reflexes": _handle_motor_reflexes,
        "reflexes": _handle_reflexes,
        "export": _handle_export,
        "import": _handle_import,
        "inquiries": _handle_inquiries,
    }

    handler = router.get(command)
    if handler is None:
        return {"status": "error", "message": f"Unknown command: {command}"}

    return handler(args)


def _get_session_manager():
    """Get a SessionManager instance using daemon config."""
    from ..daemon.config import DB_PATH, SESSION_TIMEOUT_S, ensure_data_dirs
    from ..session import SessionManager

    ensure_data_dirs()
    return SessionManager(db_path=str(DB_PATH), timeout_s=SESSION_TIMEOUT_S)


def _handle_ask(args: dict) -> dict:
    """Handle ask command: full Twin generation loop with session tracking."""
    try:
        from ..daemon.config import DB_PATH, ENCODER_TYPE, ensure_data_dirs

        ensure_data_dirs()
        question = args.get("question", "")
        provider_name = args.get("provider", "claude")
        depth = args.get("depth", "normal")
        domain = args.get("domain", "general")
        encoder = args.get("encoder", ENCODER_TYPE)
        session_id = args.get("session_id")

        # Session management
        mgr = _get_session_manager()
        session = mgr.get_or_create(session_id, domain=domain, encoder_type=encoder)

        from ..provider import get_provider
        from ..bridge.generate import generate

        provider = get_provider(provider_name)

        # Pass conversation history as context
        history = session.history if session.history else None

        result = generate(
            query=question,
            provider=provider,
            db_path=str(DB_PATH),
            domain=domain,
            encoder_type=encoder,
            recall_depth=depth,
        )

        # Record exchange in session
        response_text = result.get("response", "")
        token_estimate = len(question.split()) + len(response_text.split())
        mgr.record_exchange(session.session_id, question, response_text, tokens=token_estimate)

        result["session_id"] = session.session_id
        return {"status": "ok", "result": result}
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    except ImportError as e:
        return {"status": "error", "message": f"Provider not available: {e}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _handle_detect(args: dict) -> dict:
    """Handle detect command: run pattern detection on stored traces."""
    try:
        from ..daemon.config import DB_PATH, ensure_data_dirs

        ensure_data_dirs()
        threshold = args.get("threshold", 100)
        min_cluster = args.get("min_cluster", 3)

        from ..modulation.detector import PatternDetector
        detector = PatternDetector(str(DB_PATH), threshold=threshold)
        patterns = detector.detect_all(min_cluster_size=min_cluster)

        return {
            "status": "ok",
            "result": {
                "patterns": [p.to_dict() for p in patterns],
                "count": len(patterns),
            },
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _handle_session_start(args: dict) -> dict:
    """Handle session_start command: create a new session."""
    try:
        domain = args.get("domain", "general")
        encoder = args.get("encoder_type", "semantic")
        mgr = _get_session_manager()
        session = mgr.create(domain=domain, encoder_type=encoder)
        return {"status": "ok", "result": session.to_dict()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _handle_session_close(args: dict) -> dict:
    """Handle session_close command: close a session and trigger DMN teardown."""
    try:
        session_id = args.get("session_id", "")
        if not session_id:
            return {"status": "error", "message": "session_id is required"}
        mgr = _get_session_manager()
        session = mgr.close(session_id)
        if session is None:
            return {"status": "error", "message": f"Session not found: {session_id}"}
        return {"status": "ok", "result": session.to_dict()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _handle_session_status(args: dict) -> dict:
    """Handle session_status command: return session info."""
    try:
        session_id = args.get("session_id", "")
        if not session_id:
            return {"status": "error", "message": "session_id is required"}
        mgr = _get_session_manager()
        session = mgr.get(session_id)
        if session is None:
            return {"status": "error", "message": f"Session not found: {session_id}"}
        return {"status": "ok", "result": session.to_dict()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _handle_session_list(args: dict) -> dict:
    """Handle session_list command: list active sessions."""
    try:
        mgr = _get_session_manager()
        sessions = mgr.list_active()
        return {
            "status": "ok",
            "result": {
                "sessions": [s.to_dict() for s in sessions],
                "count": len(sessions),
            },
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _handle_health(args: dict) -> dict:
    """Handle health command: return daemon health status."""
    try:
        from ..daemon.lifecycle import get_health
        return {"status": "ok", "result": get_health()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _handle_recall(args: dict) -> dict:
    """Handle recall command via Hippocampus Rust engine or semantic encoder."""
    try:
        from ..daemon.config import DB_PATH, ENCODER_TYPE, ensure_data_dirs

        ensure_data_dirs()
        query = args.get("query", "")
        depth = args.get("depth", "normal")
        encoder = args.get("encoder", ENCODER_TYPE)

        if encoder == "semantic":
            from ..encoder import semantic_recall
            result = semantic_recall(str(DB_PATH), query, depth=depth)
            return {"status": "ok", "result": result}

        import hippocampus
        result = hippocampus.py_recall(query, depth=depth, db_path=str(DB_PATH))
        return {"status": "ok", "result": result}
    except ImportError:
        return {"status": "error", "message": "hippocampus module not built. Run: maturin develop"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _handle_store(args: dict) -> dict:
    """Handle store trace command."""
    try:
        from ..daemon.config import DB_PATH, ENCODER_TYPE, ensure_data_dirs

        ensure_data_dirs()
        trace_id = args.get("trace_id", "")
        message = args.get("message", "")
        tags = args.get("tags")
        domain = args.get("domain")
        source = args.get("source")
        encoder = args.get("encoder", ENCODER_TYPE)

        if encoder == "semantic":
            from ..encoder import semantic_store
            semantic_store(
                str(DB_PATH), trace_id, message,
                tags=tags, domain=domain, source=source,
            )
            return {"status": "ok", "trace_id": trace_id}

        import hippocampus
        hippocampus.py_store_trace(
            trace_id, message,
            tags=tags, domain=domain, source=source,
            db_path=str(DB_PATH)
        )
        return {"status": "ok", "trace_id": trace_id}
    except ImportError:
        return {"status": "error", "message": "hippocampus module not built"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _handle_consolidate(args: dict) -> dict:
    """Handle consolidate command: apoptosis + graph consolidation."""
    try:
        import hippocampus
        from ..daemon.config import DB_PATH, DEFAULT_EPSILON, ensure_data_dirs

        ensure_data_dirs()
        db = str(DB_PATH)

        micro_result = hippocampus.py_microglia(epsilon=DEFAULT_EPSILON, db_path=db)
        consol_result = hippocampus.py_consolidate(min_weight=0.5, db_path=db)

        return {
            "status": "ok",
            "microglia": micro_result,
            "consolidation": consol_result,
        }
    except ImportError:
        return {"status": "error", "message": "hippocampus module not built. Run: maturin develop"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _handle_trace(args: dict) -> dict:
    """Handle trace lookup by ID."""
    try:
        import hippocampus
        from ..daemon.config import DB_PATH, ensure_data_dirs

        ensure_data_dirs()
        trace_id = args.get("trace_id", "")

        # Use recall with the trace_id as query to find the specific trace
        result = hippocampus.py_recall(trace_id, depth="deep", db_path=str(DB_PATH))
        traces = result.get("traces", [])

        # Find exact match by trace_id
        for t in traces:
            if t.get("trace_id") == trace_id:
                return {"status": "ok", "result": t}

        # If no exact match, return first result or empty
        if traces:
            return {"status": "ok", "result": traces[0]}

        return {"status": "error", "message": f"Trace not found: {trace_id}"}
    except ImportError:
        return {"status": "error", "message": "hippocampus module not built. Run: maturin develop"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _handle_status(args: dict) -> dict:
    """Handle status command."""
    return {
        "status": "ok",
        "version": "6.0.0",
        "state": "running",
    }


def _handle_ping(args: dict) -> dict:
    """Handle ping command."""
    return {"status": "ok", "pong": True}


def _handle_resolve(args: dict) -> dict:
    """Handle resolve command: resolve a composition stage using LIVRPS."""
    try:
        from ..daemon.config import STAGES_DIR, ensure_data_dirs

        ensure_data_dirs()
        stage_id = args.get("stage_id", "")
        if not stage_id:
            return {"status": "error", "message": "stage_id is required"}

        stage_path = STAGES_DIR / f"{stage_id}.json"
        if not stage_path.exists():
            return {"status": "error", "message": f"Stage not found: {stage_id}"}

        stage_data = json.loads(stage_path.read_text(encoding="utf-8"))

        from ..composition.stage import MerkleStage
        from ..composition.resolver import resolve, Resolution
        from ..composition.audit import log_resolution

        stage = MerkleStage.from_dict(stage_data)
        resolution = resolve(stage)
        log_resolution(resolution, stage_id)

        return {"status": "ok", "result": resolution.to_dict()}
    except ImportError as e:
        return {"status": "error", "message": f"Composition module not available: {e}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _handle_compose(args: dict) -> dict:
    """Handle compose command: add a layer to a composition stage."""
    try:
        from ..daemon.config import STAGES_DIR, ensure_data_dirs

        ensure_data_dirs()
        stage_id = args.get("stage_id", "")
        layer_data = args.get("layer_data", {})
        arc_type = args.get("arc_type", "")

        if not stage_id:
            return {"status": "error", "message": "stage_id is required"}
        if not arc_type:
            return {"status": "error", "message": "arc_type is required"}

        from ..composition.stage import MerkleStage
        from ..composition.layer import Layer, ArcType

        stage_path = STAGES_DIR / f"{stage_id}.json"

        # Load existing stage or create new one
        if stage_path.exists():
            stage_data = json.loads(stage_path.read_text(encoding="utf-8"))
            stage = MerkleStage.from_dict(stage_data)
        else:
            stage = MerkleStage(stage_id=stage_id)

        # Create and add layer
        arc = ArcType(arc_type)
        layer = Layer(data=layer_data, arc_type=arc)
        stage.add_layer(layer)

        # Save stage
        stage_path.write_text(
            json.dumps(stage.to_dict(), indent=2),
            encoding="utf-8",
        )

        return {
            "status": "ok",
            "result": {
                "layer_id": layer.layer_id,
                "layer_count": len(stage.layers),
            },
        }
    except ImportError as e:
        return {"status": "error", "message": f"Composition module not available: {e}"}
    except ValueError as e:
        return {"status": "error", "message": f"Invalid arc_type: {e}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _handle_conflicts(args: dict) -> dict:
    """Handle conflicts command: detect conflicts in a composition stage."""
    try:
        from ..daemon.config import STAGES_DIR, ensure_data_dirs

        ensure_data_dirs()
        stage_id = args.get("stage_id", "")
        if not stage_id:
            return {"status": "error", "message": "stage_id is required"}

        stage_path = STAGES_DIR / f"{stage_id}.json"
        if not stage_path.exists():
            return {"status": "error", "message": f"Stage not found: {stage_id}"}

        stage_data = json.loads(stage_path.read_text(encoding="utf-8"))

        from ..composition.stage import MerkleStage
        from ..composition.conflicts import detect_conflicts

        stage = MerkleStage.from_dict(stage_data)
        conflict_list = detect_conflicts(stage)

        return {
            "status": "ok",
            "result": {
                "conflicts": [c.to_dict() if hasattr(c, "to_dict") else c for c in conflict_list],
                "layer_count": len(stage.layers),
            },
        }
    except ImportError as e:
        return {"status": "error", "message": f"Composition module not available: {e}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _handle_audit(args: dict) -> dict:
    """Handle audit command: read audit entries for a stage or entry ID."""
    try:
        from ..composition.audit import read_audit, read_audit_for_stage

        audit_id = args.get("id", "")
        if not audit_id:
            return {"status": "error", "message": "id is required"}

        # Try stage-level audit first, fall back to specific entry
        entries = read_audit_for_stage(audit_id)
        if not entries:
            entry = read_audit(audit_id)
            entries = [entry] if entry else []

        return {
            "status": "ok",
            "result": {
                "entries": [e.to_dict() if hasattr(e, "to_dict") else e for e in entries],
            },
        }
    except ImportError as e:
        return {"status": "error", "message": f"Composition module not available: {e}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _handle_verify(args: dict) -> dict:
    """Handle verify command: verify a composition stage resolution via Aletheia."""
    try:
        from ..daemon.config import STAGES_DIR, ensure_data_dirs

        ensure_data_dirs()
        stage_id = args.get("stage_id", "")
        depth = args.get("depth", "standard")

        if not stage_id:
            return {"status": "error", "message": "stage_id is required"}

        stage_path = STAGES_DIR / f"{stage_id}.json"
        if not stage_path.exists():
            return {"status": "error", "message": f"Stage not found: {stage_id}"}

        stage_data = json.loads(stage_path.read_text(encoding="utf-8"))

        from ..composition.stage import MerkleStage
        from ..composition.resolver import resolve
        from ..aletheia.protocol import run_gvr
        from ..aletheia.depth import get_depth

        stage = MerkleStage.from_dict(stage_data)
        resolution = resolve(stage)
        depth_config = get_depth(depth)
        verification = run_gvr(stage, resolution, depth_config)

        return {"status": "ok", "result": verification.to_dict()}
    except ImportError as e:
        return {"status": "error", "message": f"Aletheia module not available: {e}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _handle_stuck(args: dict) -> dict:
    """Handle stuck command: return UNPROVABLE/DEFERRED items from deferred_verifications."""
    try:
        from ..daemon.config import DEFERRED_DIR, ensure_data_dirs

        ensure_data_dirs()
        items = []

        if DEFERRED_DIR.exists():
            for path in sorted(DEFERRED_DIR.glob("*.json")):
                try:
                    entry = json.loads(path.read_text(encoding="utf-8"))
                    state = entry.get("state", "")
                    if state in ("UNPROVABLE", "DEFERRED"):
                        items.append(entry)
                except (json.JSONDecodeError, OSError):
                    continue

        return {"status": "ok", "result": {"items": items}}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _handle_deferred(args: dict) -> dict:
    """Handle deferred command: list or flush deferred verifications."""
    try:
        from ..daemon.config import DEFERRED_DIR, STAGES_DIR, ensure_data_dirs

        ensure_data_dirs()
        flush = args.get("flush", False)

        if not DEFERRED_DIR.exists():
            if flush:
                return {"status": "ok", "result": {"flushed": 0, "results": []}}
            return {"status": "ok", "result": {"items": []}}

        entries = []
        for path in sorted(DEFERRED_DIR.glob("*.json")):
            try:
                entry = json.loads(path.read_text(encoding="utf-8"))
                entry["_path"] = str(path)
                entries.append(entry)
            except (json.JSONDecodeError, OSError):
                continue

        if not flush:
            # Strip internal path before returning
            for entry in entries:
                entry.pop("_path", None)
            return {"status": "ok", "result": {"items": entries}}

        # Flush: re-run verification for each deferred entry
        from pathlib import Path

        from ..composition.stage import MerkleStage
        from ..composition.resolver import resolve
        from ..aletheia.protocol import run_gvr
        from ..aletheia.depth import get_depth

        results = []
        for entry in entries:
            stage_id = entry.get("stage_id", "")
            entry_path = entry.get("_path", "")

            stage_path = STAGES_DIR / f"{stage_id}.json"
            if not stage_path.exists():
                results.append({"stage_id": stage_id, "state": "ERROR", "reason": "Stage not found"})
                continue

            try:
                stage_data = json.loads(stage_path.read_text(encoding="utf-8"))
                stage = MerkleStage.from_dict(stage_data)
                resolution = resolve(stage)
                depth_config = get_depth("standard")
                verification = run_gvr(stage, resolution, depth_config)
                vdict = verification.to_dict()
                results.append({"stage_id": stage_id, "state": vdict.get("state", "UNKNOWN")})

                # Update or remove the deferred file based on result
                deferred_path = Path(entry_path)
                if vdict.get("state") not in ("UNPROVABLE", "DEFERRED"):
                    deferred_path.unlink(missing_ok=True)
                else:
                    deferred_path.write_text(
                        json.dumps(vdict, indent=2), encoding="utf-8"
                    )
            except Exception as e:
                results.append({"stage_id": stage_id, "state": "ERROR", "reason": str(e)})

        return {"status": "ok", "result": {"flushed": len(results), "results": results}}
    except ImportError as e:
        return {"status": "error", "message": f"Aletheia module not available: {e}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _handle_reflect(args: dict) -> dict:
    """Handle reflect command: run DMN reflection synthesis."""
    return {"status": "ok", "result": {"insights": [], "synthesis": "No reflection data yet."}}


def _handle_inquire(args: dict) -> dict:
    """Handle inquire command: detect patterns and surface as inquiries."""
    try:
        from ..daemon.config import DB_PATH, ensure_data_dirs

        ensure_data_dirs()
        depth = args.get("depth", "standard")

        from ..modulation.detector import PatternDetector
        detector = PatternDetector(str(DB_PATH))
        patterns = detector.detect_all()

        inquiries = [p.to_dict() for p in patterns]
        return {"status": "ok", "result": {"inquiries": inquiries, "depth": depth}}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _handle_boundaries(args: dict) -> dict:
    """Handle boundaries command: list/add/remove boundaries."""
    action = args.get("action", "list")
    topic = args.get("topic", "")
    # Stub: return empty boundaries list
    return {"status": "ok", "result": {"boundaries": [], "action": action}}


def _handle_profile(args: dict) -> dict:
    """Handle profile command: show current modulation profile."""
    return {"status": "ok", "result": {
        "curiosity": 0.5, "caution": 0.5, "verbosity": 0.5, "empathy": 0.5,
    }}


def _handle_modulate(args: dict) -> dict:
    """Handle modulate command: adjust modulation parameters."""
    params = args.get("params", {})
    return {"status": "ok", "result": {"updated": params}}


def _handle_mode(args: dict) -> dict:
    """Handle mode command: switch operational mode."""
    target = args.get("mode", "utility")
    return {"status": "ok", "result": {"mode": target}}


def _handle_plan(args: dict) -> dict:
    """Handle plan command: generate action plan."""
    intent = args.get("intent", "")
    return {"status": "ok", "result": {"plan_id": "plan-stub", "intent": intent, "steps": []}}


def _handle_consent(args: dict) -> dict:
    """Handle consent command: manage motor consent."""
    action = args.get("action", "show")
    return {"status": "ok", "result": {"level": action if action != "show" else "none", "action": action}}


def _handle_execute(args: dict) -> dict:
    """Handle execute command: execute an action plan."""
    plan_id = args.get("plan_id", "")
    step = args.get("step")
    return {"status": "ok", "result": {"plan_id": plan_id, "state": "pending", "executed_steps": []}}


def _handle_undo(args: dict) -> dict:
    """Handle undo command: undo a previous action."""
    action_id = args.get("action_id", "")
    return {"status": "ok", "result": {"action_id": action_id, "state": "undone"}}


def _handle_motor_reflexes(args: dict) -> dict:
    """Handle motor-reflexes command: list or invalidate motor reflexes."""
    action = args.get("action", "list")
    if action == "invalidate":
        return {"status": "ok", "result": {"invalidated": args.get("hash", "")}}
    return {"status": "ok", "result": {"reflexes": []}}


def _handle_reflexes(args: dict) -> dict:
    """Handle reflexes command: list or invalidate cognitive reflexes."""
    action = args.get("action", "list")
    if action == "invalidate":
        return {"status": "ok", "result": {"invalidated": args.get("hash", "")}}
    return {"status": "ok", "result": {"reflexes": []}}


def _handle_export(args: dict) -> dict:
    """Handle export command: export twin data."""
    path = args.get("path", "")
    return {"status": "ok", "result": {"path": path, "exported": True}}


def _handle_import(args: dict) -> dict:
    """Handle import command: import twin data."""
    path = args.get("path", "")
    return {"status": "ok", "result": {"path": path, "imported": True}}


def _handle_inquiries(args: dict) -> dict:
    """Handle inquiries command: list or expire inquiries."""
    expire = args.get("expire", False)
    if expire:
        return {"status": "ok", "result": {"expired": 0}}
    return {"status": "ok", "result": {"inquiries": []}}
