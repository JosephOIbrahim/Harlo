# Cognitive Twin v8.0 — Agent Team Execution Spec
# Pattern: Sequential MoE (Architect → Forge → Crucible) × 7 Phases
# Source: v8.0 Surgical Directives ADR (Gemini Deep Think → Claude Opus)
# Mode: Autonomous sequential execution in Claude Code

---

## COMMANDMENTS (Violation = Abort)

1. **RECON = THIS FILE.** The ADR is the spec. Do not re-explore the codebase to "understand the architecture." The specification documents every decision, every constraint, every gate. Trust it.
2. **VERIFY EVERY MUTATION.** After every file creation or modification: `python -m pytest tests/ -v --ignore=tests/test_encoder --ignore=tests/test_daemon`. If ANY existing test breaks, STOP and fix. Non-negotiable.
3. **CIRCUIT BREAKER.** 3 failed attempts at the same fix → STOP. Surface a structured blocker at `.agent-team/blockers/phase-{N}-{description}.md` with: reason, what_would_help, partial_progress. Never silently degrade.
4. **COMPLETE OR BLOCKED.** No stubs. No TODOs. No `pass` bodies. No truncated files. Every function has a docstring. Every file is finished. If you can't finish, produce a blocker — don't leave debris.
5. **TRACE EXCLUSION: ROLE ISOLATION IS STRUCTURAL.** Architect designs. Forge builds. Crucible breaks. Forge reads the design artifact, not the reasoning. Disagreements are notes at `.agent-team/blockers/`, not unilateral changes.
6. **EXPLICIT HANDOFFS.** Designs at `.agent-team/designs/phase-{N}.md`. Blockers at `.agent-team/blockers/`. Gate results at `.agent-team/gates/phase-{N}-gate.md`. Every artifact is named and pathed.
7. **CRUCIBLE IS ELENCHUS.** The verifier receives intent (spec) and output (implementation). It evaluates without seeing the builder's reasoning. It detects spec-gaming: code that technically passes but doesn't answer the actual requirement. Fix code, never weaken tests.
8. **HUMAN GATE AFTER PHASE 1.** Pause for Joe's review before proceeding to Phase 2. This is the AND-chain blocker — encoding fidelity is the hardest subtask.
9. **SEQUENTIAL PHASES.** One phase at a time. No parallelization across phases. Each gate MUST pass before the next phase begins.
10. **MATURIN DEVELOP FOR RUST.** Use `maturin develop` (not `pip install -e .`) for the Rust extension. Run from the same shell where `ANTHROPIC_API_KEY` is set.
11. **PYTHON VERSION.** Run `python -m pytest` (not bare `pytest`) — Python 3.12/3.14 coexist.
12. **THIS FILE IS LAW.** Verification commands, module boundaries, frozen boundaries, coding conventions — all constraints, not suggestions.

---

## MISSION

Disaggregate Cognitive Twin from v7.0 monolith to v8.0 Actor/Observer architecture per the resolved ADR. Seven phases, each running the full Architect → Forge → Crucible cycle with hard verification gates.

### Key Architectural Moves

| Move | What Changes |
|------|-------------|
| Actor/Observer Split | LLM (Actor) reasons. Twin (Observer/Stage) stores and projects. No more twin_ask. |
| USD-as-House | `.usda` stage is the live truth. usd_lite is the fast runtime layer (our Fabric). |
| Hot/Warm Tiered Memory | FTS5 plaintext (Hot, zero-encoding) + SDR Hamming (Warm, encoded). Federated query merges both. |
| Coach Core Projection | MCP server generates a system prompt injection from current stage state. Claude-only for v8.0. |
| Trust as Float | Continuous [0.0–1.0] trust score replaces any bitmask. Basal Ganglia evaluates the float. |
| Elenchus → Actor | Observer queues unverified claims. Actor verifies when connected. No local LLM required. |
| Replay-Then-Archive | Epoch compaction replays variants chronologically with decay, writes resolved baseline, archives originals. |

