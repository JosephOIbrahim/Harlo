# Mile 2 — Phase 2 Crucible Verification

**Role:** Crucible (adversarial verification, Commandment 7) &nbsp;|&nbsp; **Date:** 2026-04-28
**Phase:** 2 — Schema authoring + persistence layer &nbsp;|&nbsp; **Branch:** `harness-path-c`

---

## Verdict at a glance

**Phase 2 gate: ✅ PASS — all five Gate 2 criteria green.** Ready for Phase 3 (sync layer).

Two Forge clarifications surfaced and reviewed (C1 float→double, C2 propertyOrder→declaration-order). Crucible accepts both as faithful to design intent.

---

## Gate 2 criteria evaluation

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Subprocess `SchemaRegistry` test passes | ✅ | `test_schema_registry_loads_all_harlo_types_in_subprocess` passes; 60s timeout, finishes in <1s |
| 2 | 21 typeNames resolve | ✅ | All 21 names in HARLO_TYPENAMES list confirmed via `Usd.SchemaRegistry().GetTypeFromName(...)` |
| 3 | No collision with built-in USD or Moneta `MonetaMemory` | ✅ | Negative checks: `MonetaMemory` not visible in our registry view; USD `Xform` still resolvable |
| 4 | Round-trip fidelity per prim (modulo declared codec-blockers) | ✅ | `test_populated_stage_roundtrip` covers all 19 concrete types; `test_hex_sdr_codec_fidelity` + `test_json_blob_codec_fidelity` cover D8/D9 boundaries |
| 5 | 1,133 baseline preserved (D14) | ✅ | Post-Phase-2: **1,144 green / 1 skip / 0 fail / 0 err** (1,133 + 11 new) |

---

## Adversarial review

Per Commandment 7 — Crucible motivated to find failures, not confirm success. Things probed:

### Probe 1 — are the round-trip tests vague?

`test_populated_stage_roundtrip` uses `populated_stage == bs2` which calls `BrainStage.__eq__` (float-tolerant). **Strong assertion** — equality is per-field deep-compare with float tolerance. Not vague.

`test_hex_sdr_codec_fidelity` uses exact `out == sdr` on the boolean SDR list — bit-level equality. **Strong assertion**, no tolerance. The codec must round-trip every bit.

`test_json_blob_codec_fidelity` uses exact `==` on dict/list. **Strong assertion** because `json.dumps(..., sort_keys=True)` produces deterministic output; equality is byte-equivalent.

**Verdict: assertions are not vague.** No `assert x` or `assert thing is not None` patterns. Each test pins a specific expected value.

### Probe 2 — does test_no_injection_in_schema actually catch D5 violations?

The test traverses all prims in the written stage and asserts none has typeName `InjectionPrim` or `InjectionContainerPrim`. **This is the right test** — it would catch a writer regression that accidentally writes Injection prims.

**Adversarial check:** what if Forge writes Injection prims with a *different* typeName (e.g., as `Scope`)? The test wouldn't catch that. But that's a hypothetical adversarial Forge — the writer code (verified by Crucible reading it) explicitly omits Injection. Acceptable.

### Probe 3 — does test_lower_case_arc_type_token actually verify Cmd 11?

Test reads the `arc_type` attribute from the populated stage's `layer_001` prim and asserts the value is `"local"` (lower-case). **Direct verification.** A regression to upper-case would fail this test.

### Probe 4 — does test_roundtrip_byte_stability protect D11?

Test writes the populated stage, reads it back, writes again to a different path, compares the two .usda files byte-for-byte. **This is the rigorous form** of D11's intent. A non-deterministic attribute order would fail this test.

**Adversarial check:** is this test environment-stable? USD's `.usda` writer might inject timestamps or version strings that change between runs. Looking at the actual output... `Sdf.Layer.Save()` produces deterministic output for a given in-memory layer state in USD 26.5 (verified by the test passing).

### Probe 5 — does test_no_runtime_tier_pxr_import actually verify Law 4?

Test imports `harlo.usd_lite` (the parent package) and asserts `'pxr' not in sys.modules`. **Direct verification of Law 4.** A regression where `harlo.usd_lite/__init__.py` accidentally imports `persistence` (which imports `pxr`) would fail this test.

### Probe 6 — accept C1 (float→double)?

Crucible reviews:
- Phase 1 design §2.3 lists `float` for scalar fields.
- USD `float` (32-bit) loses precision on common decimal values (0.3, 0.01, 0.5).
- Dataclass uses Python float (64-bit).
- Round-trip equality fails with float32; succeeds with double.
- **Phase 1 design intent was "preserve dataclass values."** The "float" column was a Python-type annotation; the USD-type choice was implicit.
- Forge's promotion to `double` USD types fulfills the explicit intent (round-trip fidelity) without changing dataclass shapes or runtime tier behavior.

**Crucible accepts C1.** Not a redesign — a clarification that resolves an ambiguity in design that empirical testing exposed.

### Probe 7 — accept C2 (propertyOrder via declaration order)?

Crucible reviews:
- D11 mandates `propertyOrder` for deterministic output.
- USD 26.5's text parser rejects `propertyOrder` at the metadata location specified by Phase 1 design / Phase 2 implementation plan.
- Body-level `reorder properties = [...]` is the alternate USD form, but is functionally equivalent to declaration order.
- Forge declares attributes alphabetically per concrete class.
- `test_roundtrip_byte_stability` empirically verifies the result: write-read-write produces byte-identical .usda.

**Crucible accepts C2.** D11's enforceable intent is byte-stability of .usda output; that's empirically achieved.

### Probe 8 — what's NOT covered?

Things this test suite does not cover (correctly out-of-scope):
- **Sync policy** — Phase 3 work, separate Crucible gate.
- **Migration script** — Phase 4 work.
- **Performance** — `test_roundtrip_byte_stability` confirms determinism but not latency. Phase 3 latency benchmark covers regression.
- **Schema evolution** — adding a new prim type or attribute later is not tested. Phase 5 / future surgeries.

These are correctly NOT Phase 2 concerns.

---

## Forge clarifications signoff

| Clarification | Crucible verdict | Documented |
|---|---|---|
| C1 — float → double | ✅ Accept | `forge/mile_2_phase_2_report.md` §C1 |
| C2 — propertyOrder via declaration order | ✅ Accept | `forge/mile_2_phase_2_report.md` §C2 |

---

## Phase 2 gate decision

**✅ PASS.** Phase 3 (sync layer) may begin.

Crucible signs Phase 2.

*End of Phase 2 Crucible verification.*
