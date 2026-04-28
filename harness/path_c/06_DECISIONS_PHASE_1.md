# Path C Harness — Phase 1 Gate Decisions

**Status:** Phase 1 human-gate closer
**Authority:** supersedes [NEEDS DECISION] markers in
`design/mile_2_phase_1_schema_design.md` and Crucible-flagged
open items in `verify/mile_2_phase_1_crucible.md`
**Date:** 2026-04-28

These eight decisions resolve the human-review gate after Phase 1
design landed. Phase 2 (Forge implementation) treats them as
binding. Any conflict between this file and prior design /
Crucible artifacts is resolved in favor of this file.

---

## D6 — Memory hypothesis: confirmed-shipped-and-present-but-dormant

**Decision:** Real OpenUSD integration code from Sprint 4 is
**present in the repo** at `src/cognitive_stage.py` (and
neighboring files in `src/`). The recon §5 statement "no `pxr`
imports anywhere" was scope-bounded to `python/harlo/` and missed
`src/`. `.venv312` did not have `pxr` installed until Phase 0;
the code was dormant, not absent.

**Rationale:** Phase 0 grep of full repo (not scope-bounded)
located `from pxr import Sdf, Usd` in `src/cognitive_stage.py`.
Code is Sprint-4-vintage (March 30, 2026). Pre-publication
cleanup (April 1) appears to have removed the runtime wiring
without removing the source files.

**Implications for Path C:**

- Phase 2 Forge work is **closer to "rewire and verify existing
  code" than "implement from scratch."** D1's 2.5-week budget may
  tighten as a result.
- **Phase 2 scout MUST inventory `src/` before Forge writes any
  schema artifact.** Unscouted real-USD code in the repo is a
  collision risk Forge cannot afford.
- Recon scope error is a known-finite problem: Mile 1 recon
  scoped to `python/harlo/`. Future scout phases scope the
  whole repo.

**Supersedes:** memory-hypothesis classification in Mile 1 commit
message (CONFIRMED — refined to CONFIRMED-SHIPPED-AND-PRESENT-
BUT-DORMANT).

---

## D7 — Schema filename: HarloSchema.usda

**Decision:** The plugin's primary schema file is
`schema/HarloSchema.usda` (mixed-case, project-named), not
`schema/schema.usda`.

**Rationale:** Pixar convention varies — within a single plugin
directory, `schema.usda` is canonical; project-namespaced
filenames are also widely used. `HarloSchema.usda` makes the
file's owning plugin obvious in tooling output and in
filesystem-level greps. Cost-neutral vs `schema.usda`.

**Confirmation requirement:** Phase 2 scout confirms Moneta's
filename convention. If Moneta uses `schema.usda` and a strict
naming-mirror is desirable for substrate-unification clarity,
this decision can be revisited at the next gate. Default holds
unless explicitly revisited.

