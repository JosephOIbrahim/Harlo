# Mile 2 — Phase 2 Architect-as-Scout: `src/` Real-USD Inventory

**Role:** Architect-acting-as-scout (Commandment 1 + D12 mandatory) &nbsp;|&nbsp; **Date:** 2026-04-28
**Status:** Reconnaissance only. No mutations performed in scout pass.
**Authority:** D12 binding — Forge cannot write Phase 2 schema artifacts until this scout signs off.
**Repo:** `C:\Users\User\Harlo` &nbsp;|&nbsp; **Branch:** `harness-path-c`

---

## TL;DR

| Question | Answer |
|---|---|
| Files in `src/` that import `pxr`? | **3** — `cognitive_stage.py`, `engine_config.py`, `usd_bootstrap.py` |
| Files in `src/` that call `Usd.Stage` / `Sdf.Layer` directly? | **1** — `cognitive_stage.py` only |
| typeNames declared in `src/`? | **None** — `cognitive_stage.py` uses USD built-in `"Scope"` for every `DefinePrim` call |
| Attribute names declared in `src/` USD code? | **One** — `"data"` (single string-typed attr on every prim) |
| Relationship names declared? | **None** |
| Path scheme overlap with Phase 1 design's `/Brain/...`? | **None** — `src/` writes to `/state`, `/routing`, `/sessions`, `/delegates`, `/prediction`, `/memory`, `/projects` (root-level scopes, no `/Brain` ancestor) |
| Collision risk with Phase 1 design's 21 typeNames? | **Zero** |
| Collision risk with Phase 1 design's attribute names? | **Zero** (`"data"` is not used in Phase 1 schema) |
| Recommendation per D12? | **Stay separate** — no rewire, no eviction. Phase 2 Forge greenlit. |

**Forge greenlight: ✅ GRANTED.** Phase 2 may proceed to Architect implementation plan.

---

## 1. `src/` files inventory

`src/` contains 16 Python files (excluding `__pycache__`). Categorization by USD/pxr touch:

### 1.1 Hard pxr import (uses `from pxr import ...`)

| File | Import | What it does |
|---|---|---|
| `src/cognitive_stage.py` | `from pxr import Sdf, Usd` (line 21) | Sole real-USD writer/reader. Implements `CognitiveStage` class — drop-in for `MockUsdStage`. Stores `CognitiveObservation` JSON in time samples. |
| `src/usd_bootstrap.py` | `from pxr import Usd` (line 31) | Bootstrap shim — adds `C:\USD\26.03-exec` to `sys.path` and DLL directories so the vendored USD install is importable. Auto-runs on import. |
| `src/engine_config.py` | (no direct pxr API usage; references pxr in passing — verified by Phase 0 grep) | Engine config; the pxr reference is comment/string-level, not an API call. |

### 1.2 No pxr touch

Other 13 files (`__init__.py`, `bridge.py`, `cognitive_engine.py`, `consent.py`, `delegate_*.py`, `mock_cogexec.py`, `mock_usd_stage.py`, `observation_buffer.py`, `predict.py`, `schemas.py`, `stage_factory.py`, `train_predictor.py`, `trajectory_generator.py`, `validator.py`, `computations/`):

- Pure Python.
- Some reference USD concepts (`mock_usd_stage.py` is the in-memory mock that `cognitive_stage.py` is a drop-in for; `stage_factory.py` likely picks between mock and real-USD).
- **No `from pxr import` and no `Usd.Stage` / `Sdf.Layer` calls.**

These files are out of scope for Phase 2 collision concerns.

---

## 2. `src/cognitive_stage.py` — detailed scout (D12 mandatory)

333 lines. The complete pxr surface used by all of `src/`. Authored Sprint 4 Phase 1 (`7b9bcff`, 2026-03-30); two subsequent commits touched it (public release `a16b707`, package rename `f830aeb`).

### 2.1 typeName usage — exhaustive enumeration

Every `DefinePrim` call (3 sites):

| File:line | Call site | typeName argument |
|---|---|---|
| `cognitive_stage.py:89` | `self._stage.DefinePrim(path, "Scope")` (in `_init_hierarchy` for 12 root-level scopes) | `"Scope"` |
| `cognitive_stage.py:177` | `prim = sub_stage.DefinePrim(prim_path, "Scope")` (delegate sublayer write path) | `"Scope"` |
| `cognitive_stage.py:325` | `prim = self._stage.DefinePrim(prim_path, "Scope")` (in `_ensure_prim` general path) | `"Scope"` |

**Total typeNames in `src/`: 1 — `"Scope"` (USD built-in).**

### 2.2 Attribute usage — exhaustive enumeration

Every attribute name referenced (`GetAttribute` or `CreateAttribute`):

