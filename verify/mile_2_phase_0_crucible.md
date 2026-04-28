# Mile 2 — Phase 0 Crucible Verification

**Role:** Crucible (adversarial verification, Commandment 7) &nbsp;|&nbsp; **Date:** 2026-04-28
**Phase:** 0 — Pre-flight verification &nbsp;|&nbsp; **Branch:** `harness-path-c`

Crucible verifies the Phase 0 gate against the six criteria in the
session override. Crucible neither designs nor implements; it grades.

---

## Verdict at a glance

**Phase 0 gate: ⚠️ CONDITIONAL PASS — two blockers routed to human gate.**

The functional pre-flight state is sufficient to begin Phase 1
(design-only). However, two of the six criteria failed strict
evaluation; Crucible routes them to the human review gate at session
end rather than halting now, because both blockers are orthogonal to
Phase 1's design work.

This is **not** a green light. It is "the human must consciously
decide whether to accept the deltas before Phase 2 (Forge work in a
future session) commences."

---

## Per-criterion grading

### C1. `pip install -e .[substrate]` succeeds in `.venv312`

**Strict reading:** ❌ FAIL.

The command did not exit 0. Maturin reported:
> Failed to copy C:\Users\User\Harlo\target\maturin\hippocampus.dll
> to C:\Users\User\Harlo\python\harlo\hippocampus.cp312-win_amd64.pyd
> The process cannot access the file because it is being used by another process. (os error 32)

**Functional reading:** ⚠️ CONDITIONAL PASS.

The substrate dependency installed via fallback path
(`pip install "usd-core>=24.05"`). The maturin failure is environmental
(another Python process holds the `.pyd`), not a defect in the substrate
pin or the `[substrate]` extra declaration. The end state — `pxr` is
in `.venv312` — matches the gate's intent.

**Crucible position:** ⚠️ ROUTE TO HUMAN. Adversarial test: a future
Forge session retrying the strict command must succeed. If it doesn't,
the `[substrate]` extra is broken in a way this session didn't detect.
The human should require the strict command to pass before Phase 2
implementation begins.

### C2. `import pxr` works

✅ **PASS.**

```
$ .venv312/Scripts/python.exe -c "from pxr import Usd, Sdf, Plug; print(Usd.GetVersion())"
(0, 26, 5)
```

USD 26.5 is importable. `Usd`, `Sdf`, `Plug` modules all reachable —
the three modules Phase 1's subprocess SchemaRegistry test (Phase 2
Forge work) will need.

### C3. Moneta repo path located; plugInfo.json readable

✅ **PASS.**

`C:\Users\User\Moneta\schema\plugInfo.json` exists, is readable, contains
a valid Plug-Registry JSON declaration for plugin name `"moneta"`.

### C4. Moneta declared typeNames enumerated

✅ **PASS.**

Two typeNames: `MonetaMemory` (the canonical schema identifier) and
`MonetaMonetaMemory` (the prefixed alias used by Plug.Registry). Both
recorded in `design/mile_2_phase_0_scout.md` §3.

**Adversarial check:** are there other typeName-bearing artifacts in
Moneta beyond `plugInfo.json`? Crucible spot-checked
`MonetaSchema.usda` and `generatedSchema.usda` — both declare exactly
one `class MonetaMemory`. No additional typeNames found. Enumeration
complete.

### C5. Recon hypothesis recorded

✅ **PASS** (with refinement noted).

`harness/path_c/memory_hypothesis.md` filed with verdict
`CONFIRMED-SHIPPED-AND-PRESENT-BUT-DORMANT`. The user override allowed
three options (`CONFIRMED | CONFIRMED-NEVER | AMBIGUOUS`); Architect
chose a refinement of `CONFIRMED` rather than picking strictly, with
documented evidence.

**Adversarial check:** does the refinement matter? Yes — the
"PRESENT-BUT-DORMANT" qualifier flags that `src/cognitive_stage.py`
holds an active pxr import and is part of the eviction blast radius
of Phase 5 Commandment 10 (eviction of `cognitive_twin.usda`). Future
phases would have missed this if the verdict had been a flat
`CONFIRMED-NEVER`.

