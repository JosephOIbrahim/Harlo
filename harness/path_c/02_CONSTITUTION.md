# Path C Constitution — Binding Laws & Roles

**Status:** Mile 1 deliverable &nbsp;|&nbsp; **Authority:** governs Mile 2 + Mile 3

These rules are binding. A violation halts execution and surfaces to
human review. There is no on-the-fly amendment. If a phase reveals
a rule cannot be honored as written, halt and surface — do not
improvise an exception.

---

## I. The Eight Laws

Numbered for citation. Each is binary.

1. **Path C only.** No facade. No full transplant. No architectural
   drift mid-execution. If a phase reveals Path C is infeasible for
   a specific prim, halt and surface; do not invent a fourth path.

2. **1,140 tests stay green at every gate.** Pre-existing red tests
   (if any) are documented in Phase 0 as the baseline. No new red
   test is acceptable at any gate boundary.

3. **`pxr` install stays optional via `[substrate]` extra.** Core
   Harlo must import, run, and pass its core test subset with `pxr`
   absent. The `[substrate]` extra activates persistence-layer code
   paths only.

4. **Hot-path reads stay in the fast tier.** No
   `pxr.Usd.Prim.GetAttribute()` on the runtime read path.
   Persistence-layer access is gated to declared sync boundaries
   (write-through, write-behind, checkpoint).

5. **Codec-blockers handled at the persistence boundary only.**
   Default resolution: `string`-typed sidecar attribute carrying the
   existing encoding (hex SDR, JSON-encoded blob). Typed-attribute
   migration is the documented upgrade path, deferred to a follow-on
   surgery unless a Phase 5 decision overrides per blocker.

6. **Binary phase gates.** Phase N+1 work cannot begin until Phase N
   gate is signed off green. No phase overlap. No optimistic merge.

7. **Halt-and-recover at every uncertainty.** Improvisation is a
   bug. Surface to Joe; document the question; wait. The cost of
   pause is low; the cost of unwanted action is high.

8. **Patent posture preserved.** Real USD remains the canonical
   persistence embodiment. Public claims (P1 CIP) hold without
   needing facade-shaped caveats.

---

## II. The Twelve Technical Commandments

Numbered for citation. Each is verifiable.

1. **Schema authored codeless.** No `usdGenSchema` C++ wrappers.
   `schema.usda` declares classes; `plugInfo.json` registers them;
   no generated C++ code exists in the surgery diff.

2. **`plugInfo.json` registers under `harlo` namespace.** Separate
   from Moneta's `MonetaMemory` namespace. No shared registration.
   No transitive dependency on Moneta's plugin registration.

3. **`schema.usda` declares all 21 prim types** with explicit IsA
   hierarchy, typed attributes, and `allowedTokens` enums. The type
   list is fixed by `recon/harlo-schema-recon.md` §1: `BrainStage`,
   `Provenance`, `TracePrim`, `CompositionLayerPrim`,
   `GateStatusPrim`, `MerkleRootPrim`, `SessionPrim`, `InquiryPrim`,
   `MotorPrim`, `SkillPrim`, `MultipliersPrim`, `InjectionPrim`,
   `IntakeHistoryPrim`, `AssociationPrim`, `CompositionPrim`,
   `ElenchusPrim`, `InquiryContainerPrim`, `MotorContainerPrim`,
   `SkillsContainerPrim`, `InjectionContainerPrim`,
   `CognitiveProfilePrim`.

4. **Subprocess-isolated `SchemaRegistry` gate test** runs before
   any prim operation in CI. Validation runs in a fresh subprocess
   to catch plugin-load failures that would silently succeed in the
   parent's polluted process state. (Q6 carry-over from Moneta,
   scoped to schema registry validation only.)

5. **Migration script (`migrate_path_c.py`) is read-tolerant.**
   Handles both old USD-Lite text format and new real-USD format on
   input. Idempotent: running the script on already-migrated data
   is a no-op.

6. **Sync layer is explicit.** Each prim has a declared sync policy
   (write-through, write-behind, or checkpoint) in
   `harness/path_c/sync_policy.md`, authored at Phase 3. No
   implicit-sync prim is permitted.

7. **Hex SDR codec at the boundary: `string`-typed sidecar by
   default.** The 2048-bit boolean SDR is encoded as the existing
   512-char hex string and stored in a `string`-typed attribute on
   `TracePrim`. Typed migration to `int[]` or `bool[]` is documented
   in a follow-up ticket, deferred.

