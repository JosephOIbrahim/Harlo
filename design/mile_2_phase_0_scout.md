# Mile 2 — Phase 0 Scout

**Role:** Architect-acting-as-scout (Commandment 1 — first action of Phase 0).
**Status:** Reconnaissance only. No mutations performed in scout pass.
**Authority:** Findings inform Forge actions in this same Phase 0; binding for Phase 1 design.
**Repo:** `C:\Users\User\Harlo` &nbsp;|&nbsp; **Branch:** `harness-path-c` &nbsp;|&nbsp; **Date:** 2026-04-28

---

## TL;DR

| Question | Answer |
|---|---|
| Memory hypothesis (did Sprint 4 pxr.Usd.Stage ship?) | **CONFIRMED-SHIPPED-AND-PRESENT-BUT-DORMANT** — refines the three options in 03_HANDOFF |
| pxr install state in `.venv312`? | Not pip-installed. Vendored at `C:\USD\26.03-exec\lib\python\pxr` (Sprint 4 path); Sprint 4's `src/usd_bootstrap.py` consumes it via `sys.path.insert` + `os.add_dll_directory`. |
| Moneta repo locatable? | Yes: `C:\Users\User\Moneta`. |
| Moneta declared typeNames? | One: **`MonetaMemory`** (alias `MonetaMonetaMemory`). |
| Collision with Harlo's 21 prims? | **Zero collisions.** None of Harlo's typeNames match `MonetaMemory`/`MonetaMonetaMemory`. |
| Recon error to surface? | Yes — Mile 1 recon §5 said "no pxr imports anywhere" but missed `src/` (scope was `python/harlo/`). Sprint 4 pxr code is still present. |
| Test count baseline confirmed? | **Not yet** — deferred to Forge phase (`pytest --collect-only`). |
| Latency baseline captured? | **Not yet** — deferred to Forge phase. |
| Hard blocker found? | **No.** Several scope clarifications surfaced (see §6). |

---

## 1. Memory hypothesis — verdict

The 03_HANDOFF Phase 0 question was: did Sprint 4's `pxr.Usd.Stage` work
ship and get stripped, or never ship? The user override gave three
allowed verdicts: `CONFIRMED | CONFIRMED-NEVER | AMBIGUOUS`. None
exactly fits — refining to **CONFIRMED-SHIPPED-AND-PRESENT-BUT-DORMANT**.

### Evidence

`git log --all --oneline -i --grep="pxr|usd-core|usdGenSchema|OpenUSD"`
returned five commits, three of which directly bear on the question:

| Commit | Date | Subject |
|---|---|---|
| `8658777` | 2026-03-?? | `Sprint 2 Phase 0: USD 26.03 build — Circuit Breaker triggered` |
| `7b9bcff` | 2026-03-30 12:29:29 | `Sprint 4 Phase 1: CognitiveStage — real pxr.Usd.Stage` |
| `0b4973d` | 2026-03-30 12:30:34 | `Sprint 4 Phase 2: Backend swap — all tests pass on real USD` |
| `bb96d43` | 2026-03-30 12:31:34 | `Sprint 4 Phase 3: Real .usda verified — Cognitive Twin is USD` |
| `bba7a31` | 2026-03-30 12:44:21 | `Sprint 5 Phase 1+2: Engine wired to real USD + graceful degradation` |

`git log -- src/cognitive_stage.py src/usd_bootstrap.py` shows only
two commits that touched these files: the public-release commit
`a16b707` (2026-04-01) and the package rename `f830aeb` (2026-04-03).
No deletion commit exists.

**Current state of those files:**
- `src/cognitive_stage.py` line 21: `from pxr import Sdf, Usd` — **present**.
- `src/usd_bootstrap.py` lines 30-34: `from pxr import Usd` — **present**.
- `src/engine_config.py` references pxr — **present**.
- `tests/test_sprint4/{test_cognitive_stage.py, test_backend_parity.py, test_live_usda.py}` — **present**.

These six files contain real pxr usage. They are dormant only because
`pxr` is not pip-installed in `.venv312`.

### Why this matters for the harness

03_HANDOFF Phase 0 expected one of: stripped (clean slate), never-shipped
(clean slate), or ambiguous (block). The actual state is "present but
dormant" — neither stripped nor active. **Implications:**

