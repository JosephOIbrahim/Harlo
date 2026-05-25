# Path D Harness — Locked Decisions

**Status:** Phase 0 (Pre-flight) &nbsp;|&nbsp; **Authority:** subordinate to
`02_CONSTITUTION.md`; continues the path_c lineage (D1–D19). &nbsp;|&nbsp;
Date opened: 2026-05-25

Decisions are filed in real time per Constitution Article 6. Retroactive
D-blocks are forbidden. Lineage continues at **D20**.

---

## D20 — Observation schema completeness (resolves RSI item 1 by observation)

**Decision:** RSI item 1 is **resolved by observation as INCOMPLETE.** The
`CognitiveObservation` schema (`src/schemas.py`) and every stored row in
`data/observations.db` lack all three PVH-required fields: `delegate_id`,
`scaffolding_requirements`, `intervention_type`. The `delegate` block carries
only `active` and `task_type`.

**Rationale:** Direct read of `schemas.py` `DelegateBlock` + cross-reference
against 69 stored observation JSON blobs. Top-level and nested keys match the
declared schema exactly; the three fields are a genuine never-modeled gap, not
a drift.

**Implication for Phase 1:** PVH's deflection analysis depends on
`scaffolding_requirements` (did scaffolding fire between prediction and
outcome?) and ideally `delegate_id`. Neither exists. Phase 1 (extractor design)
cannot define the deflection-flag derivation without a joint RSI decision to add
these fields to the schema and re-collect, OR an explicit proxy. This is a hard
blocker, consistent with Phase 1's `[PENDING-RSI-COORDINATION]` status.

---

## D21 — Predictor feature-set / `delegate_id` (resolves RSI item 2 by static inspection)

**Decision:** RSI item 2 is **resolved by static inspection: `delegate_id` is
NOT in the 111-feature XGBoost set.** Dynamic confirmation via
`feature_names_in_` was impossible because the model artifact is absent (D22);
resolution is therefore via `src/train_predictor.py` source.

**Rationale:** `_encode_observation()` encodes state (7) + ActionType one-hot
(10) + dynamics (9) + InjectionProfile one-hot (5) + alpha (1) + phase (1) +
allostasis (4) = 37 features/observation, x a 3-step sliding window = 111
features. This reproduces the documented count exactly and confirms the
`delegate` block is never encoded. A model trained on this encoder cannot carry
`delegate_id`.

**Implication:** Per the coordination memo, PVH analysis would be bounded to a
pre-LABRE epoch. However, the corpus is 69 organic observations in a single
session with no delegate routing represented, so the epoch boundary is moot for
this data. Carried forward for when a real corpus exists.

---

## D22 — Predictor artifact is absent; PVH will not generate it

**Decision:** `models/cognitive_predictor_v1.joblib` **does not exist** and PVH
will **NOT** generate it. Crucible Gate 0 Commandment 3 (predictor load
contract) **FAILS**.

**Rationale:** `models/` is gitignored (`.gitignore:15`) — the predictor is a
locally-generated artifact (via `src/train_predictor.py`), never committed and
absent from this working tree (`models/` holds only the BGE embedding model).
Constitution **Article 1** makes `models/` read-only for PVH; generating the
artifact would be a write to a protected path. Generation is therefore a human
decision, not a PVH action.

**Options for the human at the gate:**
1. Run `.venv312/bin/python src/train_predictor.py` to (re)generate the artifact
   (requires the training dataset; note the 69-vs-458 corpus gap, D24), then
   re-run Phase 0; OR
2. Point PVH to the predictor's actual location if it lives elsewhere; OR
3. Accept that PVH cannot proceed past Gate 0 until the artifact exists.

---

## D23 — Baseline test drift: suite cannot run (`pxr` missing in `.venv312`)

**Decision:** Documented drift. The baseline suite **did not run**. Commandment 1
(baseline integrity = 1,365 passed) **cannot be established in this environment.**

