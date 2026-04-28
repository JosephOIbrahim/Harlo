# Mile 2 — Phase 6 Test Repair + Final Crucible Design

**Role:** Architect &nbsp;|&nbsp; **Date:** 2026-04-28
**Authority:** subordinate to D19 (1,170 baseline floor) + F2 (mandatory mixed-stage test).

---

## 1. Test repair scope

**Expected: minimal.** Phase 5 evicted a file that was never referenced by any test (verified). Phase 5 made no source-code changes. The 1,170 baseline held green at Phase 5 close. Therefore no test repair is expected for Phase 6.

If any test breaks during Phase 6 baseline regression, Forge fixes it forward (Cmd 7) — but the prior prediction is "zero new failures."

## 2. F2 — Mixed-stage TracePrim test (MANDATORY per Cmd 7 and session override)

### 2.1 Test purpose

Verify that the C3 reader fallback path (legacy TracePrim without `trace_id` attribute) correctly produces dict-key-consistent output when mixed with new-format TracePrims (with `trace_id` attribute) in the same stage.

### 2.2 Scenario to test

Construct a USD stage that contains BOTH:
- **Legacy TracePrim:** prim path `/Brain/Association/Traces/legacy_trace_alpha`. **No `trace_id` attribute set.** Reader must fall back to prim name → dict key = `"legacy_trace_alpha"`.
- **New-format TracePrim:** prim path `/Brain/Association/Traces/t_99deadbeef` (sanitized form). **`trace_id` attribute = `"99deadbeef"`** (canonical, original starts with digit). Reader uses attribute → dict key = `"99deadbeef"`.

Read the stage via `harlo.usd_lite.persistence.read`. Verify:
- `bs.association.traces` has exactly 2 entries
- One entry keyed by `"legacy_trace_alpha"` (fallback path)
- One entry keyed by `"99deadbeef"` (attribute path)
- The two dataclass instances have correct `trace_id` field values matching their dict keys

### 2.3 Implementation strategy

The test cannot use `persistence.write` because the writer always sets `trace_id`. Instead, the test authors the stage directly via `pxr.Usd.Stage` API:

```python
from pxr import Sdf, Usd, Plug
import harlo.usd_lite.persistence  # registers schema plugin

stage = Usd.Stage.CreateNew(target_path)
stage.DefinePrim("/Brain", "BrainStage")
stage.DefinePrim("/Brain/Association", "AssociationPrim")
stage.DefinePrim("/Brain/Association/Traces", "Scope")  # untyped grouping prim

# Legacy TracePrim: no trace_id attribute
legacy = stage.DefinePrim("/Brain/Association/Traces/legacy_trace_alpha", "TracePrim")
legacy.CreateAttribute("content_hash", Sdf.ValueTypeNames.String).Set("legacy_hash")
legacy.CreateAttribute("strength", Sdf.ValueTypeNames.Double).Set(0.5)
# ... minimum required attributes (with defaults) ...
# DELIBERATELY NO trace_id attribute

# New-format TracePrim: with trace_id attribute
new = stage.DefinePrim("/Brain/Association/Traces/t_99deadbeef", "TracePrim")
new.CreateAttribute("trace_id", Sdf.ValueTypeNames.String).Set("99deadbeef")
new.CreateAttribute("content_hash", Sdf.ValueTypeNames.String).Set("new_hash")
# ... minimum attributes ...

stage.GetRootLayer().Save()
```

Then read via `persistence.read` and assert dict keys.

### 2.4 What this test guarantees

- Reader fallback to `prim.GetName()` works when `trace_id` attribute is absent.
- Reader uses `trace_id` attribute when present.
- The two paths can co-exist in a single stage without dict key collision.
- Future schema migrations that introduce/remove the `trace_id` attribute will not silently break the dict-key contract (the test pins the expected behavior).

## 3. Crucible Gate 6 criteria (final gate before Mile 3)

| # | Criterion | How verified |
|---|---|---|
| 1 | Test baseline ≥ 1,170 + F2 test added | `pytest tests/ --tb=no -q` reports ≥1,171 green |
| 2 | F2 mixed-stage test passes | The new test under `tests/test_path_c/` |
| 3 | Hot-path read latency <10% regression vs Phase 0 baseline | Re-run microbenchmark; compare to `harness/path_c/baseline_latency.json` |
| 4 | Byte-stability test still passes (declaration order discipline holds) | `test_roundtrip_byte_stability` |
| 5 | Subprocess SchemaRegistry test still passes | `test_schema_registry_loads_all_harlo_types_in_subprocess` |

## 4. Phase 6 deliverables

| Path | Action | Authored by |
|---|---|---|
| `design/mile_2_phase_6_test_repair.md` | Created (this doc) | Architect |
| `tests/test_path_c/test_mixed_stage.py` | Created (F2 test) | Forge |
| `forge/mile_2_phase_6_report.md` | Created | Forge |
| `verify/mile_2_phase_6_crucible.md` | Created | Crucible |

## 5. Architect handoff to Forge

Forge:
1. Author `tests/test_path_c/test_mixed_stage.py` per §2 spec.
2. Run pytest on the new test in isolation to verify it passes.
3. Run full baseline; expect 1,171 green / 1 skip / 0 fail.
4. If any pre-existing test breaks: 3-retry budget per Cmd 3, fix forward, document.

*End of Phase 6 design.*
