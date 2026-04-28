# Mile 2 — Phase 3 Crucible Verification

**Role:** Crucible (adversarial verification, Commandment 7) &nbsp;|&nbsp; **Date:** 2026-04-28
**Phase:** 3 — Sync layer &nbsp;|&nbsp; **Branch:** `harness-path-c`

---

## Verdict at a glance

**Phase 3 gate: ✅ PASS — all four Gate 3 criteria green.** Ready for Phase 4 (migration script).

The Rule-1 catch during the baseline regression demonstrated the compliance suite working correctly. Forge's fix-forward response (rephrased the docstring; left the test alone) is exactly what Commandment 7 mandates.

---

## Gate 3 criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Hot-path latency <10% regression vs Phase 0 baseline | ✅ | `harness/path_c/phase_3_latency.json` — delta p50 -4.84%, p95 -3.55% (improved) |
| 2 | Per-prim sync policy table complete (no [NEEDS DECISION]) | ✅ | `policy.py` declares 19 entries; `_validate_table_completeness` runs at import |
| 3 | 1,144 baseline preserved | ✅ | 1,164 green / 1 skip / 0 fail (post-Phase-3) |
| 4 | Round-trip fidelity through sync layer | ✅ | `test_flush_round_trip_equality` (checkpoint → flush → read → equal); `test_persist_round_trip_equality` (write_through → read → equal) |

---

## Adversarial review

### Probe 1 — does the policy table actually cover the 19 typeNames?

`test_policy_table_covers_19_typenames` asserts set equality with the full expected set. **Strong assertion** — would catch any addition or omission. ✅

### Probe 2 — does `resolve_policy` correctly walk INHERIT chains?

`test_specific_inherit_resolutions` pins the expected resolved policy for each container:
- Container → write-through path: `MotorContainerPrim`, `ElenchusPrim`
- Container → checkpoint path: `AssociationPrim`, `CompositionPrim`, `InquiryContainerPrim`, `SkillsContainerPrim`, `CognitiveProfilePrim`
- Root: `BrainStage` → checkpoint (Phase 3 design §3 chose dominant child policy)

**Strong coverage.** Every container is asserted. ✅

### Probe 3 — does `test_unknown_typename_raises` actually exercise D5?

Test calls `resolve_policy("InjectionPrim")` and asserts `KeyError`. **Direct verification of D5 enforcement** at the policy layer — the evicted prim is genuinely unknown, not silently mapped to a fallback. ✅

### Probe 4 — Rule 1 catch in policy.py

A latent `while True` docstring tripped the compliance suite. Forge fixed it correctly: rephrased the docstring; the actual control flow already used a bounded `for` loop. Crucible reads the post-fix `policy.py` and confirms:
- `for _ in range(len(POLICY_TABLE) + 1):` — bounded.
- No `while True` in any code or comment.

**Fix-forward executed correctly.** Test remained untouched (Commandment 7 compliance).

### Probe 5 — does the sync layer keep the hot path off pxr?

`test_no_pxr_required_to_import_sync_package` imports `harlo.sync.policy` and asserts the table is populated. The strategy modules (`write_through.py`, `checkpoint.py`) import `harlo.usd_lite.persistence` lazily *inside function bodies*, so module-level import of `harlo.sync` does not pull `pxr` into `sys.modules`.

The strict subprocess-isolated check is in `tests/test_path_c/test_no_runtime_tier_pxr_import` (Phase 2). That test imports `harlo.usd_lite` (the runtime tier parent) and asserts pxr is absent. The sync package is a sibling, not a child, so it doesn't affect that test.

**Adversarial concern:** does importing `harlo.sync` from inside `harlo.usd_lite` somewhere accidentally chain into pxr? Crucible greps: `harlo.usd_lite/*.py` does NOT import `harlo.sync`. The two are independent. ✅

### Probe 6 — what about the WRITE_BEHIND policy?

The policy enum exposes `WRITE_BEHIND` but no entry in `POLICY_TABLE` uses it. There is no implementation — Phase 3 design §2.3 explicitly defers to a future surgery. **No D4 prim uses write-behind**, so this is a documented stub, not missing work.

If a future caller tries to use a write-behind strategy, they'll find no module path; that's intentional. The enum value exists for completeness so that future surgery doesn't need to add a new `Policy` member.

### Probe 7 — what's NOT covered?

Out-of-scope for Phase 3 (correctly):
- **Auto-dispatch from runtime mutations** — the runtime tier doesn't observe its own mutations; sync layer is opt-in invocation. Future integration is post-Step-6.
- **Concurrent flush from multiple threads** — `Checkpoint` is not thread-safe; documented in design §4.4 ("Per-process, not per-thread"). Future surgery if needed.
- **Partial-subtree writes** — `write_through.persist_prim()` accepts a `prim_path` argument but currently writes the full stage. Documented in `write_through.py` docstring as future optimization.

---

## Phase 3 gate decision

**✅ PASS.** Phase 4 (migration script) may begin.

Crucible signs Phase 3.

*End of Phase 3 Crucible verification.*
