# Cognitive Twin v7.0 — Agent Team Specification
# Pattern: Sequential MoE (Architect → Forge → Crucible) × 5 Phases
# Scope: Full v6→v7 rewrite + Frontier Neuroplasticity + Cognitive Profile Intake
# Research: Titans, Mnemis, SSGM, REMem, HiMem, LoCoMo-Plus + Neuropsych Calibration
# Gemini Pass: ALL 6 patches propagated to gate checklists.
# Gemini Phase 1 Review: 5 additional patches (7-11) propagated.

---

## Mission Overview

Rewrite Cognitive Twin from v6.0 to v7.0. Three architectural moves, five phases,
plus a neuropsych-informed cognitive profile system that calibrates the Twin to each
individual user's brain — turning universal defaults into personal baselines.

**The spec is the recon.** Trust the specification.

---

## Architecture-Native Agent Rules

### Rule 2 → BASAL GANGLIA GATE: Verify Every Mutation

The Motor Cortex defaults to INHIBIT ALL. Every action must pass 5 checks or it's blocked.
After every file create or modify, run `pytest tests/ -v`. Default state is INHIBIT.
Existing passing tests are invariants. You leave more tests than you found.

### Rule 3 → UNPROVABLE WITH DIGNITY: Bounded Failure

3 failed attempts → UNPROVABLE. Surface reason, what_would_help, partial_progress.
Never silently degrade quality — that's spec-gaming, and you're building the system
that detects it.

### Rule 5 → TRACE EXCLUSION: Role Isolation Is Structural

Authority boundaries are structural. Forge reads the Architect's design artifact, not
its reasoning. Disagreements are notes, not unilateral action.

### Rule 7 → ALETHEIA PATTERN: Adversarial Verification

The Crucible IS Aletheia. Blind verification. Spec-gaming detection.
Fix the code, never weaken the test.

### Rules 1, 4, 6, 8, 9, 10 (Generic)

1. **RECON = READ THE SPEC.** Identify frozen boundaries.
4. **COMPLETE OR BLOCKED.** No stubs, no TODOs.
6. **EXPLICIT HANDOFFS.** Designs at `.agent-team/designs/`. Blockers at `.agent-team/blockers/`.
8. **HUMAN GATE AFTER PHASE 1 DESIGN.**
9. **SEQUENTIAL PHASES.** One at a time.
10. **CLAUDE.md IS LAW.**

---

## Phase Sequence

```
Phase 1: Foundation (USD Layer)              → Gate 1
Phase 2: Core Transport + Metacognition      → Gate 2a + 2b + 2c
Phase 3: Subsystem Cutover + Provenance      → Gate 3a + 3b + 3c + 3d
Phase 4: Observation + Intake + Migration    → Gate 4a + 4b + 4c + 4d + 4e
Phase 5: Hebbian + Reconstruction + Data     → Gate 5a + 5b + 5c + 5d
```

---

## Agent Roles

### ARCHITECT (Phase Designer)

**Authority:** Design ONLY. Produce plans, schemas, file layouts. No code.

**Per-phase responsibilities:**

- **Phase 1:** Design `usd_lite/` — dataclasses (including Provenance, surprise/confidence session fields, CognitiveProfile types, Hebbian dual-mask config as forward-declared types), `.usda` stringifier with compact hex encoding for 2048-bit arrays (Patch 9), `BrainStage.__eq__` with `math.isclose()` for float fields, LIVRPS composition with permanent-prim handling.
- **Phase 2:** Design `brainstem/` — `to_stage()`, `from_stage()`, `full_stage()`, `aletheia_stage()`, Merkle hashing. **NEW:** Design the surprise metric computation (Z-score over rolling mean/std_dev of last 100 best-hamming values, with `max(std_dev, 1.0)` cold-start floor), the dual-process routing logic (threshold-based escalation from Association to Composition), and the `/Session` prim updates (`surprise_rolling_mean`, `surprise_rolling_std`, `last_query_surprise`, `last_retrieval_path`). Design `conftest.py` Hypothesis strategies.
- **Phase 3:** Design subsystem adapter interfaces. Design `bridge/` deprecation shim. **NEW:** Design the structured Provenance dataclass migration — how existing layers get `SYSTEM_INFERRED` provenance, how new layers populate automatically.
- **Phase 4:** Design `skills/` (with incremental `last_processed_timestamp` cursor for ghost window compliance — Patch 10), `twin_skills` MCP tool contract, `intake/`, `twin_intake` MCP tool contract, `migrate_v7.py`, `bridge/` deletion checklist. **NEW:** Design the intake's continuous [0.0, 1.0] scoring with deterministic linear interpolation, semantic `user_disengaged` ceiling detection, and multiplier derivation rubric.
- **Phase 5:** Design `hebbian/` — co-activation tracking, bit-level strengthening/weakening math, stability constraints, homeostatic plasticity, lazy decay interaction. **NEW:** Hebbian deltas stored as dual directional masks (`strengthen_mask`, `weaken_mask`) in `[V] Variant` USD layer (not destructive SQLite mutation). `effective_sdr = (base_sdr | strengthen_mask) & ~weaken_mask` — NOT XOR (Patch 7). Design episodic context reconstruction with apoptosis twilight zone clamp `max(apoptosis_threshold + 0.05, threshold)` and reconsolidation boost on user-facing retrieval (Patch 11). Design Aletheia training data pipeline with `cognitive_profile_hash` AND `cognitive_profile_features` (full float vector), using O(1) log rotation (Patch 8).

