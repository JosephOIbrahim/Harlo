# LOG — append-only. Read before proposing. Dead ends are memory.

## Cycle 0 — FRAME / SKETCH
Contract written (SPEC.md). Seed champion = v2 doc. Mode: SOLO (one
dependency chain, no independent lines). Confidence at seed:
P1 .7 / P2 .6 / P3 .8 / P4 .5 / P5 .9.

## Cycle 1 — live MCP surface verification (Claude.ai session)
Verifier: tool-schema inspection + one status call. Closed the v2 appendix
unknown (signatures). Champion updates:
- Δ1 RESET LEVER: stage_reload reloads .usda only → reset = daemon stop →
  restore → daemon start with per-cell env. SQLite WAL/SHM must be in snapshot.
- Δ2 resolve_verifications is adjudication (verdicts per claim_id), not a flush.
- Δ3 recall drives v9 engine (exchange_index advances); QPE docstring does not
  → QPE preferred probe tool. No claim-submission MCP tool → Elenchus
  secondary scoring moves post-cells.
- Δ4 schedule.kind is a step-function confound for warm-full (FAMILY→restorer
  observed live). Cells must share one schedule block or pin /schedule/.
Free verifier: status exposes predictor flag + observations_logged →
per-cell config proof + write-leak detection.

## Cycle 2 — repo recon (Claude Code, read-only)
All six questions answered with file:line citations. Champion updates:
- Δ5 QPE is a PURE READ (no boosts, no Hebbian, no timestamp writes; decay is
  read-side math). Living-store problem half-dissolves for warm-mem.
  Note: unchanged strengths across probes are expected, not anomalies.
- Δ6 UTILITY MODE IS A STUB (router echoes ok, engine never touched; Rule 22
  fuzzing unimplemented). Dropped from design — daemon-lifecycle protocol
  routed around it. Filed as Harlo worklist candidate (privacy-adjacent).
- Δ7 Elenchus flush demoted gate → hygiene (restore makes pending state a
  constant across cells). >5 pending requires direct SQL (no enumeration tool).
