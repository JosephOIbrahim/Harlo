# Mile 2 — Phase 6 Crucible Verification

**Role:** Crucible (adversarial verification, Commandment 7) &nbsp;|&nbsp; **Date:** 2026-04-28
**Phase:** 6 — Test repair + final Crucible &nbsp;|&nbsp; **Branch:** `harness-path-c`

This is the **final Crucible gate of Mile 2** — last verification before Mile 3 close summary.

---

## Verdict at a glance

**Phase 6 gate: ✅ PASS — all five Gate 6 criteria green.** Mile 3 may begin.

F2 mixed-stage test (mandatory per session override) implemented and passing. Cumulative net-positive Mile-1 → Phase-6: **+39 tests (1,133 → 1,172)** with zero regressions across six phase boundaries.

---

## Gate 6 criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Test baseline ≥ 1,170 + F2 added | ✅ | 1,172 green / 1 skip / 0 fail / 0 err |
| 2 | F2 mixed-stage test passes | ✅ | `test_mixed_legacy_and_new_traceprims_in_same_stage` + `test_legacy_only_stage_falls_back_for_all_traces` both pass |
| 3 | Hot-path latency <10% regression vs Phase 0 baseline | ✅ | -5.73% p50, -4.05% p95 (improvement within variance) |
| 4 | Byte-stability test still passes | ✅ | `test_roundtrip_byte_stability` in baseline |
| 5 | Subprocess SchemaRegistry test still passes | ✅ | `test_schema_registry_loads_all_harlo_types_in_subprocess` in baseline |

---

## Adversarial review

### Probe 1 — does F2 actually exercise the reader fallback?

`test_mixed_legacy_and_new_traceprims_in_same_stage` constructs a TracePrim with no authored `trace_id` value, then calls `read()`. The reader's `_read_trace`:

```python
trace_id = _get_attr(prim, "trace_id") or prim.GetName()
```

`_get_attr` calls `attr.Get()` which returns `None` for an unauthored attribute (even if the attribute spec exists per schema). The `or` clause then falls back to `prim.GetName()`.

The test asserts the dict key is the prim name (`"legacy_trace_alpha"`), not None or empty. That's exactly the fallback path executing.

**Crucible verdict:** F2 genuinely exercises the fallback path. ✅

### Probe 2 — what if the trace_id attribute is authored to an empty string?

Edge case worth checking: `trace_id = ""` (empty but authored). The reader's `or` clause treats empty string as falsy → falls back to prim name. This is **not** explicitly tested by F2 but is consistent behavior.

**Adversarial verdict:** acceptable behavior; an empty trace_id is semantically equivalent to unauthored. If the user wanted to assert "trace_id was deliberately set to empty," they shouldn't — that's a malformed stage.

Crucible files this as a minor undocumented edge. Could add an explicit test in a future surgery if needed; not a Gate 6 blocker.

### Probe 3 — does the test pin the specific guarantee?

The test asserts:
- 2 entries in the dict
- Both expected keys present
- `trace_id` field matches dict key
- Sanitized prim name does NOT appear as a key (catches reader regression that leaks presentation form)

**Strong assertions.** Not vague. ✅

### Probe 4 — `IsValid()` vs `HasAuthoredValue()` retry

Forge's first attempt asserted `not IsValid()` for the unauthored attribute, which failed because schema-defined attributes are always "valid." Forge retried with `HasAuthoredValue()` and succeeded.

**Crucible verdict:** test-setup correction, not a real bug. The reader code was always correct; the test was incorrectly checking the wrong thing. Fixed within Cmd 3's 3-retry budget (this was retry 2 of 3). No Cmd 7 violation (the test was strengthened, not weakened).

### Probe 5 — latency improvement verification

Phase 6 latency: -5.73% p50, -4.05% p95 vs Phase 0. Phase 3 measured -4.84% p50, -3.55% p95. Latency continues to be within run-to-run variance of the original baseline; runtime tier was never modified by any phase. ✅

**Adversarial check:** is the latency benchmark itself representative? The same microbenchmark (parse `data/hebbian_seeded.usda`) was used at Phase 0, Phase 3, Phase 6. Consistency of methodology preserved. The benchmark exercises a single read path; comprehensive Phase 3+ benchmark suite is post-Step-6 work.

### Probe 6 — what's NOT covered?

Out of Phase 6 scope (correctly):
- **Real-world stage performance** — no dataset larger than the 16-trace hebbian_seeded fixture exercised. Phase 4 migration handles correctness; performance at scale is post-Step-6.
- **Cross-platform `usd-core` compatibility** — only Windows + Python 3.12 verified. Linux/macOS not tested in this surgery.
- **Schema evolution** — adding/removing prim types or attributes mid-deployment not tested. Future surgeries.

These are correctly out of scope for Mile 2.

---

## Cumulative Mile 2 audit

| Phase | Gate | Status | Net-positive | Cumulative |
|---|---|---|---|---|
| 0 | Pre-flight | ⚠️→✅ (B2 deferred) | n/a | 1,065 measured |
| A (B2 resolution) | Closer | ✅ | n/a | 1,133 |
| 1 | Schema design | ✅ (design only) | 0 | 1,133 |
| 2 | Schema authoring | ✅ | +11 | 1,144 |
| 3 | Sync layer | ✅ | +20 | 1,164 |
| 4 | Migration script | ✅ | +6 | 1,170 |
| 5 | Codec resolution + eviction | ✅ | 0 | 1,170 |
| 6 | Final Crucible (this gate) | ✅ | +2 | 1,172 |

**All 6 phase gates passed.** Zero regressions across the full surgery. Mile 3 entry conditions met.

---

## Phase 6 gate decision

**✅ PASS.** Mile 3 close (summary + tag prep, no actual tag) may begin.

Crucible signs Phase 6.

*End of Phase 6 Crucible verification.*
