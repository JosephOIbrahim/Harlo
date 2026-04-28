# Path C Handoff — Phase-by-Phase Execution Plan

**Audience:** Mile 2 Claude Code session (playing Architect, Forge,
Crucible serially within each phase).
**Authority:** subordinate to `02_CONSTITUTION.md`. On any conflict,
the Constitution wins.

Each phase declares: **Architect output**, **Forge tasks**,
**Crucible gate**. Phases run strictly sequentially. No phase
begins until the prior gate is signed off green. Gate 1 has an
additional explicit **human-review halt**.

---

## Phase 0 — Pre-flight verification

### Architect output

- **Memory hypothesis resolution document.** Did the March 30
  Sprint 4 `pxr.Usd.Stage` work actually ship and get stripped
  during the April 1 pre-pub cleanup, or was it on an unmerged
  branch?
  - Method: search `git log --all --diff-filter=D
    --since=2026-03-25 --until=2026-04-05 -- '*.py'` for deleted
    code touching `pxr.Usd.Stage`. Inspect any unmerged branches
    visible in `.git/refs`. Cross-reference Sprint 4 plan if
    available.
  - Output: `harness/path_c/memory_hypothesis.md` containing one of
    `[CONFIRMED-SHIPPED-AND-STRIPPED]`, `[CONFIRMED-NEVER-SHIPPED]`,
    or `[INCONCLUSIVE]`. If confirmed-shipped, link to the deleted
    code and surface as Phase 1 reference material.
- This document is **not** a Gate 0 prerequisite — it informs Phase
  1 cost estimation. Gate 0 may pass with `[INCONCLUSIVE]`.

### Forge tasks

1. Add a `[substrate]` extra to `pyproject.toml`. Pin the USD wheel
   version (current candidate: `usd-core` from PyPI; if vendored,
   document the wheel source). Document the pin choice in
   `harness/path_c/substrate_pin.md`.
2. `pip install -e .[substrate]` into `.venv312`. Verify
   `python -c "import pxr"` exits 0.
3. Capture baseline: `pytest tests/ -v --tb=no -q
   > harness/path_c/baseline_tests.txt` to confirm pre-surgery
   green count = 1,140 (or document the actual number if it has
   drifted).
4. Capture latency baseline: run the read-path microbenchmark
   exercised by `tests/test_brainstem/test_fidelity.py`; save
   median + p99 to `harness/path_c/baseline_latency.json`.

### Crucible Gate 0 — binary

- `python -c "import pxr"` exits 0 inside `.venv312`.
- `baseline_tests.txt` shows 1,140 green (or documented baseline
  number; any pre-existing red test is enumerated).
- `baseline_latency.json` exists and contains numerical median and
  p99 measurements.

A failure on any of the three halts. The memory-hypothesis
document is required to exist but its verdict does not gate Phase 1
entry.

---

## Phase 1 — Schema authoring (Architect-heavy)

### Architect output

1. **`schema/schema.usda`** — declares all 21 prim types from recon
   §1.
   - **IsA hierarchy.** Default candidate: parallel to containment
     (recon §3), with `BrainStage` as a typed root, container prims
     as a middle tier, leaf prims as the bottom tier. Each level's
     IsA parent is documented inline.
     `[NEEDS DECISION: is the IsA hierarchy strictly parallel to
     containment, or designed independently? Deep Think brief §3.1
     stress-tests this. Architect commits to one shape before
     handing to Forge.]`
   - **Typed attributes** per prim per recon §2 property counts.
   - **`allowedTokens`** enums for `SourceType`,
     `VerificationState`, `RetrievalPath`, `MotorGateStatus`,
     `ArcType`. Casing convention fixed here (Commandment 11).
   - **Codec-blocker fields declared `string`-typed by default**
     (Commandments 7, 8). Comment on each such attribute pointing
     to the codec function in the runtime tier.
2. **`schema/plugInfo.json`** — registers the `harlo` namespace.
   Lists 21 typeNames. No dependency on `MonetaMemory` plugin.
