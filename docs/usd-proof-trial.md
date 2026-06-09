# TRIAL 01 — USD PROOF  (composed cognitive twin, depth-1)
*Harness-instantiated. Topology: SOLO. This is a FRAME draft for architect confirmation.*
*Tags — **ASSERTED**: from your cognitive-twin spec or our settled #1 plan · **INFERRED**: my construction, confirm or correct.*

---

## SPEC.md

### Outcome
Harlo's cognitive state is a *composed* USD stage — cognitive prims in a hierarchy, LIVRPS arcs
resolving cognitive priority — proven on the live (`pxr`-backed) `real_usd` stage. Not an empty
real stage that merely instantiates.  **[ASSERTED]**

### Acceptance predicates (the checkable bar)
1. Stage traversal returns a **populated hierarchy** — session / entity / decision structure + ≥1
   AIMemoryChunk prim — not a bare pseudo-root.  *[structure ASSERTED · phrasing INFERRED]*
2. **AIMemoryChunk** multi-apply schema applies and round-trips: `type` · `content` · `timestamp` ·
   `relevance_tags` · `decay_weight`.  *[schema ASSERTED · round-trip test INFERRED]*
3. **LIVRPS resolution** demonstrated on one attribute: a Local opinion > a Variant selection > a
   Specialize base (strength order *shown*, not assumed).  *[mapping ASSERTED · demo INFERRED]*
4. **Flatten-to-base-sublayer == `reconstruct_clean()`** output (structural lossless, not computational).
   *[reframing ASSERTED · equality test INFERRED]*
5. **customData** reports Unchanged / Edited / New across the composed layers.  **[ASSERTED]**
6. Extended `wave1_harness` asserts 1–5 green; `stage_type == real_usd` throughout.  **[ASSERTED]**

### Out of scope
Derivative tools (CognitiveGaffer / RoutingInspector / BurstMonitor); injection-as-evaluable-attributes
(SubEngine); the spec's **OUTSIDE-USD** set (routing cascade, momentum, PK curves, expert rewards,
lossless *math*); Wave 2 biometrics.  **[ASSERTED]**

### Falsification conditions — the approach is wrong if:
- LIVRPS strength order can't resolve cognitive priority **without fighting USD semantics** — e.g. the
  cognitive model needs Local *weaker* than Variants. That inverts the arc→role mapping and breaks the
  USD-native-priority thesis.  *[INFERRED]*
- The composed-stage round-trip can't reproduce clean state **structurally** (flatten ≠ reconstruct_clean).
  "Structural lossless" fails; lossless must stay computational.  *[INFERRED]*
- Authoring the hierarchy needs **per-traversal computation** that variants were supposed to eliminate.
  The spec's "pre-author gain tables as variants" actionable-piece is wrong.  *[INFERRED]*

> Any of these firing → **FALSIFIED exit**: stop and report, don't grind.

---

## CHAMPION.md  — v1 (Cycle 1: session + entity populated on the live stage)
`real_usd` stage **populated** with `/Brain/Session` (SessionPrim) and at least one
`/Brain/Association/Traces/t_<id>` (TracePrim) on the live (`pxr`-backed) stage. Authoring
is declarative (`stage.DefinePrim`, no per-traversal computation).

**Session + entity tiers asserted on the live stage. Decision tier deferred** — the v9
engine produces no minimal-flow MotorPrim and per amendment 2 no MotorPrim was fabricated.

**Reproduce:** `.venv312/bin/python wave1_harness.py`. New scoreboard row
`populated hierarchy (P1)` shows PASS with the persisted `.usda` path, the SessionPrim
`current_session_id`, and the TracePrim count.

**Persisted stage:** written by `persist_stage` MCP tool to
`<DATA_DIR>/stages/runtime.usda` (≈3.3 KB; 13 prims under `/Brain`).

