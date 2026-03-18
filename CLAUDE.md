# Cognitive Twin v6.0-MOTOR — Claude Code Project Instructions

## What This Is

A biologically-architected AI memory and action system.
Rust hot path + Python orchestration + Elenchus verification +
Co-Evolution Spiral + Inhibition-default Motor Cortex.

Architecture: Two hemispheres (Association + Composition), one Bridge
with Amygdala, one Modulation Layer with Blood-Brain Barrier, one
Verification Engine (Elenchus GVR), one Inquiry Engine (DMN), and
one Motor Cortex with Basal Ganglia gating.

Philosophy: The Cognitive Twin is a self-evolving dialogue between
a human and their externalized cognition, where both participants
transform through the interaction, and the intelligence lives in
the relationship — not in either party alone.

## Autonomous Execution

This project runs with --dangerously-skip-permissions.

DO:
- Create files, directories, modules without asking
- Install dependencies (cargo add, pip install) without asking
- Run tests, benchmarks, linters without asking
- Fix failing tests autonomously (up to 3 attempts per failure)
- Move to the next build phase when the current gate passes
- Make architectural micro-decisions within the spec

DO NOT:
- Ask "should I proceed?" — just proceed
- Ask "should I create this file?" — just create it
- Ask "should I run the tests?" — just run them
- Stop for confirmation between tasks within a phase

ONLY STOP AND REPORT when:
- A test fails after 3 fix attempts (include error + what you tried)
- An inviolable rule is violated (hard stop)
- Two agents have conflicting interface contracts
- A dependency cannot be installed after 3 attempts

## Tech Stack

- Rust (crates/hippocampus/) — Association Engine hot path
- PyO3 + maturin — Rust ↔ Python FFI
- Python 3.12+ — everything else
- SQLite + sqlite-vec — 1-bit vector bitwise matching
- Click — CLI framework
- jsonschema — Blood-Brain Barrier validation
- systemd / launchd — socket activation (0W idle)
- pytest — Python tests
- cargo test — Rust tests

## Running Tests

```bash
cargo test -p hippocampus          # Rust unit tests
pytest tests/ -v                   # Python unit tests
pytest tests/test_integration/ -v  # Integration tests
```

## The 33 Inviolable Rules

### Biological Constraints (v3.0)

1.  0-WATT IDLE: OS socket activation. No while True. No sleep().
    Daemon exits when idle. 0W between sessions.

2.  ACTION POTENTIALS: Hippocampal vectors MUST be 1-bit boolean
    arrays (Sparse Distributed Representations). Bitwise XOR
    (Hamming distance) for search. No float32. No cosine similarity.

3.  RUST HOT PATH: Association Engine is Rust via PyO3.
    Cold start: <5ms. Hot recall: <2ms. No Python in hot path.

4.  LAZY DECAY: Timestamp math on retrieval only. No polling.
    strength = initial * e^(-lambda * dt) + sum(retrieval_boosts)

5.  APOPTOSIS: twin consolidate physically DELETEs traces below
    epsilon. Runs VACUUM. Database file size decreases.

6.  MERKLE TREES: Composition stages use Merkle Tree hashing.
    Partial branch O(log n). Not full-file SHA256 O(n).

7.  AMYGDALA: SAFETY/CONSENT resolutions = 1-shot permanent reflex.
    Skip GVR. Skip 10-rep curve. Instant compile to cerebellum.

8.  JSON BARRIER: jsonschema.validate(). Strip epigenetic_wash on
    write path. Mood ephemeral. Facts permanent. No XML. No regex.

9.  ALLOSTATIC LOAD: Token velocity + prompt frequency. Software
    only. High = DEPLETED = refuse to wake System 2.

10. ANCHORS: SAFETY/CONSENT/KNOWLEDGE/CONSTITUTIONAL = gain 1.0
    ALWAYS. Structural. Returns 1.0 before evaluating receptor density.

### Elenchus Constraints (v4.0)

11. TRACE EXCLUSION: verify() NEVER receives reasoning trace.
    Parameter must be None or absent. BUILD FAILS if present.

