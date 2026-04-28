# Memory Hypothesis — Resolution

**Phase 0 Architect output** &nbsp;|&nbsp; **Date:** 2026-04-28
**Source of evidence:** `design/mile_2_phase_0_scout.md` §1.

---

## Verdict

**`CONFIRMED-SHIPPED-AND-PRESENT-BUT-DORMANT`**

A refinement of the three options the session override enumerated
(`CONFIRMED | CONFIRMED-NEVER | AMBIGUOUS`). Closest to `CONFIRMED`,
but with the explicit qualifier that the shipped code was **never
stripped** — it remains in `src/`, simply de-activated by removing
`pxr` from the active virtualenv.

## Evidence chain (verbatim)

```
8658777  Sprint 2 Phase 0: USD 26.03 build — Circuit Breaker triggered
7b9bcff  2026-03-30 12:29:29 -0400  Sprint 4 Phase 1: CognitiveStage — real pxr.Usd.Stage
0b4973d  2026-03-30 12:30:34 -0400  Sprint 4 Phase 2: Backend swap — all tests pass on real USD
bb96d43  2026-03-30 12:31:34 -0400  Sprint 4 Phase 3: Real .usda verified — Cognitive Twin is USD
bba7a31  2026-03-30 12:44:21 -0400  Sprint 5 Phase 1+2: Engine wired to real USD + graceful degradation
```

`git log -- src/cognitive_stage.py src/usd_bootstrap.py` returned
two commits: `a16b707` (public release, 2026-04-01) and `f830aeb`
(rename, 2026-04-03). **No deletion commit.** Code paths still
contain `from pxr import Sdf, Usd` (cognitive_stage.py:21) and
`from pxr import Usd` (usd_bootstrap.py:31).

## Implications for harness execution

1. **Phase 0 Forge proceeds with `pip install -e .[substrate]`** —
   `usd-core` from PyPI, not the vendored `C:\USD\26.03-exec`
   install the Sprint 4 bootstrap consumes. Pip is portable; the
   vendored install is per-machine.
2. **Phase 1 design draws on Sprint 4 code as reference material**
   for prim-attribute typing decisions (e.g., how `CognitiveStage`
   wrote `def Scope` blocks vs. how Path C will write
   `class TypeName "TypeName" (inherits = </Typed>)` blocks).
3. **Phase 5 eviction of `data/stages/cognitive_twin.usda`
   (Commandment 10) will silently break `src/cognitive_stage.py`'s
   read path** — flagged in scout §6 for Architect attention in a
   later phase. Out of this session's scope.

## What "PRESENT-BUT-DORMANT" means concretely

- Sprint 4 source files (`src/cognitive_stage.py`,
  `src/usd_bootstrap.py`, `src/engine_config.py`) and tests
  (`tests/test_sprint4/{test_cognitive_stage.py,
  test_backend_parity.py, test_live_usda.py}`) **import `pxr`**.
- `pxr` is **not in `.venv312/Lib/site-packages/`**.
- Therefore those modules raise `ImportError` on import in the
  current environment.
- After Forge installs `usd-core`, those modules become importable
  again; their tests may start running and pass/fail/skip.
- **Test baseline of 1,140 (the Mile 1 number) may shift.** Forge
  captures the post-install baseline; any delta is reported.

*End of memory hypothesis resolution.*