---

## PHASE SEQUENCE (AND-node: each must pass before the next begins)

```
Phase 1: Encoding & Hot Path      → Gate 1a + 1b        [RISK-1, TENSION-1]
Phase 2: Disaggregation           → Gate 2a + 2b + 2c   [RISK-2, GAP-4]
Phase 3: Trust & Cognitive Profile → Gate 3a + 3b        [RISK-3, GAP-1]
Phase 4: Elenchus Deferral        → Gate 4a + 4b        [GAP-2]
Phase 5: Temporal Compaction       → Gate 5a + 5b        [GAP-3]
Phase 6: Federated Recall & MCP   → Gate 6a + 6b + 6c   [TENSION-1]
Phase 7: Test Suite Rewrite        → Gate 7a + 7b + 7c   [GAP-5]
```

**AlphaProof value = Phase 1.** This is the AND-chain blocker. If encoding fidelity fails, nothing downstream works. Surface it early, kill it fast.

---

## AGENT ROLES

### ARCHITECT (Phase Designer)

**Authority:** Design ONLY. Produce plans, schemas, APIs, file layouts.
**Output:** `.agent-team/designs/phase-{N}.md`
**Rules:** No implementation code. No file creation outside `.agent-team/designs/`. Read 2-3 existing files of the same kind before designing. Match codebase conventions.

### FORGE (Implementer)

**Authority:** Build ONLY what the Architect designed.
**Rules:**
- Read the design artifact (`.agent-team/designs/phase-{N}.md`), not the reasoning
- Run verification after every mutation (Commandment 2)
- No stubs (Commandment 4)
- Circuit breaker at 3 failures (Commandment 3)
- Convention matching: read existing files, match import style / naming / error handling / docstrings
- No freelancing: implement the design. Disagreements → `.agent-team/blockers/`
- Git commit after each sub-task: `v8-phase{N}: {description}`
- File ownership: implementation files only. Do NOT modify designs or gate results.

### CRUCIBLE (Adversarial Verifier)

