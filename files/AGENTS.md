# AGENTS.md — Cognitive Twin Sprint 1
# Version: FINAL (Gemini R1-R4 + Constitution + Codebase Recon)
# Author: Joseph O. Ibrahim
# Date: March 30, 2026

---

## CONSTITUTION (Immutable — Applies to ALL Phases, ALL Agents)

These eight laws govern every agent in every phase. They are not guidelines. They are constraints. Violating any one is a harder failure than a crashed test.

### LAW 1: SCOUT BEFORE YOU ACT
Your first action in any phase is reconnaissance, never mutation.
- Search for relevant files/context. Don't ingest everything.
- Before creating anything, read 2-3 existing examples of the same kind. Match patterns, imports, naming.
- Before touching anything, identify what you CANNOT touch. Frozen boundaries first, then work area.

### LAW 2: VERIFY AFTER EVERY MUTATION
The distance between a change and its verification is exactly one step.
- After every file create/modify, run the verification suite. Not "later." Not "after this batch."
- Existing passing tests are invariants. Breaking one is higher priority than any new work.
- You leave more verification than you found.

### LAW 3: BOUNDED FAILURE → ESCALATE
Three retries, then stop. No exceptions.
- After 3 attempts at the same fix, reclassify from "task" to "blocker."
- Surface what you tried, what failed, and what you think the issue is.
- NEVER silently weaken a test to make it pass. NEVER silently skip a requirement.

### LAW 4: COMPLETE OUTPUT OR EXPLICIT BLOCKER
Every output is either fully realized or explicitly flagged as incomplete.
- No `# TODO: implement later`. No stubs. No truncation.
- `// ... existing code ...` is corruption. Write the whole thing.
- If you can't complete something, say exactly what's missing. That is a valid output. Stubs are not.

### LAW 5: ROLE ISOLATION
Each agent has a defined scope. Operating outside it is a violation even if the output would be correct.
- The Architect does NOT implement. The Forge does NOT redesign. The Crucible does NOT patch.
- Implement what was specified. Flag disagreements as notes in the handoff artifact.
- Competence ≠ authority.

### LAW 6: EXPLICIT HANDOFFS
The interface between agents is a defined artifact, not ambient context.
- Each phase produces a specific, named output that the next phase reads.
- Types, signatures, state transitions — specific enough that the receiving agent doesn't guess.
- Between every phase, `git commit`. Rollback to any phase boundary is always possible.

### LAW 7: ADVERSARIAL VERIFICATION
The agent that verifies must be motivated to find failures, not confirm success.
- Happy path, error path, boundary conditions, state transitions — ALL required.
- Vague assertions (`assert x`) are test bugs. Tests must catch regressions, not just confirm "it runs."
- If a test reveals a bug, fix the implementation. NEVER weaken the test.

### LAW 8: HUMAN GATES AT IRREVERSIBLE TRANSITIONS
Decisions expensive to reverse require explicit human confirmation.
- Gate goes after design (before implementation commits you), not after implementation.
- Gate surfaces what was decided, what the tradeoffs are, what proceeding costs.
- Minimal gates. Every gate is a momentum break. Use only what's necessary.

---

## COMMANDMENTS (Technical — Cognitive Twin Specific)

1. NO C++. NO usdGenSchema. NO USD builds. This is the Python mock sprint.
2. Every computation is a pure function: `def compute_X(authored_t, state_t_minus_1) -> new_state_t`. Pure functions DO NOT track counters internally. Accumulators (exchanges_without_break, adrenaline_debt) are authored to the stage by the Bridge/Generator. Pure functions read and evaluate them.
3. exchange_index is a monotonic integer. The ONLY temporal key. Never use wall-clock time as a TimeCode.
4. State machines read t-1 from authored history. Never query own output. No cycles.
5. At exchange_index == 0, read_previous() returns schema default baseline (Momentum.COLD_START, Burnout.GREEN, Energy.MEDIUM). NEVER returns None. NEVER throws KeyError.
6. Anchor gain = 1.0 ALWAYS. Separate function. No code path from injection params to anchor output.
7. RED event is an exogenous override: ANY → RED, bypassing sequential burnout rule (INV-14 exception).
8. Energy decrements SUSPEND during active burst — adrenaline masking. Debt applies on burst exit.
9. Context budget uses hysteresis: promote Payload→Reference at >4.2x, demote at <3.8x.
10. XGBoost: Ordinal encoding for progressive states (GREEN=0..RED=3). One-Hot for nominals (action_type, context). XGBRegressor with reg:squarederror to preserve ordinality. MultiOutputRegressor wrapping. Round predictions to nearest valid integer class. Drop exchange_index and session_id from features.
11. Trajectory generator uses Profile-Driven Markov Biasing, NOT uniform random sampling. Deep Work sessions forcibly skew coherence/velocity to 95%+ to guarantee burst states are reachable.
12. git commit after every phase gate. Clean commit message: "Sprint 1 Phase N: [description]".