8. **JSON-as-string blob attrs: same default.** `co_activations`,
   `competitions`, `opinion`, `answer_embeddings` carry
   `json.dumps(..., sort_keys=True)` strings in `string`-typed
   attributes. Typed-relationship or typed-array upgrades are
   documented but deferred unless Phase 5 overrides.

9. **`InjectionPrim` / `InjectionContainerPrim`: explicitly resolved
   in Phase 5.** Either finish the missing serializer/parser
   branches (and add to `BrainStage` round-trip), or evict the
   dataclasses and the `BrainStage.injection` field. Decision logged
   in `harness/path_c/blocker_decisions.md`.

10. **Stale `data/stages/cognitive_twin.usda` evicted.** File
    deleted; eviction reason recorded in `blocker_decisions.md` with
    reference to recon §1 and the package-rename commit `f830aeb`.

11. **Asymmetric `arc_type` token convention bug fixed.** The
    emitter currently writes `arc_type.name.lower()`; the parser
    reads via `ArcType[name.upper()]`. Architect picks one casing
    convention; codify it in the `allowedTokens` definition in
    `schema.usda`.

12. **No commits during execution.** Feature branch
    `path-c-surgery`, single squash commit at Mile 3 after Crucible
    Gate 6 passes. PR opens against `master` for human review.

---

## III. The Three Roles

Each role has a narrow charter. Cross-charter actions are out of
bounds. The same Claude Code session may play all three roles
serially within a phase, but switches between them explicitly and
remains in charter while in-role.

### Architect

**Owns:** design.

- `schema/schema.usda` shape and typed-attribute layout
- `schema/plugInfo.json` registration
- IsA hierarchy decisions (de novo; containment-driven candidate)
- Per-prim sync policy declarations
- Codec-blocker resolution policy per blocker
- Blocker decision log

**Does not:** write Python implementation code, run tests, run
benchmarks, commit.

### Forge

**Owns:** execution against Architect's spec.

- Real-USD writer/reader at the persistence boundary
- Sync layer implementation (`policy.py`, `dispatcher.py`)
- `migrate_path_c.py`
- Test repair where runtime tier actually changes (expected:
  minimal)
- All file edits inside `python/harlo/`

**Does not:** make design decisions, choose sync policy, choose IsA
shape, resolve codec-blocker defaults, commit.

### Crucible

**Owns:** verification.

- Run full test suite at every phase gate
- Subprocess `SchemaRegistry` gate test
- Hot-path latency benchmark (baseline at Phase 0; comparison at
  Phase 3 and Phase 6)
- Round-trip fidelity test per prim
- Sign or halt each gate

**Does not:** design, implement, commit.

When a role is uncertain whether an action is in-charter, default
to halt-and-surface (Law 7).

---

## IV. Binary Phase Gates

Each gate is pass / halt-and-recover. No partial pass. No "good
enough." Gate 1 has an explicit human-review halt.

| Gate | Phase | Pass criteria (binary) | Notes |
|------|-------|------------------------|-------|
| **0** | Pre-flight | `import pxr` succeeds in `.venv312`; baseline tests = 1,140 green (or documented baseline number); baseline latency captured | Memory hypothesis resolution document filed (separate from the gate). |
| **1** | Schema authoring | Subprocess `SchemaRegistry` test passes; 21 typeNames resolve; no collision with built-in USD or Moneta's `MonetaMemory` | **HUMAN REVIEW GATE — halt before Phase 2.** Joe signs off in writing on `schema_design.md`. |
| **2** | Persistence layer | Round-trip fidelity per prim (modulo declared codec-blockers); 1,140 tests still green | Reader + writer cover all 21 typeNames. |
| **3** | Sync layer | Hot-path read latency regression < 10% vs Phase 0 baseline; per-prim sync policy table complete (no `[NEEDS DECISION]` rows remain) | If regression > 10%, halt; sync policy redesign before Phase 4. |
| **4** | Migration script | `migrate_path_c.py` round-trips a representative session capture without data loss; idempotent on second run | Captures a representative `BrainStage` from `data/`. |
| **5** | Codec-blocker resolution | All 5 blockers resolved per Commandments 7–11; round-trip fidelity preserved; decisions logged in `blocker_decisions.md` | `InjectionPrim` finish-or-evict decision recorded. |
| **6** | Test repair + Crucible | 1,140 tests green; subprocess gate green; latency benchmark green; round-trip green | Final gate before Mile 3 squash commit. |

A halt at any gate freezes the branch. Resume requires:
- A human go-ahead.
- A documented diagnosis of the failure in
  `harness/path_c/halt_log.md`.
- A revised plan for the affected phase (not a retry of the same
  approach).
