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

---

## TI-003 — Predictor target leakage + undefined horizon — OPEN

**Filed:** 2026-05-25 during Phase 1 extractor design (per D40).
**Status:** OPEN. Belongs to **core-surgery / RSI workstream, NOT path_d.**
Escalation candidate — likely highest-leverage surgery after path_d v1 ships.
**Severity:** HIGH (model validity).

### Observation (Phase 1)

`models/cognitive_predictor_v1.joblib` (XGBoost `MultiOutputRegressor`, 111
features) was trained with **feature-target overlap** and has **no defined
forecasting horizon**:

- **Target leakage** — `src/train_predictor.py:113-135` (`_build_sliding_window`):
  features = `[obs[i-2], obs[i-1], obs[i]]`; target = `_encode_targets(obs[i])`
  (same index `i`). `_encode_observation` (`:64-66, :80`) puts those four target
  values (momentum/burnout/energy/burst_phase) into the feature vector at indices
  74/75/76/94. The model can satisfy the objective by echoing four of its inputs;
  reported accuracy is not evidence of forecasting skill.
- **Undefined horizon** — training target is the current state (horizon 0);
  `src/predict.py` relabels the output as t+1 (`exchange_index += 1`, `:82`,
  docstring "predict next state"); `02_CONSTITUTION.md` Article 2 assumes a
  tunable `t+horizon`. Three inconsistent notions, no horizon parameter in code.

### Blast radius

- **PVH (path_d):** invalidates Option δ (predictor as un-intervened baseline).
  v1 reframed to a self-validating harness (D38/D39); no deflection claim.
- **RSI / core:** any subsystem consuming predictor output as a forecast
  (routing, scaffolding triggers, recalibration) inherits the limitation.
- **Evidence ambition:** the original predict/intervene/multiply artifact is
  impossible until this is fixed.

### Recommended surgery (core/RSI, after path_d v1)

1. Redefine the training target as a **future** observation `state(t+h)` for an
   explicit horizon `h`, drawn from a later trajectory index — not `obs[i]`.
2. Remove the current-state fields from the feature window at the prediction step
   (or accept them only as lagged context at `t-1`, `t-2`, never `t` for the
   leaked targets), eliminating feature-target overlap.
3. Re-validate with a held-out forecasting metric (not in-window reconstruction).
4. Version the artifact (`cognitive_predictor_v2.joblib`) and re-activate
   Constitution Articles 2 & 3 for PVH v2.

### Re-open / close conditions

- **Close** when a leakage-free, horizon-defined forecaster exists and passes a
  genuine forecasting metric; then PVH v2 can assert deflection.
- Until then OPEN; referenced by D38/D39/D40 and the Article 2/3 v1 amendments.

*End of TI-003.*