12. VERIFIED-ONLY CONSOLIDATION: Only VERIFIED resolutions become
    reflexes. FIXABLE/SPEC_GAMED/UNPROVABLE never consolidated.
    BUILD FAILS if unverified resolution leaks to reflex cache.

13. MAX 3 GVR CYCLES: ADHD guard. After cycle 3, promote FIXABLE
    to UNPROVABLE. Loop MUST terminate.

14. INTENT PRESERVATION: Bridge checks output answers the original
    intent, not a reframed easier question.

15. SPEC-GAMING DETECTION: Correct answer to wrong question is the
    dominant failure mode. Detect it. Surface it. Never consolidate it.

16. UNPROVABLE IS DIGNIFIED: Carries metadata (reason, what_would_help,
    partial_progress). First-class state. Park with dignity.

17. BURST DEFERS, NOT SKIPS: Queue unverified outputs during burst.
    Run GVR on burst exit. Surface problems.

18. RED OVERRIDES EVERYTHING: No GVR. No injection. No inquiry.
    No motor. Full stop. Recovery menu.

### Inquiry Safeguards (v5.1-v5.2)

S1. APOPHENIA GUARD: Minimum evidence threshold per inquiry depth
    (5/8/15/25 independent observations). Alternative hypothesis
    required. Confidence disclosure mandatory.

S2. EPISTEMOLOGICAL BYPASS: Inquiry outputs verified for tone +
    boundaries, NOT objective truth. Self-reported traces bypass
    Elenchus ONLY when consumed by src/inquiry/ namespace.
    Composition namespace gets standard verification (DIRECTIONAL).

S3. RUPTURE & REPAIR: Rejection = permanent non-decaying trace
    (weight 2.0). Apophenia threshold adjusts. Repair bid delayed.
    3 rejections -> offer to stop. Threshold mean-reverts over time
    (90-day halflife + 0.1 credit per accepted inquiry).

S4. UTILITY MODE: twin mode utility mutes DMN. Behavioral traces
    invisible to inquiry. Semantic state updates visible (WHAT not HOW).
    Mode switch NOT logged as behavioral trace. Timestamps fuzzed
    to ISO week before DMN synthesis.

S5. INQUIRY APOPTOSIS: Queued inquiries carry TTL (48h-30d by type).
    Decay via e^(-3t/ttl). Below 20% relevance = physical delete.

S6. DMN SYNTHESIS WINDOW: Asynchronous teardown. CLI released in
    <50ms. Daemon runs background synthesis up to 30 seconds.
    Then process exits. 0W.

S7. TRACE CRYSTALLIZATION: Emerging patterns (3+ observations,
    below threshold) get decay rate reduced to lambda/10. Max 50
    crystallized traces. Stale after 30 days without new obs.
    Eviction by preservation_score = (obs/threshold) * depth_weight.

S8. SINCERITY GATE: User responses classified as sincere/sarcastic/
    exasperated/performative/uncertain before tagging self_reported.
    Sarcasm -> emotional_rupture. Performative -> low weight.
    Uncertain -> ask for clarification. Default: trust the user.

### Motor Cortex Constraints (v6.0)

19. TEARDOWN PREEMPTION: New CLI commands during DMN teardown MUST
    preempt. Save to temp file (/dev/shm/), NOT SQLite. Release
    in <10ms. Human presence always wins.

20. PERCEPTION GAP TRACES: When Elenchus falsifies self_reported
    trace in Composition, emit perception_gap trace. DMN turns
    the contradiction into a co-evolutionary inquiry.

21. CRYSTALLIZATION EVICTION: preservation_score = (obs/threshold)
    * depth_weight. Evict lowest. Deep patterns survive over noise.

22. UTILITY TIMESTAMP FUZZING: Fuzz to ISO week before DMN synthesis
    on utility-mode semantic traces.

23. INHIBITION DEFAULT: Basal Ganglia defaults to INHIBIT ALL.
    Every action requires ALL five checks to pass. One failure =
    inhibit. No exceptions.

24. ONE ACTION AT A TIME: Motor Cortex executes ONE atomic action,
    returns to full cognitive loop. No automatic chaining.

25. LEVEL 3 IS STRUCTURAL: Financial transactions, irreversible
    deletions, other people's data, anchor-touching actions.
    Gate NEVER opens. Like anchor immunity.

