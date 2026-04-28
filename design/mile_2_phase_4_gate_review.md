# Mile 2 — Human Review Gate (After Phase 4, Before Phase 5)

**Date:** 2026-04-28 &nbsp;|&nbsp; **Branch:** `harness-path-c` &nbsp;|&nbsp; **Session:** Phases 2–4
**Wall-clock:** ~3.5 h (8 h soft cap; 4.5 h budget remaining)
**Commits this session:** 3 internal phase-boundary commits (`052a00b`, `99ac1ea`, `775a92a`); push at session close after this gate.

---

## TL;DR

Phases 2 (schema authoring), 3 (sync layer), and 4 (migration script) are complete and Crucible-signed. **All three Crucible gates passed.** Test baseline grew from 1,133 (D14) to **1,170** (+37 net-positive across the three phases). Three Forge clarifications of Phase 1 design surfaced for human signoff (C1, C2, C3). Phase 5 (codec-blocker resolution) is deferred to the next session per the hard gate.

---

## Phase summaries

### Phase 2 — Schema authoring (Crucible Gate 2: ✅ PASS)

- **Architect-as-scout** (per D12) inventoried `src/` for real-USD usage. Found `src/cognitive_stage.py` uses generic `"Scope"` typeName + single `"data"` string attr; **zero typeName / attr / path collisions** with Phase 1 design's 21 typeNames. Recommendation: stay separate (no rewire, no eviction). Captured in `design/mile_2_phase_2_scout_src.md`.
- **Architect** produced `design/mile_2_phase_2_implementation.md`. Locked storage filename: `data/stages/brain.usda`.
- **Forge** authored:
  - `schema/HarloSchema.usda` (codeless schema, 21 prim types, 5 enums with lower-case allowedTokens, D5 evictions honored, D10 Provenance as singleApplyAPI)
  - `schema/plugInfo.json` (harlo namespace, 21 type entries)
  - `schema/generatedSchema.usda` (hand-authored compiled form)
  - `python/harlo/usd_lite/persistence/{__init__,writer,reader}.py` (real-USD reader/writer at the boundary)
  - `tests/test_path_c/{test_schema_registry_gate,test_persistence_roundtrip}.py` (11 tests)
- **Crucible** verified end-to-end plugin registration via subprocess test. All 21 typeNames resolve; `MonetaMemory` not visible (no collision); USD `Xform` still resolvable. Round-trip fidelity per prim confirmed.
- **Net-positive:** +11 tests.

### Phase 3 — Sync layer (Crucible Gate 3: ✅ PASS)

- **Architect** produced `design/mile_2_phase_3_sync_layer.md`. Defined three concrete strategies (write_through, checkpoint, write_behind-stub) and INHERIT resolution for containers. Per-prim policy table closed all D4 [NEEDS DECISION] items.
- **Forge** authored:
  - `python/harlo/sync/{__init__,policy,write_through,checkpoint}.py`
  - `tests/test_sync/{test_policy_table,test_write_through,test_checkpoint}.py` (20 tests)
- **Caught and fixed Rule 1 violation** (literal `while True` in a docstring) via the compliance suite. Fixed forward (Cmd 7): rephrased docstring; control flow already used a bounded `for` loop.
- **Crucible Gate 3 latency check:** -4.84% p50, -3.55% p95 vs Phase 0 baseline (improved within run-to-run variance; runtime tier unchanged). <10% regression criterion green.
- **Net-positive:** +20 tests.

### Phase 4 — Migration script (Crucible Gate 4: ✅ PASS)

- **Architect** produced `design/mile_2_phase_4_migration.md`. Two-phase format detection: `Usd.Stage.Open` probe → fallback text pattern. Dispatch: old → migrate, new → no-op (idempotent), unknown → exit 1.
- **Forge** authored:
  - `python/harlo/migrate_path_c.py` (executable module + CLI)
  - `tests/test_migrate_path_c/test_migration.py` (6 tests including CLI smoke)