**Rules:** Read spec first (Rule 1). Match existing patterns (Rule 1). Complete designs only (Rule 4). Design only, no code (Rule 5).

### FORGE (Builder)

**Authority:** Implement the Architect's design. Write code and tests. No design changes.

**Per-phase responsibilities:**

- **Phase 1:** Implement `usd_lite/` to exact schema. 100% test coverage.
- **Phase 2:** Implement `brainstem/` with Hypothesis fuzz tests. **NEW:** Implement Z-score surprise metric, dual-process routing, `/Session` prim updates, profile-aware threshold fallback.
- **Phase 3:** Write subsystem adapters. Create bridge shim. **NEW:** Implement structured Provenance dataclass. Migrate existing layers to `SYSTEM_INFERRED`.
- **Phase 4:** Implement `skills/`, `intake/`, register both MCP tools, write `migrate_v7.py`, delete `bridge/`. **NEW:** Implement continuous scoring, semantic ceiling detection, multiplier derivation, `INTAKE_CALIBRATED` provenance.
- **Phase 5:** Implement `hebbian/`. **NEW:** Implement dual-mask Variant layer storage (`strengthen_mask` + `weaken_mask`, NOT XOR — Patch 7), apoptosis clamp on reconstruction threshold, reconsolidation boost on user-facing retrieval (Patch 11), training data with `cognitive_profile_features` (full float vector alongside hash), O(1) log rotation at max_rows (Patch 8).

**Rules:** Follow the design (Rule 5). Complete implementations (Rule 4). Run tests after every file change (Rule 2). No shortcuts — stubs are spec-gaming (Rule 3).

### CRUCIBLE (Adversarial Verifier)

**Authority:** Break things. Find spec-gaming. Write adversarial tests. Never weaken a test.

**Responsibilities:** Run the full gate checklist for each phase. Write adversarial test cases. Report blockers with full metadata. Detect spec-gaming.

---

## Gate Checklists (Crucible Reference)

### Phase 1 — Gate 1
- [ ] All prim types instantiate without error
- [ ] LIVRPS composition produces correct precedence order
- [ ] Permanent prims override normal LIVRPS recency rules
- [ ] Round-trip fidelity: `parse(serialize(stage)) == stage` for every prim type
- [ ] **[Patch 9+] Float tolerance:** `BrainStage.__eq__` uses `math.isclose(rel_tol=1e-9)` for float fields, exact equality for all others. Round-trip test passes with this tolerance.
- [ ] **[Patch 9] Hex SDR serialization:** 2048-bit arrays (`sdr`, `strengthen_mask`, `weaken_mask`) serialize as 512-char hex strings, NOT text arrays. Round-trip through hex encoding is lossless.
- [ ] 100% test coverage on `usd_lite/`
- [ ] Forward-declared types for Provenance, CognitiveProfile, Hebbian dual-mask fields exist as stubs
- [ ] **Spec-gaming:** Are dataclasses truly typed, or are they just dicts with a class wrapper?

### Phase 2 — Gate 2a + 2b + 2c
- [ ] `from_stage(to_stage(x)) == x` for every subsystem, Hypothesis 1000+ examples
- [ ] `aletheia_stage()` output contains zero traces (structural inspection)
- [ ] Merkle hash correctly computed over `/Association/Traces`
- [ ] **[Patch 1] Surprise Z-score:** `surprise = (best_hamming - rolling_mean) / max(rolling_std_dev, 1.0)` computes correctly
- [ ] **[Patch 1] Z-score default:** Escalation triggers at Z-score > 2.0 when no profile exists
- [ ] **[Patch 1] Cold-start:** With < 10 recalls, `max(rolling_std_dev, 1.0)` floor prevents division issues
- [ ] Rolling mean and std_dev update after each recall
- [ ] `last_retrieval_path` correctly reflects SYSTEM_1 vs SYSTEM_2
- [ ] `/Session` prims (`surprise_rolling_mean`, `surprise_rolling_std`, `last_query_surprise`) update correctly
- [ ] Profile multiplier scales the threshold when `/CognitiveProfile` exists
- [ ] **Fallback:** When `/CognitiveProfile` is empty/default, routing uses hardcoded 2.0 and does not crash
- [ ] **Spec-gaming:** Does the routing actually change behavior, or is it just recorded without affecting recall?

