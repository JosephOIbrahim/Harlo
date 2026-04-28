# Mile 2 — Phase 4 Forge Report

**Role:** Forge &nbsp;|&nbsp; **Date:** 2026-04-28
**Phase:** 4 — Migration script &nbsp;|&nbsp; **Branch:** `harness-path-c`

---

## Files written / modified

| Path | Type | Verification |
|---|---|---|
| `python/harlo/migrate_path_c.py` | Created (executable module) | `python -m harlo.migrate_path_c data/hebbian_seeded.usda` produces real-USD output |
| `tests/test_migrate_path_c/__init__.py` | Created (empty package) | Pytest collects |
| `tests/test_migrate_path_c/test_migration.py` | Created (6 tests) | 6/6 pass |
| `schema/HarloSchema.usda` | Modified (added `string trace_id` to TracePrim) | Schema parses; Crucible round-trip tests pass |
| `schema/generatedSchema.usda` | Modified (added `string trace_id` to TracePrim) | Same |
| `python/harlo/usd_lite/persistence/writer.py` | Modified (`_sanitize_prim_name`, set `trace_id` attribute) | Smoke + round-trip tests pass |
| `python/harlo/usd_lite/persistence/reader.py` | Modified (read `trace_id` attribute, falls back to prim name for legacy stages) | Same |

**Lines authored: ~430** (Phase 4 migration script + tests + schema/writer/reader edits). Productivity floor cleared.

---

## Forge clarification C3 — `trace_id` as a TracePrim attribute

**Issue surfaced during migration of `data/hebbian_seeded.usda`:**

USD's `Usd.Stage.DefinePrim()` rejects prim names that aren't valid TF identifiers (`^[A-Za-z_][A-Za-z0-9_]*$`). Hebbian-seeded trace IDs include:
- `26ab7b0812da44b4` (starts with digit)
- `test-v7-001` (contains hyphens)

Phase 1 design §3 specified `/Brain/Association/Traces/<trace_id>` as the path — implicitly assuming trace_ids are TF-safe. They aren't.

**Resolution:**
- Added `string trace_id` attribute to `TracePrim` schema.
- Writer sanitizes the prim name (replace non-identifier chars with `_`, prefix `t_` if leading digit) and stores the canonical ID in the `trace_id` attribute.
- Reader uses the `trace_id` attribute as the dict key, falling back to the prim name for legacy stages predating C3.

**Per Commandment 5** (Forge doesn't redesign): this is a clarification of Phase 1 design's path scheme that empirical migration testing exposed. Same shape as C1 (float→double precision) and C2 (propertyOrder→declaration order). Documented for human-gate signoff.

---

## Verification results

### Migration tests (6 tests)

```
$ pytest tests/test_migrate_path_c/ -v --tb=short
6 passed
```

- `test_migrate_hebbian_seeded` — round-trip: parse old format → migrate → read new format → equal ✅
- `test_migrate_idempotent` — running on new format is no-op ✅
- `test_migrate_unknown_format` — invalid input → exit code 1 ✅
- `test_migrate_dry_run` — dry-run reports prim counts; no file written ✅
- `test_migrate_cli_smoke` — `python -m harlo.migrate_path_c ...` invocation ✅
- `test_migrate_report_structure` — `MigrationReport.to_dict()` exposes expected keys ✅

### CLI smoke test output (during test run)

```
input:  data/hebbian_seeded.usda
format: old
output: <tmp>/cli_output.usda
prims migrated: 26
  AssociationPrim: 1
  BrainStage: 1
  CognitiveProfilePrim: 1
  CompositionPrim: 1
  ElenchusPrim: 1
  InquiryContainerPrim: 1
  IntakeHistoryPrim: 1
  MotorContainerPrim: 1
  MultipliersPrim: 1
  SkillsContainerPrim: 1
  TracePrim: 16
codec conversions: 81
```

26 prims successfully migrated, 81 codec conversions (16 traces × 5 codec fields + 0 layers × 1 + 1 IntakeHistory).

### Full baseline regression

```
$ pytest tests/ --tb=no -q
1170 passed, 1 skipped in 54.29s
```

- Pre-Phase-4: 1,164 green
- Post-Phase-4: 1,170 green / 1 skip / 0 fail / 0 err
- Net-positive: **+6** (Commandment 2 satisfied)

### Schema regression check (C3 didn't break Phase 2 tests)

The C3 addition of `trace_id` attribute changed the schema. Crucible's Phase 2 round-trip tests (`tests/test_path_c/`) still pass — the new attribute is set and read correctly. Byte-stability test still passes — declaration order preserved.

---

## Constitution compliance

- **Law 2 (test baseline):** ✅ 1,164 → 1,170 net-positive 6.
- **Law 3 (`pxr` optional):** ✅ `migrate_path_c.py` imports pxr only inside `_detect_format` (try/except for env without substrate); core import path is clean.
- **Cmd 5 (Forge doesn't redesign):** ✅ C3 clarification documented; not a silent change.
- **Cmd 7 (fix forward):** ✅ schema change accommodates real migration data instead of restricting to test-only IDs.
- **D5:** ✅ migration script does not produce `InjectionPrim` / `InjectionContainerPrim` (writer omits per persistence layer).

---

## Forge handoff to Crucible

Phase 4 ready for Crucible Gate 4:

| Crucible Gate 4 criterion | Status |
|---|---|
| Round-trips `data/hebbian_seeded.usda` without data loss | ✅ `test_migrate_hebbian_seeded` |
| Idempotent on new format | ✅ `test_migrate_idempotent` |
| 1,164 baseline preserved | ✅ 1,170 (+6 migration tests) |

Forge recommends: ✅ Crucible signs Gate 4 green. C3 clarification surfaced for human-gate signoff.

*End of Phase 4 Forge report.*