| File:line | Call | Attribute name | USD type |
|---|---|---|---|
| `cognitive_stage.py:103, 178` | `attr = self._ensure_data_attr(prim)` / `attr = prim.GetAttribute("data")` | `"data"` | `Sdf.ValueTypeNames.String` (when created at line 332) |
| `cognitive_stage.py:112, 194, 223, 255, 265, 282, 287, 330` | `prim.GetAttribute("data")` | `"data"` | (read-only; type matches above) |

**Total attribute names in `src/`: 1 — `"data"` (string-typed).**

The single `"data"` attribute holds JSON-serialized `CognitiveObservation` blobs (or arbitrary dicts) per time-sampled `exchange_index`. There is no per-prim type; everything is shape-less JSON inside a `Scope` prim.

### 2.3 Relationship usage

**None.** No `CreateRelationship` calls, no `Relationship` references.

### 2.4 Path scheme — exhaustive enumeration

`_init_hierarchy` (line 80–89) creates 12 fixed paths plus delegate paths created on demand:

```
/state
/state/momentum
/state/burnout
/state/energy
/state/injection
/state/allostatic
/routing
/sessions
/delegates
/prediction
/memory
/projects

# created on demand by author/author_to_sublayer:
<arbitrary path passed by caller>     # via _ensure_prim, also typed Scope

# delegate sublayer files:
data/stages/delegates/{delegate_id}.usda

# root file (note: rename artifact — comment says "cognitive_twin.usda",
# code says "harlo.usda" at line 70):
data/stages/harlo.usda
```

### 2.5 Layer/sublayer composition

- Root stage: single `.usda` file (`data/stages/harlo.usda`) with all `_init_hierarchy` Scopes + time-sampled `data` attrs.
- Delegate sublayers: separate `.usda` files added to root's `subLayerPaths` list. Composition priority: last-appended wins.
- `compose()` method walks all sublayers in priority order to materialize a `dict[(prim_path, exchange_index), value]`.

### 2.6 In-memory vs on-disk modes

- `in_memory=True`: `Usd.Stage.CreateInMemory()` — used by tests.
- `in_memory=False`: opens or creates `data/stages/harlo.usda` and saves to disk.

### 2.7 Note on stale on-disk artifacts

`data/stages/cognitive_twin.usda` exists on disk but `cognitive_stage.py` writes to `harlo.usda` (post-rename). The on-disk `cognitive_twin.usda` is **truly stale** — produced before the rename, never reproduced by current code. Recon §1 flagged this; D6 confirms. **Eviction is Phase 5 scope (Commandment 10), not Phase 2.**

---

## 3. Cross-check vs Phase 1 design (`design/mile_2_phase_1_schema_design.md`)

### 3.1 typeName collision check

Phase 1 design declares **21 typeNames**: `HarloPrim` (abstract), `HarloContainer` (abstract), `BrainStage`, `AssociationPrim`, `CompositionPrim`, `ElenchusPrim`, `InquiryContainerPrim`, `MotorContainerPrim`, `SkillsContainerPrim`, `CognitiveProfilePrim`, `TracePrim`, `CompositionLayerPrim`, `Provenance`, `GateStatusPrim`, `MerkleRootPrim`, `SessionPrim`, `InquiryPrim`, `MotorPrim`, `SkillPrim`, `MultipliersPrim`, `IntakeHistoryPrim`.

`src/` declares **1 typeName**: `"Scope"` (USD built-in).

**Set intersection: ∅. Zero collisions.**

`"Scope"` is registered by USD core itself, not by Harlo's plugin. Phase 1's 21 typeNames are namespaced under `harlo` plugin. The two coexist without conflict.

### 3.2 Attribute name collision check

Phase 1 design declares attributes per prim type; the full attribute name set across all 19 concrete types (per Phase 1 design §2.3):

```
sdr_hex, content_hash, strength, last_accessed,
co_activations_json, competitions_json,
hebbian_strengthen_mask_hex, hebbian_weaken_mask_hex,
arc_type, opinion_json, timestamp, permanent,
source_type, origin_timestamp, event_hash, session_id,
verification_state, cycle_count, last_verified,
root_hash, trace_count,
current_session_id, exchange_count,
surprise_rolling_mean, surprise_rolling_std, last_query_surprise,
last_retrieval_path,
hypothesis, confidence,
action, gate_status,
trace_count, first_seen, last_seen, growth_arc, hebbian_density,
surprise_threshold, reconstruction_threshold, hebbian_alpha,
allostatic_threshold, detail_orientation,
last_intake, intake_version, answer_embeddings_json
```

`src/` declares **1 attribute name**: `"data"` (string-typed).

**Set intersection: ∅. Zero attribute-name collisions.**