- **Migration validated against real fixture:** `data/hebbian_seeded.usda` migrates round-trip with **16 TracePrims** preserved, **81 codec conversions** (hex SDR + JSON sidecars), under `BrainStage.__eq__` equality.
- **C3 surfaced during this phase** (see "Forge clarifications" §3 below).
- **Net-positive:** +6 tests.

### Cumulative net-positive

| Phase | New tests | Cumulative |
|---|---|---|
| Pre-session (D14 baseline) | 1,133 | 1,133 |
| Phase 2 | +11 | 1,144 |
| Phase 3 | +20 | 1,164 |
| Phase 4 | +6 | 1,170 |

**+37 tests added; 0 lost.** Commandment 2 satisfied.

---

## Decisions applied under D-block authority

This session executed against the locked decisions in `harness/path_c/05_DECISIONS.md` (D1–D5) and `06_DECISIONS_PHASE_1.md` (D6–D14). Specific applications:

| Decision | Phase | How applied |
|---|---|---|
| **D2** — IsA parallel-to-containment | Phase 2 | 3-tier hierarchy: `Typed → HarloPrim (abstract) → {HarloContainer (abstract), leaves}` declared in `HarloSchema.usda`. |
| **D3** — Moneta `plugInfo.json` collision check | Phase 2 (scout) | `MonetaMemory` confirmed sole Moneta typeName; zero collision with Harlo's 21. Subprocess gate verifies non-visibility. |
| **D4** — Sync policies for orphan prims | Phase 3 | `MotorPrim → write_through` (safety), `InquiryPrim → checkpoint`, codified in `policy.POLICY_TABLE`; tests pin both. |
| **D5** — Injection evicted from disk | Phase 2 | `InjectionPrim` and `InjectionContainerPrim` NOT declared in schema; writer omits; runtime dataclasses retained. `test_no_injection_in_schema` enforces. |
| **D6** — Memory hypothesis | Phase 2 (scout §1.x) | `src/cognitive_stage.py` confirmed dormant; D12 scout coverage performed. |
| **D7** — Schema filename `HarloSchema.usda` | Phase 2 | Adopted per D7. |
| **D8** — `opinion_json` sidecar | Phase 2 | `string opinion_json = "{}"` declared on `CompositionLayerPrim`. |
| **D9** — `answer_embeddings_json` sidecar | Phase 2 | `string answer_embeddings_json = "[]"` on `IntakeHistoryPrim`. |
| **D10** — Provenance as `singleApplyAPI` | Phase 2 | `class "Provenance" (inherits = </APISchemaBase>, schemaKind = singleApplyAPI)` in schema. |
| **D11** — `propertyOrder` mandatory | Phase 2 | **C2 clarification:** USD 26.5 parser rejected metadata-level `propertyOrder`; D11 fulfilled via alphabetical declaration order + byte-stability test. |
| **D12** — `src/` scout coverage | Phase 2 | `design/mile_2_phase_2_scout_src.md`. |
| **D13** — `.pyd` lock workaround | Pre-session | Already documented in Mile 2 Phase 0–1 commit; not re-encountered this session. |
| **D14** — 1,133 baseline | All phases | Net-positive at every internal commit; final 1,170. |

No D-block conflicts encountered.

---

## Surprises surfaced (Forge clarifications C1, C2, C3)

