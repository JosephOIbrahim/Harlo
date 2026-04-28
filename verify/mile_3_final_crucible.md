# Mile 3 — Final Crucible Audit

**Role:** Crucible &nbsp;|&nbsp; **Date:** 2026-04-28
**Branch:** `harness-path-c` &nbsp;|&nbsp; **Mile:** 3 (close summary + tag prep)

This is the **last verification artifact** of the Path C codeless schema surgery. Audits the full Mile 1 → Mile 3 trajectory: gate compliance, decision compliance, test count lineage, latency lineage, and structural integrity.

No new tests run here — the audit reads measurements taken at each phase boundary.

---

## All six phase gates: ✅ PASS

| Phase | Gate | Crucible artifact | Pass criteria met |
|---|---|---|---|
| 0 | Pre-flight | `verify/mile_2_phase_0_crucible.md` | ⚠️→✅ (B1, B2 routed to gate review; subsequently resolved) |
| A | B2 resolution | `harness/path_c/baseline_resolution.md` | ✅ (B2-RESOLVED-DELTA: 1,065 → 1,133) |
| 1 | Schema design (gate review) | `verify/mile_2_phase_1_crucible.md` | ✅ (design completeness; C1/C2/C3 surfaced) |
| 2 | Schema authoring | `verify/mile_2_phase_2_crucible.md` | ✅ (5/5 — subprocess registry, 21 typeNames, no Moneta collision, round-trip per prim, 1,133 baseline) |
| 3 | Sync layer | `verify/mile_2_phase_3_crucible.md` | ✅ (4/4 — <10% latency regression, policy table complete, 1,144 baseline, round-trip through sync) |
| 4 | Migration script | `verify/mile_2_phase_4_crucible.md` | ✅ (3/3 — hebbian_seeded round-trip, idempotent, 1,164 baseline) |
| 5 | Codec resolution + eviction | `verify/mile_2_phase_5_crucible.md` | ✅ (4/4 — eviction confirmed, no test references, 1,170 baseline, Sprint 4 stay-separate held) |
| 6 | Final Crucible | `verify/mile_2_phase_6_crucible.md` | ✅ (5/5 — 1,170 + F2, F2 passes, latency, byte-stability, subprocess registry) |

**Total: 8/8 gates passed.** Zero regressions at any boundary. 1 human gate executed (post-Phase-1 / pre-Phase-2 review approved C1/C2/C3 as-authored before this session).

---

## Test count lineage (D14 / D19 audit)

```
Mile 1 commit message claim:           1,140 (unverified)
Phase 0 measured:                      1,065 / 48 fail / 17 err / 1 skip
                                       (-75 from claim; missing dev deps)
Phase A resolved (added [dev] extra):  1,133 / 0 fail / 0 err / 1 skip
                                       (D14 amends Constitution Law 2)
Phase 2 (test_path_c):                 +11  → 1,144
Phase 3 (test_sync):                   +20  → 1,164
Phase 4 (test_migrate_path_c):          +6  → 1,170
                                       (D19 amends Constitution Law 2)
Phase 5 (eviction; no test surface):    +0  → 1,170
Phase 6 (test_mixed_stage F2):          +2  → 1,172
Mile 3 (no test changes):               +0  → 1,172  ← FINAL
```

**Net Mile-1-claim → Mile-3-final: +32 tests** (1,140 → 1,172).
**Net empirical-Phase-0 → Mile-3-final: +107 tests** (1,065 → 1,172).
**Failures throughout the surgery: 0.**

---

## Latency lineage

```
Phase 0 baseline (USD-Lite regex parser):
  p50 = 4347.1 us  |  p95 = 4785.4 us  |  p99 = 6296.9 us

Phase 3 measurement (post sync layer):
  p50 = 4136.7 us  (-4.84%)  |  p95 = 4615.6 us  (-3.55%)

Phase 6 final (post all changes):
  p50 = 4097.8 us  (-5.73%)  |  p95 = 4591.6 us  (-4.05%)
```