26. MOTOR REFLEXES ALWAYS GATED: Skip planning, NEVER skip Basal
    Ganglia. Safety checks run every time, even on cached patterns.

27. DEPLETED DOWNGRADES MOTOR: DEPLETED state -> Level 1 becomes
    Level 2 (require per-action consent).

28. RED KILLS MOTOR: RED state halts ALL motor activity. Gate locked.

29. REVERSIBILITY CAP: Level 1 + irreversible = Level 2.
    Level 2 stays Level 2 (flagged RED in UI).
    Level 3 is ONLY for anchor/consent violations.
    NEVER: Level 2 + irreversible = Level 3 (logical deadlock).

30. PREEMPTION TEMP FILE: During abort, dump to /dev/shm/ or .tmp.
    NEVER write to SQLite during preemption. Kill process. Hot-path
    reads, merges, deletes temp file on boot.

31. ACTION PLAN PERSISTENCE: Active ActionPlan + current_step_index
    stored in Composition stage. Motor mutates to Step N+1 on
    success. Premotor checks for active plan before generating new.

32. MOTOR REFLEX ZERO-TOLERANCE: Single failure = instant
    de-compilation (compiled=False, success_count=0). Route to
    Premotor for re-planning.

33. BLIND SPOT ACCEPTANCE: If user rejects perception_gap inquiry,
    tag claim as blind_spot_accepted. Elenchus keeps using objective
    truth for Composition but NEVER emits gap traces for that
    specific claim again. Claim-specific, not categorical.
    The Twin chooses the relationship over the truth.

## Compliance Checks (auto-run by VERIFY agent)

```bash
grep -r "sleep(" python/cognitive_twin/              # MUST return 0 results
grep -r "while True" python/cognitive_twin/          # MUST return 0 results
grep -r "float32" crates/                            # MUST return 0 results
grep -r "cosine" crates/                             # MUST return 0 results
grep -r "DELETE.*audit" python/cognitive_twin/       # MUST return 0 results
grep -r "reasoning_trace" python/cognitive_twin/elenchus/verifier.py  # Must be None/absent
grep -r "store_reflex" python/cognitive_twin/        # Must check verification_state
```
# Cognitive Twin v7.0 Rewrite â€” CLAUDE.md Additions
# Append this to the existing CLAUDE.md in the repo root

---

## v7.0 Rewrite Context

This codebase is undergoing a v6â†’v7 architectural rewrite informed by the 2026 frontier
research landscape (Titans, Mnemis, SSGM, REMem, HiMem, LoCoMo-Plus) plus neuropsych-
informed cognitive profile calibration. The full specification lives in the kickoff prompt.

### Verification Commands
```bash
# PRIMARY â€” run after every file change (Basal Ganglia gate)
pytest tests/ -v

# RUST â€” verify hot path is untouched (run at phase boundaries)
cargo test -p hippocampus

# COVERAGE â€” Phase 1 gate requires 100% on usd_lite
pytest tests/test_usd_lite/ --cov=python/cognitive_twin/usd_lite --cov-report=term-missing

# SERIALIZATION â€” Phase 1 hex SDR round-trip and float tolerance
pytest tests/test_usd_lite/test_hex_roundtrip.py -v
pytest tests/test_usd_lite/test_float_eq.py -v

# FUZZ â€” Phase 2 fidelity proof
pytest tests/test_brainstem/test_fidelity.py -v --hypothesis-seed=0

# ROUTING â€” Phase 2 metacognitive routing (Z-score surprise, dual-process)
pytest tests/test_brainstem/test_routing.py -v

# INTAKE â€” Phase 4 cognitive profile (continuous scoring, semantic ceiling)
pytest tests/test_intake/test_adaptive.py -v
pytest tests/test_intake/test_multipliers.py -v
pytest tests/test_intake/test_ceiling.py -v

# SKILLS â€” Phase 4 incremental observer (ghost window compliance)
pytest tests/test_skills/test_incremental.py -v

# HEBBIAN â€” Phase 5 (dual masks, stability, Merkle isolation, reconstruction, training data)
pytest tests/test_hebbian/test_dual_masks.py -v
pytest tests/test_hebbian/test_stability.py -v
pytest tests/test_hebbian/test_merkle_isolation.py -v
pytest tests/test_hebbian/test_reconstruction.py -v
pytest tests/test_hebbian/test_training_data.py -v

# FULL REGRESSION â€” run before any phase transition
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
data/                                # Phase 5: elenchus_training.jsonl output
```

