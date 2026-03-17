# Phase 2 Design: Disaggregation (v8.0)
# Architect: Claude Opus 4.6 | Date: 2026-03-17
# Resolves: RISK-2 (Kill twin_ask), GAP-4 (Claude-only v8.0)

---

## 1. Overview

Three moves:
1. **Kill twin_ask** — Remove LLM client code from MCP server
2. **Observer** — Background process for Hot→Warm SDR promotion
3. **Coach.md** — System prompt projection from stage state

---

## 2. File Layout

```
python/cognitive_twin/observer/
├── __init__.py              # Public API: Observer class
└── lifecycle.py             # Start/stop/promote_cycle

python/cognitive_twin/coach/
├── __init__.py              # Public API: project_coach()
└── projection.py            # Stage → Anthropic XML

tests/test_observer/
├── __init__.py
├── conftest.py
└── test_observer.py         # Lifecycle, promotion, no-LLM

tests/test_coach/
├── __init__.py
├── conftest.py
└── test_coach.py            # Projection correctness, XML format
```

---

## 3. Kill twin_ask

### Deletions
- `mcp_server.py`: Remove `twin_ask` function (lines ~117-162)
- `mcp_server.py`: Remove `import os` if no longer needed
- `daemon/router.py`: Remove `_handle_ask` function, remove "ask" from router dict
- `tests/test_mcp/test_mcp_server.py`: Remove `TestTwinAsk` class
- Update server instructions docstring to remove twin_ask reference

### What stays
- `python/cognitive_twin/provider/` — kept for daemon backward compat
- `python/cognitive_twin/brainstem/generate.py` — kept, used by daemon

### Verification
- `grep -r "twin_ask" python/cognitive_twin/mcp_server.py` → 0 results
- MCP server starts without ANTHROPIC_API_KEY

---

## 4. Observer

### Design
- NOT a daemon (Rule 1: 0W idle). Called externally.
- Single method: `run_promotion_cycle(batch_size=50) -> int`
- Wraps PromotionPipeline from Phase 1
- Loads ONNX encoder ONCE, reuses across cycles
- No LLM imports

### API
```python
class Observer:
    def __init__(self, db_path: str, model_path: str) -> None:
        """Initialize with database and ONNX model paths."""

    def run_promotion_cycle(self, batch_size: int = 50) -> int:
        """Promote pending hot traces to warm tier. Returns count."""

    def pending_count(self) -> int:
        """Return number of traces awaiting promotion."""
```

---

## 5. Coach.md Projection

### Design
- Reads current state from HotStore + session manager
- Returns Anthropic XML system prompt block
- Deterministic for same input state
- No LLM imports

### API
```python
def project_coach(
    db_path: str,
    session_id: str | None = None,
) -> str:
    """Project current Twin state as Anthropic XML system prompt.

    Returns XML block with:
    - Active session info (exchange count, domain)
    - Recent hot traces (last 5, for immediate context)
    - Trust level placeholder (Phase 3)
    - Pending patterns count
    """
```

### MCP Tool
```python
@server.tool()
def twin_coach(session_id: str | None = None) -> str:
    """Get coaching context for the current session."""
```

---

## 6. Gate Criteria

### Gate 2a: twin_ask is Dead
- grep returns 0 results for twin_ask in mcp_server.py
- No LLM client imports in MCP server
- MCP server starts without ANTHROPIC_API_KEY

### Gate 2b: Coach.md Projection
- twin_coach returns valid XML block
- Output includes session info and recent traces
- Deterministic for same state

### Gate 2c: Observer Lifecycle
- Observer.run_promotion_cycle() promotes traces
- Observer does not import LLM client libraries
- Pending count decreases after promotion

---

## 7. Forge Order

```
Step  Action                                      Verify
1     Delete twin_ask from mcp_server.py           pytest tests/ -v --ignore=...
2     Delete TestTwinAsk from test_mcp_server.py   pytest tests/ -v --ignore=...
3     Remove "ask" from daemon router              pytest tests/ -v --ignore=...
4     Create observer module                       pytest tests/ -v --ignore=...
5     Create coach module                          pytest tests/ -v --ignore=...
6     Add twin_coach to MCP server                 pytest tests/ -v --ignore=...
7     Write observer tests                         pytest tests/test_observer/ -v
8     Write coach tests                            pytest tests/test_coach/ -v
9     Full regression                              pytest tests/ -v --ignore=...
```
