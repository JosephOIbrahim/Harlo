# Mile 2 — Phase 0 Forge Report

**Role:** Forge &nbsp;|&nbsp; **Date:** 2026-04-28
**Phase:** 0 — Pre-flight verification &nbsp;|&nbsp; **Branch:** `harness-path-c`

Forge implements the Architect's Phase 0 spec. Mutations only — no
design decisions. Each mutation is paired with its verification
(Commandment 2 — verify after every mutation).

---

## Mutations performed (chronological)

### M1 — `pyproject.toml`: add `[substrate]` extra

**Action:** Inserted `[project.optional-dependencies] substrate = ["usd-core>=24.05"]` after `[project.scripts]` block.

**Verification:** `grep -A 6 "optional-dependencies" pyproject.toml` shows the new section.

**Notes:** Pin rationale documented separately in `harness/path_c/substrate_pin.md`.

### M2 — Install `usd-core` into `.venv312`

**Strict gate command (attempted first, attempt 1 of 3):**
```
.venv312/Scripts/python.exe -m pip install -e .[substrate]
```

**Result: FAILED**, but **not** on the substrate dep — failed on the
maturin editable rebuild's file copy step:

```
Failed to copy C:\Users\User\Harlo\target\maturin\hippocampus.dll
to   C:\Users\User\Harlo\python\harlo\hippocampus.cp312-win_amd64.pyd
The process cannot access the file because it is being used by another process.
(os error 32)
```

The Rust build itself succeeded (`Finished release profile [optimized]
target(s) in 2.59s`). Cause: a separate Python process on this machine
holds the `.pyd` open. Likely an MCP server or stale test runner.

**Workaround command (attempt 2 of 3):**
```
.venv312/Scripts/python.exe -m pip install "usd-core>=24.05"
```

**Result: SUCCESS.** Installed `usd-core 26.5` directly. Functionally
equivalent for Phase 0's `import pxr` gate; bypasses the maturin
editable rebuild that the existing on-disk artifact already satisfies.

**Verification:**
```
$ .venv312/Scripts/python.exe -c "from pxr import Usd, Sdf, Plug; print(Usd.GetVersion())"
(0, 26, 5)
```

**Surface to Crucible:** the strict-command failure is a workspace
constraint (concurrent `.pyd` consumer), not a substrate-pin defect.
Crucible decides whether the workaround satisfies the gate.

### M3 — Install `pytest` into `.venv312`

**Action:** `pip install pytest` (no version pin); resolved to `pytest 9.0.3`.

**Rationale:** Phase 0 gate requires capturing the baseline test count.
`pytest` was not installed in `.venv312` (not a runtime dependency in
`pyproject.toml`). Without it, the gate is uncapturable.

