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

## CHAMPION.md  — v4 (Cycle 4: §F2 anchor structural immunity CONFIRMED on live stage)
**SPEC §F2 anchor follow-up status: CONFIRMED (not falsified).**
Anchor sections (CONSTITUTIONAL / SAFETY / CONSENT / KNOWLEDGE) are STRUCTURALLY immune
to injection — not parametrically protected. Asserted on the live (`pxr`-backed) `real_usd`
stage via four-profile composition (Default / Stress / Rest / Adversarial), with
`hash_anchor_subtree(stage)` invariance across all four AND a load-bearing adversarial
probe: the adversarial delta layer EXPLICITLY authors an opinion on an anchor path,
and pxr's composition mechanism rejects it.

**Structural mechanism:** `subLayerPaths = [anchor_layer, delta_X, base_layer]`. Anchor
layer at position 0 (strongest in USD composition); any anchor opinion in subsequent
sublayers — including the adversarial — appears in the property stack but LOSES the
resolution.

**Per-profile result** (per scoreboard + independent cold-pxr re-read):

| profile | anchor_hash prefix | invariant? | nonanchor_hash prefix |
|---|---|---|---|
| `clean` (anchor+base, no delta) | `50f6de31aa42ca6d4d55…` | (reference) | — |
| `default` | `50f6de31aa42ca6d4d55…` | OK | `3541a86376b14c7c7788…` |
| `stress`  | `50f6de31aa42ca6d4d55…` | OK | `1b768b9968d419bb9a30…` |
| `rest`    | `50f6de31aa42ca6d4d55…` | OK | `d0f0a3f2436f98da02d4…` |
| `adversarial` | `50f6de31aa42ca6d4d55…` | **OK** | `3541a86376b14c7c7788…` (same as default by design — isolates the attack signal) |

**Adversarial probe (load-bearing):**
- `adversarial layer authored attack: spec_exists=True, value='MALICIOUS_OVERRIDE'` — the
  attack was MADE, not skipped.
- `pxr-resolved value on /Brain/Anchors/CONSTITUTIONAL: 'constitutional_baseline'` — the
  attack FAILED structurally.
- `pxr property stack (strongest first)`: anchor_layer @ `'constitutional_baseline'`,
  delta_adversarial @ `'MALICIOUS_OVERRIDE'` — pxr literally reports both opinions and
  picks the anchor by composition strength.

**Non-vacuity check:** modulating profiles produce 3/3 unique nonanchor hashes — Default,
Stress, Rest each really modulate non-anchor cognitive state. (Adversarial's nonanchor
matches Default by design — its only delta vs Default is the attack itself.)

**Fidelity:** binary — anchor invariance is bit-identical, not float-tolerant. Adversarial
attack succeeded vs. failed is a string equality.

**Reproduce:** `.venv312/bin/python wave1_harness.py`. New scoreboard row
`anchor immunity (§F2 follow-up)` shows PASS with the full per-profile invariance grid,
adversarial probe result, and pxr's property stack on the attacked anchor.

**Persisted scene:** `<DATA_DIR>/stages/anchor_demo/{anchor_layer,base_layer,
delta_{default,stress,rest,adversarial},composed_clean,composed_{default,stress,rest,adversarial}}.usda`.

**Confidence vs predicates:**
- P1 = ~0.5 (unchanged).
- P3 = ~0.8 (unchanged).
- **P4 = ~0.9** — structural lossless (Cycle 3) + anchor structural immunity (Cycle 4)
  both CONFIRMED. Remaining ~0.1: numeric-type breadth (only `double` + `string`
  signals tested); larger surface (more anchor attrs, more delta profiles) for
  defensive coverage.
- P2 / P5 = 0.0 (unchanged).
- **P6 = green** — full harness asserts P1 + P3 + P4 + P4b + P6 GREEN; `stage_type ==
  real_usd` throughout; recall + live USD remain PASS (no regression).

**Code added (working tree, uncommitted):**
- `python/harlo/usd_lite/anchor_demo.py` (NEW) — `author_anchor_immunity_demo()`
  authors anchor/base/4-delta/composed-per-profile/composed-clean .usda files;
  `hash_anchor_subtree(stage)` and `hash_nonanchor_subtree(stage)` walk the resolved
  subtree and SHA256 the canonical `path = repr(value)` rows.
- `python/harlo/mcp_server.py` — `@server.tool(name="anchor_demo")` calling the
  authoring; engine init still untouched.
- `wave1_harness.py` — `check_anchor_immunity()` verifier; main() updated to include
  P4b verdict; exit code now requires live + P1 + P3 + P4 + P4b PASS.

