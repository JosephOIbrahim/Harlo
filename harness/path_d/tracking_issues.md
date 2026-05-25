# Path D Harness — Tracking Issues

**Status:** Long-lived audit document. Append new TIs as filed.
**Initial entry:** Phase 0 CLOSE, 2026-05-25.

---

## TI-002 — Test suite non-hermetic with the analytic corpus — OPEN

**Filed:** 2026-05-25 during Phase 0 CLOSE (per D36).
**Status:** OPEN. Recommended near-term surgery after path_d v1 ships.
**Severity:** HIGH (data integrity).

> Note on numbering: TI-001 lives in `harness/path_c/tracking_issues.md`
> (pre-existing test failures, resolved 2026-04-28). This is a distinct,
> unrelated issue; numbering continues across the harness lineage as TI-002.

### Observation (Phase 0)

Running the full `pytest tests/` suite against the analytic tree wrote 3 new
observations to `data/observations.db` (69 → 72 rows; see D31). The rows were
real `partition='organic'`, `session_id='live'` entries dated to the test run
(2026-05-25), indistinguishable in schema from genuine organic observations.
Restored to 69 under D32 (`DELETE WHERE created_at >= '2026-05-25'`).

### Root cause

The Harlo test suite shares `data/observations.db` with production analytics —
one or more tests (executed in the first ~26% of the suite, before the unrelated
USD+tqdm segfault, D30) connect to the canonical DB in read-write mode and
persist observations rather than using a temp/fixture DB.

### Blast radius (beyond path_d)

- **PVH (path_d):** any baseline/CI run mutates the exact corpus PVH must
  read-only-analyze. Mitigated for path_d by the D33 Article 1 amendment
  (no full-suite captures against the analytic `data/`).
- **RSI workstream:** LABRE downstream analytics consume the same observation
  buffer; non-hermetic tests would corrupt their inputs too.
- **Any future analytic surgery** against `observations.db` inherits this hazard.

### Recommended surgery (near-term, after path_d v1)

1. Point the test suite at an isolated DB (env override / fixture, e.g.
   `HARLO_OBSERVATIONS_DB` → tmp path) so no test touches the canonical corpus.
2. Add a hermeticity guard (a test that asserts `observations.db` mtime is
   unchanged after a suite run, mirroring the planned `test_pvh_readonly.py`).
3. Audit which tests write observations and convert them to fixtures.

### Re-open / close conditions

- **Close** when the suite is provably hermetic w.r.t. `data/observations.db`
  (guard test green; full-suite run leaves row count and mtime unchanged).
- Until then this stays OPEN and is referenced by D31/D32/D33.

*End of TI-002.*