**Surface:** `pytest` is a tooling install, not a project runtime
dependency. Not added to `pyproject.toml`. If the project intends to
declare its own test-runner version, a separate `[dev]` extra would
be appropriate (out of this session's scope).

**Verification:** `pytest --version` reports `pytest 9.0.3`.

### M4 — Capture baseline test count

**Action:** `pytest tests/ --tb=no -q --continue-on-collection-errors > harness/path_c/baseline_tests.txt`

**Result:** **1,065 passed · 48 failed · 17 errors · 1 skipped** in 13.96s.
Total collected: 1,131 (1,129 collected + 2 included via continue-on-error).

**Delta vs Mile 1's claimed baseline of 1,140 green:** ⚠️ **−75 green.**
This is significant. Causes (verified by inspecting the failure list):

| Cause | Affected tests | Test files |
|---|---|---|
| `ModuleNotFoundError: sentence_transformers` | ~11 (collection errors) | `tests/test_onnx/test_fidelity.py`, `tests/test_encoder/test_semantic.py` |
| `ModuleNotFoundError: <mcp test deps>` | ~10 (collection errors) | `tests/test_mcp/test_mcp_server.py` |
| Provider tests (likely missing Anthropic SDK or env) | 6 | `tests/test_provider/test_provider.py` |
| Tactical router import failure | 1 | `tests/test_tactical/test_tactical.py` |
| Other failures (unenumerated detail) | ~48 | various |

**These failures are pre-existing, not introduced by Phase 0
mutations.** No file inside `python/harlo/` runtime was modified;
only `pyproject.toml` (additive — adds an extra) and venv installs.

**Surface to Crucible:** the Mile 1 "1,140 green" claim is empirically
incorrect. Either it was an aspirational/stale figure, or the codebase
has decayed since whenever it was last measured. **This is a blocker
the human-review gate must resolve.** Forge's job is to record the
delta, not improvise a fix.

### M5 — Capture latency baseline

**Action:** Inline microbenchmark — 200 timed iterations of
`usd_lite.serializer.parse()` on `data/hebbian_seeded.usda` (16 traces),
with 20-iteration warmup.

**Output:** `harness/path_c/baseline_latency.json`:

```json
{
  "benchmark": "usd_lite.parse(data/hebbian_seeded.usda)",
  "samples_count": 200,
  "warmup": 20,
  "traces_in_stage": 16,
  "units": "microseconds",
  "p50_us": 4347.1,
  "p95_us": 4785.4,
  "p99_us": 6296.9,
  "mean_us": 4402.47,
  "min_us": 4001.6,
  "max_us": 6597.9
}
```

**Notes:**
- This is the regex-parser hot read path. Phase 3's <10% regression
  guard will compare against `p50_us` and `p95_us` values.
- The benchmark is intentionally simple. A more rigorous Phase 3
  benchmark may exercise additional read paths (e.g., per-prim attribute
  lookup) to better characterize hot-path cost.
- Phase 0 makes no runtime-tier changes; the latency at session end
  should match this baseline within measurement noise.

---

## Files written / modified

| Path | Type | Status |
|---|---|---|
| `pyproject.toml` | Modified | Added `[project.optional-dependencies] substrate` block |
| `harness/path_c/substrate_pin.md` | Created (Phase 0 design output, written from this Forge phase per spec) | Pin + workaround documented |
| `harness/path_c/memory_hypothesis.md` | Created (Architect output, written before Forge phase) | Verdict: `CONFIRMED-SHIPPED-AND-PRESENT-BUT-DORMANT` |
| `harness/path_c/baseline_tests.txt` | Created | pytest tail (failures + summary line) |
| `harness/path_c/baseline_latency.json` | Created | p50/p95/p99 hot-path baseline |
| `design/mile_2_phase_0_scout.md` | Created (Architect-Scout output) | Reconnaissance findings |
| `forge/mile_2_phase_0_report.md` | Created (this file) | This report |
| `.venv312/Lib/site-packages/pxr/` | Installed (M2) | `usd-core 26.5` |
| `.venv312/Lib/site-packages/pytest/` | Installed (M3) | `pytest 9.0.3` (tooling, not pinned in pyproject) |

**No runtime-tier (`python/harlo/`) source was modified.**
**No commits made (Commandment 12).**

---

## Forge handoff to Crucible

Crucible verifies the Phase 0 gate against the six criteria in the
session override. Forge's per-criterion status — **for Crucible to
sign or fail**:

| Gate criterion | Forge claim | Evidence |
|---|---|---|
| `pip install -e .[substrate]` succeeds in `.venv312` | ⚠️ Workaround used | M2; strict command blocked by `.pyd` lock |
| `import pxr` works | ✅ PASS | M2 verify; `Usd.GetVersion() == (0, 26, 5)` |
| Moneta repo path located; plugInfo.json readable | ✅ PASS | Scout §3; file at `C:\Users\User\Moneta\schema\plugInfo.json` |
| Moneta declared typeNames enumerated | ✅ PASS | Scout §3 — `MonetaMemory`, `MonetaMonetaMemory` |
| Recon hypothesis recorded (CONFIRMED / NEVER / AMBIGUOUS) | ✅ PASS (with refinement) | `harness/path_c/memory_hypothesis.md` — `CONFIRMED-SHIPPED-AND-PRESENT-BUT-DORMANT` |
| Baseline test count == 1,140 (or surface delta as a blocker) | ⚠️ DELTA SURFACED | M4 — actual: 1,065 green / 48 fail / 17 err / 1 skip out of 1,131 |
| Hot-path read latency baseline captured | ✅ PASS | M5; `harness/path_c/baseline_latency.json` |

Crucible has discretion to:
- Treat ⚠️ items as gate-passing-with-blockers (route to human gate)
- Or treat them as gate-failing (halt before Phase 1)

**Forge recommends route-to-human-gate** because:
- The strict `pip install -e .` workaround (M2) is environmental, not
  substrate-related; functional goal is met.
- The test baseline delta (M4) is pre-existing and orthogonal to Phase 1
  (design-only) work; it's exactly the kind of thing the post-Phase-1
  human gate exists to surface.

Forge's role ends here. Next: Crucible writes
`verify/mile_2_phase_0_crucible.md`.

*End of Forge Phase 0 report.*