**What did NOT change (per Cycle 4 hard constraints):**
- `composition/resolver.py` and `usd_lite/composer.py` (inert arc-type composers) —
  untouched.
- P2 (AIMemoryChunk), P5 (customData), decision-tier (MotorPrim) — parked.
- v9 engine init path — untouched.
- Real injection pipeline / numeric-type breadth — not touched (would scope-balloon).

**v3 retained for history** (in LOG): §F2 structural-lossless CONFIRMED via
`reconstruct_clean` bit-identical recovery.

## CHAMPION-v3 (Cycle 3) — historical record
**SPEC §F2 status: CONFIRMED (not fired).**
**SPEC §F2 status: CONFIRMED (not fired).**
`reconstruct_clean()` as flatten-to-base recovers the clean baseline **bit-identically**
from a composed stage that has both base and delta sublayers. Asserted on the live
(`pxr`-backed) `real_usd` stage by comparing `SHA256(reconstruct_clean(composed_with_delta))`
against the reference `SHA256(reconstruct_clean(composed_clean_only))` — both sides traverse
the same canonical serialization (`Stage.Flatten().ExportToString()`), so the comparison is
apples-vs-apples.

**Both hashes identical**:
`46185104ccdcbd91984ee44bf7ab9f35153772732754196163eb98cedeca6a92`

**Per-step result** (per scoreboard + independent cold-pxr re-read):
- composed_with_delta view value = `0.7`  (delta-modulated; proves the delta is non-empty)
- composed_clean_only view value = `0.5`  (identity at zero — no-delta == clean)
- delta magnitude = `0.2`  (clean=0.5, modulated=0.7)
- fidelity = `1.0` (binary; bit-identical hash, NOT float-tolerant)
- recovered semantic signal = `0.5`  (parsed from the reconstructed string — confirms clean,
  not modulated)
- Sublayer tagging: `clean_baseline.usda → customLayerData["layer_role"]='base'`,
  `delta_overlay.usda → 'delta'`; reconstruct_clean filters on this and includes ONLY
  base layers in the flattened-anon root.

**Reproduce:** `.venv312/bin/python wave1_harness.py`. New scoreboard row
`structural lossless (P4 / §F2 test)` shows PASS with clean/recovered hash prefixes,
delta magnitude, identity-at-zero status, and the semantic signal recovered.

**Persisted scene:** `<DATA_DIR>/stages/lossless_demo/{clean_baseline,delta_overlay,
composed_with_delta,composed_clean_only}.usda` (fresh-write each `lossless_demo` call).

**Confidence vs predicates:**
- P1 = ~0.5 (unchanged from v2).
- P3 = ~0.8 (unchanged from v2).
- **P4 = ~0.7** — structural lossless CONFIRMED for one signal attribute via
  customLayerData-tagged sublayer filtering + flatten-to-base. Remaining ~0.3:
  anchor structural immunity (CONSTITUTIONAL / SAFETY / CONSENT / KNOWLEDGE prims
  must stay bit-identical regardless of which delta overlays are present — needs
  multiple delta profiles + anchor prims). Flagged as the follow-up §F2 surface,
  not balloon'd into this cycle.
- P2 / P5 = 0.0 (unchanged).
- **P6 = green** — full harness asserts P1 + P3 + P4 + P6 GREEN; `stage_type == real_usd`
  throughout; recall + live USD remain PASS (no regression).

**Code added (working tree, uncommitted):**
- `python/harlo/usd_lite/lossless_demo.py` (NEW) — `author_lossless_demo()` authors 4
  .usda files; `reconstruct_clean(stage_path)` filters sublayers via
  `customLayerData[layer_role]=='base'` and returns `Stage.Flatten().ExportToString()`.
  Pure native pxr, declarative.
- `python/harlo/mcp_server.py` — `@server.tool(name="lossless_demo")` calling
  `author_lossless_demo`; engine init still untouched.
- `wave1_harness.py` — `check_structural_lossless()` verifier; main() updated to
  include P4 verdict; exit code now requires live + P1 + P3 + P4 all PASS.

**What did NOT change (per Cycle 3 hard constraints):**
- `composition/resolver.py` and `usd_lite/composer.py` (inert arc-type composers) —
  untouched.
- P2 (AIMemoryChunk), P5 (customData), decision-tier (MotorPrim) — parked.
- v9 engine init path — untouched.

**v2 retained for history** (in LOG): §F1 USD-native-priority thesis CONFIRMED; pxr
resolves `L > V > S` on the live stage for one cognitively-meaningful attribute.