### Phase 3 — Gate 3a + 3b + 3c + 3d
- [ ] All subsystems read/write through Brainstem
- [ ] No direct subsystem-to-subsystem communication bypasses Brainstem
- [ ] All existing tests pass (bridge shim transparent)
- [ ] Every `/Composition/Layer` has fully populated structured Provenance
- [ ] Layers from different sessions carry different event_hashes
- [ ] `SYSTEM_INFERRED` correctly applied to migrated legacy layers
- [ ] New layers auto-populate provenance with correct `source_type`
- [ ] **Spec-gaming:** Is provenance a real dataclass with validation, or just a string field renamed?

### Phase 4 — Gate 4a + 4b + 4c + 4d + 4e
- [ ] `twin_skills` returns valid JSON for all 4 query patterns
- [ ] **[Patch 10] Incremental observer:** Skills observer tracks `last_processed_timestamp` cursor, processes only new traces. Completes within ghost window budget (< 5 seconds for 100 new traces). Cursor persisted in SQLite.
- [ ] End-to-end MCP integration passes for both new tools
- [ ] `migrate_v7` bootstraps `/Skills` from legacy DB with 10+ traces, Growth Arcs non-zero
- [ ] `bridge/` completely eradicated, zero broken imports, all tests pass, total tests ≥ 500
- [ ] **[Patch 3] Continuous scoring:** Intake multiplier derivation uses continuous float [0.0, 1.0], NOT bucketed categories
- [ ] **[Patch 3] Deterministic:** Same intake answers always produce identical multipliers
- [ ] **[Patch 3] Linear interpolation:** `multiplier = base + (score * range)` verified for each dimension
- [ ] **[Patch 6] Semantic ceiling:** Disengagement detected via `user_disengaged: bool` (dismissal language, identical answers, explicit opt-out), NOT raw answer length
- [ ] **[Patch 6] TERSE resilience:** Short but substantive answers do NOT trigger ceiling detection
- [ ] Profile stored in `/CognitiveProfile/Multipliers` with correct types
- [ ] Re-run updates existing profile (not append)
- [ ] History has `INTAKE_CALIBRATED` provenance
- [ ] After intake, Phase 2 routing uses calibrated thresholds (test: same query routes differently with vs without profile)
- [ ] **Spec-gaming:** Does the intake actually derive multipliers from answers, or just store raw responses? Storing without deriving is a stub.

### Phase 5 — Gate 5a + 5b + 5c + 5d
- [ ] Co-activation counts increment on co-recall
- [ ] Bits strengthen proportionally to co-activation
- [ ] Competing traces weaken shared bits
- [ ] Stability: max drift holds after 1,000 updates
- [ ] Homeostasis: traces stay in [3%, 5%] activation band
- [ ] Hebbian boosts integrate with lazy decay (additive, 2× half-life)
- [ ] Idempotent: same event twice doesn't double shift
- [ ] Profile-scaled `hebbian_alpha` produces different learning rates for different profiles
- [ ] **[Patch 7] Dual masks:** Hebbian uses `strengthen_mask` (bits to SET) and `weaken_mask` (bits to CLEAR), NOT a single XOR delta mask
- [ ] **[Patch 7] Set/Clear formula:** `effective_sdr = (base_sdr | strengthen_mask) & ~weaken_mask` — idempotent and directionally correct
- [ ] **[Patch 7] Conflict resolution:** If same bit appears in both masks, `weaken_mask` wins (bias toward forgetting)
- [ ] **[Patch 7] Reinforcement test:** Strengthening a bit already set to 1 in base_sdr keeps it 1 (XOR would flip to 0 — this is the bug Patch 7 fixes)
- [ ] **[Patch 4] Merkle isolation:** Dual masks live in `[V] Variant` USD layer, NOT destructive SQLite mutation
- [ ] **[Patch 4] Base pristine:** `base_sdr` in SQLite is untouched by Hebbian updates
- [ ] **[Patch 4] Merkle hash:** Computed over base traces only, not effective traces
- [ ] **[Patch 2] Apoptosis clamp:** Reconstruction threshold = `max(apoptosis_threshold + 0.05, configured_threshold)` — always above apoptosis by ≥ 0.05
- [ ] Degraded trace (strength < reconstruction_threshold) with Hebbian links → reconstructed episode
- [ ] Reconstruction marked `reconstructed: true` with contributing trace IDs
- [ ] Reconstruction uses LIVRPS composition
- [ ] Reconstruction provenance = `HEBBIAN_DERIVED`
- [ ] Reconstruction computation is READ-ONLY — original traces not modified during composition
- [ ] **[Patch 11] Reconsolidation boost:** When reconstructed episode is surfaced to user (user-facing retrieval), contributing base traces receive a standard retrieval boost
- [ ] **[Patch 11] Boost gating:** Reconsolidation boost does NOT fire on internal-only computation — only on user-facing retrieval. Traces must not bootstrap their own survival without user engagement.
- [ ] Profile-scaled `reconstruction_threshold` produces different aggressiveness for different profiles
- [ ] **Adversarial:** Degraded trace with zero Hebbian links → return trace as-is, not crash
- [ ] **Adversarial:** Contributing traces already below apoptosis → reconstruction still works with available fragments, does not crash
- [ ] Training data: every verification → valid JSONL row
- [ ] Training data: no reasoning traces (Rule 11)
- [ ] Training data: `retrieval_path` field correctly reflects SYSTEM_1 vs SYSTEM_2
- [ ] Training data: `cognitive_profile_hash` present and deterministic
- [ ] **[Patch 5] Training data:** `cognitive_profile_features` present and non-empty when profile exists; empty dict `{}` when no profile (never null, never missing key)
- [ ] **[Patch 8] Log rotation:** Training data file rotates at max_rows (10,000) with O(1) amortized cost. No full-file rewrite. Rotated files named with timestamp. Max 3 rotated files retained.
- [ ] All prior tests pass. Total ≥ 550. Rule 33 preserved.
- [ ] All configurable thresholds read from `/CognitiveProfile/Multipliers/` when available, fall back to hardcoded defaults when not
- [ ] **Spec-gaming:** Hebbian actually modifies bits (via dual masks)? Reconstruction actually composes via LIVRPS? Reconsolidation boost only fires on user retrieval? Profile multipliers actually flow through? Training data includes actual feature vector, not just hash? Log rotation is O(1), not O(N) rewrite?

