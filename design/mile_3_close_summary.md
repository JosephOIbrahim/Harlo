# Mile 3 — Step 3 Close Summary

**Date:** 2026-04-28
**Branch:** `harness-path-c`
**Step 3 status:** **CLOSED on `harness-path-c`** (pending human-driven tag + PR)

---

## What shipped

- **Path C codeless schema surgery complete.**
- **21 prim types** declared in `schema/HarloSchema.usda` (2 abstract bases + 8 concrete containers + 10 concrete typed leaves + 1 singleApply API schema).
- **Real OpenUSD as canonical persistence** (P1 CIP defensible — public embodiment now ships with `pip install -e .[substrate]`).
- **USD-Lite engine retained** as fast in-memory runtime tier (`python/harlo/usd_lite/` unchanged in shape; sub-ms reads preserved).
- **Sync layer per D4 policy table** (`python/harlo/sync/`): `WRITE_THROUGH` for SessionPrim, GateStatusPrim, MerkleRootPrim, MotorPrim; `CHECKPOINT` for high-write-rate prims; INHERIT resolution for containers.
- **Migration script** (`python/harlo/migrate_path_c.py`): USD-Lite v1 → real USD; format detection; idempotent on already-migrated input; CLI with `--dry-run` and `--report`.
- **Substrate-unification with Moneta** verified: zero typeName collision; Harlo plugin under `harlo` namespace, Moneta under `moneta`.

## Test baseline lineage

```
Mile 1 commit message claim:           1,140  (unverified)
Phase 0 measured:                      1,065  (D14 amends)
Phase A resolved ([dev] extra):        1,133
Phase 2 (test_path_c +11):             1,144
Phase 3 (test_sync +20):               1,164
Phase 4 (test_migrate_path_c +6):      1,170  (D19 amends)
Phase 5 (eviction; +0):                1,170
Phase 6 (test_mixed_stage F2 +2):      1,172  ← FINAL
```

**Net Mile-1-claim → Mile-3-final: +32 tests** (1,140 → 1,172).
**Net Phase-0-empirical → Mile-3-final: +107 tests** (1,065 → 1,172).
**Failures throughout the surgery: 0.**
**Skipped: 1 (pre-existing intentional skip; not a regression target).**

## Latency lineage

| Measurement point | p50 (μs) | p95 (μs) |
|---|---|---|
| Phase 0 baseline (USD-Lite regex parser) | 4,347.1 | 4,785.4 |
| Phase 3 post sync layer | 4,136.7 (-4.84%) | 4,615.6 (-3.55%) |
| Phase 6 final | 4,097.8 (-5.73%) | 4,591.6 (-4.05%) |

**Hot-path read latency improved within run-to-run variance.** The runtime tier (regex parser) was never modified; the variation is benchmark noise. Constitution Law 4 / Gate 3's <10% regression criterion satisfied with substantial margin.

## Decisions log (D1–D19)

All 19 D-block decisions applied per `verify/mile_3_final_crucible.md` audit. Reference docs:

- `harness/path_c/05_DECISIONS.md` — D1–D5 (Mile 1)
- `harness/path_c/06_DECISIONS_PHASE_1.md` — D6–D14 (Phase 1 gate)
- `harness/path_c/07_DECISIONS_PHASE_4.md` — D15–D19 (Phase 4 gate)

**No D-block conflicts encountered.** Future surgeries continue this lineage; new decisions filed as D20+.

## Codec-blockers (CB-1 through CB-5)

All five Mile-1-identified codec-blockers closed per `harness/path_c/blocker_decisions.md`:

- CB-1, CB-2, CB-3, CB-4: Phase 2 absorbed all sidecar work into the persistence-layer writer/reader.
- CB-5: stale `data/stages/cognitive_twin.usda` evicted in Phase 5 (filesystem-level; `data/` is gitignored, so no git deletion entry).

## Tracking issues

| ID | Status | Subject |
|---|---|---|
| TI-001 | RESOLVED-ON-ARRIVAL | Pre-existing test failures hypothesized in Phase 0; turned out to be missing dev deps; fully resolved by `[dev]` extra |

No further TIs filed during this session.

## What was deferred (post-Step-6 work, NOT in scope of Path C)

- **Typed migration of `opinion_json`** (D8) — `CompositionLayerPrim.opinion` remains a `string` sidecar. Future surgery may decide between permanent-string-sidecar vs typed-relationship; deferred.
- **Typed migration of `answer_embeddings_json`** (D9) — `IntakeHistoryPrim.answer_embeddings` remains a `string` sidecar. Could migrate to `double[]` cheaply; deferred.
- **InjectionPrim cross-session persistence** (D5) — Injection state remains session-scoped (in-memory only). Tracking issue: "InjectionPrim cross-session persistence — design decision deferred until post-Step-6" (per D5).
- **Sprint 4 `src/cognitive_stage.py` rewire** (D6 stay-separate) — dormant Sprint 4 code preserved; future post-Step-6 work can decide whether to evict, rewire, or modernize.
- **Comprehensive Phase 3+ benchmark suite** — Phase 3 latency benchmark is a single read path. Production deployment may want broader coverage.
- **Cross-platform `usd-core` testing** — Windows + Python 3.12 verified. Linux/macOS not tested in this surgery.