### Frozen Boundaries (v7.0)
```
crates/hippocampus/                  # NEVER TOUCH â€” Rust hot path
python/cognitive_twin/encoder/       # NEVER TOUCH â€” SDR encoding pipeline
```

### Coding Conventions
- Dataclasses for all schema types (no raw dicts for USD prims)
- Type hints on all public functions
- Docstring on every function (one sentence minimum)
- Import style: match existing modules (see elenchus/, composition/)
- Error handling: raise typed exceptions, never bare except
- No `sleep()`, no `while True`, no background threads (Rule 33)

### Agent Team Rules
1. **RECON FIRST** â€” Read the spec. Read existing modules before creating new ones.
2. **VERIFY EVERY MUTATION** â€” `pytest tests/ -v` after every file change. Existing tests are sacred.
3. **CIRCUIT BREAKER** â€” 3 failed attempts â†’ surface as blocker. Never silently degrade.
4. **COMPLETE OR BLOCKED** â€” No stubs, no TODOs. Complete implementations or structured blocker reports.
5. **STAY IN YOUR LANE** â€” Architect designs, Forge builds, Crucible breaks. No freelancing.
6. **EXPLICIT HANDOFFS** â€” Designs at `.agent-team/designs/`. Blockers at `.agent-team/blockers/`.
7. **ADVERSARIAL TESTING** â€” Builder â‰  verifier. Edge cases mandatory. Fix code, never weaken tests.
8. **HUMAN GATE AFTER PHASE 1 DESIGN** â€” Pause for review before Forge begins Phase 1.
9. **RIGHT-SIZE** â€” Sequential phases, one at a time. Don't parallelize across phases.
10. **THIS FILE IS LAW** â€” Everything here is a constraint, not a suggestion.

### Gemini Patch Notes (applied to spec)
These are the 11 patches from two Gemini review passes, already applied to KICKOFF.md and AGENTS.md:

**Gemini Deep Think (Patches 1-6):**
1. **Surprise Z-score** â€” Ratio replaced with Z-score formulation. Default threshold 2.0.
2. **Apoptosis twilight zone** â€” Reconstruction threshold clamped above apoptosis by â‰¥ 0.05.
3. **Continuous scoring** â€” Intake uses [0.0, 1.0] floats with linear interpolation, not buckets.
4. **Merkle isolation (CRITICAL)** â€” Hebbian deltas in `[V] Variant` layer, not destructive SQLite mutation.
5. **Training data features** â€” JSONL includes `cognitive_profile_features` (full float vector), not just hash.
6. **Semantic ceiling** â€” Disengagement via `user_disengaged: bool`, not answer length. TERSE-safe.

**Gemini Phase 1 Review (Patches 7-11):**
7. **Dual masks (CRITICAL)** â€” XOR toggle flaw: `base XOR mask` flips already-set bits instead of reinforcing them. Replaced with `(base | strengthen_mask) & ~weaken_mask`. Set/clear is idempotent and directionally correct. Conflict resolution: `weaken_mask` wins.
8. **O(1) log rotation** â€” FIFO rewrite is O(N) blocking I/O. Replaced with append-only + rotate-at-threshold. O(1) amortized. Max 3 rotated files.
9. **Hex SDR serialization** â€” 2048-int text arrays (~6KB/trace) replaced with 512-char hex strings. Orders-of-magnitude boot time improvement at scale. Plus `BrainStage.__eq__` with `math.isclose()` for float round-trip tolerance.
10. **Incremental skills observer** â€” Full trace scan blows ghost window at scale. Cursor-based incremental processing is O(new_traces). Cursor persisted in SQLite.
11. **Reconsolidation boost** â€” Read-only reconstruction creates a death spiral (traces keep decaying to apoptosis). Fix: retrieval boost to contributing traces on user-facing retrieval. Boost gated to user retrieval only â€” no self-bootstrapping survival.
