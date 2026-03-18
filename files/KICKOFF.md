# COGNITIVE TWIN v7.0 REWRITE — KICKOFF PROMPT
# Paste this entire file into Claude Code from the Cognitive_Twin project root.
# Prerequisites: AGENTS.md updated, CLAUDE.md updated, .agent-team/ directory exists.
# Gemini Deep Think pass: ALL 6 patches applied (Z-score, apoptosis clamp, continuous scoring,
#   semantic ceiling, Merkle isolation, training data features).
# Gemini Phase 1 Review: 5 additional patches applied (dual masks, log rotation, hex serialization,
#   incremental skills observer, reconsolidation boost, float tolerance __eq__).

---

You are executing a 5-phase architectural rewrite of the Cognitive Twin codebase from v6.0 to v7.0.

## YOUR OPERATING MODE

You are running as a Sequential MoE pipeline: **Architect → Forge → Crucible**, repeated for each of 5 phases. There is no Scout phase — the engineering specification below IS the reconnaissance.

Read AGENTS.md for your role definitions, rules, and verification gates.
Read CLAUDE.md for frozen boundaries, verification commands, and coding conventions.

**Your agent rules are derived from the Twin's own architecture.** You operate under the same principles you are building:
- **Rule 2 = Basal Ganglia Gate:** Every mutation is gated. Default state is INHIBIT.
- **Rule 3 = UNPROVABLE:** 3 failures → park with dignity. Reason, what_would_help, partial_progress.
- **Rule 5 = Trace Exclusion:** Role boundaries are structural. Forge reads the design, not the reasoning.
- **Rule 7 = Crucible IS Elenchus:** Blind verification. Spec-gaming detection. Fix forward, never weaken tests.

## PHASE EXECUTION ORDER

```
Phase 1: Foundation (USD Layer)        → Architect → [HUMAN GATE] → Forge → Crucible → Gate 1
Phase 2: Core Transport (Brainstem)    → Architect → Forge → Crucible → Gate 2a + 2b + 2c
Phase 3: Subsystem Cutover             → Architect → Forge → Crucible → Gate 3a + 3b + 3c + 3d
Phase 4: Observation + Migration       → Architect → Forge → Crucible → Gate 4a + 4b + 4c + 4d + 4e
Phase 5: Hebbian Neuroplasticity       → Architect → Forge → Crucible → Gate 5a + 5b + 5c + 5d
```

**CRITICAL: After Phase 1 Architect completes its design, PAUSE and present the design for human review before Forge begins.** This is the single human gate. For Phases 2-5, proceed automatically unless a blocker is surfaced.

**CRITICAL: Do NOT begin a new phase until ALL gate checks for the current phase pass. Gates are binary — fully pass or fully fail. Partial gates are spec-gaming.**

---

## 1. Executive Constraints & Immutable Rules

These constraints strictly bound the v7.0 refactor. No phase may violate any of them.

1. **The Rust Hot Path:** `crates/hippocampus/` remains untouched. Sub-2ms XOR + popcount recall is the performance core. USD is strictly for serialization/composition, not compute.
2. **Zero-Watt Lifecycle (Rule 33):** Socket-activated daemon. No background polling, no `while True` loops. Operations run on demand or during the 30-second teardown ghost window.
3. **Trace Exclusion (Rule 11):** Elenchus is physically forbidden from seeing reasoning traces. Enforced structurally, not by filtering. Two Brainstem construction paths:
   - Path A (`full_stage()`): Complete USD stage with all prims including `/Association` traces. Used for session capsules, export, skill building.
   - Path B (`elenchus_stage()`): Restricted input set that structurally cannot include `/Association` or any reasoning trace data. Elenchus receives only its own state, gate status, and the Merkle root. Never trace content.