- Phase 0 Forge must decide: install via pip (`usd-core`), reuse the
  vendored install at `C:\USD\26.03-exec`, or both. **Default proposal:
  pip-install `usd-core` for the harness's `[substrate]` extra.** The
  vendored install is per-machine; pip is portable.
- Phase 5 Commandment 10 says evict `data/stages/cognitive_twin.usda`.
  That file is written by `src/cognitive_stage.py`'s `def Scope` blocks
  (recon §1 noted this style; this scout confirms the writer).
  **Eviction is destructive of the dormant Sprint 4 stack** — flagging
  for Architect attention in Phase 5 (out of this session).
- Test baseline at Phase 0 may shift once `pxr` is pip-installed, because
  `tests/test_sprint4/*` may suddenly start being collected/passing/
  failing where they were previously skipped.

### Recon error correction

Mile 1 `recon/harlo-schema-recon.md` §5 stated "no `pxr` imports found"
and "no `Sdf.Schema`/`UsdSchemaRegistry`/`usdGenSchema` matches." That
claim is **scope-bounded correct**: my Mile 1 grep was scoped to
`python/harlo/` (the new package root). Across the whole repo (`src/`
+ `python/`), pxr imports exist as documented above. The Path C
surgery still operates on `python/harlo/usd_lite/` only — the recon's
schema-surgery scope conclusions stand — but the global "no pxr"
phrasing was inaccurate and is corrected here.

---

## 2. pxr install state in `.venv312`

- Python: **3.12.10** (`.venv312/pyvenv.cfg`).
- `.venv312/Lib/site-packages/`: **no `pxr`/`Usd`/`Sdf`/`opentime` dirs**.
  Confirmed by glob.
- Vendored install: `C:\USD\26.03-exec\lib\python\pxr` exists. Sprint 4's
  `src/usd_bootstrap.py` adds this to `sys.path` and registers DLL
  directories on import.

**For Phase 0 Forge: `pip install -e .[substrate]` should pull
`usd-core>=24` from PyPI** (covers Python 3.12). Latest stable on
PyPI is `usd-core` 24.x as of cutoff; harness's `[substrate]` extra
will pin a tested version (Forge writes `harness/path_c/substrate_pin.md`).

[NEEDS VERIFICATION in Forge: that `usd-core` from PyPI imports cleanly
on Python 3.12.10 + Windows. Pre-built wheels exist; should be
straightforward.]

---

## 3. Moneta — collision check (D3)

### Repo location

`C:\Users\User\Moneta` exists. Top-level files include the full Moneta
codeless-schema harness pattern (`KICKOFF_codeless_schema.md`,
`EXECUTION_constitution_codeless_schema.md`,
`HANDOFF_codeless_schema_moneta.md`, `DEEP_THINK_BRIEF_codeless_schema.md`,
`SURGERY_complete_codeless_schema.md`, `SCHEMA_read_path_audit.md`).
**This is the precedent the Path C harness was modeled on.** Useful as
structural reference for Phase 1 design.

### Schema artifacts

`C:\Users\User\Moneta\schema\` contains:
- `MonetaSchema.usda`
- `plugInfo.json`
- `generatedSchema.usda`

### plugInfo.json contents (verbatim)

```json
{
    "Plugins": [
        {
            "Info": {
                "Types": {
                    "MonetaMonetaMemory": {
                        "alias": { "UsdSchemaBase": "MonetaMemory" },
                        "autoGenerated": true,
                        "bases": ["UsdTyped"],
                        "schemaIdentifier": "MonetaMemory",
                        "schemaKind": "concreteTyped"
                    }
                }
            },
            "LibraryPath": "",
            "Name": "moneta",
            "ResourcePath": ".",
            "Root": ".",
            "Type": "resource"
        }
    ]
}
```

### Collision check vs Harlo's 21 prim types

Moneta declares **one** typeName: `MonetaMemory` (with prefixed alias
`MonetaMonetaMemory` for the `<libraryName><className>` C++-style
identifier).

Harlo's 21 declared typeNames per recon §1 (with D5 evictions noted):
`BrainStage`, `Provenance`, `TracePrim`, `CompositionLayerPrim`,
`GateStatusPrim`, `MerkleRootPrim`, `SessionPrim`, `InquiryPrim`,
`MotorPrim`, `SkillPrim`, `MultipliersPrim`, `~~InjectionPrim~~` (D5),
`IntakeHistoryPrim`, `AssociationPrim`, `CompositionPrim`, `ElenchusPrim`,
`InquiryContainerPrim`, `MotorContainerPrim`, `SkillsContainerPrim`,
`~~InjectionContainerPrim~~` (D5), `CognitiveProfilePrim`.

Net: **19 typeNames** declared in Harlo's `schema.usda` after D5.

**Collision result: NONE.** No member of Harlo's set matches
`MonetaMemory` or `MonetaMonetaMemory` under exact-match or
prefix-disambiguation rules. Confirmed clean.

### Moneta as structural reference

`MonetaSchema.usda` shape (lines 1-57) — the codeless idiom Harlo's
Phase 1 will mirror at scale:

```usda
#usda 1.0
(
    subLayers = [@usd/schema.usda@]
)