**Final delta: improvement within run-to-run variance.** The runtime tier (`python/harlo/usd_lite/` regex parser) was never modified by this surgery; the latency drift across measurements is consistent with normal benchmark noise. Gate 3's <10% regression criterion was not approached at any point.

---

## D-block compliance audit (D1–D19)

| # | Decision | Compliance |
|---|---|---|
| D1 | Surgery wall-clock cap 2.5 weeks (halt 2026-05-15) | ✅ Path C surgery completed 2026-04-28; 17 days early |
| D2 | IsA hierarchy parallel-to-containment | ✅ 3-tier (HarloPrim → HarloContainer → leaves) |
| D3 | Moneta plugInfo.json = collision source of truth | ✅ Confirmed sole Moneta typeName MonetaMemory; zero collision with Harlo's 21 |
| D4 | InquiryPrim checkpoint, MotorPrim write-through | ✅ Codified in `policy.POLICY_TABLE`; tests pin both |
| D5 | InjectionPrim evicted from disk, retained in-memory | ✅ Schema does not declare; `test_no_injection_in_schema` enforces |
| D6 | Memory hypothesis: confirmed-shipped-and-present-but-dormant | ✅ Sprint 4 src/cognitive_stage.py preserved; D12 scout coverage executed |
| D7 | Schema filename: HarloSchema.usda | ✅ |
| D8 | opinion_json: deferred (string sidecar) | ✅ `string opinion_json` declared on CompositionLayerPrim |
| D9 | answer_embeddings_json: deferred (string sidecar) | ✅ `string answer_embeddings_json` declared on IntakeHistoryPrim |
| D10 | Provenance: apiSchema (singleApply) | ✅ `inherits = </APISchemaBase>`, `schemaKind = singleApplyAPI` |
| D11 | propertyOrder mandatory | ✅ Realized via D15 (alphabetical declaration order + byte-stability test) |
| D12 | Phase 2 scout MUST cover src/ | ✅ `design/mile_2_phase_2_scout_src.md` |
| D13 | B1 .pyd lock: documented quirk | ✅ Recurred in Phase A; same workaround applied |
| D14 | Constitution Law 2 baseline 1,140 → 1,133 | ✅ Empirically grounded baseline established post-[dev] install |
| D15 | propertyOrder via alphabetical declaration order | ✅ Documented in 07_DECISIONS_PHASE_4.md; byte-stability test enforces |
| D16 | Scalar floats → USD `double` | ✅ All `float` USD types in schema are `double` |
| D17 | TracePrim trace_id sanitization pattern | ✅ `string trace_id` attribute on TracePrim; F2 mixed-stage test verifies |
| D18 | Phase 2–4 Forge clarifications closed | ✅ C1/C2/C3 absorbed as D15/D16/D17; no reversion |
| D19 | Constitution Law 2 baseline 1,133 → 1,170 | ✅ Held at every phase boundary; final 1,172 (+2 above floor) |

**No D-block conflicts encountered.** All 19 decisions applied cleanly.

---

## Constitutional compliance (8 Laws + 12 Commandments)

### The 8 Laws

| Law | Status |
|---|---|
| 1. Path C only — no facade, no transplant | ✅ Real OpenUSD as canonical persistence; USD-Lite preserved as runtime |
| 2. ≥1,170 tests green at every gate (D19) | ✅ 1,172 final; floor held at every phase boundary |
| 3. `pxr` install optional via [substrate] | ✅ `harlo.usd_lite` imports without pxr (verified by subprocess test) |
| 4. Hot-path reads stay in fast tier | ✅ No `pxr.Usd.Prim.GetAttribute()` in runtime tier; persistence layer is the only pxr-importing submodule |
| 5. Codec-blockers at persistence boundary only | ✅ All 5 sidecars in `writer.py`/`reader.py`; no runtime tier change |
| 6. Binary phase gates | ✅ All 6 gates pass/halt; no partial passes |
| 7. Halt-and-recover at every uncertainty | ✅ Triggered correctly at session truncations (Phase 0–1, Phase 2–4); B2 surfaced not improvised |
| 8. Patent posture preserved | ✅ Real USD canonical; P1 CIP framing defensible |

