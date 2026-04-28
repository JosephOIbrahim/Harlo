# Mile 2 — Phase 3 Forge Report

**Role:** Forge &nbsp;|&nbsp; **Date:** 2026-04-28
**Phase:** 3 — Sync layer &nbsp;|&nbsp; **Branch:** `harness-path-c`

Implements Architect's plan in `design/mile_2_phase_3_sync_layer.md`.

---

## Files written

| Path | Type | Verification |
|---|---|---|
| `python/harlo/sync/__init__.py` | Created | Imports without `[substrate]` (lazy pxr via persistence) |
| `python/harlo/sync/policy.py` | Created | 19 typeNames in `POLICY_TABLE`; `_validate_table_completeness()` runs at module load |
| `python/harlo/sync/write_through.py` | Created | `persist()` + `persist_prim()` exported |
| `python/harlo/sync/checkpoint.py` | Created | `Checkpoint` class + `default_checkpoint` instance |
| `tests/test_sync/__init__.py` | Created (empty package) | Pytest collects |
| `tests/test_sync/test_policy_table.py` | Created (10 tests) | 10/10 pass |
| `tests/test_sync/test_write_through.py` | Created (3 tests) | 3/3 pass |
| `tests/test_sync/test_checkpoint.py` | Created (7 tests) | 7/7 pass |
| `harness/path_c/phase_3_latency.json` | Created | Latency measurement vs Phase 0 baseline |

**Lines authored: ~520.** Productivity floor cleared (>50 lines/phase).

---

## Verification results

### Sync layer tests

```
$ pytest tests/test_sync/ -v --tb=short
20 passed in 0.34s
```

All 20 tests pass:
- 10 policy-table tests (coverage, D4/§6 rulings, INHERIT resolution, no-pxr-import, no-Injection)
- 3 write-through tests (file written, round-trip equality, persist_prim arg)
- 7 checkpoint tests (clean state, mark_dirty dedup, flush no-op clean, flush writes dirty, round-trip equality, clear, default_checkpoint identity)

### Latency (Crucible Gate 3 criterion 1)

```json
{
  "baseline_p50_us": 4347.1,  "current_p50": 4136.7,  "delta_p50_pct": -4.84,
  "baseline_p95_us": 4785.4,  "current_p95": 4615.6,  "delta_p95_pct": -3.55,
  "gate_pass": true
}
```

Latency is **lower** than baseline (run-to-run variance; runtime tier unchanged). <10% regression criterion satisfied.

### Full baseline regression

```
$ pytest tests/ --tb=no -q
1164 passed, 1 skipped in 35.45s
```

- Pre-Phase-3: 1,144 green
- Post-Phase-3: 1,164 green / 1 skip / 0 fail / 0 err
- Net-positive: **+20** (Commandment 2 satisfied)

---

## Forge note — caught Rule 1 violation pre-commit

During Phase 3 baseline regression, `tests/test_integration/test_compliance.py::TestRule01_ZeroWattIdle::test_no_while_true` failed because `python/harlo/sync/policy.py:78` originally contained the literal phrase `while True` inside a docstring. The compliance check is text-pattern based and does not exclude comments/strings.

**Fix:** rephrased the docstring to "no unbounded loops" instead of "no `while True`". The actual control flow already used `for _ in range(len(POLICY_TABLE) + 1):` (bounded), so only the docstring needed editing.

**Per Commandment 7** (fix forward, not down): test was correct, code was wrong (or rather, the docstring tripped a legitimate compliance heuristic). Test left untouched.

This was a 5-minute round-trip caught before commit. The compliance suite is doing exactly what it's supposed to do — catching latent unbounded-loop patterns even in non-executing text.

---

## Constitution compliance

- **Law 1 (zero-watt idle):** ✅ no unbounded loops; explicit bounded iteration in `resolve_policy`.
- **Law 2 (test baseline):** ✅ 1,144 → 1,164 net-positive 20.
- **Law 3 (`pxr` optional):** ✅ `harlo.sync` package imports without `[substrate]`. Strategy modules import persistence lazily inside function bodies.
- **Law 4 (hot-path stays in fast tier):** ✅ sync layer is write-side only. Latency measurement confirms runtime tier latency unchanged.
- **Cmd 5 (Forge doesn't redesign):** ✅ implemented design verbatim.
- **Cmd 7 (fix forward):** ✅ Rule 1 caught and fixed in code, not test.
- **D4:** ✅ `MotorPrim` write-through, `InquiryPrim` checkpoint codified.
- **D5:** ✅ no Injection in policy table; explicit test asserts.

---

## Forge handoff to Crucible

Phase 3 ready for Crucible Gate 3 verification:

| Crucible Gate 3 criterion | Status |
|---|---|
| Hot-path read latency <10% regression | ✅ -4.84% p50 / -3.55% p95 (improved) |
| Per-prim sync policy table complete | ✅ 19 entries, no [NEEDS DECISION] |
| 1,144 baseline preserved | ✅ 1,164 (+20) |
| Round-trip fidelity through sync layer | ✅ `test_flush_round_trip_equality` + `test_persist_round_trip_equality` |

Forge recommends: ✅ Crucible signs Gate 3 green.

*End of Phase 3 Forge report.*