**Authority:** Break ONLY. Run tests, write adversarial tests, verify gate conditions.
**Rules:**
- Receive intent (spec) and output (implementation). Evaluate blind.
- Write adversarial tests that attempt to break assumptions
- Detect spec-gaming (technically passes but doesn't satisfy the intent)
- If something fails: describe the failure. Do NOT fix it. Forge fixes.
- Gate results go to `.agent-team/gates/phase-{N}-gate.md`
- Tests are sacred: fix code, NEVER weaken tests
- On gate failure: loop Forge → Crucible until pass

---

## PHASE 1: ENCODING & HOT PATH
**Resolves:** RISK-1 (Encoding Fidelity), TENSION-1 (Store vs Recall Latency)
**AND-chain blocker. Hardest subtask. Do this first.**

### Architect Scope
Design the dual-tier memory architecture:

**Hot Tier (L1 — zero encoding, zero latency):**
- SQLite table with FTS5 full-text index
- Schema: `trace_id TEXT PK, message TEXT, tags JSON, domain TEXT, timestamp REAL, encoded BOOLEAN DEFAULT FALSE`
- `twin_store` writes here immediately with `encoded=FALSE`
- Zero-encoding constraint: no model loading in the MCP hot path
- Target: <2ms store latency

**Warm Tier (L2 — SDR encoded, Hamming search):**
- Existing Rust hippocampus crate (unchanged per Commandment — crates/hippocampus is frozen unless encoding gate requires it)
- Background Observer process promotes Hot → Warm after SDR encoding
- SDR encoding via ONNX Runtime (not sentence-transformers — eliminates the BGE load hang)

**Encoder Pipeline:**
- Convert BAAI/bge-small-en-v1.5 to ONNX format
- Attempt INT8 quantization
- Validation: 1,000-trace reference corpus, 0.95 Hamming distance correlation threshold
- **If INT8 fails the 0.95 gate: fall back to FP16 ONNX immediately. Do not attempt QAT.**
- FP16 payload (~60-100MB) is acceptable for desktop consumer hardware
- ONNX model loads ONCE at Observer startup, not per-call

**Design output:** File layout, schemas, API signatures for Hot Tier CRUD, promotion pipeline, ONNX encoder wrapper.

### Forge Scope
1. Create `python/cognitive_twin/hot_store/` — SQLite + FTS5 Hot Tier
2. Create `python/cognitive_twin/encoder/onnx_encoder.py` — ONNX Runtime wrapper
3. Export BGE-small-en-v1.5 to ONNX, attempt INT8 quantization
4. Build reference corpus (1,000 traces from existing test data or synthetic)
5. Run Hamming correlation validation
6. If INT8 < 0.95: switch to FP16, re-validate (must be ≥ 0.95)
7. Create `python/cognitive_twin/hot_store/promotion.py` — Hot → Warm async promotion
8. Modify `twin_store` MCP tool: write to Hot Tier only (zero-encoding path)
9. Tests in `tests/test_hot_store/`

### Crucible Gates

**Gate 1a: Encoding Fidelity**
- Run 1,000-trace corpus through both the original sentence-transformers encoder AND the ONNX encoder
- Compute SDRs from both
- Hamming distance correlation between the two sets ≥ 0.95
- **If this fails, Phase 1 loops. Nothing proceeds.**

**Gate 1b: Hot Path Latency**
- `twin_store` completes in <2ms (measured over 100 calls, p99)
- No model loading occurs during `twin_store`
- FTS5 search returns results for a plaintext query
- Hot Tier correctly marks traces as `encoded=FALSE`

**⚠️ HUMAN GATE: Pause here. Present Gate 1a/1b results to Joe before proceeding.**

---

## PHASE 2: DISAGGREGATION
**Resolves:** RISK-2 (Kill twin_ask), GAP-4 (Claude-only v8.0)

### Architect Scope
Design the Actor/Observer disaggregation:

**Actor (LLM — Claude via MCP):**
- Receives structured context via Coach Core system prompt injection
- All reasoning happens in the Actor. No LLM calls from the Twin.
- MCP tools are read/write data operations, not reasoning operations

**Observer (Background daemon):**
- Runs locally as a persistent process
- Handles: SDR encoding (Hot → Warm promotion), structural USD updates, Hebbian decay
- Does NOT call any external LLM
- Communicates with the stage via usd_lite

**Coach Core Projection:**
- New MCP tool: `twin_coach` — returns a formatted system prompt block
- Reads current stage state, projects it into Anthropic XML format
- Includes: active cognitive profile, trust level, recent patterns, pending Elenchus items
- Claude-only formatting for v8.0 (hardcoded Anthropic XML)

**Kill twin_ask:**
- Remove `twin_ask` MCP tool entirely
- Remove any LLM client code from the MCP server
- Remove `ANTHROPIC_API_KEY` requirement from the MCP server (Observer needs no API key)

**Design output:** Observer process architecture, Coach Core template, twin_coach tool signature, deletion manifest for twin_ask.

### Forge Scope
1. Create `python/cognitive_twin/observer/` — background daemon process
2. Create `python/cognitive_twin/coach/` — Coach Core projection engine
3. Implement `twin_coach` MCP tool
4. Delete `twin_ask` and all associated LLM client code
5. Remove `ANTHROPIC_API_KEY` from MCP server requirements
6. Update MCP server tool registry
7. Tests in `tests/test_observer/`, `tests/test_coach/`

### Crucible Gates

**Gate 2a: twin_ask is Dead**
- `grep -r "twin_ask" python/` returns zero results
- No LLM client imports remain in MCP server code
- MCP server starts without `ANTHROPIC_API_KEY` in env

**Gate 2b: Coach Core Projection**
- `twin_coach` returns valid Anthropic XML system prompt block
- Projection includes cognitive profile, trust level, recent patterns
- Output is deterministic for the same stage state

**Gate 2c: Observer Lifecycle**
- Observer process starts, runs encoding promotion loop, shuts down cleanly
- Hot → Warm promotion moves traces correctly
- Observer does not import any LLM client libraries

---

## PHASE 3: TRUST & COGNITIVE PROFILE
**Resolves:** RISK-3 (3-Tier Float Trust), GAP-1 (Intake Migration)

### Architect Scope

**Trust Ledger:**
- USD path: `/RelationalModel/Trust`
- Schema: `trust_score: float [0.0–1.0]`
- Thresholds: 0.0–0.3 (New: passive store), 0.3–0.7 (Familiar: context/pattern surfacing), 0.7–1.0 (Trusted: proactive coaching/pushback)
- Basal Ganglia evaluates the float directly — smooth continuous updates
- Update formula: define based on interaction quality signals (session length, explicit feedback, correction acceptance)

**Cognitive Recalibration:**
- New MCP tool: `trigger_cognitive_recalibration`
- Resets `/Meta/intake_complete` to `false`
- Clears `/CognitiveProfile` sublayer
- Actor can invoke autonomously when user indicates major life/role change
- Re-triggerable: can be called multiple times across the lifetime

**Design output:** Trust schema, Basal Ganglia integration points, update formula, recalibration tool signature, intake re-entry flow.

### Forge Scope
1. Implement trust float in `/RelationalModel/Trust` USD schema
2. Wire Basal Ganglia to read trust float with threshold-based behavior gating
3. Implement trust update logic (interaction quality → score delta)
4. Create `trigger_cognitive_recalibration` MCP tool
5. Implement intake flag reset + CognitiveProfile sublayer clearing
6. Update Coach Core to inject trust-appropriate behavior directives
7. Tests in `tests/test_trust/`, `tests/test_recalibration/`

### Crucible Gates

**Gate 3a: Trust Float**
- Trust score initializes at 0.0 for new user
- Score updates continuously (not discrete jumps)
- Basal Ganglia gates behavior correctly at each threshold
- Score is readable via existing `twin_session_status`

**Gate 3b: Recalibration**
- `trigger_cognitive_recalibration` resets intake flag
- CognitiveProfile sublayer is cleared
- Next Actor turn receives intake-mode Coach Core projection
- Calling recalibration twice is idempotent

---

## PHASE 4: ELENCHUS DEFERRAL
**Resolves:** GAP-2 (Observer LLM Requirement)

### Architect Scope

**Pending Verification Queue:**
- USD path: `/Elenchus/Pending`
- Schema: list of `{claim_id, claim_text, source_traces[], structural_score, timestamp}`
- Observer evaluates structural/heuristic checks locally
- Semantic claims that need LLM evaluation are queued here

**Actor-Side Verification:**
- New MCP tool: `resolve_verifications`
- Coach Core injects a system block when pending items exist: "Evaluate these claims silently"
- Actor submits boolean verdicts per claim via `resolve_verifications`
- Tool moves verified claims to `/Elenchus/Verified` or `/Elenchus/Rejected`
- "Renting cloud LLM compute to verify sovereign local state"

**Design output:** Pending queue schema, resolve_verifications tool signature, Coach Core injection template for pending claims, Observer-side structural evaluation pipeline.

### Forge Scope
1. Implement `/Elenchus/Pending` USD layer
2. Implement Observer-side structural claim evaluation (non-LLM heuristics)
3. Implement `resolve_verifications` MCP tool
4. Update Coach Core to inject pending claims when queue is non-empty
5. Implement claim lifecycle: Pending → Verified/Rejected
6. Tests in `tests/test_elenchus_v8/`

### Crucible Gates

**Gate 4a: Pending Queue**
- Observer queues semantic claims correctly
- Structural claims are resolved locally without queuing
- Queue persists across Observer restarts

**Gate 4b: Actor Verification**
- `resolve_verifications` accepts claim_id + boolean verdict
- Verified claims move to `/Elenchus/Verified`
- Rejected claims move to `/Elenchus/Rejected`
- Coach Core stops injecting claims once queue is empty

---

## PHASE 5: TEMPORAL COMPACTION
**Resolves:** GAP-3 (Epoch-Based Flattening Semantics)

### Architect Scope

**Replay-Then-Archive Compaction:**
- Deep-idle daemon process (runs when system is idle, not real-time)
- Input: variant stack (temporal layers of USD opinions)
- Algorithm:
  1. Chronologically sort variant stack by timestamp
  2. Replay each layer, applying elapsed-time Hebbian decay at `t_now`
  3. Write resolved state to `/Baseline`
  4. Zip variant stack into `.usda.archive/` directory
- **Critical invariant:** Flattening MUST commute with Hebbian neuroplasticity. `flatten(decay(variants)) == decay(flatten(variants))` — if this doesn't hold, the compaction is lossy.
- Preserves temporal archaeology: archived variants are queryable but don't bloat the active stage

**Design output:** Compaction algorithm pseudocode, archive format, decay-commutation proof sketch, daemon trigger conditions (idle detection).

### Forge Scope
1. Create `python/cognitive_twin/compaction/` — replay-then-archive engine
2. Implement chronological variant replay with decay curves
3. Implement baseline write after compaction
4. Implement archive creation (`.usda.archive/`)
5. Implement idle-trigger daemon hook
6. Tests in `tests/test_compaction/`

### Crucible Gates

**Gate 5a: Compaction Correctness**
- Create 10 variants with known decay parameters
- Compact them
- Verify: compacted baseline matches manual chronological replay result
- Verify: decay commutation holds (within floating-point epsilon)

**Gate 5b: Archive Integrity**
- Archived variants are readable
- Stage size decreases after compaction
- Original variant data is recoverable from archive
- Compaction is idempotent (running twice on already-compacted data = no-op)

---

## PHASE 6: FEDERATED RECALL & MCP
**Resolves:** TENSION-1 (Store vs Recall Latency)

### Architect Scope

**Federated query_past_experience:**
- New MCP tool replacing/augmenting `twin_recall`
- Executes TWO simultaneous queries:
  1. FTS5 plaintext search on Hot Tier (SQLite, un-encoded, immediate)
  2. SDR Hamming search on Warm Tier (Rust hippocampus, encoded)
- Merges results by relevance score (FTS5 rank + Hamming distance normalized)
- Returns unified result set to Actor
- Satisfies "what did I just say?" (Hot, zero-latency) and "what patterns exist?" (Warm, semantic)

**MCP Tool Registry v8.0:**
| Tool | Status | Path |
|------|--------|------|
| twin_store | MODIFIED | Hot Tier only, zero-encoding |
| twin_session_status | KEPT | Includes trust float |
| twin_patterns | KEPT | Reads from Warm Tier |
| twin_recall → query_past_experience | REPLACED | Federated L1/L2 |
| twin_ask | DELETED | Killed in Phase 2 |
| twin_coach | NEW | Coach Core projection |
| trigger_cognitive_recalibration | NEW | Intake reset |
| resolve_verifications | NEW | Elenchus actor-side |

**Design output:** query_past_experience signature, merge algorithm, result schema, MCP tool registry diff.

### Forge Scope
1. Implement `query_past_experience` with federated search
2. Wire FTS5 Hot Tier query path
3. Wire SDR Warm Tier query path (existing hippocampus)
4. Implement result merging (normalized scoring)
5. Update MCP server tool registry
6. Deprecate `twin_recall` (redirect to query_past_experience)
7. Tests in `tests/test_federated_recall/`

### Crucible Gates

**Gate 6a: Hot Recall**
- Store a trace via `twin_store`
- Immediately query via `query_past_experience`
- Trace appears in results (from FTS5 Hot Tier)
- Latency <5ms for the Hot path

**Gate 6b: Warm Recall**
- After Observer promotion, query returns SDR-matched results from Warm Tier
- Semantic similarity search works (not just keyword match)

**Gate 6c: Federated Merge**
- Query that matches both Hot and Warm tiers returns merged, deduplicated results
- Results are ranked by unified relevance score
- No duplicate traces in output

---

## PHASE 7: TEST SUITE REWRITE
**Resolves:** GAP-5 (Testing Strategy)

### Architect Scope

**Test Architecture:**
- **REJECT** full backward compatibility with the 720 v7 integration tests
- **RETAIN** v7 tests as unit tests for pure math (Hamming distance, LIVRPS logic, SDR ops)
- **NEW** disaggregated test suite organized by v8 component boundaries:

```
tests/
├── test_unit/              # Pure math, no I/O
│   ├── test_hamming.py     # Retained from v7
│   ├── test_livrps.py      # Retained from v7
│   └── test_sdr_ops.py     # Retained from v7
├── test_hot_store/         # Phase 1
├── test_encoder/           # Phase 1 (ONNX pipeline)
├── test_observer/          # Phase 2
├── test_coach/             # Phase 2
├── test_trust/             # Phase 3
├── test_recalibration/     # Phase 3
├── test_elenchus_v8/       # Phase 4
├── test_compaction/         # Phase 5
├── test_federated_recall/  # Phase 6
├── test_integration/       # Cross-component flows
│   ├── test_store_recall_cycle.py
│   ├── test_observer_promotion.py
│   └── test_coach_projection.py
└── test_latency/           # SLA enforcement
    ├── test_hot_store_sla.py    # <2ms store
    ├── test_mcp_latency.py      # <2ms Hot Store reads
    └── test_recall_sla.py       # <50ms federated recall
```

**Latency SLAs (enforced in CI):**
- Hot Store write: <2ms (p99, 100 calls)
- Hot Store read (FTS5): <2ms (p99, 100 calls)
- Federated recall: <50ms (p99, 100 calls)
- Coach Core projection: <10ms
- MCP tool round-trip (stdio): <100ms

**Design output:** Test directory structure, SLA thresholds, which v7 tests to retain, integration test scenarios.

### Forge Scope
1. Reorganize test directory per Architect design
2. Move retained v7 pure-math tests to `test_unit/`
3. Write latency SLA tests
4. Write cross-component integration tests
5. Ensure all phases' tests are collected properly
6. Final full suite run: `python -m pytest tests/ -v --ignore=tests/test_encoder --ignore=tests/test_daemon`

### Crucible Gates

**Gate 7a: Unit Test Survival**
- All retained v7 pure-math tests pass
- No test regressions from the move

**Gate 7b: Latency SLAs**
- All latency tests pass their thresholds
- Hot Store <2ms, federated recall <50ms, Coach Core <10ms

**Gate 7c: Full Suite Green**
- Complete test suite runs green
- Total test count documented
- No skipped tests (except explicitly excluded: test_encoder, test_daemon)

---

## FROZEN BOUNDARIES (Do Not Touch)

| Path | Reason |
|------|--------|
| `crates/hippocampus/` | Rust core. Warm Tier engine. Untouched unless encoding gate requires it. |
| `pyproject.toml` | Only modify if adding new dependencies required by v8 components |
| `.mcp.json` | MCP config — modify only to add new tools |

---

## VERIFICATION COMMANDS

```bash
# Primary test command (use after every mutation)
python -m pytest tests/ -v --ignore=tests/test_encoder --ignore=tests/test_daemon

# Rust extension rebuild (only if touching crates/)
maturin develop

# Type checking (if mypy is configured)
python -m mypy python/cognitive_twin/ --ignore-missing-imports

# Latency SLA tests (Phase 7)
python -m pytest tests/test_latency/ -v --tb=short
```

---

## CODING CONVENTIONS (Match Existing Codebase)

- **Imports:** `from cognitive_twin.module import Class` (absolute, never relative)
- **Docstrings:** Google style, one-line summary + Args/Returns/Raises
- **Type hints:** All function signatures typed. Use `typing` for complex types.
- **Error handling:** Custom exceptions in `cognitive_twin/exceptions.py`. Never bare `except`.
- **USD paths:** String constants in `cognitive_twin/usd_lite/paths.py`
- **Logging:** `logging.getLogger(__name__)` — no print statements
- **Tests:** pytest + fixtures. One assert per test where practical. Descriptive test names: `test_{what}_{condition}_{expected}`.
- **Commits:** `v8-phase{N}: {description}` — one commit per sub-task minimum

---

## EXECUTION SEQUENCE

```
mkdir -p .agent-team/designs .agent-team/blockers .agent-team/gates

For phase in 1..7:
    ARCHITECT:
        Read this file + existing codebase patterns
        Produce .agent-team/designs/phase-{N}.md
    
    FORGE:
        Read .agent-team/designs/phase-{N}.md
        Implement per design
        Run verification after every mutation
        Git commit per sub-task
    
    CRUCIBLE:
        Run gate tests
        Write adversarial tests
        Produce .agent-team/gates/phase-{N}-gate.md
        If FAIL → Forge fixes → Crucible re-verifies (loop)
        If PASS → proceed to next phase
    
    If phase == 1:
        ⚠️ HUMAN GATE — present results, wait for Joe
```

---

## ADR DECISION SUMMARY (Quick Reference)

| ID | Decision | Binding Directive |
|----|----------|------------------|
| RISK-1 | FP16 fallback authorized | 0.95 Hamming correlation gate. No QAT. INT8 first, FP16 if needed. |
| RISK-2 | Kill twin_ask | Actor reasons. Twin stores. No LLM in MCP server. |
| RISK-3 | 3-tier float trust | [0.0–1.0] continuous. Basal Ganglia evaluates float. |
| GAP-1 | Intake re-triggerable | trigger_cognitive_recalibration MCP tool. Resets flag + clears profile. |
| GAP-2 | Defer Elenchus to Actor | Observer queues. Actor verifies via resolve_verifications. |
| GAP-3 | Replay-then-archive | Chronological replay with decay. Commutes with Hebbian math. |
| GAP-4 | Claude-only v8.0 | Coach Core hardcoded Anthropic XML. Multi-model deferred to v8.1. |
| GAP-5 | Clean test rewrite | Reject v7 integration backward compat. Retain pure-math unit tests. |
| TENSION-1 | FTS5 + SDR federated | L1 Hot (FTS5, zero-encoding) + L2 Warm (SDR). Merged query. |

---

## KICKOFF PROMPT (Paste into Claude Code)

```
You are executing a 7-phase architectural rewrite of the Cognitive Twin codebase from v7.0 to v8.0.

Read AGENTS.md in the project root. It is your operating specification.

You are a Sequential MoE pipeline: Architect → Forge → Crucible, repeated for each of 7 phases. There is no Scout phase — the AGENTS.md IS the reconnaissance.

Your agent rules are derived from the Twin's own architecture:
- Rule 2 = Basal Ganglia Gate: Every mutation is gated. Default state is INHIBIT.
- Rule 3 = UNPROVABLE: 3 failures → park with dignity.
- Rule 5 = Trace Exclusion: Role boundaries are structural.
- Rule 7 = Crucible IS Elenchus: Blind verification. Spec-gaming detection.

Begin Phase 1: Encoding & Hot Path. Start as Architect.
```

---

*v8.0 Agentic Build Teams Execution Spec — derived from Gemini Deep Think ADR*
*AlphaProof AND/OR decomposition — hardest subtask (Phase 1) surfaced first*
*MoE pattern: Architect → Forge → Crucible × 7 sequential phases*