## Patent posture impact

**P1 CIP framing now defensible.** Real-USD substrate is in production embodiment via `pip install -e .[substrate]`. Public Apache-2.0 release continues to support core Harlo without `[substrate]` (Constitution Law 3); the substrate extra is the canonical-persistence path for any deployment that wants real-USD round-trip.

The Path C choice (real USD as canonical persistence, USD-Lite as fast in-memory runtime) was the **architecturally correct alternative** to:
- **Path A** (mock real USD as a USD-Lite facade) — would have undermined CIP claims
- **Path B** (full transplant — `pxr` replaces USD-Lite) — would have detonated 1,140-claim test baseline and blown hot-path latency on subprocess IPC

Mile 1's recon correctly identified Harlo's USD-Lite reality and triaged to Path C. Mile 2 executed cleanly with all six phase gates passing.

## Step 4–6 prerequisites

| Prerequisite | Status |
|---|---|
| Substrate-unified: Harlo + Moneta both speak real USD | ✅ Both register codeless schema plugins; zero typeName collision |
| ComfyCozy demo can read either substrate via real USD | ✅ Both projects' `.usda` files round-trip through `pxr.Usd.Stage` |
| Benchmark measures architecture, not bridge layer | ✅ Path C eliminates the format-bridge that would have inflated benchmark numbers |

Step 4 (ComfyCozy × Moneta demo) may begin after Mile 3 tag + merge.

## Manual human actions to take after review

1. **Review this document** plus `verify/mile_3_final_crucible.md`.

2. **Push current state to origin/harness-path-c:**
   ```
   git push origin harness-path-c
   ```
   (Mile 3 commit will land on `harness-path-c`; this surgery has avoided pushes mid-session per LR7.)

3. **Create the close tag** on the final Mile 3 commit:
   ```
   git tag -a v3.4.0-path-c -m "Path C codeless schema surgery complete

   - 21 prim types in schema/HarloSchema.usda (codeless)
   - Real OpenUSD as canonical persistence (substrate extra)
   - USD-Lite engine retained as fast in-memory runtime tier
   - Sync layer per D4 policy
   - Migration script (USD-Lite v1 -> real USD)
   - All 19 D-block decisions applied
   - Test baseline 1,172 (1,170 floor + F2 mixed-stage)
   - Hot-path latency improved within variance
   - Substrate-unified with sister project Moneta"
   git push origin v3.4.0-path-c
   ```

4. **Open PR** from `harness-path-c` → `master`:
   ```
   gh pr create --base master --head harness-path-c \
     --title "Path C codeless schema surgery (Step 3 of mandatory stack)" \
     --body-file design/mile_3_close_summary.md
   ```

5. **Wait for CI green** (the `[dev]` extra and `[substrate]` extra will need to install on CI's environment; if the maturin `.pyd` lock issue manifests there, document via D13's pattern).

6. **Merge PR** after CI green and any final review.

7. **Move to Step 4** (ComfyCozy × Moneta demo).

## Session metrics

```
Wall-clock used:    ~1h05m of 5h soft cap, 7h hard cap
Phases completed:   5, 6, Mile 3 (all gates passed)
Internal commits:   3 (Phase 5: af47ab5, Phase 6: cfb1f97, Mile 3: pending)
                    plus prior session commits already on harness-path-c

F1 (D15–D19):       harness/path_c/07_DECISIONS_PHASE_4.md ✓
F2 (mixed-stage):   tests/test_path_c/test_mixed_stage.py ✓ (2 subtests pass)
F3 (codec audit):   CONFIRMED-ABSORBED (Phase 2 absorbed all 5 codec-blockers)
F4 (path overlap):  CONFIRMED-NONE (Sprint 4 writes /state, /routing, etc.;
                    Path C writes /Brain; zero overlap)

Files touched this session:        12
Tests added this session:          +2
Final test count:                  1,172 / 1,170 floor (D19)
Latency p50/p95 vs Phase 0:        -5.73% / -4.05% (improvement)

Eviction log:       harness/path_c/blocker_decisions.md ✓
Close summary:      design/mile_3_close_summary.md ✓ (this document)

Step 3 status:      CLOSED on harness-path-c
```

---

*End of Mile 3 close summary. Path C codeless schema surgery is complete; awaiting human review, tag, and PR.*
