# Cognitive Twin v7.0 Rewrite — CLAUDE.md Additions
# Append this to the existing CLAUDE.md in the repo root

---

## v7.0 Rewrite Context

This codebase is undergoing a v6→v7 architectural rewrite informed by the 2026 frontier
research landscape (Titans, Mnemis, SSGM, REMem, HiMem, LoCoMo-Plus) plus neuropsych-
informed cognitive profile calibration. The full specification lives in the kickoff prompt.

### Verification Commands
```bash
# PRIMARY — run after every file change (Basal Ganglia gate)
pytest tests/ -v

# RUST — verify hot path is untouched (run at phase boundaries)
cargo test -p hippocampus

# COVERAGE — Phase 1 gate requires 100% on usd_lite
pytest tests/test_usd_lite/ --cov=python/cognitive_twin/usd_lite --cov-report=term-missing

# SERIALIZATION — Phase 1 hex SDR round-trip and float tolerance
pytest tests/test_usd_lite/test_hex_roundtrip.py -v
pytest tests/test_usd_lite/test_float_eq.py -v

# FUZZ — Phase 2 fidelity proof
pytest tests/test_brainstem/test_fidelity.py -v --hypothesis-seed=0

# ROUTING — Phase 2 metacognitive routing (Z-score surprise, dual-process)
pytest tests/test_brainstem/test_routing.py -v

# INTAKE — Phase 4 cognitive profile (continuous scoring, semantic ceiling)
pytest tests/test_intake/test_adaptive.py -v
pytest tests/test_intake/test_multipliers.py -v
pytest tests/test_intake/test_ceiling.py -v

# SKILLS — Phase 4 incremental observer (ghost window compliance)
pytest tests/test_skills/test_incremental.py -v

# HEBBIAN — Phase 5 (dual masks, stability, Merkle isolation, reconstruction, training data)
pytest tests/test_hebbian/test_dual_masks.py -v
pytest tests/test_hebbian/test_stability.py -v
pytest tests/test_hebbian/test_merkle_isolation.py -v
pytest tests/test_hebbian/test_reconstruction.py -v
pytest tests/test_hebbian/test_training_data.py -v

# FULL REGRESSION — run before any phase transition
pytest tests/ -v && cargo test -p hippocampus
```

### Module Boundaries (v7.0)
```
python/cognitive_twin/usd_lite/      # Phase 1: USD container format (dataclasses, LIVRPS, serialization)
python/cognitive_twin/brainstem/     # Phase 2: Lossless translation + metacognitive routing
python/cognitive_twin/intake/        # Phase 4: Cognitive profile intake system
python/cognitive_twin/skills/        # Phase 4: Competence tracking observer
python/cognitive_twin/hebbian/       # Phase 5: Neuroplasticity + reconstruction + training data
tests/test_usd_lite/                 # Phase 1 tests
tests/test_brainstem/                # Phase 2 tests (fidelity, routing)
tests/test_intake/                   # Phase 4 tests (adaptive, multipliers, ceiling)
tests/test_skills/                   # Phase 4 tests
tests/test_hebbian/                  # Phase 5 tests (stability, merkle isolation, reconstruction, training data)
data/                                # Phase 5: aletheia_training.jsonl output
```

### Frozen Boundaries (v7.0)
```
crates/hippocampus/                  # NEVER TOUCH — Rust hot path
python/cognitive_twin/encoder/       # NEVER TOUCH — SDR encoding pipeline
```

### Coding Conventions
- Dataclasses for all schema types (no raw dicts for USD prims)
- Type hints on all public functions
- Docstring on every function (one sentence minimum)
- Import style: match existing modules (see aletheia/, composition/)
- Error handling: raise typed exceptions, never bare except
- No `sleep()`, no `while True`, no background threads (Rule 33)

### Agent Team Rules
1. **RECON FIRST** — Read the spec. Read existing modules before creating new ones.
2. **VERIFY EVERY MUTATION** — `pytest tests/ -v` after every file change. Existing tests are sacred.
3. **CIRCUIT BREAKER** — 3 failed attempts → surface as blocker. Never silently degrade.
4. **COMPLETE OR BLOCKED** — No stubs, no TODOs. Complete implementations or structured blocker reports.
5. **STAY IN YOUR LANE** — Architect designs, Forge builds, Crucible breaks. No freelancing.
6. **EXPLICIT HANDOFFS** — Designs at `.agent-team/designs/`. Blockers at `.agent-team/blockers/`.
7. **ADVERSARIAL TESTING** — Builder ≠ verifier. Edge cases mandatory. Fix code, never weaken tests.
8. **HUMAN GATE AFTER PHASE 1 DESIGN** — Pause for review before Forge begins Phase 1.
9. **RIGHT-SIZE** — Sequential phases, one at a time. Don't parallelize across phases.
10. **THIS FILE IS LAW** — Everything here is a constraint, not a suggestion.

### Gemini Patch Notes (applied to spec)
These are the 11 patches from two Gemini review passes, already applied to KICKOFF.md and AGENTS.md:

**Gemini Deep Think (Patches 1-6):**
1. **Surprise Z-score** — Ratio replaced with Z-score formulation. Default threshold 2.0.
2. **Apoptosis twilight zone** — Reconstruction threshold clamped above apoptosis by ≥ 0.05.
3. **Continuous scoring** — Intake uses [0.0, 1.0] floats with linear interpolation, not buckets.
4. **Merkle isolation (CRITICAL)** — Hebbian deltas in `[V] Variant` layer, not destructive SQLite mutation.
5. **Training data features** — JSONL includes `cognitive_profile_features` (full float vector), not just hash.
6. **Semantic ceiling** — Disengagement via `user_disengaged: bool`, not answer length. TERSE-safe.

**Gemini Phase 1 Review (Patches 7-11):**
7. **Dual masks (CRITICAL)** — XOR toggle flaw: `base XOR mask` flips already-set bits instead of reinforcing them. Replaced with `(base | strengthen_mask) & ~weaken_mask`. Set/clear is idempotent and directionally correct. Conflict resolution: `weaken_mask` wins.
8. **O(1) log rotation** — FIFO rewrite is O(N) blocking I/O. Replaced with append-only + rotate-at-threshold. O(1) amortized. Max 3 rotated files.
9. **Hex SDR serialization** — 2048-int text arrays (~6KB/trace) replaced with 512-char hex strings. Orders-of-magnitude boot time improvement at scale. Plus `BrainStage.__eq__` with `math.isclose()` for float round-trip tolerance.
10. **Incremental skills observer** — Full trace scan blows ghost window at scale. Cursor-based incremental processing is O(new_traces). Cursor persisted in SQLite.
11. **Reconsolidation boost** — Read-only reconstruction creates a death spiral (traces keep decaying to apoptosis). Fix: retrieval boost to contributing traces on user-facing retrieval. Boost gated to user retrieval only — no self-bootstrapping survival.