**Rationale:** `.venv312` lacks the `pxr` (OpenUSD) module. Three
`tests/test_schedule/` modules import `from pxr import ...` and fail at
collection (`test_migration.py`, `test_reload.py`, `test_usd_roundtrip.py`).
pytest aborts the entire session on collection errors, so 0 of 1174 collected
items executed (4 skipped). Expected: 1,365 passed / 11 skipped — note even the
collected count (1174) is short of ~1,376, suggesting additional uncollected
modules.

**[CONTRADICTION]** The setup note calls `.venv312` "the USD-compatible venv per
NEXT.md." `.venv312` has no `pxr`, and no other venv or `pxr` install exists in
the repo. `NEXT.md` does not exist anywhere in the repo to reconcile this.

**Implication:** Later Crucible gates that re-verify "1,365 tests still green"
have no valid baseline until a USD-capable interpreter runs the suite. Human
decision required: provide/point to a `pxr`-enabled environment, or amend the
baseline expectation.

---

## D24 — Dataset cardinality: 69 organic observations, not 458

**Decision:** Documented contradiction. The analytic corpus is **69 organic
observations in a single session**, not the "458 organic observations" cited in
Constitution Article 4, the Deep Think Brief, and the coordination memo.

**Rationale:** `SELECT COUNT(*) FROM observation_buffer` = 69; partition split
= organic 69 / anchor 0; distinct `session_id` = 1.

**Implication:** Article 4's scope ("single-architect dataset (the 458 organic
observations)") does not match reality. With a single session, trajectory
reconstruction yields one trajectory of 69 observations — likely insufficient
for the lead-time distribution and deflection-vs-overshoot delta to reach
statistical significance. This strengthens the case that the eventual evidence
artifact may honestly report "not statistically distinguishable." Human decision
required on whether the 458-observation corpus exists elsewhere or whether
Article 4 should be amended via `[RELITIGATION-REQUEST]`.

---

## D25 — Phase 1 entry: explicit HALT

**Decision:** **Do not enter Phase 1.** Phase 0 closes at Crucible Gate 0 with a
**FAIL** verdict, and the session **HALTS for human sign-off** as instructed.

**Rationale:** This satisfies the handoff's anticipated "D22: assumption-set OR
explicit halt" as an explicit halt. Four independent blockers preclude a
documented assumption-set robust enough to proceed:
- predictor artifact absent (D22) — Gate 0 Commandment 3 hard-fails;
- baseline suite cannot run (D23) — no integrity baseline to preserve;
- schema missing all three RSI-item-1 fields (D20) — deflection derivation
  undefinable;
- corpus is 69/single-session vs. 458 (D24) — Article 4 scope invalid.

Phase 1 is independently `[PENDING-RSI-COORDINATION]`; this halt does not
shortcut any work that was startable.

---

## D26 — D22 resolution: git-lfs predictor materialization is repo-state prep (Architect)

**Decision (Architect):** Predictor regeneration via git-lfs is **repo state
preparation, not PVH-internal work.** Constitution Article 1 is **not violated**
when the architect pulls existing artifacts the repo already tracks via git-lfs.
Architect **authorizes git-lfs operations** for the predictor.

**Rationale:** Article 1's read-only discipline constrains PVH's analytic writes;
materializing a tracked artifact via `git lfs pull` is repo provisioning, the
same class of action as cloning. The architect, not PVH, performs it.

**Note for executor:** Phase 0 evidence (D22) found `models/` gitignored and the
`.joblib` not in `git ls-files`. If `git lfs pull` does not materialize the
predictor, that conflicts with this decision's premise — surface as
`[CONTRADICTION]` and halt per the action sequence.

---

## D27 — D23 resolution: substrate install in `.venv312` is repo-state prep (Architect)

**Decision (Architect):** Substrate installation in `.venv312` is **repo state
preparation per path_c precedent.** Article 1 **not violated.** Architect
**authorizes `pip install -e ".[substrate]"`** in `.venv312`.

**Rationale:** Installing the USD substrate (`pxr`) into the isolated `.venv312`
provisions the environment; it does not write to any PVH-protected path
(`data/`, `models/`, `src/`, `python/harlo/`, `crates/`).

---

## D28 — Commit Phase 0 FAIL artifacts as historical record (Architect)