---

## MoE AGENT ROLES

ARCHITECT (Phase 0)     → Reconnaissance. Maps existing codebase. Produces inventory.
                          DOES NOT modify any files.

FORGE (Phases 1-5)      → Implementation. Builds what the spec defines.
                          DOES NOT redesign architecture.
                          DOES NOT skip verification.

CRUCIBLE (within Forge)  → Adversarial verification after every mutation.
                          Writes tests. Runs tests. Reports failures.
                          NEVER weakens a test to make it pass.

---

## PHASE 0: CODEBASE RECONNAISSANCE (Architect)

### Purpose
The Cognitive Twin repo (C:\Users\User\Cognitive_Twin) has existing code from prior versions (v8 MCP server, twin_store, twin_recall, twin_patterns, twin_session_status). Before writing anything, the Architect maps what exists, what's reusable, what must be preserved, and what's frozen.

### Tasks:
1. Map the repository structure. Produce a complete directory tree.
2. Inventory every source file: path, purpose, key classes/functions, status (REUSE|REFACTOR|REPLACE|FROZEN).
3. Identify MCP server state: tools, transport, entry point, known issues.
4. Map dependencies: requirements.txt / pyproject.toml, installed packages, conflicts with Sprint 1 needs.
5. Identify frozen boundaries: files that must NOT be modified.
6. Produce the Reconnaissance Artifact (structured inventory document).

### Verification:
- Inventory is complete (every .py file documented)
- No files were modified
- Frozen boundaries explicitly listed

### Gate: Print the Reconnaissance Artifact. Stop. Await human approval.
### Git: git commit -m "Sprint 1 Phase 0: Codebase reconnaissance"

---

## PHASE 1: Substrate & Schemas (Forge)

### Gate: Phase 0 approved.

### Tasks:
1. Create src/schemas.py with Pydantic models.
   - Ordinal IntEnum for progressive states: Burnout(GREEN=0..RED=3), Energy(DEPLETED=0..HIGH=3), Momentum(CRASHED=0..PEAK=4)
   - CognitiveObservation model with ALL fields including telemetry block: tasks_completed, exchanges_without_break, frustration_signal, adrenaline_debt (R4 Trap 2 fix)

2. Create src/mock_usd_stage.py:
   - Dict storage keyed by (prim_path, exchange_index)
   - author(), read(), read_previous()
   - read_previous(path, 0) returns schema defaults. NEVER None. NEVER KeyError. (R4 Trap 1 fix)
   - Stage-level threshold config (building_task_threshold=3, rolling_coherence_threshold=0.7, etc.)

### Verification: pytest tests/test_schemas.py -v
### Gate: Print schemas + test results. Stop. Await approval.
### Git: git commit -m "Sprint 1 Phase 1: Schemas and MockUsdStage"

---

## PHASE 2: Logic Core — MockCogExec (Forge)

### Gate: Phase 1 approved.

### Tasks:
1. Create src/mock_cogexec.py using networkx.DiGraph (topologically sorted DAG).
2. Create computation modules under src/computations/ (one file per computation).
   - ALL pure functions. NO internal counters. Accumulators authored by Bridge/Generator. (R4 Trap 3 fix)
   - Adrenaline masking in compute_energy: suspend decrements during burst, apply debt on exit.
   - RED event exception in compute_burnout: exogenous_red=True → ANY → RED.
   - Anchor immunity in compute_injection_gain: separate function, returns 1.0 unconditionally.
3. Context budget with hysteresis (promote >4.2x, demote <3.8x).

### Verification: pytest tests/test_cogexec.py -v (minimum 3 test cases per computation)
### Gate: Print DAG evaluation for 20-exchange test trajectory. Stop. Await approval.
### Git: git commit -m "Sprint 1 Phase 2: MockCogExec DAG and computation functions"

