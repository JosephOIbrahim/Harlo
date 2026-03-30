# AGENTS.md — Cognitive Twin Sprint 5
# Production Hardening: Wire Live + Error Handling + First Real Session
# Author: Joseph O. Ibrahim
# Date: March 30, 2026
# Prerequisites: Sprints 1-4 complete (228 tests, real USD stage, Hydra delegates, CognitiveEngine)

---

## CONSTITUTION (All 8 Laws Apply)

## MISSION

Three moves. Make it production-real.

1. **Wire CognitiveEngine (real USD backend) into the live MCP server.** When Claude Desktop calls `twin_coach`, the DAG evaluates against real `.usda`, delegates route by capability, observations emit.
2. **Harden every failure path.** Locked files, missing models, corrupt DB, import failures — every one falls back gracefully. The MCP server never crashes.
3. **Run the first real session.** Open Claude Desktop, have a conversation, verify organic data is flowing.

---

## COMMANDMENTS

1. **228 Sprint tests + 890 existing tests are invariants.**
2. **The MCP server MUST NOT crash.** Any failure in the cognitive engine → logged warning + pre-Sprint 3 behavior. The MCP server is the product. The engine is an enhancement. Enhancement failure ≠ product failure.
3. **USE_REAL_USD=True by default.** CognitiveStage (pxr.Usd) is the backend. MockUsdStage is the fallback if USD import fails.
4. **Every `try/except` logs the exception.** No silent swallowing. `logging.getLogger(__name__)` everywhere.
5. **The first real session is the acceptance test.** If observations don't emit during a real Claude Desktop conversation, the sprint is not done.

---

## PHASE 0: Audit Current Wiring (Architect)

### Tasks:

1. **Read `src/cognitive_engine.py`** — does it currently import CognitiveStage or MockUsdStage?
2. **Read `python/cognitive_twin/mcp_server.py`** — is CognitiveEngine hooked in? If Sprint 3 added the hook, verify it uses the real USD backend.
3. **Read `src/engine_config.py`** — what's the current state of all toggles?
4. **Read `.mcp.json`** — what's the entry point? How does Claude Desktop launch the server?
5. **Map the exact path:** Claude Desktop → `.mcp.json` → MCP server process → tool handler → CognitiveEngine → CognitiveStage → `.usda`
6. **Identify every gap in this path.** What's connected? What's not?

### Gate: Print the wiring audit. What works, what's disconnected. Stop. Await approval.

---

## PHASE 1: Wire CognitiveEngine to Real USD (Forge)

### Gate: Phase 0 approved.

### Tasks:

1. **Update `src/cognitive_engine.py`** to use stage_factory:
   ```python
   from src.stage_factory import create_stage

   class CognitiveEngine:
       def __init__(self):
           try:
               self.stage = create_stage()  # Real USD if available, mock fallback
               self.stage_type = "real_usd" if hasattr(self.stage, 'stage') else "mock"
           except Exception as e:
               logger.warning(f"CognitiveStage init failed, using mock: {e}")
               from src.mock_usd_stage import MockUsdStage
               self.stage = MockUsdStage()
               self.stage_type = "mock"

           self.cogexec = MockCogExec(self.stage)
           self.registry = DelegateRegistry()
           self.buffer = ObservationBuffer(...)
           # ... rest of init with try/except on each component
   ```

2. **Update `src/engine_config.py`:**
   ```python
   USE_REAL_USD = True              # Real pxr.Usd.Stage by default
   ENGINE_ENABLED = True            # Master kill switch
   OBSERVATION_LOGGING = True       # Emit observations
   PREDICTION_ENABLED = True        # Run XGBoost predictions
   GRACEFUL_FALLBACK = True         # On failure: fall back, don't crash

   USD_STAGE_DIR = "data/stages"
   OBSERVATION_DB = "data/observations.db"
   MODEL_PATH = "models/cognitive_predictor_v1.joblib"
   SYNTHETIC_DATA = "synthetic_data/trajectories"

   LOG_LEVEL = "INFO"
   ```

3. **Verify the MCP server hook from Sprint 3:**
   - `python/cognitive_twin/mcp_server.py` should import and initialize CognitiveEngine
   - `twin_coach` handler should call `engine.process_exchange()`
   - If the hook doesn't exist yet, add it (minimal, non-invasive)

4. **Ensure USD Python path is set at server startup:**
   ```python
   # In mcp_server.py or cognitive_engine.py, before any pxr import:
   from src.usd_bootstrap import bootstrap_usd
   bootstrap_usd()  # Adds C:\USD\26.03-exec\lib\python to sys.path
   ```