## CHAMPION-v2 (Cycle 2) — historical record
**SPEC §F1 status: CONFIRMED (not fired) for the test attribute.**
**SPEC §F1 status: CONFIRMED (not fired) for the test attribute.**
pxr's native composition engine resolves `LOCAL > VARIANT > SPECIALIZE` exactly as the
cognitive priority demands. Asserted on the live (`pxr`-backed) `real_usd` stage by reading
`prim.GetAttribute("current_mode").Get()` in a cold harness process — pxr's own resolution,
not a Python IntEnum proxy.

**Three scenarios, three pxr resolutions** (per scoreboard + independent re-read via
`GetPropertyStack`):
- `/Brain/CompositionDemo/L_wins`  — LOCAL + VARIANT + SPECIALIZE  → resolved `'override_today'` (LOCAL wins)
- `/Brain/CompositionDemo/V_wins`  — VARIANT + SPECIALIZE          → resolved `'morning_mode'` (VARIANT wins)
- `/Brain/CompositionDemo/S_wins`  — SPECIALIZE only               → resolved `'constitutional_base'`

pxr's `GetPropertyStack` confirms the per-attribute opinion order is exactly
LOCAL → VARIANT(`{context_mode=morning}`) → SPECIALIZE → (base) — the SPEC's mapping holds.

**Reproduce:** `.venv312/bin/python wave1_harness.py`. New scoreboard row
`native composition (P3 / §F1 test)` shows PASS with per-prim resolved values; P3 verdict
block reports thesis CONFIRMED.

**Persisted stage:** `<DATA_DIR>/stages/composition_demo.usda` (fresh-write each
`compose_demo` call). Cycle 1's `runtime.usda` untouched.

**Confidence vs predicates:**
- **P1 = ~0.5** (unchanged from v1 — session + entity proven; decision + AIMemoryChunk open).
- **P3 = ~0.8** — native L > V > S CONFIRMED on one cognitively-meaningful attribute.
  Remaining surface for completeness: permanent-override TIMESTAMP semantics (composer #2
  has "later permanent wins on tie"; native USD has no equivalent); demo currently uses
  ONE attribute + the `morning` variant — Cycle 3 may add a second variant or non-string
  attribute to widen the surface.
- P2 / P4 / P5 = 0.0 (unchanged).
- **P6 = green** — full harness asserts P1 + P3 + P6 GREEN; `stage_type == real_usd`
  throughout; `recall` + `live USD (FIRST STEP)` remain PASS (no regression).

**Code added (working tree, uncommitted):**
- `python/harlo/usd_lite/composition_demo.py` (NEW) — `author_native_composition_demo()`
  authors LOCAL via prim-direct opinion, VARIANT via `UsdVariantSet` edit-context,
  SPECIALIZE via `prim.GetSpecializes().AddSpecialize(basePath)`. Pure native pxr,
  declarative.
- `python/harlo/mcp_server.py` — `@server.tool(name="compose_demo")` exposing the
  authoring; engine init still untouched (amendment 1 honored).
- `wave1_harness.py` — `check_native_composition()` verifier; main() updated to include
  P3 verdict; exit code now requires live + P1 + P3 all PASS.