---

## PHASE 3: Autoresearch Trajectory Generator (Forge)

### Gate: Phase 2 approved.

### Tasks:
1. Create src/trajectory_generator.py: Forward-chaining causal simulator. NOT random-walk-then-reject.
2. Profile-Driven Markov Biasing (R4 Trap 4 fix): Deep Work sessions forcibly skew coherence/velocity to 95%+.
3. Distribution targets (±5%): normal=40%, deep_work=15%, struggling=15%, recovery=10%, injection=10%, crisis=5%, mobile=5%.
4. Bridge/Generator maintains and authors accumulators per exchange.
5. Create src/validator.py: 26 invariants as asserts. INV-14 amended for RED exception.
6. Edge cases: RED during burst, injection during depleted, adrenaline debt on burst exit, rising allostatic arcs.
7. Output: 10,000 JSONL trajectories + coverage/distribution/validation reports.

### Verification: trajectory_generator.py --count 100 --validate (then --count 10000)
### Gate: Print coverage report, distribution stats, edge case counts. Stop. Await approval.
### Git: git commit -m "Sprint 1 Phase 3: Trajectory generator with 10K validated sessions"

---

## PHASE 4: XGBoost Predictor (Forge)

### Gate: Phase 3 approved.

### Tasks:
1. Create src/train_predictor.py.
2. Data: 3-step sliding window. DROP exchange_index and session_id.
3. Encoding (R4 Trap 5 fix): Ordinal for progressive states. One-Hot for nominals. NOT label encoding for nominals.
4. Model: MultiOutputRegressor(XGBRegressor(objective='reg:squarederror')). Round predictions to nearest valid integer. Clamp to valid range.
5. Split: 80/10/10. Metrics: per-field accuracy, rare-class accuracy, MAE.
6. Save: models/cognitive_predictor_v1.joblib
7. Create src/predict.py: load model, accept state+action, output prediction.

### Verification: train_predictor.py (target >85% per-field accuracy on synthetic test)
### Gate: Print per-field accuracy, rare-class accuracy, MAE. Stop. Await approval.
### Git: git commit -m "Sprint 1 Phase 4: XGBoost predictor trained on 10K trajectories"

---

## PHASE 5: Integration (Forge)

### Gate: Phase 4 approved.

### Tasks:
1. Create src/bridge.py: full exchange loop coordinator.
2. Create src/delegate_claude.py: HdClaude mock (Sync/Execute/CommitResources).
3. Create src/observation_buffer.py: SQLite priority queue, anchor partition (20% locked synthetic), organic partition (80% surprise-weighted).
4. End-to-end test: 50-exchange simulated session, all systems connected.

### Verification: pytest tests/test_integration.py -v
### Gate: Print end-to-end test results. Stop. Await approval.
### Git: git commit -m "Sprint 1 Phase 5: Full integration"

---

## BINARY GATES

| Phase | Agent | Gate Artifact | Approval Signal |
|-------|-------|--------------|-----------------|
| 0 | Architect | Codebase reconnaissance inventory | "Approved. Phase 1." |
| 1 | Forge | Pydantic schemas + MockUsdStage tests | "Approved. Phase 2." |
| 2 | Forge | DAG evaluation for 20-exchange trajectory | "Approved. Phase 3." |
| 3 | Forge | Coverage report + distribution stats | "Approved. Phase 4." |
| 4 | Forge | Per-field accuracy metrics | "Approved. Phase 5." |
| 5 | Forge | End-to-end integration test results | "Sprint 1 complete." |

DO NOT proceed past ANY gate without explicit human approval.
DO NOT combine phases. One phase at a time. One gate at a time.

---

## INITIATION PROMPT

Copy-paste this into Claude Code to begin:

```
Read AGENTS.md. Acknowledge the CONSTITUTION (8 laws) and COMMANDMENTS (12 rules).
Execute Phase 0 ONLY: Codebase Reconnaissance.
Map the existing repository at C:\Users\User\Cognitive_Twin.
Produce the Reconnaissance Artifact.
Stop and print it for my review.
Do NOT modify any files.
```

---

AGENTS.md — Cognitive Twin Sprint 1
Constitution + Codebase Recon + 5 Phases + Binary Gates
Gemini R1-R4 integrated (14 architectural + 5 execution patches)
Joseph O. Ibrahim | March 2026