3. **`harness/path_c/schema_design.md`** — narrative
   justification:
   - Why this IsA shape (and what was rejected)
   - Why these `allowedTokens` enums (and what was rejected)
   - Token-casing decision and rationale
   - Naming inconsistency on `Provenance` resolved (rename to
     `ProvenancePrim` or accept the bare name; document the
     choice and any read-path consequences)
   - How collision with Pixar built-ins was checked (e.g., `Scope`,
     `Xform`, `Material` cannot be reused by the surgery)
   - How collision with Moneta's `MonetaMemory` was checked
     `[NEEDS DECISION: where to source Moneta's typeName list — a
     read-only checkout, a published artifact, or a manual
     enumeration? Architect picks before Phase 1 begins.]`

### Forge tasks

(none — Phase 1 is Architect-only authoring. Forge stages files
into the working tree only.)

### Crucible Gate 1 — binary

- Subprocess test passes:
  ```
  python -c "
  from pxr import Usd, Plug
  Plug.Registry().RegisterPlugins('schema/')
  s = Usd.Stage.CreateInMemory()
  for t in [<21 typeNames>]:
      s.DefinePrim(f'/test_{t}', t)
  "
  ```
  exits 0 in a fresh subprocess.
- Listing registered types via `Usd.SchemaRegistry()` contains all
  21 names.
- No collision with Pixar built-in typeNames.
- No collision with Moneta's `MonetaMemory`-namespaced typeNames
  (verified by name-diff against the source chosen in
  `schema_design.md`).

### **HUMAN REVIEW GATE — halt before Phase 2**

Joe reads `schema_design.md` and signs off in writing on:

- IsA hierarchy shape
- `allowedTokens` choices and casing convention
- Codec-blocker default (string sidecar)
- `Provenance` naming inconsistency resolution
- Moneta typeName collision check

Without this written sign-off, Phase 2 does not begin. The session
halts at Gate 1 even if the binary criteria pass.

---

## Phase 2 — Persistence layer

### Architect output

- **`harness/path_c/attribute_mapping.md`** — per-prim table
  mapping each Python `@dataclass` field to a USD attribute name +
  type. Codec notes inline (e.g., `TracePrim.sdr` →
  `string`-typed sidecar named `sdr_hex`, codec =
  `usd_lite.hex_sdr.sdr_to_hex / hex_to_sdr`).

### Forge tasks

1. New submodule `python/harlo/usd_lite/persistence/`:
   - `writer.py` — accepts a `BrainStage` dataclass, writes a
     real-USD `.usda` via `pxr.Usd.Stage`. **Imports `pxr` only
     here.**
   - `reader.py` — reads a real-USD `.usda`, returns a `BrainStage`.
   - `__init__.py` — exports `write()` and `read()`. Guards `pxr`
     import so absence raises a clear
     `[substrate] extra required` error.
2. The existing `usd_lite.serializer.parse / serialize` is
   orthogonal — both code paths exist; runtime tier still uses the
   regex parser; persistence layer uses real USD.

### Crucible Gate 2 — binary

- For each of the 21 prim types, `BrainStage` round-trip through
  `persistence.write` → `persistence.read` preserves all
  non-blocker fields under float-tolerant equality
  (`BrainStage.__eq__` already implements this).
- Codec-blocker fields (hex SDR, JSON-as-string blobs) round-trip
  via string sidecars per `attribute_mapping.md`.
- 1,140 tests still green (runtime tier untouched; sync layer not
  yet wired).

---

## Phase 3 — Sync layer

### Architect output

**`harness/path_c/sync_policy.md`** — per-prim policy table.

Default candidates (Architect confirms or revises before Forge
implements):