over "GLOBAL" (
    customData = {
        string libraryName = "moneta"
        string libraryPath = "./"
        bool skipCodeGeneration = true
    }
)
{
}

class MonetaMemory "MonetaMemory" (
    inherits = </Typed>
    customData = {
        string className = "MonetaMemory"
        string schemaKind = "concreteTyped"
    }
    doc = "..."
)
{
    string payload (doc = "...")
    float utility (doc = "...")
    int attendedCount (doc = "...")
    float protectedFloor (doc = "...")
    double lastEvaluated (doc = "...")
    token priorState (
        allowedTokens = ["volatile", "staged_for_sync", "consolidated", "pruned"]
        doc = "..."
    )
}
```

Key idioms to carry into Harlo's `HarloSchema.usda`:
- `subLayers = [@usd/schema.usda@]` to inherit USD base schema
- `over "GLOBAL"` declaring `libraryName`/`libraryPath`/`skipCodeGeneration`
- `class TypeName "TypeName" (inherits = </Typed>, customData = {...})`
- `token <name> (allowedTokens = [...])` for enum-typed attributes
- Inline `doc = "..."` per attribute

`plugInfo.json` idiom: each typeName as `{<LibraryName><ClassName>: {...}}`,
`alias.UsdSchemaBase = <ClassName>`, `bases = ["UsdTyped"]`,
`schemaKind = "concreteTyped"`.

---

## 4. Containment graph — confirmed for Phase 1 IsA design (D2)

Per Mile 1 recon §3, with D5 evictions removed:

```
BrainStage  (root, 8 children — 9 minus injection)
├── AssociationPrim
│   └── dict[str, TracePrim]
├── CompositionPrim
│   └── dict[str, CompositionLayerPrim]
│                  └── Optional[Provenance]   (nested-emit child)
├── ElenchusPrim
│   ├── Optional[GateStatusPrim]
│   └── Optional[MerkleRootPrim]
├── Optional[SessionPrim]                     (root-level field)
├── InquiryContainerPrim
│   └── list[InquiryPrim]
├── MotorContainerPrim
│   └── list[MotorPrim]
├── SkillsContainerPrim
│   └── dict[str, SkillPrim]
└── CognitiveProfilePrim
    ├── MultipliersPrim
    └── IntakeHistoryPrim

EVICTED FROM SCHEMA.USDA per D5 (retained in runtime tier only):
    InjectionContainerPrim → list[InjectionPrim]