(`"data"` is a generic name, but it doesn't appear in Phase 1's set. If Phase 2 Forge writes a `data` attr anywhere on a Harlo prim, that would collide; the design doesn't.)

### 3.3 Path-scheme collision check

Phase 1 design (§3): all paths rooted at `/Brain`.

```
/Brain
/Brain/Association
/Brain/Association/Traces/<trace_id>
/Brain/Composition
/Brain/Composition/Layers/<layer_id>
/Brain/Composition/Layers/<layer_id>/provenance
/Brain/Elenchus
/Brain/Elenchus/GateStatus
/Brain/Elenchus/MerkleRoot
/Brain/Session
/Brain/Inquiry
/Brain/Inquiry/hypothesis_<i>
/Brain/Motor
/Brain/Motor/action_<i>
/Brain/Skills
/Brain/Skills/<domain>
/Brain/CognitiveProfile
/Brain/CognitiveProfile/Multipliers
/Brain/CognitiveProfile/IntakeHistory
```

`src/` writes to: `/state`, `/state/...`, `/routing`, `/sessions`, `/delegates`, `/prediction`, `/memory`, `/projects` (plus arbitrary caller-supplied paths).

**Set intersection: ∅. Zero path-scheme collisions.** The two subsystems write to **disjoint USD prim trees**. They could coexist in the same `.usda` file without conflict (Phase 1 design's writer would write under `/Brain`; Sprint 4's writer continues to write to its own scopes if reactivated).

### 3.4 Storage-file collision check

| Subsystem | Output file |
|---|---|
| Phase 1 design (Forge in Phase 2 will write to) | `[NEEDS DECISION at Phase 2 implementation: which file path?]` — design §3 says root prim `/Brain` but doesn't pin a filename. Defaulting to `data/stages/brain.usda` is the obvious choice; could collide with Sprint 4's `harlo.usda` if both are reactivated. |
| Sprint 4 `src/cognitive_stage.py` | `data/stages/harlo.usda` |
| Stale demo data | `data/stages/cognitive_twin.usda` (no current writer; eviction in Phase 5) |

**[NEEDS DECISION] surfaced for Phase 2 Architect implementation plan:** which `.usda` file does the new persistence-layer writer use? Architect proposes `data/stages/brain.usda` in §4 below.

---

## 4. Storage-file decision (Phase 2 implementation plan input)

**Architect proposal:** Phase 2 Forge writes to `data/stages/brain.usda` (matching the `/Brain` root prim convention). Rationale:

- Mirrors the prim-path scheme — file is named for its root prim, easy filesystem-level identification.
- Avoids any conceivable name collision with Sprint 4's `harlo.usda` even if both subsystems are simultaneously active.
- `cognitive_twin.usda` (stale) and `harlo.usda` (Sprint 4) are pre-existing names; `brain.usda` is the third, distinct, path-C-specific name.
- D5 evicted Injection from disk; the new file holds 19 concrete prim types under `/Brain` as Phase 1 design specifies.

**Locked in this scout report.** Phase 2 Architect implementation plan adopts unless human gate overrules.

---

## 5. Recommendation per D12 — rewire vs separate

**D12 mandates:** "Recommendation: rewire `src/cognitive_stage.py` to consume the new schema, OR document why it stays separate."

**Recommendation: STAY SEPARATE.**

### 5.1 Reasons

1. **Sprint 4 code is dormant** (D6 verdict —
   `CONFIRMED-SHIPPED-AND-PRESENT-BUT-DORMANT`). No production
   traffic touches `CognitiveStage` in current `python/harlo/`
   code paths. Rewiring would consume Phase 2 budget for code with
   zero current consumers.

2. **Sprint 4 uses a fundamentally different schema model** —
   shape-less JSON blobs in a single `data` attr on type-less
   `Scope` prims. The Path C model is type-aware (21 typed prim
   classes with typed attributes per prim). Rewiring would require
   either (a) re-authoring `CognitiveStage` to use the new prim
   classes (incompatible with the JSON-blob storage assumption) or
   (b) wrapping the new schema with a JSON-blob adapter
   (defeats the purpose of typed schemas).

3. **Path C's separation of concerns** holds: real-USD persistence
   layer at `/Brain/...` is the canonical truth; runtime tier at
   `python/harlo/usd_lite/` is the fast in-memory tier. Sprint 4
   is structurally a third tier (legacy real-USD with shape-less
   storage) — it doesn't fit the persistence-layer role and
   shouldn't be promoted to it.

4. **Out of scope for Step 3.** D1's 2.5-week wall-clock cap
   (halt 2026-05-15) is for the codeless schema surgery, not for
   modernizing legacy `src/` code. Rewiring is a separate
   workstream; defer.

5. **Eviction is also out of scope.** Removing `src/cognitive_stage.py`
   would break `tests/test_sprint4/*` (3 test files, ~30+ tests
   in the 1,133 baseline). Test repair is Phase 6 work, not Phase 2.

### 5.2 What "stay separate" means concretely

- `src/cognitive_stage.py` is **not modified** by any phase 2/3/4 work this session.
- `tests/test_sprint4/*` is **not modified**.
- Phase 2 Forge writes the new persistence layer in
  `python/harlo/usd_lite/persistence/` (per Phase 1 design §2 / 03_HANDOFF Phase 2) using `from pxr import Sdf, Usd` independently of Sprint 4's bootstrap pattern (substrate `usd-core 26.5` from PyPI is sufficient; Sprint 4's `usd_bootstrap.py` is not invoked).