4. **Lazy Decay Model (Rule 4):** `strength = initial · e^(-λt) + Σ(retrieval_boosts)`. Decay is evaluated on read, not maintained by a background process.
5. **Existing 5 MCP Tools:** `twin_store`, `twin_recall`, `twin_ask`, `twin_patterns`, `twin_session_status` remain. Phase 4 adds `twin_skills` (#6) and `twin_intake` (#7).
6. **SQLite as Source of Truth:** `.usda` files are computed views, never replacements.
7. **33 Inviolable Rules:** All existing rules remain in force. The v7 rewrite operates within them.

---

## 2. Architecture Specification

### 2.1 Move 1: USD as Brain Housing

#### 2.1.1 Problem
Each subsystem has its own data format. The Bridge stitches them together through ad-hoc Python orchestration. Session capsules are unstructured text blobs. Brain state is not inspectable by external tools. No unified composition order across the whole brain. No single serialization format. Diffing brain states across time is not possible.

#### 2.1.2 Solution: USD Stage as Universal Container
Universal Scene Description (USD), created by Pixar, solves exactly this problem for 3D scenes: many subsystems contributing opinions to a shared stage, with deterministic composition rules (LIVRPS). The Composition Engine already uses LIVRPS for knowledge conflicts. This move promotes USD from "conflict resolution tool in one subsystem" to "the container format for the entire brain state."

Every subsystem writes to a shared USD stage. Each subsystem owns a layer. LIVRPS composition order determines what wins when subsystems disagree. Not just for knowledge conflicts, but across the entire brain.

#### 2.1.3 Prim Schema Design

```
/Brain                              # Root
  /Association                      # Hippocampus recall results
    /Traces                         # Individual memory traces
      /{trace_id}
        sdr: int[2048]             # Sparse Distributed Representation
        content_hash: string
        strength: float            # Lazy decay formula
        last_accessed: datetime
        co_activations: dict       # Phase 5: Hebbian tracking
        competitions: dict         # Phase 5: Anti-Hebbian tracking
        hebbian_strengthen_mask: int[2048]  # Phase 5: bits to force ON (Patch 7)
        hebbian_weaken_mask: int[2048]      # Phase 5: bits to force OFF (Patch 7)
  /Composition                      # LIVRPS opinion layers
    /Layers
      /{layer_id}
        arc_type: enum             # LOCAL, REFERENCE, INHERIT, VARIANT, PAYLOAD, SPECIALIZE
        opinion: any
        timestamp: datetime
        provenance: Provenance     # Phase 3: structured dataclass
        permanent: bool            # Amygdala reflexes = immutable
  /Elenchus                         # Verification engine state
    /GateStatus
      verification_state: enum     # TRUSTED, CONTESTED, REFUTED, PENDING
      cycle_count: int
      last_verified: datetime
    /MerkleRoot
      root_hash: string
      trace_count: int
  /Session                          # Session metadata
    current_session_id: string
    exchange_count: int
    surprise_rolling_mean: float   # Rolling mean hamming (last 100 recalls) — Phase 2
    surprise_rolling_std: float    # Rolling std dev hamming (last 100 recalls) — Phase 2
    last_query_surprise: float     # Z-score of most recent recall — Phase 2
    last_retrieval_path: enum      # SYSTEM_1 or SYSTEM_2 — Phase 2
  /Inquiry                          # DMN hypotheses
    /Active
      hypothesis: string
      confidence: float
  /Motor                            # Action proposals
    /Pending
      action: string
      gate_status: enum            # INHIBITED, APPROVED, EXECUTING
  /Skills                           # Phase 4: competence tracking
    /{domain}
      trace_count: int
      first_seen: datetime
      last_seen: datetime
      growth_arc: list[float]      # Strength trajectory over time
      hebbian_density: float       # Phase 5: co-activation richness
  /CognitiveProfile                 # Phase 4: personal calibration
    /Multipliers
      surprise_threshold: float    # Default 2.0 (Z-score) if no intake
      reconstruction_threshold: float  # Default 0.3 if no intake
      hebbian_alpha: float         # Default 0.01 if no intake
      allostatic_threshold: float  # Default 1.0 if no intake
      detail_orientation: float    # [0.0, 1.0] continuous — affects reconstruction aggressiveness
    /IntakeHistory
      last_intake: datetime
      intake_version: string
      answer_embeddings: list      # For future reprocessing
```

#### 2.1.4 Implementation: `usd_lite/`

**NOT** full OpenUSD. A lightweight Python module that provides:
- Dataclasses matching every prim type above (type-safe, IDE-friendly)
- `.usda` text serialization (human-readable export)
- LIVRPS composition logic (precedence: L > I > V > R > P > S)
- Permanent-prim handling: prims with `permanent: true` override normal LIVRPS recency rules
- Round-trip guarantee: `parse(serialize(stage)) == stage`
- **`BrainStage.__eq__` with float tolerance (Patch 11+):** Float fields (`strength`, `confidence`, `surprise_rolling_mean`, etc.) compared via `math.isclose(rel_tol=1e-9)`. All other fields use exact equality. Without this, the round-trip guarantee will fail on float serialization/deserialization rounding.
- **Compact SDR serialization (Patch 9):** 2048-bit integer arrays (`sdr`, `hebbian_strengthen_mask`, `hebbian_weaken_mask`) MUST be serialized in `.usda` as dense 512-character hex strings, NOT as text arrays of 2048 integers. A text array consumes ~6KB per trace; hex packs to 512 bytes. With thousands of traces, this is the difference between sub-second and multi-minute boot times. Arrays are unpacked to `List[int]` only during the in-memory `parse()` step.

**Why not full USD:** Full OpenUSD has a 2GB C++ dependency. The Twin needs ~5% of USD's functionality. `usd_lite/` implements just what's needed: dataclasses, serialization, and composition.

---

### 2.2 Move 2: Brainstem as Lossless Bridge

#### 2.2.1 Problem
The current `bridge/` module translates between subsystems through ad-hoc conversions. Each subsystem pair has custom glue code. Round-trip fidelity is untested. Adding a new subsystem requires N new bridge adapters.

#### 2.2.2 Solution: Lossless Translation Layer
The Brainstem converts any subsystem's native format to/from the USD stage with proven round-trip fidelity. Every subsystem gets one adapter (to_stage + from_stage), not N-1 pairwise bridges.

#### 2.2.3 Fidelity Proof
For every adapter: `assert from_stage(to_stage(native_data)) == native_data`. This is tested with Hypothesis (property-based testing) to cover edge cases automatically.

#### 2.2.4 Merkle Integrity
The Brainstem computes a Merkle hash over the `/Association/Traces` subtree. This hash is stored at `/Elenchus/MerkleRoot/root_hash`. Any bit-flip in any trace is detectable by comparing the recomputed hash against the stored one.

**CRITICAL (Patch 4 — Merkle Isolation, refined by Patch 7 — Dual Masks):** Hebbian modifications are NOT applied destructively to the base SDR stored in SQLite. Instead, Hebbian deltas are stored as two directional masks in a `[V] Variant` USD layer: `hebbian_strengthen_mask` (bits to force ON) and `hebbian_weaken_mask` (bits to force OFF). The effective SDR for recall is computed as: `effective_sdr = (base_sdr | strengthen_mask) & ~weaken_mask`. This avoids the XOR toggle flaw where reinforcing a bit that's already 1 would inadvertently flip it to 0. Set/clear is idempotent: reinforcing a 1 keeps it 1, weakening a 0 keeps it 0. The base trace in SQLite stays pristine. The Merkle hash is computed over the base traces only. This prevents Hebbian learning from triggering false-positive corruption detection.

#### 2.2.5 Metacognitive Routing (Dual-Process — from Mnemis/Titans research)

- **Surprise Metric (Z-score — Patch 1):** After every recall, compute `surprise = (best_hamming - rolling_mean) / max(rolling_std_dev, 1.0)`. Store `surprise`, `rolling_mean`, `rolling_std_dev` in `/Session`. Update rolling stats over last 100 recalls. The Z-score formulation prevents division-by-zero cold-starts (when rolling_std_dev is near zero, the floor of 1.0 prevents blowup) and adapts to SDR dimensionality clustering.
- **Dual-Process Routing:** When `surprise > /CognitiveProfile/Multipliers/surprise_threshold` (or > 2.0 if no profile exists), escalate from System 1 (Association — fast hamming search) to System 2 (Composition — deliberative LIVRPS traversal). Store `last_retrieval_path` in `/Session`.
- **Personal calibration:** The escalation threshold is NOT a universal constant. It is read from `/CognitiveProfile/Multipliers/surprise_threshold`. The intake calibrates this per-user. Default 2.0 Z-score if no intake has been run. An associative thinker gets a higher threshold (their System 1 is naturally stronger). A linear thinker gets a lower threshold (they benefit from System 2 more often).
- **Profile-Aware Defaults:** The Brainstem reads multipliers from `/CognitiveProfile/Multipliers/` when computing thresholds. If no profile exists (no intake has been run), use hardcoded defaults (2.0 for surprise Z-score, 0.3 for reconstruction, etc.). The Brainstem NEVER fails if the profile is empty — it gracefully falls back to universal baseline.

---

### 2.3 Move 3: Skill Building Engine

#### 2.3.1 Problem
The Twin stores and recalls memories but has no model of what the user is getting better at, what they're avoiding, or where their gaps are. It's a filing cabinet, not a twin.

#### 2.3.2 Solution: `/Skills` Observer
A new module that observes `/Association/Traces` during the ghost window (Rule 33 compliant) and builds a `/Skills` subtree. It tracks:
- **Domain clustering:** Groups traces by topic/domain
- **Growth arcs:** Strength trajectory over time per domain
- **Gap detection:** Domains with decaying traces and no new additions
- **Avoidance detection:** Topics queried about but never deeply engaged with
- **Hebbian density:** (Phase 5) How richly co-activated a domain's traces are — a proxy for deep vs superficial knowledge

**Incremental processing (Patch 10 — Ghost Window Compliance):** The observer MUST be incremental, not exhaustive. It tracks a `last_processed_timestamp` cursor and only computes clustering/density math for traces newer than the cursor. Full re-scan of all traces will blow past the 30-second ghost window with any non-trivial trace count. The cursor is persisted in SQLite alongside the `/Skills` data. On first run (migration), the full scan is acceptable as a one-time cost; subsequent runs are O(new_traces) only.

#### 2.3.3 MCP Tool: `twin_skills`

**Tool signature:**
```python
def twin_skills(query: str) -> str:
    """
    Query the user's skill/competence model.
    
    Patterns:
    - "what am I getting better at?" → domains with positive growth arcs
    - "what am I avoiding?" → domains with gap/avoidance signals
    - "how deep is my knowledge of X?" → specific domain analysis
    - "what should I work on?" → prioritized growth recommendations
    
    Returns: JSON matching /Skills schema with natural language summary.
    """
```

**Natural language triggers for Claude:** "what do I know about", "where are my gaps", "what am I learning", "how am I doing with", "skill", "growth", "progress", "weakness".

---

### 2.4 Cognitive Profile Intake System

#### 2.4.1 Problem
Every user gets the same surprise threshold, reconstruction aggressiveness, and learning rate. But cognitive profiles differ wildly — an associative thinker needs different routing thresholds than a linear thinker.

#### 2.4.2 Solution: Adaptive Neuropsych-Informed Intake
A conversational intake administered via the `twin_intake` MCP tool. It asks 5-8 questions drawn from validated neuropsychological dimensions, then derives personal multipliers that calibrate the Twin's routing, reconstruction, and learning parameters.

**Dimensions probed:**
- Associative vs. Linear thinking (→ surprise_threshold)
- Detail-oriented vs. Big-picture (→ reconstruction_threshold, detail_orientation)
- Attention sustain vs. Burst (→ hebbian_alpha)
- Stress tolerance (→ allostatic_threshold)

**Multiplier derivation (Patch 3 — Continuous Scoring):**
- Each answer maps to a continuous float score in [0.0, 1.0] via deterministic linear interpolation — NOT stepped/bucketed categories.
- Multiplier = `base + (score * range)` where base and range are fixed per dimension.
- Example: `surprise_threshold = 1.5 + (associativity_score * 1.0)` → range [1.5, 2.5].
- Deterministic: same answers always produce same multipliers.

**Ceiling detection (Patch 6 — Semantic):**
- Do NOT use raw answer length to detect disengagement. Short answers may be the user's natural style (especially TERSE cognitive profiles).
- Instead, track a semantic `user_disengaged: bool` flag based on: explicit dismissal language ("whatever", "skip", "don't care"), identical answers to different questions, or explicit opt-out.
- If `user_disengaged` triggers, offer to pause intake and use defaults. Never silently infer ceiling from response length.

**Re-callable:** Running the intake again updates the profile. History preserved in `/CognitiveProfile/IntakeHistory`. All changes carry `INTAKE_CALIBRATED` provenance.

**MCP Tool: `twin_intake`**
```python
def twin_intake(action: str) -> str:
    """
    Manage cognitive profile calibration.
    
    Actions:
    - "start" → Begin adaptive intake questionnaire
    - "answer:{response}" → Process user's answer, return next question or results
    - "status" → Show current profile multipliers
    - "reset" → Clear profile, return to universal defaults
    
    Returns: Next question, multiplier summary, or status report.
    """
```

---

## 3. Phase Specifications

### Phase 1: Foundation (USD Layer)

Create `python/cognitive_twin/usd_lite/`:
- Dataclasses for ALL prim types in schema (Section 2.1.3), including `Provenance` (Phase 3), `CognitiveProfile` types (Phase 4), surprise/confidence session fields (Phase 2), and Hebbian tracking fields (Phase 5) as forward-declared types.
- `.usda` text serializer with round-trip guarantee.
- LIVRPS composition engine with permanent-prim handling.
- 100% test coverage on `usd_lite/`.

**Phase 1 Gates:**
- Gate 1: All prim types instantiate. LIVRPS composition produces correct precedence. Permanent prims override recency. Round-trip fidelity holds for every prim type (`parse(serialize(stage)) == stage`), including float tolerance via `math.isclose()` in `BrainStage.__eq__`. **Hex serialization: 2048-bit arrays round-trip through 512-char hex strings without data loss.** 100% coverage.

### Phase 2: Core Transport (Brainstem)

Create `python/cognitive_twin/brainstem/`:
- `to_stage(native_data, subsystem) → Stage`: Convert any subsystem's output to USD prims.
- `from_stage(stage, subsystem) → native_data`: Convert back.
- `full_stage() → Stage`: Complete brain state (for session capsules, export, skill building).
- `elenchus_stage() → Stage`: Restricted stage (for Elenchus — NO `/Association`, NO traces).
- Merkle hash computation over `/Association/Traces`.
- Hypothesis-based fuzz testing for round-trip fidelity.
- **NEW:** Surprise metric computation (Z-score over rolling window of last 100 hamming distances).
- **NEW:** Dual-process routing logic (threshold-based escalation from System 1 to System 2).
- **NEW:** `/Session` prim updates after each recall.

**Phase 2 Gates:**
- Gate 2a (Fidelity): `from_stage(to_stage(x)) == x` for every subsystem adapter, proven by Hypothesis with 1,000+ examples.
- Gate 2b (Isolation): `elenchus_stage()` output contains zero traces. Verified by structural inspection, not content filtering.
- Gate 2c (Metacognitive Routing): Surprise Z-score computes correctly. Escalation triggers at threshold. Rolling mean and std_dev update after each recall. Profile multiplier scales the threshold. **Fallback test: when `/CognitiveProfile` is empty/default, routing uses hardcoded 2.0 Z-score threshold and does not crash.** **Cold-start test: with fewer than 10 recalls, rolling_std_dev near zero, the max(std_dev, 1.0) floor prevents blowup.**

### Phase 3: Subsystem Cutover

Adapt all existing subsystems (Association, Composition, Elenchus, Motor, DMN) to read/write through Brainstem instead of Bridge. Deprecate Bridge with a compatibility shim.

- **Structured Provenance (from SSGM/REMem research):** The plain `provenance: str` field in `/Composition/Layers` becomes a structured dataclass:
  ```python
  @dataclass
  class Provenance:
      source_type: SourceType  # USER_DIRECT | EXTERNAL_REFERENCE | SYSTEM_INFERRED | HEBBIAN_DERIVED | INTAKE_CALIBRATED
      origin_timestamp: datetime
      event_hash: str           # Deterministic hash of the originating event
      session_id: str
  ```
- Existing layers get `SYSTEM_INFERRED` provenance during migration.
- New layers populate provenance automatically.

**Phase 3 Gates:**
- Gate 3a: All subsystems read/write through Brainstem. Bridge shim handles any legacy calls.
- Gate 3b: No direct subsystem-to-subsystem communication bypasses the Brainstem.
- Gate 3c: All existing tests pass (Bridge shim is transparent).
- Gate 3d (Provenance): Every `/Composition/Layer` has fully populated structured Provenance. Layers from different sessions carry different event_hashes. `SYSTEM_INFERRED` correctly applied to migrated legacy layers.

### Phase 4: Observation + Migration

- Create `python/cognitive_twin/skills/`: The `/Skills` observer (ghost window compliant).
- Register `twin_skills` as MCP tool #6.
- Create cognitive profile intake system in `python/cognitive_twin/intake/`.
- Register `twin_intake` as MCP tool #7.
- Create `migrate_v7.py`: Bootstraps `/Skills` from legacy timestamps.
- DELETE `bridge/` entirely. Remove ALL references.

**Phase 4 Gates:**
- Gate 4a: `twin_skills` returns valid JSON for all 4 query patterns. **Skills observer is incremental: tracks `last_processed_timestamp` cursor, processes only new traces, completes within ghost window budget (< 5 seconds for 100 new traces).**
- Gate 4b: End-to-end MCP integration test passes for both new tools.
- Gate 4c: `migrate_v7` bootstraps `/Skills` from legacy DB with 10+ traces. Growth Arcs show non-zero deltas.
- Gate 4d: `bridge/` completely eradicated, zero broken imports, all tests pass, total tests ≥ 500.
- Gate 4e (Intake): Intake questionnaire administers adaptively. Multiplier derivation uses continuous [0.0, 1.0] float scores with deterministic linear interpolation. Profile stored in `/CognitiveProfile/Multipliers`. Re-run updates (not appends). Ceiling detection uses semantic `user_disengaged` flag (not answer length). After intake, Phase 2 routing uses calibrated thresholds (test: same query routes differently with vs without profile). History has `INTAKE_CALIBRATED` provenance. **Spec-gaming check:** Does the intake actually derive multipliers from answers, or does it just store raw answers without computing downstream effects? Storing without deriving is a stub.

### Phase 5: Hebbian Neuroplasticity + Episodic Reconstruction + Training Data

Create `python/cognitive_twin/hebbian/`:

**5A. Hebbian Learning — "Neurons that fire together wire together" (Hebb, 1949)**

- **Co-activation tracking:** Two traces co-fire in top-K → `co_activations[other_id] += 1`. Pure counting.
- **Competition tracking:** Co-fire with contradicting content (domain match + Composition conflict flags) → `competitions[other_id] += 1`.
- **Bit-level strengthening (Patch 4+7 — Dual Mask Variant Layer):** For co-activated trace pairs above threshold, compute bit flip probabilities: `P(set 0→1) = (α × CognitiveProfile.hebbian_alpha) · (co_activations[j] / max_co_activation)`. Note: base `α` is scaled by the profile multiplier. A BURST attention profile with `hebbian_alpha = 1.5` learns 50% faster during co-activation. **Hebbian deltas are stored as two directional masks in the `[V] Variant` USD layer, NOT as destructive SQLite mutations.** `effective_sdr = (base_sdr | strengthen_mask) & ~weaken_mask`. Strengthening sets bits in `strengthen_mask`; weakening sets bits in `weaken_mask`. This replaces the original XOR formulation which had a toggle flaw: XOR on a bit already set to 1 would flip it to 0 instead of reinforcing it. Set/clear is idempotent and directionally correct. The base is never touched — the masks are opinion layers, and LIVRPS composes them deterministically.
- **Anti-Hebbian weakening:** `P(clear 1→0) = β · (competitions[j] / max_competition)`. Sets bits in `weaken_mask`. If the same bit appears in both masks (contradictory signal), `weaken_mask` wins (bias toward forgetting matches biological synaptic competition).
- **Stability:** Max drift 2% per epoch. Homeostatic plasticity keeps [3%, 5%] activation band.
- **Lazy decay interaction:** `strength = initial · e^(-λt) + Σ(retrieval_boosts) + Σ(hebbian_boosts)`. Hebbian half-life = 2× retrieval half-life.

**5B. Episodic Context Reconstruction**

- When trace strength < `max(apoptosis_threshold + 0.05, /CognitiveProfile/Multipliers/reconstruction_threshold)` (Patch 2 — apoptosis twilight zone clamp, default 0.3 if no profile):
  - Pull top-N Hebbian-linked co-activations.
  - Compose via LIVRPS → reconstructed episode.
  - Mark `reconstructed: true`, `contributing_traces: [ids]`, `provenance: HEBBIAN_DERIVED`.
- Note: a user with `detail_orientation: 0.2` (big picture) has a HIGHER reconstruction threshold (reconstructs more aggressively). A user with `detail_orientation: 0.9` (granular) has a LOWER threshold (only reconstructs when truly degraded).
- The clamp `max(apoptosis_threshold + 0.05, threshold)` ensures the reconstruction threshold is always above the apoptosis threshold by at least 0.05, preventing traces from being deleted before they ever qualify for reconstruction.
- **Reconsolidation boost (Patch 11 — Death Rattle Prevention):** Reconstruction alone is read-only, but if the reconstructed episode is **actually retrieved by the user** (surfaced in a recall response, not just computed internally), apply a standard retrieval boost to all contributing base traces. This mimics biological reconsolidation: recalling a reconstructed memory strengthens its fragments, saving them from apoptosis on the next decay cycle. Without this, reconstructed traces continue decaying and hit apoptosis immediately — a death spiral. **CRITICAL CAVEAT:** The boost fires ONLY on user-facing retrieval, not on internal computation. Otherwise traces bootstrap their own survival without user engagement, violating the lazy decay philosophy.

**5C. Elenchus Training Data Pipeline**

- Every verification → JSONL row to `data/elenchus_training.jsonl`.
- Row schema (Patch 5 — full profile features):
  ```json
  {
    "intent_hash": "sha256...",
    "output_hash": "sha256...",
    "verification_state": "TRUSTED|CONTESTED|REFUTED|PENDING",
    "cycle_count": 2,
    "timestamp": "2026-03-15T12:00:00Z",
    "domain": "physics",
    "confidence_score": 0.87,
    "retrieval_path": "SYSTEM_1|SYSTEM_2",
    "cognitive_profile_hash": "sha256...",
    "cognitive_profile_features": {
      "surprise_threshold": 2.3,
      "reconstruction_threshold": 0.25,
      "hebbian_alpha": 0.015,
      "allostatic_threshold": 0.8,
      "detail_orientation": 0.4
    }
  }
  ```
- `cognitive_profile_hash` captures a deterministic hash of the profile state at verification time.
- `cognitive_profile_features` captures the **actual float multiplier vector** — essential for training a model that can learn per-profile verification patterns, not just per-hash buckets. The hash alone would require the model to memorize arbitrary strings; the features let it learn continuous relationships between cognitive style and verification behavior.
- Rule 11: NO reasoning traces in dataset.
- **O(1) log rotation (Patch 8):** Do NOT implement naive FIFO (rewriting 9,999 lines on every event is O(N) blocking I/O). Instead: append sequentially to `data/elenchus_training.jsonl`. When row count hits `max_rows` (10,000), rotate: rename current file to `elenchus_training.{timestamp}.jsonl`, start a new empty file. Retain at most `max_rotated_files` (default 3) old files. This is O(1) amortized write cost and Rule 33 compliant.

**Phase 5 Gates:**
- Gate 5a (Hebbian Correctness): Co-activation counts increment on co-recall. Bits strengthen proportionally. Competing traces weaken shared bits. Stability holds after 1,000 updates. Sparsity stays in [3%, 5%]. Hebbian boosts integrate with lazy decay (additive, 2× half-life). Idempotent: same event twice doesn't double the shift. Profile-scaled `hebbian_alpha` produces different learning rates for different profiles. **Merkle isolation: Hebbian deltas live in `[V] Variant` layer as dual masks (`strengthen_mask`, `weaken_mask`). `effective_sdr = (base_sdr | strengthen_mask) & ~weaken_mask`. Base SDR in SQLite is untouched. Merkle hash computed over base traces only. Mask conflict resolution: if same bit in both masks, `weaken_mask` wins.**
- Gate 5b (Reconstruction): Degraded trace (strength < reconstruction_threshold with apoptosis clamp) with Hebbian links → richer reconstructed episode. Reconstruction marked `reconstructed: true` with contributing trace IDs. Uses LIVRPS composition. Provenance = `HEBBIAN_DERIVED`. Reconstruction computation is READ-ONLY — original traces not modified during composition. **Reconsolidation boost: when a reconstructed episode is surfaced to the user (user-facing retrieval), contributing base traces receive a standard retrieval boost. Boost does NOT fire on internal-only computation.** Profile-scaled `reconstruction_threshold` produces different reconstruction aggressiveness for different profiles. **Adversarial: degraded trace with zero Hebbian links → return trace as-is, not crash. Adversarial: contributing traces already below apoptosis → reconstruction still works with available fragments, does not crash.**
- Gate 5c (Training Data): Every verification event → valid JSONL row. No reasoning traces (Rule 11). `retrieval_path` correctly reflects SYSTEM_1 vs SYSTEM_2. `cognitive_profile_hash` present and deterministic. **`cognitive_profile_features` present and non-empty when a profile exists; empty dict `{}` when no profile (never null, never missing).** **Log rotation: file rotates at max_rows (10,000) with O(1) amortized cost. No full-file rewrite. Rotated files named with timestamp. Max 3 rotated files retained.**
- Gate 5d (Integration): All prior phase tests pass. Total ≥ 550. Rule 33 preserved. All configurable thresholds read from `/CognitiveProfile/Multipliers/` when available, fall back to hardcoded defaults when not.

---

## 4. Gates Summary

| Gate | Phase | Description |
|------|-------|-------------|
| 1 | Phase 1 | USD schema + LIVRPS + round-trip (float tolerance + hex SDR) + 100% coverage |
| 2a | Phase 2 | Round-trip fidelity (Hypothesis, 1000+ examples) |
| 2b | Phase 2 | Elenchus stage isolation (structural, not filtered) |
| 2c | Phase 2 | Metacognitive routing (Z-score surprise, dual-process, profile-aware, cold-start safe) |
| 3a | Phase 3 | All subsystems through Brainstem |
| 3b | Phase 3 | No bypass of Brainstem |
| 3c | Phase 3 | All existing tests pass |
| 3d | Phase 3 | Structured provenance on all layers |
| 4a | Phase 4 | twin_skills JSON for 4 patterns + incremental observer (cursor-based, ghost-window safe) |
| 4b | Phase 4 | MCP integration (both new tools) |
| 4c | Phase 4 | migrate_v7 bootstraps /Skills |
| 4d | Phase 4 | bridge/ deleted, ≥ 500 tests |
| 4e | Phase 4 | Intake: adaptive, continuous scoring, semantic ceiling, provenance |
| 5a | Phase 5 | Hebbian correctness + dual-mask Merkle isolation (set/clear, not XOR) |
| 5b | Phase 5 | Episodic reconstruction + apoptosis clamp + reconsolidation boost on user retrieval |
| 5c | Phase 5 | Training data + profile features + O(1) log rotation |
| 5d | Phase 5 | Integration: ≥ 550 tests, Rule 33, profile fallbacks |

---

## 5. What Does NOT Change

- `crates/hippocampus/` (Rust hot path)
- 33 inviolable rules
- Lazy decay model (Hebbian boosts integrate additively)
- Socket-activated daemon
- Existing 5 MCP tools (`twin_skills` #6 and `twin_intake` #7 added in Phase 4)
- SQLite as source of truth
- Encoder (BGE + LSH → 2048-bit SDR)

---

## 6. Migration Strategy

- SQLite remains source of truth. `.usda` files are computed views.
- On v7 boot, engine reads SQLite and projects SDR metadata into `[S] Sublayer` in-memory.
- `migrate_v7` bootstraps `/Skills` from legacy timestamps.
- Hebbian co-activation counters start at zero from deployment. Historical co-activation is not retroactively computed — the system begins learning from the moment v7.0 is deployed. This matches biological reality.
- Surprise baseline initializes from first 100 recalls or from `/CognitiveProfile/Multipliers/surprise_threshold` if intake has been run.
- `/CognitiveProfile` starts empty (universal defaults). The Twin works from the first interaction. The intake makes it work BETTER, but is never required.
- Legacy provenance defaults to `SYSTEM_INFERRED`.

---

## 7. Frontier AI (implemented or ready)

- **Hebbian SDR Evolution:** IMPLEMENTED. Computational neuroplasticity. Profile-scaled learning rate. Merkle-safe via dual-mask Variant layer isolation (set/clear, not XOR).
- **Episodic Context Reconstruction:** IMPLEMENTED. Fragment assembly via Hebbian links + LIVRPS. Profile-scaled aggressiveness. Apoptosis clamp prevents reconstruction/deletion race condition. Reconsolidation boost on user-facing retrieval prevents death spiral.
- **Dual-Process Retrieval:** IMPLEMENTED. System 1 → System 2 on surprise. Z-score formulation. Profile-scaled threshold.
- **Structured Provenance:** IMPLEMENTED. Authenticated source tracking with INTAKE_CALIBRATED type.
- **Elenchus Training Data:** IMPLEMENTED. Structured dataset with `cognitive_profile_hash` AND `cognitive_profile_features`. Ready for LoRA.
- **Cognitive Profile Intake:** IMPLEMENTED. Adaptive neuropsych-informed calibration. Continuous scoring. Semantic ceiling detection. Personal baseline replaces universal defaults. Re-callable.
- **Learned Elenchus:** READY. Training data + profile features = personalized verification model.
- **Active DMN Probing:** READY. Surprise metric provides trigger signal.
- **Proactive Nudges:** READY. `twin_skills` + Hebbian data + surprise metric + profile = full input set.

---

## 8. Research Alignment

| Research Concept | Twin v6.0 | Twin v7.0 | Status |
|---|---|---|---|
| SSGM temporal decay | Lazy decay | Same | Already ahead |
| SSGM pre-consolidation validation | Elenchus trace exclusion | Same (blinded) | Already ahead |
| Analog I sovereign refusal | Basal Ganglia gate | Same | Already ahead |
| Titans forgetting gate | Apoptosis | Same (more aggressive) | Already ahead |
| HiMem reconsolidation | LIVRPS composition | Brain-wide LIVRPS | Extended |
| Titans test-time memorization | — | Hebbian SDR evolution | **New** |
| Mnemis entropy gating | — | Surprise metric (Z-score) + dual routing | **New** |
| SSGM provenance | — | Structured Provenance | **New** |
| SSGM fragment reconstruction | — | Episodic reconstruction | **New** |
| LoCoMo-Plus Level-2 memory | — | Skill building | **New** |
| (No equivalent in literature) | — | Cognitive Profile intake | **Original** |

---

## BEGIN

Start as the **Architect** for **Phase 1**. Read the spec above. Read AGENTS.md. Read the existing modules in `python/cognitive_twin/composition/` and `python/cognitive_twin/elenchus/` to understand current patterns. Then produce your design for `usd_lite/` at `.agent-team/designs/phase-1.md`.

After you complete the Phase 1 design, STOP and present it for review.