**Supersedes:** [NEEDS DECISION #1] in
`design/mile_2_phase_1_schema_design.md`.

---

## D8 — opinion_json: deferred (string sidecar)

**Decision:** `CompositionLayerPrim.opinion` is declared as
**`string` sidecar** in the codeless schema. Typed-attribute
migration to native USD types is **deferred**, not wontfix.

**Rationale:** Mile 1 codec-blocker policy: string sidecar at
the persistence boundary, typed migration documented but
deferred. Wontfix closes the door; deferred keeps the upgrade
path open for post-Step-6 cycles.

**Tracking:** Open issue "opinion typed migration —
post-Step-6" filed in repo issue tracker.

**Supersedes:** [NEEDS DECISION #2] in design doc.

---

## D9 — answer_embeddings: deferred (string sidecar)

**Decision:** `IntakeHistoryPrim.answer_embeddings` is declared
as **`string` sidecar** in the codeless schema. Typed-array
migration is **deferred**.

**Rationale:** Same as D8. The Mile 1 codec-blocker policy
holds uniformly — breaking it for one field needs a stronger
reason than convenience. If a Phase 2 / Phase 3 read-path
performance argument emerges for typed migration, surface as a
follow-up; the default holds today.

**Tracking:** Open issue "answer_embeddings typed migration —
post-Step-6" filed in repo issue tracker.

**Supersedes:** [NEEDS DECISION #3] in design doc.

---

## D10 — Provenance: apiSchema (applied schema)

**Decision:** `Provenance` is declared as an **`apiSchema`
(applied schema)** in the codeless schema, not a `typedSchema`.

**Rationale:** Recon flagged Provenance as "the only non-`*Prim`-
suffixed type, only emitted as a child of `CompositionLayerPrim`."
That structure indicates Provenance is a property bundle that
attaches to host prims, not a standalone prim type. This is the
exact use case `apiSchema` was designed for in real USD: applied
schemas grant a set of attributes to any prim that opts in.

**Implications:**

- Provenance gains the ability to attach to **any** prim that
  needs origin-tracking, not just `CompositionLayerPrim`. Future
  Step 4 (ComfyCozy) work that needs provenance on its prims
  scales without schema changes.
- Phase 2 Forge codegen path for Provenance differs from typed
  prims — applied-schema authoring uses
  `IsPrim().HasAPI<HarloProvenanceAPI>()` semantics rather than
  `IsA<HarloProvenance>()`.

**Supersedes:** Crucible-flagged open item "typedSchema vs
apiSchema for Provenance" in
`verify/mile_2_phase_1_crucible.md`.

---

## D11 — propertyOrder: mandatory

**Decision:** `propertyOrder` declarations are **mandatory** in
`HarloSchema.usda` for every prim type. Determines stable
attribute serialization order in `.usda` output.

**Rationale:** Without `propertyOrder`, USD writes attributes in
hash-table iteration order, which is non-deterministic across
runs. Test diffs become unstable; the new empirical test
baseline (1,133 — see D14) becomes unreproducible. This is a
regression-defense requirement, not optional polish.

**Implications for Phase 2 Forge:**

- Every prim in `HarloSchema.usda` declares `propertyOrder = [...]`
  listing all its attributes in fixed lexicographic order
- Crucible Phase 2 gate: round-trip diff stability check
  required (write → read → write, byte-identical output)

**Supersedes:** Crucible-flagged open item "propertyOrder
declaration for deterministic .usda output" in
`verify/mile_2_phase_1_crucible.md`.

---

## D12 — src/cognitive_stage.py: Phase 2 scout coverage mandatory

**Decision:** Phase 2 Architect-as-scout **must inventory `src/`
in addition to `python/harlo/` and `schema/`** before Forge
writes any schema artifact. Specifically required: every file
in `src/` that imports from `pxr`, every class that uses
`Usd.Stage` / `Sdf.Layer` / related runtime types, every
attribute or relationship name referenced in real-USD code.

**Rationale:** D6 establishes that real-USD code is present and
dormant. Forge writing schema artifacts without first knowing
what `src/` already declares risks **collision between schema
typeNames and existing runtime references** — exactly the
collision class Path C was supposed to avoid by separating
persistence and runtime tiers.

**Phase 2 scout output requirements:**

- File-by-file inventory of `src/` real-USD usage
- Every typeName, attribute name, or relationship name
  referenced in `src/` cross-checked against the 21 typeNames in
  Phase 1 design
- Any collision flagged before Forge work begins
- Recommendation: rewire `src/cognitive_stage.py` to consume the
  new schema, OR document why it stays separate

**Supersedes:** No prior decision (this is new from D6's
discovery).

---

## D13 — B1 (.pyd file lock workaround): documented, not blocking

**Decision:** The `.pyd` file lock that prevented `pip install
-e .[substrate]` from succeeding strict-form is a Windows-on-
already-loaded-DLL quirk. Workaround (`pip install usd-core==26.5`
direct) achieved the functional goal. Not blocking; documented in
`harness/path_c/substrate_pin.md`.

**Phase 2 implications:** None for execution. Mile 3 release
notes should mention the install pattern for Windows users:

```
# If `pip install -e .[substrate]` fails on .pyd lock:
# 1. Close any process holding usd-core .pyd files
# 2. Retry, OR
# 3. pip install usd-core==26.5 directly, then retry the
#    editable install
```

**Phase A confirmation:** the same lock recurred when running
`pip install -e .[dev]` in Phase A. Same workaround
(`pip install sentence_transformers anthropic pytest` direct)
succeeded. Confirms the quirk is reproducible and the workaround
is reliable. Consolidated install instructions for both extras
go into Mile 3 release notes.

**Supersedes:** Crucible-flagged blocker B1 in
`verify/mile_2_phase_0_crucible.md` — reclassified from blocker
to documented quirk.

---

## D14 — Constitution Law 2 baseline: amend 1,140 → 1,133

**Decision:** Constitution Law 2 amends from "**1,140 tests
stay green at every gate**" to "**1,133 tests stay green at
every gate**." Mile 1's "1,140 green" figure was unverified;
the empirical baseline measured in Phase A (post-`[dev]`-install)
is **1,133 green / 1 skipped / 0 failed / 0 errored**.

**Rationale:** Mile 1 cited 1,140 in its commit message and
KICKOFF doc without empirical verification. Phase A's
post-`[dev]`-install measurement of 1,133 is **7 tests off**
the cited figure — natural drift territory for a codebase that
has had test files added/removed in the weeks between the
unverified Mile 1 number and the Phase A measurement. The
empirical figure is the correct binding number for Constitution
Law 2 going forward.

**Resolution of B2 (Phase 0 Crucible blocker):** classified
**B2-RESOLVED-DELTA** per
`harness/path_c/baseline_resolution.md`. The hypothesized "~52
pre-existing failures unrelated to dev-deps" did not exist as a
separate phenomenon — every failure resolved when `[dev]` was
installed (cascading import failures from `sentence_transformers`
and `anthropic` were the root cause of the mcp/tactical/provider
errors as well).

**TI-001 status:** filed and **closed on arrival** in
`harness/path_c/tracking_issues.md`. Audit trail preserved; no
residual failures to track. TI-001 re-opens if any of the
affected test categories breaks again in Phase 2+ for reasons
not explained by missing dev deps.

**Implications for Phase 2 Crucible:**

- Phase 2 (and all subsequent phases) gate on **1,133 green /
  1 skipped**, not 1,140.
- A new failure relative to 1,133 is a Path-C-caused regression
  and halts the gate.
- The 1 skip is intentional (existing test-suite skip logic);
  not a regression target.

**Supersedes:** Mile 1 commit message claim of "1,140 tests
unaffected"; Constitution Law 2 in `02_CONSTITUTION.md`
(text amended in spirit by this decision; physical edit
deferred to Mile 3 if/when `02_CONSTITUTION.md` is touched
again, since this file's authority is binding without that
edit).

---

## Decision summary table

| #   | Decision                                                                            | Authority                                  |
|-----|-------------------------------------------------------------------------------------|--------------------------------------------|
| D6  | Memory hypothesis: confirmed-shipped-and-present-but-dormant                        | Mile 1 commit message refinement           |
| D7  | Schema filename: HarloSchema.usda                                                   | Phase 1 design [NEEDS DECISION #1]         |
| D8  | opinion_json: deferred (string sidecar)                                             | Phase 1 design [NEEDS DECISION #2]         |
| D9  | answer_embeddings: deferred (string sidecar)                                        | Phase 1 design [NEEDS DECISION #3]         |
| D10 | Provenance: apiSchema                                                               | Crucible Phase 1 open item                 |
| D11 | propertyOrder: mandatory                                                            | Crucible Phase 1 open item                 |
| D12 | Phase 2 scout MUST cover src/ for real-USD collision check                          | New (from D6 discovery)                    |
| D13 | B1 .pyd lock: documented quirk, not blocking                                        | Crucible Phase 0 blocker reclassification  |
| D14 | Constitution Law 2 baseline: amend 1,140 → 1,133 (B2 resolution)                    | Crucible Phase 0 blocker B2 / Phase A      |

---

## Mile 2 Phase 1 gate closes with this file

When `06_DECISIONS_PHASE_1.md` is committed alongside Phase 0
artifacts, Phase 0–1 of Mile 2 is complete. Next session: Phase
2 Forge implementation against `design/mile_2_phase_1_schema_design.md`
+ this decisions doc. Mandatory: Phase 2 scout per D12 before
any Forge writes.

*End of Phase 1 gate decisions.*