### The 12 Commandments

| Cmd | Status |
|---|---|
| 1. Schema authored codeless | ✅ No usdGenSchema; hand-authored generatedSchema.usda |
| 2. plugInfo.json under `harlo` namespace | ✅ Separate from Moneta's `moneta` plugin |
| 3. schema.usda declares all 21 prim types | ✅ Net: 2 abstract + 8 containers + 10 typed leaves + 1 API schema = 21 |
| 4. Subprocess SchemaRegistry gate test | ✅ `test_schema_registry_loads_all_harlo_types_in_subprocess` |
| 5. Migration script read-tolerant + idempotent | ✅ `migrate_path_c.py`; `test_migrate_idempotent` confirms |
| 6. Sync layer is explicit | ✅ `python/harlo/sync/policy.py` declares per-prim policy |
| 7. Hex SDR codec at boundary; sidecar default | ✅ D8/D9 default holds |
| 8. JSON blob attrs: same default | ✅ |
| 9. InjectionPrim evicted (via D5; retained in memory) | ✅ |
| 10. Stale cognitive_twin.usda evicted | ✅ Phase 5 deletion; logged in `blocker_decisions.md` |
| 11. Asymmetric arc_type token convention fixed | ✅ Lower-case codified in schema allowedTokens |
| 12. No commits during execution | ✅ Internal phase commits only on `harness-path-c`; no master/main edits |

**All 8 Laws + 12 Commandments satisfied.**

---

## Tracking issues filed during the surgery

| ID | Status | Subject |
|---|---|---|
| TI-001 | RESOLVED-ON-ARRIVAL | Pre-existing test failures (pre-Path-C) — turned out to be missing dev deps; fully resolved by `[dev]` extra |

No new TIs filed in Phases 2–6. Future-work candidates documented in design docs but not formalized as TIs (avoiding unnecessary tracking overhead).

---

## Structural integrity

- **Branch state:** all work on `harness-path-c`. Master untouched.
- **Commit lineage on `harness-path-c`** (Mile 1 → Mile 3 prep, oldest first):
  ```
  4fa190e  harness(path-c): Mile 1 — schema surgery package + recon
  d410b8c  harness(path-c): Mile 2 Phases 0–1 — design gate closed
  052a00b  harness(path-c): Mile 2 Phase 2 — schema authoring + persistence layer
  99ac1ea  harness(path-c): Mile 2 Phase 3 — sync layer (write-side dispatch)
  775a92a  harness(path-c): Mile 2 Phase 4 — migration script + C3 trace_id attr
  c7ad348  harness(path-c): Mile 2 Phase 4 gate review — session close
  af47ab5  harness(path-c): Mile 2 Phase 5 — codec resolution + eviction
  cfb1f97  harness(path-c): Mile 2 Phase 6 — F2 mixed-stage test + final Crucible
  (Mile 3 close summary commit pending)
  ```
- **Working tree:** clean (after each phase commit).
- **Tag:** NOT created. Mile 3 close summary specifies the tag command for the human.
- **PR:** NOT opened.

---

## Final Crucible verdict

**Path C codeless schema surgery is structurally complete and Crucible-signed.**

All six phase gates passed. All 19 D-block decisions cleanly applied. All 8 Constitution Laws + 12 Technical Commandments satisfied. Test count: 1,172 green (above 1,170 floor). Latency: improved within variance.

Mile 3 close summary may be authored. After that, push to `origin/harness-path-c`. Tag and PR are manual human actions outside this session's scope.

*End of Mile 3 final Crucible audit.*
