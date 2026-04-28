# Mile 2 — Phase 4 Crucible Verification

**Role:** Crucible (adversarial verification, Commandment 7) &nbsp;|&nbsp; **Date:** 2026-04-28
**Phase:** 4 — Migration script &nbsp;|&nbsp; **Branch:** `harness-path-c`

---

## Verdict at a glance

**Phase 4 gate: ✅ PASS — all three Gate 4 criteria green.** Hard human-review gate engages next (no Phase 5 in this session).

C3 (Forge clarification: `trace_id` attribute on TracePrim) accepted; documented for human signoff alongside C1 (float→double) and C2 (propertyOrder→declaration order).

---

## Gate 4 criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Round-trips `data/hebbian_seeded.usda` without data loss | ✅ | `test_migrate_hebbian_seeded` — parse old format, migrate, read new format, `BrainStage.__eq__` true |
| 2 | Idempotent: running on new-format output is no-op | ✅ | `test_migrate_idempotent` — `input_format == "new"`, `prims_migrated == {}`, no second-pass output written |
| 3 | 1,164 baseline preserved | ✅ | 1,170 green / 1 skip / 0 fail (post-Phase-4) |

---

## Adversarial review

### Probe 1 — does `_detect_format` correctly distinguish formats?

The function tries `Usd.Stage.Open` first (new format check), falls back to text-pattern match (old format check). 

**Adversarial concern:** could the new-format path open OLD-format files? The old USD-Lite format uses `def BrainStage "Brain"` which is also the new-format prim definition. **However**, USD 26.5's parser would reject the old format because `def TracePrim` is followed by attributes that aren't part of the TracePrim schema in old USD-Lite (e.g., `hex` typed-token). And USD validates types it knows about — `Plug.Registry` isn't pre-registered when `_detect_format` runs.

Actually — Crucible does a deeper check: in `_detect_format`, the new-format branch calls `stage.GetPrimAtPath("/Brain")` and asserts `brain.GetTypeName() == "BrainStage"`. For the old format, `/Brain` doesn't exist (the old format defines `BrainStage` as a class spec at the layer root; `/Brain` is the prim name). Wait — actually old format has `def BrainStage "Brain"` where "Brain" IS the prim name — so `/Brain` would resolve.

**Empirical check:** `test_migrate_hebbian_seeded` passes, meaning `_detect_format` correctly returned `"old"` for the hebbian_seeded fixture. So the format detection works for our existing data.

**Adversarial verdict:** detection is empirically correct for the data we have, but the algorithm could in theory misclassify edge cases. For Phase 4's purpose (migrating existing fixtures + supporting idempotent re-runs), this is sufficient.

### Probe 2 — does the migration preserve all 16 hebbian-seeded traces?

`test_migrate_hebbian_seeded` reads `data/hebbian_seeded.usda` via the old USD-Lite parser (canonical reference), migrates, and reads back via the persistence layer. Equality via `BrainStage.__eq__` covers all fields. The CLI smoke test reports `TracePrim: 16` — matches the fixture's content.

**Adversarial concern:** could trace IDs that round-trip via sanitization+attribute lookup produce the wrong dict key? The reader uses `_get_attr(prim, "trace_id")` first, falling back to `prim.GetName()`. If `trace_id` attribute is set, the fallback is unreached.

**Empirical:** all 16 traces survive round-trip with their original IDs (including `26ab7b...` and `test-v7-001`). ✅

### Probe 3 — does idempotence actually work, or is it a partial check?

`test_migrate_idempotent` writes a new-format file directly via `persistence.write`, then invokes `migrate(...)` on it. Asserts:
- `input_format == "new"`
- `prims_migrated == {}`
- The would-be output file is NOT written

**Strong assertion** — three independent checks. ✅

**Adversarial concern:** what if `_detect_format` fails on a new-format file and falls through to "unknown"? Then idempotence becomes "won't run, errors out." Test would catch this (assertion would fail). Empirically passes.

### Probe 4 — does the C3 schema change break Phase 2 tests?

C3 adds `string trace_id` to TracePrim. Phase 2 round-trip test (`test_populated_stage_roundtrip`) uses a TracePrim with `trace_id="ab12cd34"`. After C3:
- Writer sets the attribute.
- Reader reads the attribute back, uses it as the dict key.
- Round-trip equality holds (the dataclass `trace_id` field matches).

Re-running `tests/test_path_c/` confirms: 11/11 pass.

**Adversarial concern:** byte-stability test (`test_roundtrip_byte_stability`). Adding a new attribute changes the file content, but stability is about CONSECUTIVE writes producing identical output, not about the absolute content. Test passes — declaration order discipline still holds.

### Probe 5 — accept C3?

Crucible reviews:
- Phase 1 design §3 specified `/Brain/Association/Traces/<trace_id>` paths — implicit assumption that trace_ids are TF-safe.
- Empirical migration data violates the assumption.
- Forge's options were:
  - (a) Reject non-identifier trace_ids — breaks migration of existing data.
  - (b) Reversibly hex-encode prim names — clutters the path scheme.
  - (c) Use a sanitized presentation name + canonical attribute — separates presentation from semantics.
- Forge chose (c). Adds 1 attribute to schema, 1 sanitization function to writer, 1 attribute lookup to reader.
- The dataclass shape is unchanged.
- Backward compat: reader falls back to prim name when `trace_id` attribute is absent.

**Crucible accepts C3.** Empirically necessary; minimally invasive; documented.

### Probe 6 — what's NOT covered?

Out of scope for Phase 4:
- **Backward migration** (new format → old) — not specified. Not implemented.
- **Partial migration** (migrate only some prims) — not specified. Not implemented.
- **Data validation** — migration trusts the parser's output.
- **Performance** — Phase 4 doesn't have a latency gate (Gate 3 already passed).

These are correctly out of scope for this surgery.

---

## Forge clarifications signoff

| Clarification | Crucible verdict | Documented |
|---|---|---|
| C1 — float → double | ✅ Accept (Phase 2 already signed) | `forge/mile_2_phase_2_report.md` §C1 |
| C2 — propertyOrder via declaration order | ✅ Accept (Phase 2 already signed) | `forge/mile_2_phase_2_report.md` §C2 |
| C3 — `trace_id` attribute on TracePrim | ✅ Accept | `forge/mile_2_phase_4_report.md` |

All three clarifications surface to the human-review gate at session close.

---

## Phase 4 gate decision

**✅ PASS.**

**Hard human-review gate engages now.** Phase 5 (codec-blocker resolution) does NOT begin in this session per session scope. Crucible's verdict + the three Forge clarifications go to the human via the session-close gate review document.

Crucible signs Phase 4.

*End of Phase 4 Crucible verification.*
