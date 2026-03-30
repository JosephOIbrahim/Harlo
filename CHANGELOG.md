# Changelog

## v3.3.1 — Production Live (March 30, 2026)

Production release. 5 sprints, 250 tests, real USD stage, organic data flowing.

### Sprint 1: Cognitive State Machine Simulation
- Pydantic schemas with IntEnum ordinal types (Momentum, Burnout, Energy, Burst, Injection)
- CognitiveObservation canonical schema with telemetry block
- MockUsdStage (dict-based, read_previous at index 0 returns baseline, NEVER None)
- MockCogExec: networkx DAG with topological evaluation (7 computation nodes)
- Pure computation functions: momentum, burnout, energy, burst, allostasis, injection_gain, context_budget
- Adrenaline masking (energy suspends during burst, debt on exit)
- Anchor immunity (gain = 1.0 ALWAYS, separate function)
- RED exogenous override (ANY → RED, Commandment 7)
- Context budget hysteresis (promote >4.2x, demote <3.8x)
- 26-invariant validator (INV-01 to INV-26, RED exception for INV-14)
- Trajectory generator: 10,000 sessions, 278,577 exchanges, 0 violations
- Profile-Driven Markov Biasing (7 profiles, distribution targets ±5%)
- XGBoost MultiOutputRegressor (111 features, 4 targets, 100% per-field accuracy)
- Bridge integration: 50-exchange end-to-end with delegate + buffer + predictor
- Observation buffer: SQLite priority queue with anchor (20%) / organic (80%) partitions

### Sprint 2: USD 26 OpenExec (Circuit-Breaker)
- USD 26.03 built from source with PXR_BUILD_EXEC=ON on Windows
- C++ Exec libraries compiled (usd_exec.dll, usd_execGeom.dll, usd_execIr.dll, usd_execUsd.dll)
- usdGenSchema available
- **Circuit-breaker triggered:** Zero Python bindings in v26.03 source. MockCogExec continues.

### Sprint 3: Hydra Cognitive Delegates + Live MCP
- HdCognitiveDelegate ABC (Sync/Execute/CommitResources)
- DelegateRegistry with capability-matching selection
- HdClaude (interactive reasoning) + HdClaudeCode (batch implementation)
- compute_routing: outputs capability requirements, NOT delegate names
- OOB consent tokens (HMAC-signed, TTL, revocable, app-layer only)
- Sublayer-per-delegate concurrency (LIVRPS composition, interactive wins)
- CognitiveEngine singleton: DAG → route → delegate → observe → predict
- 20-exchange end-to-end live test

### Sprint 4: Real USD Stage
- CognitiveStage wrapping pxr.Usd.Stage (drop-in for MockUsdStage)
- .usda files on disk: data/stages/cognitive_twin.usda
- Delegate sublayers: data/stages/delegates/{id}.usda
- Time samples via Usd.TimeCode(exchange_index)
- stage_factory toggle (USE_REAL_USD env var)
- Backend parity verified (mock produces identical results to real USD)

### Sprint 5: Production Hardening
- Graceful degradation (every component fails independently)
- Health check endpoint (engine.get_health())
- Kill switches: ENGINE_ENABLED, USE_REAL_USD, OBSERVATION_LOGGING, PREDICTION_ENABLED
- Memory queue for observations when DB locked (max 100)
- First session verified: 10 exchanges, real .usda on disk, predictions flowing
- 458 organic observations collected

### Test Summary
| Suite | Tests |
|-------|-------|
| Sprint 1 | 84 |
| Sprint 3 | 85 |
| Sprint 4 | 59 |
| Sprint 5 | 22 |
| **Total Sprint** | **250** |
| Core Twin | 890 |
| Rust (hippocampus) | 41 |

---

## v8.0.0 — Actor/Observer Disaggregation + Hot/Warm Tiered Memory

### Architecture

Complete v7 to v8 rewrite per the Surgical Directives ADR. 7 phases executed via Sequential MoE pipeline (Architect → Forge → Crucible). The Actor (LLM) reasons. The Observer (Twin) stores and projects. No local LLM required.

**7 phases completed:**

1. **Encoding & Hot Path** — Zero-encoding Hot Tier (SQLite + FTS5, <0.2ms store p99), ONNX Runtime encoder (BGE-small CLS pooling, Hamming correlation >= 0.95), Hot→Warm promotion pipeline
2. **Disaggregation** — Killed `twin_ask`, removed `ANTHROPIC_API_KEY` from MCP server, built Observer (background promotion, no LLM deps), built Coach (stage → Anthropic XML system prompt projection)
3. **Trust & Cognitive Profile** — Continuous [0.0, 1.0] Trust Ledger with 3-tier gating (new/familiar/trusted), `trigger_cognitive_recalibration` MCP tool
4. **Elenchus Deferral** — Pending verification queue (SQLite-backed), Actor-side `resolve_verifications` MCP tool, Coach Core injects pending claims
5. **Temporal Compaction** — Replay-then-archive engine with decay commutation invariant, recoverable archives at `.usda.archive/`
6. **Federated Recall** — `query_past_experience` searches Hot (FTS5) + Warm (SDR Hamming) simultaneously, normalizes scores, deduplicates, merges ranked results
7. **Test Suite + SLAs** — Latency SLA enforcement (store <2ms, FTS5 <2ms, Coach <10ms)

### MCP tool registry changes