### C6. Baseline test count == 1,140 (or surface delta as a blocker)

⚠️ **DELTA SURFACED — BLOCKER ROUTED TO HUMAN.**

**Strict reading:** the count is 1,065 green (1,131 collected total),
not 1,140. Numerical match fails.

**Escape clause:** the criterion's parenthetical "or surface delta as a
blocker" is satisfied by Forge's M4 in
`forge/mile_2_phase_0_report.md`. The delta is empirical, documented,
attributed to specific causes, and not introduced by any Phase 0
mutation.

**Crucible's adversarial position on this is sharper than Forge's:**

1. The Mile 1 harness was authored citing "1,140 tests" as if known. It
   was not measured at Mile 1; the number was an assumption that has
   now been falsified.
2. Constitution Law 2 — "1,140 tests stay green at every gate" — is
   structurally undermined. It cannot be enforced if no observed state
   of the codebase has 1,140 green tests.
3. Treatment options the human must choose between:
   - **(a)** Revise Constitution Law 2 to reflect the actual measured
     baseline (1,065 green or whatever post-dev-dep-install reaches).
     Update `02_CONSTITUTION.md` and `01_KICKOFF.md`. Continue.
   - **(b)** Halt and install missing dev dependencies
     (`sentence_transformers`, `mcp` test deps, possibly Anthropic SDK
     for provider tests) until the green count climbs back near
     1,140 — then verify that's defensible.
   - **(c)** Accept 1,065 as new baseline only for Path C work; old
     stale tests separately tracked. Hybrid.
4. **None of the three is Crucible's choice to make.** Surfaced to
   the human-review gate.

This blocker is the largest-blast-radius finding of Phase 0. It does
not block Phase 1 design (which is independent of test execution), but
it must be resolved before Phase 2 (Forge work) begins, because Phase 2
Crucible verification depends on a defensible baseline.

### C7. Hot-path read latency baseline captured

✅ **PASS.**

`harness/path_c/baseline_latency.json` filed with p50=4347μs,
p95=4785μs, p99=6296μs over 200 samples.

**Adversarial check:** is the benchmark representative? It exercises
`usd_lite.serializer.parse` on a 16-trace stage. This is one read path;
the runtime tier has more (per-attribute reads, container traversal,
SDR codec calls). A more comprehensive Phase 3 benchmark suite is
likely needed. Forge flagged this in M5 notes. Crucible concurs but
does not require a richer benchmark in Phase 0 — the gate criterion
says "captured", which is satisfied.

---

## Two blockers routed to human gate

| # | Blocker | Severity | Resolution required by |
|---|---|---|---|
| B1 | Strict `pip install -e .[substrate]` failed on `.pyd` file lock; workaround used | Low (environmental, not architectural) | Before Phase 2 Forge begins |
| B2 | Test baseline is 1,065 green, not 1,140 — Mile 1 number was wrong | **High (structural — undermines Constitution Law 2)** | Before Phase 2 Forge begins (mandatory) |

B2 is the more important one. It is not a Phase 0 deficiency; it is a
Mile 1 harness defect that Phase 0 surfaced. The harness's Constitutional
guarantee about test count was never grounded in measurement.

---

## Phase 0 gate decision

**Decision: ⚠️ CONDITIONAL PASS. Phase 1 may proceed; B1 and B2 attach
to the post-Phase-1 human-review gate.**

Conditions:
- Phase 1 work is design-only (per session override).
- No additional mutations to runtime tier this session.
- Human review at session end addresses B1 and B2 explicitly.
- If human declines to accept B2's resolution, Mile 2 halts before
  Phase 2 begins (a future session) regardless of how good Phase 1's
  design output is.

Crucible signs Phase 0 with this conditional. Architect-as-Phase-1
may begin.

*End of Phase 0 Crucible verification.*