**Decision (Architect):** **Commit the Phase 0 FAIL artifacts as a historical
record BEFORE any fixes.** The FAIL is part of the methodology's paper trail.

**Rationale:** The harness methodology values the audit trail; a green-only
history would erase the empirical contradictions that drove D20–D29.

---

## D29 — D24 (corpus 69 vs 458) is DEFERRED pending investigation (Architect)

**Decision (Architect):** D24 is **DEFERRED pending investigation.** Do **not**
act on any reframe of Article 2 or any other Constitution amendment until the
corpus question is resolved and the architect signs off.

**Rationale:** The 69-vs-458 gap may reflect an alternate observation surface or
a history of buffer movement, not a true corpus loss. A diagnostic
(`corpus_investigation.md`) gathers evidence; the decision stays with the
architect.

**Executor constraint:** `corpus_investigation.md` presents evidence only. The
executor does NOT make the corpus decision.

---

## Observations (non-decision log)

### Obs 2026-05-25 — Step 2 verification: local checkout is 13 commits behind `origin/master`

Per the architect's Step 2 instruction (note as observation, not a D-block):

- Local `harness-path-d` base = `0498ee1`; `origin/master` (post-fetch) = `092f420`.
  `git log master..origin/master` = **13 commits** local does not have, including:
  - `3f4133a chore: track predictor artifacts via git-lfs`
  - `303239f docs(next): document git-lfs as primary path for predictor artifacts`
  - `2d4b7b7 docs: NEXT.md ...`
  - `f0ce331 Phase 5A: macOS bundle, intake calibration, biometric barrier, operator tooling (#10)`
- **`NEXT.md`** is NOT genuinely missing from canonical master — it exists on
  `origin/master`, absent only from the local (behind) checkout.
- **Predictor LFS:** `.gitattributes` (`models/*.joblib filter=lfs`) and the
  `!models/cognitive_predictor_v1.joblib` un-ignore exist on `origin/master`
  only. Local has no `.gitattributes` and gitignores all of `models/`. The
  origin LFS pointer is valid: `oid sha256:dde0…`, `size 385803` (~385KB).
- **`substrate` extra IS present locally** (`pyproject.toml:32`,
  `usd-core>=24.05`) — Step 4 is unblocked on the current checkout.
- **`git-lfs` binary is NOT installed** (`git-lfs not found`).

**Implication (for architect, not an executor decision):** D26/D27 fixes cannot
execute on the current local checkout. Materializing the predictor (D26) requires
BOTH (a) `brew install git-lfs` AND (b) syncing `harness-path-d` with
`origin/master` so the LFS tracking + pointer + un-ignore are present. (b) is a
merge/rebase that modifies read-only protected paths (`src/`, `python/harlo/`
via the Phase 5A bundle) and is NOT covered by D26/D27 — it needs explicit
architect authorization. Halting at Step 3 per the action sequence.

---

## Decision summary table

| # | Decision | Authority touched |
|---|---|---|
| D20 | Observation schema INCOMPLETE — 3 PVH fields absent | RSI item 1 / Article 2,3 |
| D21 | `delegate_id` NOT in 111-feature set (static) | RSI item 2 / Article 2 |
| D22 | Predictor artifact absent; PVH won't generate (Article 1) | Gate 0 Commandment 3 |
| D23 | Baseline suite can't run (`pxr` missing); no baseline | Commandment 1 |
| D24 | Corpus = 69 organic / 1 session, not 458 | Article 4 |
| D25 | Explicit HALT; do not enter Phase 1 | Handoff Phase 0 close |
| D26 | git-lfs predictor materialization = repo-state prep (Architect) | resolves D22 / Article 1 |
| D27 | `pip install -e ".[substrate]"` in `.venv312` = repo-state prep (Architect) | resolves D23 / Article 1 |
| D28 | Commit FAIL artifacts as historical record before fixes (Architect) | methodology |
| D29 | D24 corpus question DEFERRED pending investigation (Architect) | Article 2/4 — frozen |

---

*Phase 0 Gate 0 FAILed (D20–D25). Architect resolutions filed (D26–D29).
Re-running Phase 0 with fixes; new Gate 0 verdict pending.*