### Verification:
```bash
python -m pytest tests/test_sprint5/test_engine_wiring.py -v
```
- CognitiveEngine initializes with real USD stage
- process_exchange evaluates DAG against real .usda
- Observation emitted after process_exchange
- Prediction authored to /prediction on real stage
- Stage saved to disk after exchange
- Fallback: if USD import fails, engine uses MockUsdStage (logged)
- Fallback: if model missing, prediction disabled (logged), rest works
- Fallback: if DB locked, observation queued in memory (logged)

### Gate: Print wiring tests. Stop. Await approval.
### Git: `git commit -m "Sprint 5 Phase 1: CognitiveEngine wired to real USD"`

---

## PHASE 2: Error Handling + Graceful Degradation (Forge)

### Gate: Phase 1 approved.

### Tasks:

1. **Wrap every CognitiveEngine component with graceful fallback:**

   ```python
   class CognitiveEngine:
       def process_exchange(self, tool_name, tool_input):
           if not engine_config.ENGINE_ENABLED:
               return None  # Engine disabled, MCP continues normally

           try:
               self.exchange_index += 1
               self._author_exchange(tool_name, tool_input)
           except Exception as e:
               logger.error(f"Stage authoring failed: {e}")
               return None  # MCP continues without cognitive state

           try:
               computed = self.cogexec.evaluate_all()
           except Exception as e:
               logger.error(f"DAG evaluation failed: {e}")
               computed = self._default_computed_values()

           try:
               routing = computed.get("computeRouting", {})
               delegate = self.registry.select(routing.get("requirements", {}))
               delegate.sync(...)
               result = delegate.execute(tool_input)
               delegate.commit_resources(result)
           except Exception as e:
               logger.error(f"Delegate cycle failed: {e}")
               result = None

           if engine_config.OBSERVATION_LOGGING:
               try:
                   observation = self._build_observation(computed, tool_name)
                   self.buffer.ingest(observation)
               except Exception as e:
                   logger.error(f"Observation logging failed: {e}")

           if engine_config.PREDICTION_ENABLED:
               try:
                   prediction = self.predictor.predict(observation)
                   self.stage.author("/prediction/forecast", prediction, self.exchange_index)
               except Exception as e:
                   logger.error(f"Prediction failed: {e}")

           try:
               self.stage.save()
           except Exception as e:
               logger.error(f"Stage save failed: {e}")

           return result
   ```

   **The principle:** Each component fails independently. A prediction failure doesn't kill observation logging. A delegate failure doesn't kill the DAG. Nothing kills the MCP server.

2. **File locking protection for `.usda`:**
   ```python
   def save(self):
       try:
           self.stage.GetRootLayer().Save()
       except Exception as e:
           logger.warning(f"Stage save failed (file locked?): {e}")
           # Queue for next save attempt
           self._pending_save = True
   ```

3. **Missing model graceful handling:**
   ```python
   def _init_predictor(self):
       if not os.path.exists(engine_config.MODEL_PATH):
           logger.warning(f"Predictor model not found at {engine_config.MODEL_PATH}")
           self.predictor = None
           return
       self.predictor = Predictor(engine_config.MODEL_PATH)
   ```

4. **Observation buffer overflow protection:**
   ```python
   class ObservationBuffer:
       MAX_MEMORY_QUEUE = 100  # If DB is locked, buffer in memory up to this limit

       def ingest(self, observation):
           try:
               self._write_to_db(observation)
           except sqlite3.OperationalError:  # DB locked
               if len(self._memory_queue) < self.MAX_MEMORY_QUEUE:
                   self._memory_queue.append(observation)
                   logger.warning("DB locked, observation queued in memory")
               else:
                   logger.error("Memory queue full, observation dropped")

       def flush_memory_queue(self):
           """Called periodically to drain memory queue to DB."""
           while self._memory_queue:
               try:
                   self._write_to_db(self._memory_queue.popleft())
               except sqlite3.OperationalError:
                   break  # Still locked, try again later
   ```

5. **Health check endpoint:**
   ```python
   def get_health(self) -> dict:
       return {
           "engine": "active" if engine_config.ENGINE_ENABLED else "disabled",
           "stage_type": self.stage_type,  # "real_usd" or "mock"
           "stage_file": os.path.exists(os.path.join(engine_config.USD_STAGE_DIR, "cognitive_twin.usda")),
           "predictor": self.predictor is not None,
           "observations_logged": self.buffer.count() if self.buffer else 0,
           "exchange_index": self.exchange_index,
           "delegates_registered": len(self.registry.list_delegates()),
           "memory_queue_size": len(self.buffer._memory_queue) if self.buffer else 0,
       }
   ```