**Confidence vs predicates:**
- **P1 = ~0.5** — session + entity tiers proven on the live stage; decision tier deferred;
  `AIMemoryChunk` not addressed (that is P2's author-fresh path).
- P2 / P3 / P4 / P5 = 0.0 (unchanged from v0; later cycles).
- **P6 = green** — `wave1_harness` asserts P1 + P6 GREEN; `stage_type == real_usd`
  throughout; `recall` + `live USD (FIRST STEP)` remain PASS (no regression).

**Code added (working tree, uncommitted):**
- `python/harlo/usd_lite/persistence/__init__.py` — `persist_current_brain()` thin
  explicit entrypoint (lazy imports keep module surface pxr-only per Constitution Law 3).
- `python/harlo/mcp_server.py` — `@server.tool(name="persist_stage")` calling the
  entrypoint; engine init untouched.
- `wave1_harness.py` — `check_populated_hierarchy()` verifier; added to scoreboard;
  exit code now reflects P1 status.

**v0 retained for history** (in LOG): `real_usd` stage instantiates; 0 cognitive prims;
no composition. Confidence P1–P5 = 0.0; P6 = partial.

---

## LOG.md  — append-only
- `SEED` | mock→real swap done — `stage_type real_usd`, usd-core 26.5, `.venv312` | prior session, verified.
- `OPEN` | spec lists LIVRPS / variants / layers as INSIDE-USD "Implemented"; runtime unproven on the
  real stage | branch **(a) verify-and-fix** vs **(b) author-fresh** — unresolved, owned by Mile 1.
- `MILE-1` | scout — P1=PARTIAL, P2=NO-CODE, P3=PARTIAL, P4=NO-CODE, P5=NO-CODE; branch **(a) verify-and-fix**
  with P2/P4/P5 as author-fresh additions INSIDE (a); falsification conditions: none fired | 2026-06-09
  SOLO, read-only. Substrate evidence: `python/harlo/usd_lite/persistence/writer.py:99-259` (live
  `pxr.Usd.Stage` + 21-prim `DefinePrim` authoring), `arc_types.py:12-19` + `composer.py:30-109` (LIVRPS
  enum + precedence engine), `schema/HarloSchema.usda` (21 concreteTyped prims; singleApply `Provenance`
  only — no multi-apply, no `AIMemoryChunk`).
- `FRAME-CONFIRMED` | architect confirmed FRAME + branch (a); engine cycle opens — `OPEN` resolved | 2026-06-09.
- `CYCLE-1` | PROPOSE→CRITIQUE→BUILD→CHECK on C1 (verifier-first for P1 on the live stage).
  C2 killed on paper — in-memory composer test doesn't satisfy SPEC §Outcome's "proven on
  the live (`pxr`-backed) `real_usd` stage". C3 killed on paper — `AIMemoryChunk` schema
  needs its own PROPOSE/CRITIQUE pass before BUILD (multipleApply pattern not present
  anywhere in the codebase to lift from). RED observed: `persist_stage tool not exposed;
  tools = [recall, query_past_experience, store, coach, patterns, status,
  resolve_verifications, trigger_cognitive_recalibration, stage_reload]`. BUILD per
  amendments 1 + 2 — explicit `persist_current_brain()` entrypoint, NOT engine-init hook;
  triad seeded (session via SessionManager auto-create, entity via existing `store` path,
  decision deferred — no fabrication). GREEN observed: 1 SessionPrim
  (`current_session_id='2e9f898e540041fd'`) + 1 TracePrim (`/Brain/Association/Traces/
  t_1e09e573541441db`) on `<DATA_DIR>/stages/runtime.usda` (≈3.3 KB, 13 prims).
  Writer spot-check: declarative `DefinePrim` only — SPEC §Falsification #3 does NOT
  fire. Promotes CHAMPION v0 → v1 | 2026-06-09 SOLO; working tree only, no commit.

---

## FIRST ENGINE MOVE — Mile 1 scout  *(verifier-first)*
The predicate *"the spec's claimed structure exists in code"* has **no verifier** → building the scout
is the first action (the verifier is the deliverable).

- Inspect the repo for prim-authoring / schema-registration / composition code.
- Classify each of **P1–P5**: `has-code` / `partial` / `no-code`.
- Output picks the branch: **(a)** verify-and-fix the existing authoring on the live stage, or
  **(b)** author-fresh.
- ~10 min · SOLO · **no building** until the scout returns and the contract is confirmed.