- The two pxr-using subsystems coexist in `.venv312` without interference because USD's `Plug.Registry` is global — both subsystems see all registered plugins (including Harlo's new one and any USD built-ins).

### 5.3 Future work (not this session, not this surgery)

- **Post-Step-6 candidate:** rewire `src/cognitive_stage.py` to consume the new schema. Tracked as future-work item in `harness/path_c/tracking_issues.md` (TI-002 candidate; not filed yet).
- **Alternative future work:** evict `src/` entirely once test_sprint4 tests are migrated to the new persistence layer. Even larger workstream.

---

## 6. Test impact assessment (D12 secondary)

Sprint 4 tests in `tests/test_sprint4/`:
- `test_cognitive_stage.py` (227 lines per Sprint 4 commit `7b9bcff`)
- `test_backend_parity.py`
- `test_live_usda.py`

These tests exercise `src/cognitive_stage.py` directly. Per Phase A measurement (post-`[dev]` install), they are part of the **1,133 green baseline** (D14).

**Stay-separate recommendation preserves these tests as-is.** Phase 2 Forge does not touch `tests/test_sprint4/`.

If `src/cognitive_stage.py` is later rewired or evicted, those 30+ tests would need migration. That work is out of Path C scope.

**Phase 2 Crucible gate criterion: 1,133 green still holds after schema/persistence-layer authoring.** The Sprint 4 test subset must remain green; Phase 2 mutations should not affect it because Phase 2 doesn't touch `src/` or any test the Sprint 4 suite depends on.

---

## 7. Forge greenlight conditions

D12 requirement met. Conditions for Phase 2 Forge to proceed:

| Condition | Status |
|---|---|
| `src/` files inventoried for pxr usage | ✅ §1 |
| `src/cognitive_stage.py` typeNames enumerated | ✅ §2.1 — only `"Scope"` |
| `src/` attribute names enumerated | ✅ §2.2 — only `"data"` |
| `src/` relationship names enumerated | ✅ §2.3 — none |
| Path-scheme overlap check | ✅ §3.3 — none |
| typeName collision vs Phase 1 design | ✅ §3.1 — zero |
| Attribute-name collision vs Phase 1 design | ✅ §3.2 — zero |
| Storage-file collision check | ⚠️ §3.4 — surfaced [NEEDS DECISION]; Architect proposes `data/stages/brain.usda` (§4) |
| D12 rewire-vs-separate recommendation | ✅ §5 — STAY SEPARATE with documented reasons |
| Test impact assessed | ✅ §6 — Sprint 4 tests preserved |

**Forge greenlight: ✅ GRANTED.** Phase 2 Architect implementation plan may be authored next, locking the storage-file decision (§3.4) and referencing the Phase 1 design as the sole authoritative spec.

---

## 8. What scout did NOT cover (and why that's OK)

- **Per-attribute USD-type validation** (e.g., does `Sdf.ValueTypeNames.String` actually exist in `usd-core 26.5`?) — Forge verifies at implementation time; scout's job is convention discovery, not API verification. Phase 1 design §2 uses standard USD types; no exotic types declared.
- **`generatedSchema.usda` shape** — output of `usdGenSchema --codeless`, generated from `HarloSchema.usda`. Not predictable from scout alone; Forge produces and Crucible validates round-trip.
- **`Plug.Registry` runtime behavior** — exercised by the subprocess SchemaRegistry test specified in Phase 1 design §8. Crucible runs that test in Phase 2 gate.

These are correctly Forge / Crucible concerns, not scout concerns.

---

## 9. Architect-as-scout exits role

Next: Architect-as-Architect produces
`design/mile_2_phase_2_implementation.md` — the Phase 2
implementation plan that Forge consumes. That plan locks the
storage-file decision (§3.4 → `data/stages/brain.usda`) and
references Phase 1 design as the sole authoritative spec for the
schema artifacts.

*End of Phase 2 src/ scout. Forge greenlit. Architect continues to implementation plan.*