| Prim | Default policy | Rationale |
|------|----------------|-----------|
| `SessionPrim` | write-through | Low write rate, high consistency need (routing depends on it) |
| `GateStatusPrim` | write-through | Verification state must persist immediately to survive a crash mid-cycle |
| `MerkleRootPrim` | write-through | Audit hash; persist on update or audit chain breaks |
| `TracePrim` | checkpoint | High write rate; batch on session boundary to avoid hot-path stall |
| `CompositionLayerPrim` | checkpoint | Same write-rate profile as `TracePrim` |
| `SkillPrim` / `SkillsContainerPrim` | checkpoint | Updated by `skills/observer.py`; batch acceptable |
| `MultipliersPrim` | checkpoint | Calibration; rare writes; OK to batch |
| `IntakeHistoryPrim` | checkpoint | Append-mostly |
| `CognitiveProfilePrim` | checkpoint (inherit from contained leaves) | Container; matches its leaves |
| `Provenance` | inherits from parent `CompositionLayerPrim` | Nested-only emit |
| `InjectionPrim` / `InjectionContainerPrim` | `[NEEDS DECISION: pending Phase 5 finish-or-evict — if finished, default proposal: write-through to mirror `SessionPrim` consistency]` |
| `InquiryPrim` / `InquiryContainerPrim` | `[NEEDS DECISION: candidate write-behind — DMN hypotheses change frequently, can tolerate brief lag]` |
| `MotorPrim` / `MotorContainerPrim` | `[NEEDS DECISION: candidate write-through — basal ganglia gate state has safety implications]` |
| `AssociationPrim` / `CompositionPrim` / `ElenchusPrim` | inherit from contained leaves | Containers |
| `BrainStage` | inherit (root) | Root |

Architect picks final policy per `[NEEDS DECISION]` row before
Forge implements.

### Forge tasks

1. New submodule `python/harlo/usd_lite/sync/`:
   - `policy.py` — declarative table `{TypeName: Policy}` loaded
     from `sync_policy.md`. Validates that every typeName has a
     non-decision policy at module import time.
   - `dispatcher.py` — on every runtime mutation, dispatches per
     policy:
     - `write-through` calls `persistence.write` synchronously.
     - `write-behind` queues onto a per-prim background queue;
       drained on an explicit `flush()` or process-exit hook.
     - `checkpoint` defers; persists only on explicit `flush()`
       or session-boundary trigger.
2. Hot-path read API unchanged. Reads always hit the runtime tier;
   the sync layer is write-side only.

### Crucible Gate 3 — binary

- Hot-path read latency benchmark vs `baseline_latency.json` shows
  regression < 10% on **both** median and p99.
- Sync policy table covers all 21 typeNames; no `[NEEDS DECISION]`
  entries remain in `sync_policy.md`.
- 1,140 tests green.
- Round-trip fidelity preserved through the sync layer: write a
  mutation, force checkpoint via `flush()`, read back via
  `persistence.read`, equality holds.

If latency regresses > 10%: halt; sync policy redesigned before
proceeding to Phase 4.

---

## Phase 4 — Migration script

### Architect output

**`harness/path_c/migration_design.md`** — algorithm sketch:

1. Detect input format: regex header check (`#usda 1.0` followed
   by `def BrainStage` → old format) or `pxr.Usd.Stage.Open` probe
   for new format.
2. If old USD-Lite format: parse via existing
   `usd_lite.serializer.parse`, write via `persistence.write`.
3. If new real-USD format: no-op (idempotent).
4. Report per-prim migrated count, blockers encountered, codec
   conversions performed.

### Forge tasks

1. **`python/harlo/migrate_path_c.py`** — executable script. CLI:
   `python -m harlo.migrate_path_c <stage_path> [--dry-run]
   [--report <out.json>]`.
2. Update `migrate_v7.py` notes: the new script supersedes for
   v7 → v8-substrate; the v6 → v7 path is retained.

### Crucible Gate 4 — binary

- Script round-trips `data/hebbian_seeded.usda` (representative
  existing capture) without data loss vs current
  `usd_lite.parse` output.
- Idempotent: running the script on its own output produces an
  identical stage (`BrainStage.__eq__` true).
- 1,140 tests green.

---

## Phase 5 — Codec-blocker resolution

### Architect output

**`harness/path_c/blocker_decisions.md`** — one section per
blocker, decision logged with rationale:

1. Hex SDR
2. JSON-as-string blobs
3. `InjectionPrim` finish-vs-evict
4. Stale `cognitive_twin.usda` eviction
5. Asymmetric `arc_type` token convention

### Forge tasks (per blocker)

1. **Hex SDR on `TracePrim`.** Confirm `string`-sidecar default;
   port the `hex_sdr.py` codec call into `persistence/writer.py`
   and `persistence/reader.py`. Preserve the 512-char invariant.
2. **JSON-as-string blobs.** `co_activations`, `competitions`,
   `opinion`, `answer_embeddings` — confirm string sidecar; port
   `json.dumps(..., sort_keys=True)` round-trip. Sorted-keys
   discipline is required for round-trip equality.
3. **`InjectionPrim` / `InjectionContainerPrim` finish-or-evict.**
   Architect decides:
   - **Finish:** add `_serialize_injection_*` and
     `_build_injection_*` to `usd_lite/serializer.py`; add
     `persistence.write/read` coverage; add to `BrainStage`
     round-trip; ensure `tests/test_injection/test_injection.py`
     stays green.
   - **Evict:** delete `InjectionPrim`, `InjectionContainerPrim`,
     `BrainStage.injection` field; remove
     `tests/test_injection/test_injection.py` references; document
     the public-API change.

   `[NEEDS DECISION: finish or evict — Deep Think brief §3.5
   stress-tests this. Architect commits before Forge implements.]`
4. **Stale `data/stages/cognitive_twin.usda`.** Delete file. Note
   eviction in `blocker_decisions.md` referencing recon §1 and
   commit `f830aeb` (the package rename).
5. **Asymmetric `arc_type` token convention.** Architect picks
   casing (lower-case or upper-case); Forge updates both emitter
   (`usd_lite/serializer.py`) and parser; codifies in the
   `allowedTokens` declaration in `schema.usda`.

### Crucible Gate 5 — binary

- All 5 blockers resolved per `blocker_decisions.md`.
- Round-trip fidelity preserved.
- 1,140 tests green (note: the `InjectionPrim` decision may add
  or remove test count — any baseline change is documented).

---

## Phase 6 — Test repair + Crucible verification

### Architect output

(none — Architect's role concludes after Phase 5 sign-off.)

### Forge tasks

Address any test breakage from Phases 2–5. Expected scope:
minimal, because the runtime tier is preserved. Likely sources:

- `tests/test_usd_lite/test_serializer.py` — if asymmetric
  `arc_type` fix changed token casing.
- `tests/test_injection/test_injection.py` — if `InjectionPrim`
  evicted (delete) or finished (extend).
- New tests added: persistence round-trip per prim, sync policy
  enforcement, subprocess `SchemaRegistry` gate.

### Crucible Gate 6 — binary (FINAL)

- 1,140 tests green (or documented adjusted baseline from
  `InjectionPrim` decision).
- Subprocess `SchemaRegistry` gate green.
- Hot-path latency benchmark green: < 10% regression vs Phase 0
  baseline on median and p99.
- Round-trip fidelity per prim green.
- All 5 codec-blockers resolved per `blocker_decisions.md`.
- Branch `path-c-surgery` ready for squash commit.

On all green: Mile 3 single squash commit, push, open PR. Halt
and surface to Joe for review.

---

## Cross-phase notes

- **Branch hygiene:** all work on `path-c-surgery` only. No
  commits to `master` until PR merge.
- **Halt protocol:** any gate failure → freeze branch, document
  diagnosis in `harness/path_c/halt_log.md`, surface to Joe with
  a clear ask. Do not retry the same approach without a revised
  plan.
- **Architect / Forge / Crucible alternation:** within a phase,
  the three roles run sequentially. The same Claude Code session
  may play all three, but switches roles explicitly and stays in
  charter while in-role.
- **Memory hypothesis re-use:** if Phase 0 returned
  `[CONFIRMED-SHIPPED-AND-STRIPPED]`, Phase 1 Architect should
  inspect the stripped code as reference material before
  authoring `schema.usda` from scratch. It is *not* a substitute
  for the schema design narrative.
