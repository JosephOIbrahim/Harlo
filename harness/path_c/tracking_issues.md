# Path C Harness — Tracking Issues

**Status:** Long-lived audit document. Append new TIs as filed.
**Initial entry:** Mile 2 Phase A close, 2026-04-28.

---

## TI-001 — Pre-existing test failures (pre-Path-C) — RESOLVED

**Filed:** 2026-04-28 during Mile 2 Phase 0–1 gate close.
**Status:** RESOLVED ON FILING.

### Hypothesis (Phase 0)

Phase 0 baseline measured **1,065 passed / 48 failed / 17 errored / 1 skipped** out of 1,131 collected, vs Mile 1's claimed "1,140 green." The Phase 0 Crucible report
(`verify/mile_2_phase_0_crucible.md`, B2) attributed the ~75-test gap to missing dev deps but flagged that ~52 of those failures *might* be pre-existing failures unrelated to packaging — categorized as:

- mcp test runtime errors (`tests/test_mcp/test_mcp_server.py::*`)
- tactical router import failure (`tests/test_tactical/test_tactical.py::TestRouterImport`)
- Provider/SDK tests (6 failures, possibly env-related)
- ~48 additional failures unenumerated in the Phase 0 tail

### Resolution (Phase A)

Mile 2 Phase A added a `[dev]` extra to `pyproject.toml` declaring `sentence_transformers`, `anthropic`, and `pytest`, and installed it.

Re-running `pytest --tb=no -q` produced **1,133 passed / 0 failed / 0 errored / 1 skipped** in 49.22s.

**All categories enumerated above are now green.** The hypothesized ~52 pre-existing failures **did not exist as a separate phenomenon**. They were collateral from cascading import failures in the encoder, provider, and mcp modules — every one of which imports `sentence_transformers` or `anthropic` directly or transitively. With the dev deps installed, the cascade resolves and the entire suite returns to green.

### What this means

- The Mile 1 "1,140 green" figure was 7 tests off the empirically-measured 1,133 — well within natural drift territory (test files added/removed since whenever the figure was last sourced).
- The `[dev]` extra is the **only** packaging gap. No other latent dev-deps were lurking.
- No further investigation is required.

### Status

**RESOLVED.** TI-001 closes on the same day it filed. Audit trail preserved here for future readers wondering whether Phase 0's "~52 residual failures" was a real concern (it wasn't).

### Re-open conditions

If any of the test categories above breaks again during Phase 2 / 3 / later sessions in a way that **isn't** explained by missing dev deps, re-open TI-001 with the new evidence rather than filing TI-002 — the lineage is informative.

*End of TI-001.*