- Δ8 Schedule pin mechanism verified: experiment sublayer at position 0
  (strongest); migrate_inline tolerates it; root-layer overs are stripped
  (don't use); MANDATORY teardown — position-0 layer persists silently.
Traps logged: env parse is literal == "1" ("true" silently disables) ·
launchd socket activation respawns daemon mid-restore (unload for window) ·
Claude Desktop MCP server also holds connections (disconnect during window).

## Cycle 3 — BUILD: experiments/memory-uplift/ (Claude Code)
14 files landed, engine code untouched, inert composers untouched.
Commits c3971f2..59d4596. Verifier ladder caught 3 bugs PRE-commit:
1. restore.sh relative-path hash verify after cd → absolutized early.
2. probe_lint.py mode=ro fails on cleanly-closed WAL db (SQLite err 14 — the
   shape of every clean snapshot) → temp-copy-and-checkpoint open, replays
   captured -wal without mutating the snapshot.
3. probe_lint.py crashed on lazily-created elenchus_pending absent → guarded.
P1 ACCEPTANCE PASSED on real data (282 sessions, integrity ok, no corruption).
Substitution logged honestly: shellcheck unavailable arm64 → bash -n (clean ×3).
Launchd pulse unit unloaded for test, re-armed and confirmed.

## Cycle 4 — INVENTORY / KILL (Claude Code, read-only vs snapshot)
Snapshot 20260610-181809 (daemon down, pulse unloaded for capture, re-armed).
inventory.py (temp-copy-checkpoint open, never live). Result: **KILL CONDITION
FIRED — VERIFIED probe pool = 0 < 12.**
- Store at snapshot: hot_traces=16, warm traces=0, reflexes=0, elenchus_pending
  table ABSENT, patterns=0, graph_edges=0. observations.db=1437 behavioral
  records (not memory traces, no verification).
- The 16 hot traces are all tagged `wave1-trial` ("wave1 trial probe entity")
  — synthetic USD-proof-harness placeholders, NOT organic verified memory.
- Tier criterion used: table residency (hot_traces=Hot, traces=Warm). Neither
  carries a verification column → a trace is probe-eligible only when its id is
  in source_traces of a VERIFIED elenchus_pending claim (or is a verified
  reflex). Zero of either exist → pool 0 by construction.
- ADVERSARIAL VERIFY (3 independent lenses, Workflow wf_c6820ec7-995):
  schema-exhaustion / architecture-intent / raw-SQL all returned
  max_verified_probeable=0, can_reach_floor_12=false. KILL robust, not a
  definitional artifact.
- Δ9 OBSERVATION (root cause, out-of-scope per SPEC): decay is wall-clock
  SECONDS with λ=0.05 (query.rs now=as_secs, created_at=Unix s). Any warm
  trace older than ~92 s falls below epsilon=0.01 and is apoptosis-eligible →
  the warm tier cannot accumulate. Likely a λ-unit mismatch (per-day intended,
  per-second applied) OR boost-sustained-only by design. Filed as Harlo
  worklist candidate; NOT this experiment's to fix.
- CONSEQUENCE: P2 cannot be satisfied from this store. Before any cell runs,
  the store must accumulate ≥12 Elenchus-VERIFIED traces (real coaching
  sessions through the verify path), or the probe definition must be rescoped.
  No padding with marginal/unverified traces (SPEC falsification clause).

## Cycle 5 — DIAGNOSE Δ9 (Claude Code, read-only; Workflow wf_919b174f-b10, 5 lenses)
Q: is warm-tier decay a unit bug or by design, and how much of pool=0 does it
explain vs VERIFIED starvation?

FORMULA (decay.rs:25-54): strength = initial·e^(−λ·dt) + Σ boost_i·e^(−λ·dt_i).
- λ=0.05 default: store.rs:52 (traces DDL); mirrored encoder/__init__.py:66,
  hot_store/promotion.py:109, modulation/profile.py:28.
- dt = now − created_at in RAW UNIX SECONDS. now = SystemTime…as_secs
  (lib.rs:172-176, query.rs:57-60); created_at = int(time.time())
  (encoder:104, promotion:142). NO seconds→days scaling anywhere
  (decay.rs:32, encoder:227). ⇒ half-life 13.86 s; time-to-ε (ε=0.01,
  config.py:104) 92.1 s.

INTENT: no retention horizon promised; Rule 4 states the formula with NO unit
(CLAUDE.md:52). Every OTHER timescale is days/weeks — S3 90-day (:118), S5
48h–30d (:125), S7 30-day stale (:134), inquiry reversion 24h
(threshold_reversion.py:15), biometric freshness 5 min (ADR-0001:52). The
core-memory 14-second half-life is the lone absurd outlier → strong
circumstantial evidence the seconds-scale is unintended.

WHY 1,140 TESTS PASS: every decay/apoptosis test uses synthetic tiny/origin
timestamps — Rust decay.rs:68-120 dt∈{0,50,100,1000}; store.rs apoptosis
:350-414 created_at∈{0,999_990}, now=1_000_000; query recalls at dt≈0. Python
test_compaction dt≤100, test_phase2 apoptosis at dt≈0, inquiry/compliance use
the SEPARATE e^(−3t/ttl) vitality formula. NO test feeds realistic Unix-epoch
created_at (~1.7e9) + now ≥1 day apart — the one combination that exposes the
collapse. Apoptosis tests pick extreme deltas to FORCE deletion, so they
neither catch nor pin the intended unit.

EMPIRICAL (snapshot 20260610-181809, read-only): warm `traces`=0; hot_traces=16
(all encoded=0, wave1-trial synthetic); sessions=282; observations.db=1437
behavioral. Warm tier empty for TWO reasons, in order: (1) PROMOTION NEVER RAN
— PromotionPipeline.promote_batch (promotion.py:48-98) has zero
source='hot_promotion' rows; the 16 hot traces were never even encoded; (2)
decay would apoptose any promoted trace in ~92 s anyway. So warm is empty
because nothing was promoted, NOT because decay deleted promoted traces. Decay
is a LATENT second kill.

DECOUPLE: pool=0 forced by |verified_source_trace_ids ∩ (hot∪warm)| =
|∅ ∩ …| = 0. Cause A (VERIFIED starvation: reflexes_verified=0,
elenchus_verified=0, elenchus_pending ABSENT) is SUFFICIENT ALONE — pool=0 for
ANY warm state. Cause B (warm decay/emptiness) marginal contribution to THIS
pool=0 = ZERO. Independent causes.

VERDICT
- Δ9 decay unit: **BUG (latent, representation-level)** by overwhelming
  circumstantial evidence (14 s half-life vs the system's own day/week
  conventions; no test exercises real timestamps). Intended λ-semantics
  UNDETERMINED (undocumented) → fix is architect's call. BY-DESIGN
  (boost-sustained-only) implausible: 14 s half-life can't support week-scale
  coaching patterns or S7's 30-day crystallization.
- pool=0 attribution: VERIFIED starvation ≈100% (logically sufficient); decay
  ≈0% of THIS pool=0. Δ9 is NOT why Cycle 4 killed — separate latent defect.

BLAST RADIUS (reads decayed strength; all LATENT today — warm tier unused):
- microglia apoptosis (store.rs) — would PHYSICALLY DELETE+VACUUM promoted warm
  traces ~92 s after creation → permanent data loss. Highest severity.
- recall ranking (query.rs recall) — warm traces >92 s read ≈0 strength →
  ranking flattened, threshold filters drop them.
- DMN / patterns — collapsed strengths → patterns never accrete.
- NOT affected: hot tier (no decay fields, FTS-resident), reflexes (gated by
  verification/permanence, not ε decay).

FIX SKETCHES (sketch only — NOT applied):
A. Scale dt→days at the boundary: dt_days=(now−created_at)/86400 before the
   exp. λ=0.05 ⇒ ~13.9-day half-life, ~92-day ε — matches conventions. Smallest
   change; must land identically in decay.rs + encoder + apoptosis or the
   engines diverge; apoptosis tests need new expected values.
B. Retune λ for seconds: λ≈5.8e-7 (~14-day half-life). Touches only the
   constant (store.rs:52, encoder, promotion, profile). Hides the unit behind a
   magic number; existing rows need migration.
C. Explicit unit / store half-life-in-days, derive λ. Most invasive; removes
   ambiguity permanently; pair with an ADR fixing "what retention means in
   Harlo." Closes the intent gap.

PREREQUISITE (separate gap): even a perfect decay fix won't populate the warm
tier — promotion never runs (Thread 4). Δ9 fix is necessary-not-sufficient.

Δ10: warm-tier decay is a latent representation BUG (architect's call on λ
semantics), NOT the cause of pool=0. HALT for architect review — λ semantics
is a representation decision about what "memory" means in Harlo.

## REPAIR SPRINT — Phase 0: repo topology (read-only, report-only)
Premise ("public github.com/JosephOIbrahim/Harlo = 2 commits, v3.3.1 README,
cognitive_twin layout, Latest=v9.0.0 Mar 30") is STALE, not a different repo.
Authoritative state (git + gh):
- origin = https://github.com/JosephOIbrahim/Harlo.git (single remote, https).
  gh active account = JosephOIbrahim (joe002 also keyring-authed, INACTIVE;
  scopes gist/read:org/repo — no `workflow`, known).
- Remote default branch = master (ls-remote --symref HEAD → refs/heads/master),
  tip=0250db3 (current). Repo PUBLIC, created 2026-03-15, pushed today. README
  on master = current ("Local first AI Coach" logo).
- ALL this week's pushes + gh ops (v0.1.6 = Latest, topics healthkit/ios,
  description, 4 logos, positioning) landed HERE. gh release list shows
  v0.1.6=Latest AND orphaned legacy v8.0.0/v9.0.0 (Mar) tags coexisting.
- Topology: ONE repo, rewritten in place. Created Mar 15 on the v3.x→v9.0.0
  line (python/cognitive_twin/, v3.3.1 README); later replaced by the v0.1.x
  line (python/harlo/, current). Fingerprints: version reset 9.0.0→0.1.0,
  orphaned v8/v9 release tags, layout swap. The architect's "2-commit/v3.3.1"
  view is the PRE-REWRITE state — a cached/stale browser view of the SAME repo.
- Siblings (NOT where this lives): JosephOIbrahim/Harlo_OS (private),
  JosephOIbrahim/Hanna (public).
- CONSEQUENCE (logo): the 4 logo pushes DID land on master (default branch).
  "Logo isn't updating" = stale/cached view, NOT a push failure. Hard refresh
  / cache-bust shows the current logo.
- Per mandate: PROPOSE nothing, FIX nothing. Public-surface fate (orphaned
  v8/v9 tags, the 9.0.0→0.1.0 version-reset optics) is the architect's
  representation decision.

## REPAIR SPRINT — Phase 1: Δ9 decay fix (Option A + ADR-0003)
RULED: dt→days (/86_400), test-first.
- REGRESSION FIRST (the proof the 1,140 never had): realistic Unix epochs
  (created=1.7e9, now=+1/+14/+90 days), assert ≈ e^(-0.05·days). Pre-fix both
  FAILED hard — Rust decay::tests::test_decay_unit_is_days → "1 day -> 0"
  (panic); Python tests/test_decay_units.py → "1 day -> 0.0" (wanted 0.951).
- FIX (one commit), dt=(now-created_at)/86_400 at TWO implementations — NOT
  three: store.rs apoptosis DELEGATES to compute_lazy_decay, so fixing decay.rs
  fixes recall AND apoptosis with one change (they now provably share one decay,
  cannot drift):
    · crates/hippocampus/src/decay.rs (base + boost dt) → query.rs recall +
      store.rs microglia_apoptosis.
    · python/harlo/encoder/__init__.py _compute_lazy_decay (base + boost dt).
- GREEN: cargo test -p hippocampus 43/43 (+1 regression). pytest 1383 passed /
  5 skipped — identical 39 ML-stack env failures as baseline (anthropic /
  sentence_transformers / onnx), ZERO new regressions. Updated 3 tests that
  hard-coded seconds (decay test_decay_over_time → 100 days; store
  test_apoptosis_deletes_weak_traces + test_apoptosis_chunked_path → 200-day
  now). Rebuilt the PyO3 extension (maturin develop) so the FFI carries the fix.
- NO ROW MIGRATION (confirmed): no persisted `strength` column anywhere;
  strength is computed read-side from (initial_strength, decay_lambda,
  created_at, boosts_json). Only the interpretation changed.
- ADR-0003 written; CLAUDE.md Rule 4 formula now carries the unit (dt in days,
  λ=0.05/day, 13.9-day half-life), coherent with S5/S7/S3.
- Δ11 (flagged, NOT fixed — scope): compaction/__init__.py:211 variant
  weighting shares the seconds-dt shape; separate USD-Lite subsystem,
  composer-adjacent → architect's call.
- Effective decay now: 1d→0.951, 14d→0.497, 90d→0.011 (just above ε=0.01). A
  trace stored today survives a simulated day. PHASE 1 CONTRACT: MET.

## Open items
- P2: KILL FIRED (Cycle 4) — VERIFIED pool 0. Rescope: accumulate verified
  material via real sessions, or redefine the probe source. Re-run inventory.py.
- Representation decision parked for architect: wordmark "AI-Assisted OS"
  vs README/repo/release "local-first AI coach" — four surfaces must agree.
- Worklist candidates (NOT this experiment): utility-mode stub wiring;
  Elenchus pending-claim enumeration tool.

## Dead ends
DEAD-END | stage_reload as the between-cell reset | reloads stage only;
  SQLite + hippocampus state untouched; superseded by daemon lifecycle (Δ1)
DEAD-END | utility mode as harness contamination boundary | stub — reports
  ok while DMN observes (Δ6)
DEAD-END | "frozen store" / flatten-to-base cold condition (v1) | superseded
  in v2 already; cold = MCP unmounted, daemon down
