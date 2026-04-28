# Mile 2 — Phase 6 Forge Report

**Role:** Forge &nbsp;|&nbsp; **Date:** 2026-04-28
**Phase:** 6 — Test repair + final Crucible &nbsp;|&nbsp; **Branch:** `harness-path-c`

---

## Files written / modified

| Path | Type | Verification |
|---|---|---|
| `tests/test_path_c/test_mixed_stage.py` | Created (2 tests for F2) | Both pass |
| `harness/path_c/phase_6_latency.json` | Created | Latency vs Phase 0 baseline |

**Test repair:** none required. Phase 5's eviction broke nothing (verified by post-eviction baseline still 1,170).

**Lines authored: ~150.** Productivity floor cleared.

---

## F2 — Mixed-stage TracePrim test

### Implementation

`tests/test_path_c/test_mixed_stage.py` contains two tests:

1. **`test_mixed_legacy_and_new_traceprims_in_same_stage`** — A single stage contains:
   - Legacy TracePrim at `/Brain/Association/Traces/legacy_trace_alpha` with **no authored `trace_id`** value (schema-defined attr exists but is unauthored)
   - New-format TracePrim at `/Brain/Association/Traces/t_99deadbeef` with `trace_id = "99deadbeef"` (canonical, original starts with digit)

   Reads via `harlo.usd_lite.persistence.read`. Asserts:
   - 2 dict entries
   - Legacy keyed by `"legacy_trace_alpha"` (prim-name fallback)
   - New keyed by `"99deadbeef"` (attribute path)
   - `trace.trace_id` field matches dict key in both cases
   - Sanitized prim name `"t_99deadbeef"` does NOT appear as a dict key

2. **`test_legacy_only_stage_falls_back_for_all_traces`** — Pre-C3 stages (no `trace_id` attribute anywhere) read back with prim-name fallback for all traces. Validates 100% legacy compatibility.

### Implementation note — `IsValid()` vs `HasAuthoredValue()`

First-pass test setup attempted to assert `not legacy.GetAttribute("trace_id").IsValid()` to verify the legacy trace had no `trace_id`. **This was wrong.** USD's `IsValid()` returns True for schema-defined attributes regardless of whether a value was authored. The correct invariant is `not HasAuthoredValue()`. Fixed on retry; both tests pass cleanly.

This is a USD API subtlety, not a logic bug. Reader code already handled the unauthored case correctly (`_get_attr` returns the default when `.Get()` returns None).

### What F2 guarantees

- Reader fallback to `prim.GetName()` works when `trace_id` is unauthored.
- Reader uses `trace_id` attribute when authored.
- Both paths can co-exist in a single stage; dict keys are consistent.
- Future schema migrations affecting `trace_id` cannot silently break the dict-key contract — F2 pins the expected behavior.

---

## Crucible Gate 6 verification (Forge claim — Crucible signs)

```
$ pytest tests/ --tb=no -q
1172 passed, 1 skipped in 42.49s
```

| Gate 6 criterion | Status | Measurement |
|---|---|---|
| Test baseline ≥ 1,170 + F2 added | ✅ | 1,172 = 1,170 + 2 (F2) |
| F2 mixed-stage test passes | ✅ | Both subtests pass |
| Hot-path latency <10% regression | ✅ | -5.73% p50 / -4.05% p95 (improved) |
| Byte-stability test passes | ✅ | `test_roundtrip_byte_stability` in 1,172 baseline |
| Subprocess SchemaRegistry test passes | ✅ | `test_schema_registry_loads_all_harlo_types_in_subprocess` in 1,172 baseline |

---

## Cumulative session metrics

| Metric | Value |
|---|---|
| Pre-session baseline (D19) | 1,170 |
| Phase 5 baseline | 1,170 (no test surface change) |
| Phase 6 baseline | 1,172 |
| Net-positive Mile-1 → Mile-3-prep | **+39** (1,133 → 1,172) |
| Hot-path latency vs Phase 0 | **-5.73% p50 / -4.05% p95** (improved within run-to-run variance; runtime tier unchanged) |

---

## Forge handoff to Crucible

Phase 6 ready for Gate 6:
- ✅ All 5 criteria green per measurement above.
- F2 implemented and passing.
- No test repair was required (Phase 5 eviction broke nothing).
- Ready for Mile 3.

*End of Phase 6 Forge report.*