### Verification:
```bash
python -m pytest tests/test_sprint5/test_error_handling.py -v
```
Must pass:
- Engine works normally when everything is healthy
- USD import failure → falls back to mock (logged, not crashed)
- Model file missing → prediction disabled (logged), rest works
- DB locked → observations queue in memory (logged)
- Memory queue overflow → oldest dropped (logged)
- Stage save failure → queued for retry (logged)
- Delegate failure → returns None (logged), MCP continues
- DAG failure → returns defaults (logged), MCP continues
- Health check returns accurate status for all components
- **CRITICAL: MCP server NEVER raises an unhandled exception from the engine**

### Gate: Print error handling tests. Stop. Await approval.
### Git: `git commit -m "Sprint 5 Phase 2: Graceful degradation — nothing crashes the MCP"`

---

## PHASE 3: MCP Server Integration Verification (Forge)

### Gate: Phase 2 approved.

### Tasks:

1. **Simulate the real MCP flow** end-to-end:
   ```python
   # test_mcp_live.py
   # Simulates what Claude Desktop does when calling twin_coach

   def test_mcp_twin_coach_with_engine():
       """
       The full path:
       Claude Desktop → MCP stdio → twin_coach handler
       → CognitiveEngine.process_exchange()
       → DAG evaluates against real .usda
       → Delegate routes by capability
       → Observation emitted to buffer
       → Prediction authored to stage
       → Response returned to Claude
       """
       # Initialize MCP server context
       # Call twin_coach with real parameters
       # Verify: cognitive_twin.usda updated on disk
       # Verify: observation in buffer
       # Verify: prediction on stage
       # Verify: response contains enriched cognitive context
   ```

2. **Test all 7 MCP tools with engine active:**
   - twin_coach → full engine cycle
   - twin_store → engine observes the store event
   - twin_recall → engine evaluates state before recall
   - twin_patterns → engine observes
   - twin_session_status → engine provides enriched status
   - resolve_verifications → engine observes
   - trigger_cognitive_recalibration → engine observes

3. **Test all 7 MCP tools with engine DISABLED (kill switch):**
   - Every tool returns exactly the same result as pre-Sprint 3
   - No errors, no warnings (engine is off, not broken)

4. **Test engine failure during MCP call:**
   - Engine raises during process_exchange
   - MCP tool still returns valid response (pre-engine behavior)
   - Error logged

### Verification:
```bash
python -m pytest tests/test_sprint5/test_mcp_live.py -v
```
- All 7 tools work with engine ON
- All 7 tools work with engine OFF (identical pre-Sprint behavior)
- Engine crash mid-call → MCP tool still responds
- .usda updated after twin_coach call
- Observation count increases after each tool call

### Gate: Print MCP integration tests. Stop. Await approval.
### Git: `git commit -m "Sprint 5 Phase 3: MCP integration verified — 7 tools hardened"`

---

## PHASE 4: First Real Session Test (Forge)

### Gate: Phase 3 approved.

### Tasks:

1. **Create `scripts/first_session.py`** — simulates a real 10-exchange session:
   ```python
   """
   Simulates a real session as if Claude Desktop were calling the MCP server.
   10 exchanges. Verifies everything works end-to-end with real USD.
   """
   from src.cognitive_engine import CognitiveEngine
   import json, os

   engine = CognitiveEngine()
   print(f"Engine health: {json.dumps(engine.get_health(), indent=2)}")

   # 10 exchanges simulating a real session
   exchanges = [
       ("twin_coach", {"context": "session_start"}),
       ("twin_store", {"message": "Working on Cognitive Twin patent filing"}),
       ("twin_coach", {"context": "architecture_question"}),
       ("twin_coach", {"context": "deep_work"}),
       ("twin_coach", {"context": "deep_work"}),
       ("twin_coach", {"context": "deep_work"}),
       ("twin_store", {"message": "Decided on XGBoost over HMM for prediction"}),
       ("twin_coach", {"context": "energy_check"}),
       ("twin_patterns", {}),
       ("twin_coach", {"context": "session_end"}),
   ]

   for i, (tool, input_data) in enumerate(exchanges):
       print(f"\n--- Exchange {i+1}: {tool} ---")
       result = engine.process_exchange(tool, input_data)
       print(f"Exchange index: {engine.exchange_index}")
       print(f"Stage type: {engine.stage_type}")

   # Verify
   print("\n\n=== VERIFICATION ===")
   health = engine.get_health()
   print(f"Health: {json.dumps(health, indent=2)}")

   # Check .usda exists and has content
   usda_path = os.path.join(engine.stage.stage_dir, "cognitive_twin.usda")
   print(f"\n.usda exists: {os.path.exists(usda_path)}")
   print(f".usda size: {os.path.getsize(usda_path)} bytes")

   # Check observations
   print(f"Observations logged: {health['observations_logged']}")

   # Print the actual .usda content
   if hasattr(engine.stage, 'export_flat'):
       engine.stage.export_flat("data/stages/session_flat.usda")
       print("\nFlattened stage exported to data/stages/session_flat.usda")

   assert health['exchange_index'] == 10, f"Expected 10 exchanges, got {health['exchange_index']}"
   assert health['observations_logged'] >= 10, f"Expected >=10 observations, got {health['observations_logged']}"
   assert health['stage_file'], "cognitive_twin.usda not found!"
   print("\n✓ FIRST SESSION: ALL CHECKS PASSED")
   ```