```

D2 says IsA hierarchy mirrors this. Phase 1 design will lift each
node into a `class TypeName "TypeName" (inherits = </Typed>, ...)`
declaration. Containment edges become typed attributes (when scalar)
or relationships (when reference-y).

---

## 5. Enum types confirmed for `allowedTokens` (D2 + Commandment 11)

Per `python/harlo/usd_lite/prims.py` and `arc_types.py`:

| Enum | Members | Used by |
|---|---|---|
| `SourceType` | `user_direct`, `external_reference`, `system_inferred`, `hebbian_derived`, `intake_calibrated` | `Provenance.source_type` |
| `VerificationState` | `trusted`, `contested`, `refuted`, `pending` | `GateStatusPrim.verification_state` |
| `RetrievalPath` | `system_1`, `system_2` | `SessionPrim.last_retrieval_path` |
| `MotorGateStatus` | `inhibited`, `approved`, `executing` | `MotorPrim.gate_status` |
| `ArcType` | `local`, `inherit`, `variant`, `reference`, `payload`, `sublayer` (lower-case per Commandment 11 fix) | `CompositionLayerPrim.arc_type` |

Commandment 11 (asymmetric `arc_type` casing): emitter currently writes
`arc_type.name.lower()`; parser reads via `ArcType[name.upper()]`.
**Phase 1 fix proposal: lower-case in the schema's `allowedTokens`,**
since the emitter already produces lower-case and that's what's on
disk in `data/hebbian_seeded.usda`. Parser update is Forge work in a
later phase.

---

## 6. Scope clarifications surfaced (do not silently expand scope — Architect rule)

These are flagged for human attention, not improvised through:

1. **`src/` directory contains a parallel, dormant Sprint 4 USD stack.**
   Path C surgery targets `python/harlo/usd_lite/`. `src/` is out of
   scope per Mile 1's read of the codebase. But because Phase 5
   Commandment 10 evicts `data/stages/cognitive_twin.usda` (which is
   written by `src/cognitive_stage.py`), the eviction will silently
   break `src/` — flagging now so the Architect can decide in a future
   phase whether to (a) leave `src/` untouched and accept its tests
   stay skipped, (b) evict `src/` along with the data file, or (c)
   modernize `src/` onto the new schema. **Out of this session's scope;
   surfaced for Mile 2 / Phase 5 awareness.**

2. **Memory hypothesis verdict doesn't fit the three-option enum.**
   User override said "CONFIRMED | CONFIRMED-NEVER | AMBIGUOUS". The
   actual state is "shipped-and-still-present-but-dormant". Treating
   as **CONFIRMED-SHIPPED-AND-PRESENT-BUT-DORMANT** (a refinement of
   CONFIRMED). The Architect logs this verdict in
   `harness/path_c/memory_hypothesis.md` (next artifact) so reviewers
   can object if they prefer one of the strict three options.

3. **Test baseline of 1,140 may shift after pxr install.**
   `tests/test_sprint4/*` (3 files) currently can't import pxr and
   would skip/error. After Phase 0 Forge installs `usd-core`, they
   may run. The "1,140" baseline number from Mile 1 was captured
   without pxr. Phase 0 Forge captures a NEW baseline post-install;
   any delta is documented as a blocker per the override.

4. **`pip install .[substrate]` may need to pin a USD version that
   doesn't conflict with the vendored 26.03-exec.** Both could
   coexist; pip-installed `usd-core` would supersede the bootstrap
   path. The Sprint 4 bootstrap activates only when `src/` modules
   are imported, which doesn't happen during `python/harlo/` test
   runs. Should be fine but flagged.

5. **`schema.usda` filename: `HarloSchema.usda` vs `schema.usda`.**
   Moneta uses `MonetaSchema.usda`. 03_HANDOFF says `schema/schema.usda`.
   **[NEEDS DECISION at Phase 1 design]** — propose `schema/HarloSchema.usda`
   for parallel naming with Moneta; Phase 1 design will pick.

---

## 7. Scout-only artifact list

- `design/mile_2_phase_0_scout.md` (this file) — recon findings
- `harness/path_c/memory_hypothesis.md` (next, Architect output) —
  written immediately after this scout artifact

## 8. Forge tasks queued for next role transition

When ENTERING FORGE PHASE:
1. Edit `pyproject.toml` to add `[project.optional-dependencies] substrate = ["usd-core>=24"]` (exact pin TBD).
2. Write `harness/path_c/substrate_pin.md` documenting the pin.
3. `pip install -e .[substrate]` in `.venv312`; verify `python -c "import pxr"` exits 0.
4. `pytest tests/ -v --tb=no -q > harness/path_c/baseline_tests.txt`; capture green count + any pre-existing red.
5. Capture latency baseline → `harness/path_c/baseline_latency.json` (median + p95 of `tests/test_brainstem/test_fidelity.py` read-path microbenchmark or equivalent).

## 9. Crucible gate criteria for Phase 0 (per session override)

Verifying after Forge work:
- [ ] `pip install -e .[substrate]` exited 0
- [ ] `python -c "import pxr"` exits 0
- [ ] Moneta `plugInfo.json` located and read (DONE this scout)
- [ ] Moneta typeNames enumerated and recorded (DONE this scout: `MonetaMemory` / `MonetaMonetaMemory`)
- [ ] Recon hypothesis verdict logged (TODO: Architect writes `memory_hypothesis.md`)
- [ ] Baseline test count recorded (delta from 1,140 documented if any)
- [ ] Hot-path read latency p50/p95 captured

*End of scout. Architect-acting-as-scout exits role. Next: write
`harness/path_c/memory_hypothesis.md`, then ENTER FORGE PHASE.*