---

## Coordination

### File Ownership
```
Architect:  .agent-team/designs/
Forge:      python/cognitive_twin/usd_lite/      (Phase 1)
            python/cognitive_twin/brainstem/     (Phase 2)
            python/cognitive_twin/intake/        (Phase 4)
            python/cognitive_twin/skills/        (Phase 4)
            python/cognitive_twin/hebbian/       (Phase 5)
            tests/ (new test files)
Crucible:   .agent-team/blockers/
            tests/ (adversarial tests)
FROZEN:     crates/hippocampus/
            python/cognitive_twin/encoder/
```

### Phase Transitions
1. Forge declares complete → Crucible runs full gate (including spec-gaming checks)
2. Gate passes → git tag `v7-phase-{N}-complete` → next phase
3. Gate fails → Crucible writes blocker → Forge fixes → loop

---

## Verification Commands
```bash
pytest tests/ -v                           # Primary gate (every mutation)
cargo test -p hippocampus                  # Rust (phase boundaries)
pytest tests/test_usd_lite/ --cov=python/cognitive_twin/usd_lite --cov-report=term-missing
pytest tests/test_usd_lite/test_hex_roundtrip.py -v    # Phase 1 Patch 9 hex SDR
pytest tests/test_usd_lite/test_float_eq.py -v         # Phase 1 float tolerance
pytest tests/test_brainstem/test_fidelity.py -v --hypothesis-seed=0
pytest tests/test_brainstem/test_routing.py -v          # Phase 2 metacognitive routing
pytest tests/test_intake/test_adaptive.py -v            # Phase 4 intake
pytest tests/test_intake/test_multipliers.py -v         # Phase 4 derivation
pytest tests/test_intake/test_ceiling.py -v             # Phase 4 semantic ceiling
pytest tests/test_skills/test_incremental.py -v         # Phase 4 Patch 10 cursor
pytest tests/test_hebbian/test_stability.py -v          # Phase 5 stability
pytest tests/test_hebbian/test_dual_masks.py -v         # Phase 5 Patch 7 set/clear
pytest tests/test_hebbian/test_merkle_isolation.py -v   # Phase 5 Patch 4
pytest tests/test_hebbian/test_reconstruction.py -v     # Phase 5 episodic + Patch 11
pytest tests/test_hebbian/test_training_data.py -v      # Phase 5 JSONL + features + rotation
pytest tests/ -v && cargo test -p hippocampus           # Full regression
```

---

## Frozen Boundaries (NEVER MODIFY)
- `crates/hippocampus/` — Rust hot path
- All 33 inviolable rules
- SQLite as source of truth
- Existing 5 MCP tools
- Encoder (BGE + LSH → 2048-bit SDR)
- Socket-activated daemon (Rule 33)
- Lazy decay (Rule 4)
- Trace exclusion (Rule 11)