2. **Run the first session:**
   ```bash
   python scripts/first_session.py
   ```

3. **Print the cognitive state:**
   ```bash
   type data\stages\cognitive_twin.usda
   ```
   This is the moment. Your cognitive state. Real USD. On disk.

4. **Print observation count:**
   ```bash
   python -c "from src.observation_buffer import ObservationBuffer; b = ObservationBuffer('data/observations.db'); print(f'Observations: {b.count()}')"
   ```

### Verification:
- 10 exchanges processed without errors
- cognitive_twin.usda exists with authored state
- ≥10 observations in the buffer
- Health check shows all systems green
- No unhandled exceptions

### Gate: Print session output + .usda content + observation count. Stop.
### Git: `git commit -m "Sprint 5 Phase 4: First session verified — organic data flowing"`

---

## PHASE 5: Production Readiness Checklist (Forge)

### Gate: Phase 4 approved.

### Tasks:

1. **Full test suite:**
   ```bash
   python -m pytest tests/ -v --ignore=tests/test_encoder --ignore=tests/test_daemon
   ```
   Everything green. Every sprint. Every existing test.

2. **Document the production configuration:**
   Create `docs/PRODUCTION.md`:
   - How to start the MCP server with the cognitive engine
   - Environment variables (USE_REAL_USD, ENGINE_ENABLED, etc.)
   - Kill switches and how to use them
   - Where data lives (stages/, observations/, models/)
   - How to monitor health (engine.get_health())
   - How to disable components independently
   - Backup strategy for .usda files

3. **Log verification:**
   - Run first_session.py
   - Check logs contain INFO for normal operations
   - Check logs contain WARNING for any fallbacks triggered
   - No ERROR or CRITICAL in clean run

4. **Create `scripts/health_check.py`:**
   ```python
   from src.cognitive_engine import CognitiveEngine
   import json
   engine = CognitiveEngine()
   print(json.dumps(engine.get_health(), indent=2))
   ```

### Gate: Print full test suite + health check. Stop.
### Git: `git commit -m "Sprint 5 Phase 5: Production ready — Cognitive Twin is live"`

---

## BINARY GATES

| Phase | Gate | Approval Signal |
|-------|------|-----------------|
| 0 | Wiring audit | "Approved. Phase 1." |
| 1 | Engine wired to real USD | "Approved. Phase 2." |
| 2 | Error handling tests | "Approved. Phase 3." |
| 3 | MCP integration (7 tools) | "Approved. Phase 4." |
| 4 | First session verified | "Approved. Phase 5." |
| 5 | Full suite + health check | "Sprint 5 complete." |

---

## WHAT SHIPS

When Sprint 5 gates, the Cognitive Twin is **production-live:**

- Every MCP call evaluates cognitive state against real `.usda`
- Observations accumulate from real sessions
- Failures degrade gracefully — MCP never crashes
- Kill switches for every component independently
- Health check endpoint for monitoring
- First organic data verified flowing

**After Sprint 5, open Claude Desktop. Have a real conversation. The twin is watching, learning, predicting.**

---

## INITIATION PROMPT

```
Read AGENTS.md. Sprint 5: Production Hardening.
Acknowledge CONSTITUTION and COMMANDMENTS.

ultrathink. Execute all phases sequentially. Stop ONLY on:
- Test failures after 3 retries
- Import errors
- Genuine blockers

Do NOT stop for routine gates. Ship it.
```

---

*AGENTS.md — Cognitive Twin Sprint 5*
*Production Hardening: Wire it. Harden it. Run it.*
*Joseph O. Ibrahim | March 2026*