| Tool | Status |
|------|--------|
| `twin_store` | MODIFIED — writes to Hot Tier, zero-encoding |
| `twin_recall` | KEPT — warm-tier SDR search (backward compat) |
| `query_past_experience` | **NEW** — federated Hot+Warm recall |
| `twin_coach` | **NEW** — system prompt projection |
| `twin_patterns` | KEPT |
| `twin_session_status` | KEPT |
| `resolve_verifications` | **NEW** — Actor-side Elenchus |
| `trigger_cognitive_recalibration` | **NEW** — intake/trust reset |
| `twin_ask` | **DELETED** — Actor reasons, Twin stores |

### Modules added

- `python/cognitive_twin/hot_store/` — Hot Tier (L1) with FTS5 + promotion pipeline
- `python/cognitive_twin/observer/` — Background Hot→Warm SDR promotion
- `python/cognitive_twin/coach/` — Coach Core system prompt projection
- `python/cognitive_twin/trust/` — Trust Ledger + cognitive recalibration
- `python/cognitive_twin/elenchus_v8/` — Deferred verification queue
- `python/cognitive_twin/compaction/` — Temporal compaction engine
- `python/cognitive_twin/federated_recall.py` — Federated Hot+Warm query
- `python/cognitive_twin/encoder/onnx_encoder.py` — ONNX Runtime BGE encoder

### Dependencies added

- `onnxruntime>=1.17` — ONNX model inference for SDR encoding
- `transformers>=4.36` — AutoTokenizer for ONNX encoder input

### By the numbers

- 791 tests, all passing (was 761 in v7)
- 27 test modules (was 20 in v7)
- 8 MCP tools (was 5 in v7)
- 0 LLM dependencies in MCP server (was 1 in v7)
- <0.2ms store latency (p99)
- <2ms FTS5 search latency (p99)
- >= 0.95 Hamming distance correlation (ONNX vs reference encoder)

### Breaking changes

- `twin_ask` removed — Actor (Claude) provides reasoning via MCP tools
- `twin_store` response format changed: `{status: "stored", tier: "hot", encoded: false}`
- `ANTHROPIC_API_KEY` no longer required by MCP server
- New dependencies: `onnxruntime`, `transformers`

---

## v7.0.0 — USD Brain Housing + Brainstem + Hebbian Neuroplasticity

### Architecture

Complete v6 to v7 rewrite informed by 2026 frontier research (Titans, Mnemis, SSGM, REMem, HiMem, LoCoMo-Plus) plus neuropsych-informed cognitive profile calibration.

**5 phases completed:**

1. **USD-Lite Container** — 17 typed prim dataclasses, `.usda` serialization, LIVRPS composition, hex SDR encoding (512-char strings), float tolerance via `math.isclose()`
2. **Brainstem Translation** — Lossless adapter pairs with Hypothesis property-based fidelity proofs, Z-score surprise metric, dual-process routing (System 1/System 2), structured provenance (5 source types)
3. **Elenchus + Composition** — Already existed in v6, integrated with brainstem stage builder
4. **Cognitive Profile Intake** — Adaptive questionnaire, continuous [0.0, 1.0] scoring, personal multipliers, semantic ceiling detection (disengagement-based, not answer length). Incremental skills observer with cursor-based O(new_traces) processing
5. **Hebbian Neuroplasticity** — Dual-mask SDR evolution (`(base | strengthen) & ~weaken`), homeostatic plasticity [3%-5%], episodic context reconstruction, reconsolidation boost (user-retrieval gated), Elenchus training data pipeline (JSONL with full cognitive profile feature vector)

### 11 Gemini-reviewed patches applied

1. Surprise Z-score (ratio replaced with Z-score formulation, threshold 2.0)
2. Apoptosis twilight zone (reconstruction threshold clamped above apoptosis by 0.05)
3. Continuous scoring (intake uses [0.0, 1.0] floats, not buckets)
4. Merkle isolation (Hebbian deltas in [V] Variant layer, not destructive SQLite mutation)
5. Training data features (JSONL includes full cognitive_profile_features vector)
6. Semantic ceiling (disengagement detection, not answer length)
7. Dual masks (XOR toggle flaw fixed: `(base | strengthen) & ~weaken`, weaken wins)
8. O(1) log rotation (append-only + rotate-at-threshold, max 3 rotated files)
9. Hex SDR serialization (512-char hex strings, not 6KB text arrays)
10. Incremental skills observer (cursor-based, O(new_traces), ghost window safe)
11. Reconsolidation boost (retrieval boost to contributing traces, user-retrieval gated)

### Modules added

- `python/cognitive_twin/usd_lite/` — USD container format
- `python/cognitive_twin/brainstem/` — Lossless translation + metacognitive routing
- `python/cognitive_twin/hebbian/` — Neuroplasticity + reconstruction + training data
- `python/cognitive_twin/intake/` — Cognitive profile intake system
- `python/cognitive_twin/skills/` — Competence tracking observer
- `python/cognitive_twin/migrate_v7.py` — v6 to v7 migration

### Modules removed

- `python/cognitive_twin/bridge/` — Replaced by brainstem

### By the numbers

- 761 tests (720 Python + 41 Rust), all passing
- 20 test modules across all subsystems
- 17 typed prim dataclasses
- 5 MCP tools
- 33 inviolable architectural rules
- 5 source types for structured provenance

### Breaking changes

- Bridge module removed, replaced by brainstem with adapter-based translation
- USD-Lite stage format replaces raw dict-based brain state
- MCP server instructions updated (v6.0 to v7.0)
- CLI version string updated to 7.0.0
- Export format version bumped to 7.0.0

## v6.0.0 — Motor Cortex

Initial public architecture with Association Engine (Rust), Composition Engine, Elenchus verification, Inquiry/DMN, Motor Cortex with Basal Ganglia gating, and 33 inviolable rules.