Three implementation-time clarifications of Phase 1 design. Each is a Forge clarification (Commandment 5: doesn't redesign), surfaced to the human-gate now for explicit signoff.

### C1 — Scalar `float` USD type → `double`

**Issue:** Phase 1 design §2.3 listed `float` as the USD type for several scalar attrs (e.g., `MultipliersPrim.surprise_threshold` defaulting to 2.0, `hebbian_alpha` defaulting to 0.01). USD's `Sdf.ValueTypeNames.Float` is 32-bit; Python `float` is 64-bit. Round-tripping `0.3` through float32 produces `0.30000001192092896` — exceeds `BrainStage.__eq__`'s `rel_tol=1e-9`.

**Resolution:** all scalar `float` USD types in `HarloSchema.usda` and `generatedSchema.usda` declared `double`. `float[]` (e.g., `growth_arc`) → `double[]`. Writer uses `Sdf.ValueTypeNames.Double` / `DoubleArray`.

**Crucible accepted:** the design intent (preserve dataclass values) was implicit in the "round-trip equality" gate criterion. The "float" column was a Python-type annotation; the USD type choice was unstated. Forge's promotion to `double` fulfills design intent.

**Asks the human:** confirm `double` is the right binding for these fields, OR explicitly accept the float32 precision loss with relaxed tolerance.

### C2 — `propertyOrder` via declaration order

**Issue:** D11 mandates `propertyOrder` for deterministic .usda output. Phase 1 design §1 / Phase 2 implementation plan §3.1 specified placing `propertyOrder = [...]` in the class header `customData`. USD 26.5's text parser rejects with `"propertyOrder" is registered as a non-metadata field`.

**Resolution:** removed metadata-level `propertyOrder`; declared attributes in alphabetical order in every concrete class. Empirically verified by the byte-stability test (`test_roundtrip_byte_stability`): write-read-write produces byte-identical output.

**Crucible accepted:** D11's enforceable intent (byte-stable diffs) is achieved. Stricter form (`reorder properties = [...]` body statement) would be functionally equivalent to declaration discipline.

**Asks the human:** confirm declaration-order discipline is sufficient D11 fulfillment, OR mandate `reorder properties` body statements (cosmetic; same outcome).

### C3 — `trace_id` attribute on TracePrim

**Issue:** Phase 1 design §3 specified `/Brain/Association/Traces/<trace_id>` paths — implicit assumption that trace_ids are TF-identifier-safe. The `data/hebbian_seeded.usda` fixture has IDs like `26ab7b0812da44b4` (leading digit) and `test-v7-001` (hyphen). USD's `DefinePrim` rejects them.

**Resolution:** added `string trace_id` attribute to `TracePrim` schema. Writer sanitizes the prim name (non-identifier chars → `_`, prefix `t_` if leading digit) and stores the canonical ID in the `trace_id` attribute. Reader uses the attribute as the dict key, falling back to the prim name for legacy stages.

**Crucible accepted:** empirical migration data violated the implicit assumption; the fix is minimally invasive (one attribute add, two functions).

**Asks the human:** confirm that adding `trace_id` to the TracePrim schema is acceptable, OR specify an alternative (e.g., index-based prim names with a separate ID map; reversible hex encoding of the prim name).

---

## `src/` scout findings (per D12)

Captured in `design/mile_2_phase_2_scout_src.md`. Summary:

- **3 files** in `src/` directly import `pxr`: `cognitive_stage.py`, `usd_bootstrap.py`, `engine_config.py`. Only `cognitive_stage.py` makes USD API calls.
- **`src/cognitive_stage.py`** uses **only** the USD built-in `"Scope"` typeName for every `DefinePrim` call (3 sites), plus a single `"data"` string attribute per prim. **Zero typeName collisions**, **zero attribute name collisions**, **zero path overlap** (writes under `/state`, `/routing`, etc.; Path C writes under `/Brain`).
- **`tests/test_sprint4/*`** (3 test files) exercise `cognitive_stage.py`. They are part of the 1,133 D14 baseline.
- **Recommendation:** stay separate (no rewire, no eviction). Sprint 4 code remains dormant; Path C operates independently. Future post-Step-6 work can decide whether to evict, rewire, or modernize.

D12 satisfied. No collision flagged. Phase 2 Forge greenlit on this basis.

---

## Baseline at session close

| Metric | Value |
|---|---|
| Total tests collected | 1,171 |
| Passed | **1,170** |
| Skipped | 1 |
| Failed | 0 |
| Errored | 0 |
| Net-positive vs D14 (pre-session) | **+37** |

Pytest wall-clock at session close: 54.29s. Hot-path read latency vs Phase 0 baseline: -4.84% p50 / -3.55% p95 (improved within variance).

---

## Phase 5 entry conditions (deferred — next session)

Phase 5 (codec-blocker resolution) does NOT begin in this session. Per session override hard gate, the human must approve before Phase 5 starts.

**Pre-Phase-5 checklist for the next session:**

1. **Resolve C1, C2, C3 explicitly.** Either accept Forge's resolutions or specify alternatives. The schema is currently authored against Forge's resolutions; reverting any of them would require schema-level edits.
2. **Confirm D8/D9 string sidecars stay deferred.** Phase 5 work touches the sidecars; the human-review gate is the natural point to revisit (e.g., "actually let's typed-migrate `answer_embeddings` now while we're in there"). Default holds: deferred.
3. **Confirm `cognitive_twin.usda` eviction (Commandment 10) is Phase 5 scope.** D6 noted that `src/cognitive_stage.py` writes a similar but distinct file (`harlo.usda`) in current code. Eviction of `cognitive_twin.usda` does not break Sprint 4 since the path differs. Phase 5 can proceed.
4. **Confirm D5 stay-evicted.** No new evidence to revisit.

**Phase 5 Forge work (if approved):**
- Hex SDR / JSON sidecar conventions are already correct per Phase 2. Phase 5 work is primarily:
  - Evict `data/stages/cognitive_twin.usda`. Eviction reason logged in `harness/path_c/blocker_decisions.md`.
  - Resolve any per-blocker overrides the human authorizes (most likely: leave defaults alone).
- Phase 5 expected to be small (1–2 hours).

**Phase 6 work (further out):**
- Test repair (expected minimal — `tests/test_sprint4/*` untouched per stay-separate).
- Final Crucible verification.
- Mile 3 squash commit + PR.

---

## Specific question for the human

**Approve C1, C2, C3, and the Phase 2-4 deliverables, or request changes?**

If approve: next session begins Phase 5 (codec-blocker resolution + `cognitive_twin.usda` eviction) and Phase 6 (test repair + final Crucible) under the same harness, with no design changes.

If request changes: name the specific Forge clarification (C1/C2/C3) or design point (D-numbers, Phase n design doc section) you'd like reworked. Architect re-engages for a delta pass.

If escalate: the harness's adversarial-review brief (`harness/path_c/04_DEEP_THINK_BRIEF.md`) is the existing entry point; this session's findings are stronger context for that review than the original brief had.

---

## Session artifacts inventory

13 commits in this session (3 internal phase commits + Phase 0–1 closer from prior session):

```
$ git log harness-path-c --oneline | head -10
775a92a harness(path-c): Mile 2 Phase 4 — migration script + C3 trace_id attr
99ac1ea harness(path-c): Mile 2 Phase 3 — sync layer (write-side dispatch)
052a00b harness(path-c): Mile 2 Phase 2 — schema authoring + persistence layer
d410b8c harness(path-c): Mile 2 Phases 0–1 — design gate closed
4fa190e harness(path-c): Mile 1 — schema surgery package + recon
```

**Files added/modified this session:**

| Category | Count |
|---|---|
| Schema artifacts | 3 (HarloSchema.usda, plugInfo.json, generatedSchema.usda) |
| Persistence layer | 3 (init, writer, reader) |
| Sync layer | 4 (init, policy, write_through, checkpoint) |
| Migration script | 1 (migrate_path_c.py) |
| Tests | 13 files / 37 tests |
| Design / Forge / Crucible artifacts | 14 |

Push happens after this gate review per session override (push only at session close).

*End of human-review gate document. Awaiting human input before Phase 5.*