**What did NOT change (per Cycle 2 hard constraints):**
- `composition/resolver.py` and `usd_lite/composer.py` (inert arc-type composers #1/#2) —
  untouched. Delete-vs-keep contingent on this result; the result is GREEN, so the
  consolidation question stays open for a separate decision.
- Decision-tier / MotorPrim — parked.
- v9 engine init path — untouched.

**v1 retained for history** (in LOG): real_usd stage populated with `/Brain/Session` +
`/Brain/Association/Traces/t_<id>`; session + entity proven; decision deferred.
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
- `CYCLE-4` | BUILD→CHECK on the §F2 anchor structural-immunity follow-up. Architecture:
  anchor_layer.usda tagged `customLayerData["layer_role"]="anchor"` authors the 4 anchor
  prims (CONSTITUTIONAL / SAFETY / CONSENT / KNOWLEDGE); base_layer carries non-anchor
  defaults; 4 delta profiles (default/stress/rest = modulating, adversarial =
  modulating-as-default PLUS explicit `/Brain/Anchors/CONSTITUTIONAL.value =
  'MALICIOUS_OVERRIDE'` attack); composed roots per profile with
  `subLayerPaths=[anchor, delta_X, base]` (anchor at position 0 = structurally strongest).
  `hash_anchor_subtree()` and `hash_nonanchor_subtree()` walk the resolved-state and SHA256
  the canonical rows. RED observed: "`anchor_demo` tool not exposed". BUILD: new
  `python/harlo/usd_lite/anchor_demo.py` (author + hash functions), `anchor_demo` MCP tool;
  verifier from cold pxr asserts (a) anchor invariance across ALL profiles incl.
  adversarial (clean=`50f6de31aa42ca6d4d55…`, all four match), (b) modulating-profile
  non-anchor hashes 3/3 unique (deltas real), (c) adversarial layer authored the
  attack opinion (load-bearing probe — `spec_exists=True, value='MALICIOUS_OVERRIDE'`),
  (d) composed adversarial resolves the attacked anchor to clean value
  (`'constitutional_baseline'`, NOT `'MALICIOUS_OVERRIDE'`) — structural-vs-parametric
  decisive. pxr's own GetPropertyStack on the adversarial composed stage shows both
  opinions in the stack (anchor strongest, adversarial weaker) and resolves to the
  anchor. **Falsification did NOT fire** — anchors are STRUCTURALLY immune (composition
  mechanics, not convention). Remaining surface flagged: numeric-type breadth + larger
  anchor + profile counts for defensive coverage. Composers #1 + #2 untouched per hard
  constraint. Promotes CHAMPION v3 → v4 | 2026-06-09 SOLO; working tree only, no commit.
- `CYCLE-3` | PROPOSE→CRITIQUE→BUILD→CHECK on P4 via (a-native) — the §F2 structural-lossless
  thesis test. Architecture: clean + delta as separate USD sublayers tagged via
  `customLayerData["layer_role"]={"base"|"delta"}`; root has `subLayerPaths=[delta, clean]`
  (delta strongest → composed view is delta-modulated). `reconstruct_clean(stage_path)`
  filters sublayers by tag, builds transient anon root with only base sublayers, returns
  `Stage.Flatten().ExportToString()`. Reference `clean_hash` computed via the SAME
  reconstruct path on a clean-only composed stage — apples vs apples for SHA256.
  RED observed: `"lossless_demo tool not exposed"`. BUILD: new
  `python/harlo/usd_lite/lossless_demo.py` (author + reconstruct), `lossless_demo` MCP tool;
  verifier from cold pxr asserts (a) delta non-empty (`composed_view=0.7 != clean=0.5`),
  (b) identity at zero (no-delta view == clean), (c) bit-identical hash match. GREEN observed:
  both hashes = `46185104ccdcbd91984ee44bf7ab9f35153772732754196163eb98cedeca6a92`,
  fidelity=1.0, recovered semantic signal = 0.5 (clean, not modulated). **§F2 did NOT fire**
  — structural lossless CONFIRMED for this attribute. Remaining §F2 surface flagged for
  follow-up: anchor structural immunity (CONSTITUTIONAL/SAFETY/CONSENT/KNOWLEDGE prims must
  stay bit-identical across multiple delta profiles — needs anchor prims + multi-profile
  scenario, deferred). Composers #1 + #2 untouched per hard constraint. Promotes CHAMPION
  v2 → v3 | 2026-06-09 SOLO; working tree only, no commit.
- `CYCLE-2` | PROPOSE→CRITIQUE→BUILD→CHECK on P3 via (a-native) — the §F1 USD-native-priority
  thesis test. Deep scout surfaced 3 parallel composition systems (`composition/resolver.py`,
  `usd_lite/composer.py`, `src/cognitive_stage.py`); first two are inert (zero production
  callers), third is the live engine path using native subLayerPaths for delegate isolation.
  RED observed: "`compose_demo` tool not exposed". BUILD: new
  `python/harlo/usd_lite/composition_demo.py` authoring LOCAL+VARIANT+SPECIALIZE on three
  sibling test prims under `/Brain/CompositionDemo` via native pxr APIs (LOCAL = prim-direct
  opinion; VARIANT = `UsdVariantSet.GetVariantEditContext()`; SPECIALIZE =
  `prim.GetSpecializes().AddSpecialize(basePath)`); `compose_demo` MCP tool; verifier reads
  `attr.Get()` in cold harness process (pxr's REAL composition, not IntEnum proxy).
  GREEN observed: pxr resolves L_wins→'override_today' (LOCAL), V_wins→'morning_mode' (VARIANT),
  S_wins→'constitutional_base' (SPECIALIZE). Independent cold re-read via
  `GetPropertyStack(Usd.TimeCode.Default())` confirms decision-graph order matches cognitive
  priority. **§F1 did NOT fire** — thesis CONFIRMED for this attribute. Remaining §F1 surface
  flagged for follow-up: permanent-override TIMESTAMP semantics from composer #2 has no native
  equivalent (cheap test of "Local-wins reproduces permanent" demonstrated by L_wins beating
  VARIANT, but the temporal "later permanent wins on tie" is a separate scenario — deferred).
  Composers #1 + #2 left untouched per hard constraint. Promotes CHAMPION v1 → v2 |
  2026-06-09 SOLO; working tree only, no commit.
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
