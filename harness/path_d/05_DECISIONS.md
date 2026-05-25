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

## D30 — Baseline re-run: collection fixed, execution hits documented USD+tqdm segfault

**Decision:** Documented drift. After D27 (substrate), `pxr` collection errors
are **resolved** — pytest now collects **1376 items / 1 skipped** (= the expected
1,365 + 11 total). But the **full single-process run segfaults deterministically**
(exit 139 / SIGSEGV) at ~26% (around `tests/test_injection/`), so the canonical
"1,365 passed / 11 skipped" tally **cannot be captured in this environment.**

**Rationale / root cause:**
- `NEXT.md:80` already tracks this: *"Investigate the `test_injection` segfault …
  pre-existing flake during full `make verify` runs (USD + tqdm threading
  interaction). Doesn't affect CI (Python 3.12) or isolated test runs."*
- Confirmed pre-existing, NOT a PVH regression: PVH is read-analytical and added
  only `harness/path_d/`. The crash trace shows `Thread 0x…` (threading), matching
  the documented cause.
- Deterministic here across 3 runs (`baseline_tests.txt`,
  `baseline_tests_retry.txt`, `baseline_tests_tqdmoff.txt`). `TQDM_DISABLE=1` did
  not avoid it. `test_injection` passes 37/37 in isolation.
- The canonical 1,365/11 baseline (NEXT.md:13) was produced by `make verify`
  auto-detecting **`.venv314`**, which is **absent** on this machine. `make test`
  uses the same raw `pytest tests/ -v`, so make verify on `.venv312`+usd-core
  would hit the same crash.
- A reproducible cluster of failures/errors appears at ~20% before the crash;
  the full tally is unknowable because the run never completes.

**This resolves the D23 collection blocker** (pxr now present) but replaces it
with a deterministic execution segfault.

**Options for the architect (Commandment 1 baseline integrity):**
1. Accept documented drift: treat NEXT.md:80 as the standing explanation and
   gate later phases on per-module / isolated runs (which pass) rather than a
   single full-suite run; OR
2. Restore/recreate **`.venv314`** and capture the baseline via `make verify`
   (the canonical procedure); OR
3. Add an isolating runner (e.g. `pytest-forked` / `-p forked`, not currently
   installed) so a native crash in one module doesn't abort the session; OR
4. Fix the underlying USD+tqdm threading interaction (NEXT.md item 4, currently
   low priority).

PVH does not choose — Commandment 1 baseline integrity is an architect call.

---

## D31 — `[CONTRADICTION]` Baseline test run MUTATES the analytic corpus (read-only breach by side-effect)

**Decision:** Documented contradiction; **HALT for architect remediation.** PVH
will NOT attempt to repair the corpus (decontamination is a `data/` write and an
architect call).

**Observation:** `data/observations.db` grew **69 → 72 rows** during this
session. The 3 new rows are `partition='organic'`, `session_id='live'`,
`created_at` ≈ **2026-05-25 18:30 UTC** (≈14:30 EDT — within this session's test
runs), vs. the original 69 all dated 2026-05-11. File mtime moved to today; size
73728 → 77824 (one SQLite page).

**Cause:** the full `pytest tests/` baseline capture (handoff Phase 0 step 2 /
architect Step 6) is **not hermetic** — executed tests write to the real
`data/observations.db`. PVH made **no direct write** (git shows zero changes
under `data/`); the mutation is a side-effect of the instructed baseline run.
This only became visible after the D27 fix let tests actually execute (the
pre-merge run aborted at collection, 0 tests, 0 writes).

**Severity: HIGH.** `data/observations.db` is the exact corpus PVH must
read-only-analyze. Constitution Article 1 lists it first among no-write paths.
Capturing the baseline pollutes it. Compounds D24 — the corpus is now 72, of
which 3 are test artifacts.

**Remediation options (architect):**
1. Restore `observations.db` to the pre-session 69-row state from a backup, if
   one exists;
2. Delete the 3 rows where `created_at >= '2026-05-25'` under explicit architect
   authorization (trivially separable by date);
3. Redirect the test suite to a temp/fixture DB (env override) so future
   baseline runs never touch the canonical corpus;
4. Run baseline captures in a **separate clone/worktree** so the analytic tree's
   `observations.db` is never executed against.

**Forward rule (proposed):** future Phase 0 baseline captures must NOT run the
full suite against the analytic tree's `data/`. PVH read-only integrity on the
corpus requires test isolation. Architect to confirm.

---

## D32 — D31 remediation: one-time authorized deletion = corpus restoration (Architect)

**Decision (Architect):** The 3 test-generated rows in `data/observations.db`
(`created_at >= 2026-05-25`) are **AUTHORIZED FOR DELETION as RESTORATION** of the
analytic corpus to its pre-breach state. This is not a polluting write — it
restores integrity the architect's own baseline instruction breached. Article 1
is not violated. ONE-TIME authorization only; no other `data/` writes permitted.

**Audit (logged BEFORE the DELETE, per D32 requirement):**

```
rows_to_delete (obs_id, partition, created_at):   [match_count = 3]
  b9624070  organic  2026-05-25 18:30:17
  bcb9102d  organic  2026-05-25 18:30:17
  d1c0ab6a  organic  2026-05-25 18:30:17
pre-delete count:  72
post-delete count: 69   (verified in Step 2)
safety backup:     /tmp/observations.db.prebreach.bak (77824 bytes, outside repo, not committed)
note: all 3 are partition='organic' test artifacts dated today; none are anchor.
```

---

## D33 — `[RELITIGATION-REQUEST]` Forward rule, Constitution-level (Architect)

**Decision (Architect):** NO full-suite pytest runs against the analytic tree's
`data/`. Future baseline integrity captures use one of: `make verify` on the
canonical venv (per NEXT.md); a separate clone with empty/fixture `data/`;
`pytest-forked` or equivalent isolation.

**Amendment (this request):** `02_CONSTITUTION.md` **Article 1** gains:
> "Baseline test captures that would mutate `data/observations.db` are
> forbidden. Use `make verify` on the canonical venv, or run baselines in a
> separate clone."

Filed as a `[RELITIGATION-REQUEST]` per the Constitution's amendment rule
(silent amendment forbidden). Applied in Step 3.

---

## D34 — D30 baseline integrity: documented drift accepted (Architect)

**Decision (Architect):** The `.venv314` USD+tqdm threading segfault (NEXT.md
known fragility) is **ACCEPTED as known drift**. Canonical baseline =
**1,365 passed / 11 skipped** per `make verify` on `.venv314`. Phase 0's
`baseline_tests.txt` reflects documented drift (deterministic segfault on
`.venv312`+usd-core), not a clean run. Gate 0 criterion 2 passes as
"documented drift per D30/D34."

---

## D35 — `[RELITIGATION-REQUEST]` D24 resolution + scope reframe to methodology validator (Architect)

**Decision (Architect):** The single-session corpus is **ACCEPTED as the actual
organic corpus**. The "458" figure across README and earlier path_d docs was
aspirational/incorrect.

**Measured-corpus correction (executor):** the architect's D35 text says
"~66 organic + 3 anchor / N=66." Measured reality after D32 restoration is
**69 organic, 0 anchor, single `'live'` session (N=69)**. The 3 deleted rows
were organic test artifacts, not anchor; the DB has never held anchor rows.
Authoritative figure for all amendments: **N=69 organic, 0 anchor.**

**path_d v1 REFRAMED as a METHODOLOGY VALIDATOR:**
- Build the full PVH pipeline (extractor → evaluators → reporters).
- Run against the actual N=69 organic single-session corpus.
- Evidence artifact MUST state: *"Methodology proven. Statistical claims about
  Harlo multiplying the user require a larger corpus and are NOT supported by
  N=69 single-session data."*
- v2 (deferred) is the real evidence harness once the corpus grows.

**Amendments (this request), applied in Step 3:**
- `02_CONSTITUTION.md` Article 4 — replace "458 organic observations" with the
  actual corpus + methodology-validator reframe.
- `01_KICKOFF.md` — update all "458" references; add a "Scope Reframe (D35)"
  section.
- `04_DEEP_THINK_BRIEF.md` — append "Phase 0 Discoveries" (D20, D21, D24→D35,
  D31, the v1 reframe).

---

## D36 — TI-002 filed: test suite non-hermetic with analytic corpus (Architect)

**Decision (Architect):** File TI-002 in a new
`harness/path_d/tracking_issues.md` (path_c format). The test suite sharing
`data/observations.db` with production analytics is a Harlo-wide architectural
issue beyond path_d's scope; recommended near-term surgery after path_d v1
ships. Applied in Step 4.

---

## D37 — Phase 1 unblocked by the D35 reframe (Architect)

**Decision (Architect):** The methodology-validator scope does NOT require RSI
items 3–7. Items 1 & 2 are already resolved empirically (D20/D21). Phase 1
design proceeds against the current schema with graceful handling of absent
fields:
- `delegate_id` absent → column-aware analysis (no delegate conditioning);
- `scaffolding_requirements` absent → deflection analysis bounded, with an
  explicit caveat in the evidence artifact.

Phase 1 remains NOT-STARTED here; this decision only records that it is
unblocked. Phase 1 spec authoring awaits the Phase 0 CLOSE sign-off.

---

## D38 — Trajectory Deflection premise (Article 2) INVALIDATED for v1 (Architect)

**Decision (Architect):** The Trajectory Deflection premise as written in Article
2 is **invalidated for v1** given the current predictor. The Constitution assumed
a real forecaster; the actual model has:
- **Target leakage** — `train_predictor.py:113-135`: the target is
  `_encode_targets(trajectory[i])` while the features for observation `i` are in
  the same window (the 4 targets — momentum/burnout/energy/burst_phase — appear
  verbatim as feature indices 74/75/76/94).
- **Undefined horizon** — `predict.py` relabels the horizon-0 output as t+1
  (`exchange_index += 1`); the Constitution assumes a tunable t+horizon; no
  horizon parameter exists in code.

All three layers (training, inference, Constitution) are mutually inconsistent.

---

## D39 — `[RELITIGATION-REQUEST]` v1 narrowed beyond D35 to a self-validating harness (Architect)

**Decision (Architect):** path_d v1 now means:
- Harness runs end-to-end (extract → feed reference model → compute outputs →
  emit artifact).
- Evidence artifact MUST document: (a) corpus N=69 insufficient for statistical
  claims; (b) reference predictor has target leakage per
  `train_predictor.py:113-135`; (c) **no deflection claim is asserted** from v1.
- The harness validates **its own mechanics**, not Harlo's multiplier effect.

**Amendments (this request), applied in Step 3:**
- `02_CONSTITUTION.md` Article 2 — predictor's v1 role is "**reference output to
  characterize, not validated baseline**"; note the leakage limitation.
- `02_CONSTITUTION.md` Article 3 (Cassandra) — preserved as a **v2 concern**;
  inapplicable in v1 with a leaky reference predictor.

---

## D40 — TI-003 filed: predictor target leakage = core/RSI surgery, not path_d (Architect)

**Decision (Architect):** File TI-003 in `tracking_issues.md`.
`models/cognitive_predictor_v1.joblib` was trained with feature-target overlap;
requires retraining with a proper `t+horizon` target schema. **Belongs to the
core-surgery / RSI workstream, NOT path_d.** Escalation candidate — likely the
highest-leverage next surgery after path_d v1 ships. Applied in Step 4 (file).

---

## D41 — Phase 1 prerequisite: confirm no alternative forecaster exists (Architect)

**Decision (Architect):** Before locking D38–D40 amendments, confirm (per
Resolution 4 of the Phase 1 halt) that no non-leaky forecaster exists elsewhere
in the repo. Decision rule: if one is found → HALT before Step 3, architect
re-evaluates D38–D40; if none → D38–D40 stand.

**Investigation (Step 2 findings, logged as observations — not new D-blocks):**

```
1. .joblib files (excl venvs):  ONLY models/cognitive_predictor_v1.joblib
2. *predict* source files:      ONLY src/train_predictor.py, src/predict.py
                                (+ their .pyc) — no alternative
3. regressor classes in src:    ONLY train_predictor.py + predict.py
                                (no RandomForest/LGBM/other model code)
4. models/ contents:            BGE embedder (tokenizer + onnx) + the one
                                cognitive_predictor_v1.joblib. No other model.
5. git log (all refs) predict:  only git-lfs tracking (3f4133a) + regen make
                                targets (aa63953) for the SAME model.
                                No corrected/retrained forecaster commit.
6. NEXT.md:38:                  "Trained this session: XGBoost
                                MultiOutputRegressor ... 111 features" — the
                                same leaky model. No horizon / no leakage fix.

VERDICT: No alternative non-leaky forecaster exists anywhere in the repo.
Decision rule → D38–D40 STAND. Proceed to Step 3 amendments.
```

---

## D42 — Trajectory ordering key (Architect-approved)

Within-session ordering: primary `exchange_index` ASC, tiebreaks
`observation_index` → `created_at` → `obs_id`. Rationale: `schemas.py`
Commandment 3 ("exchange_index is the ONLY temporal key"); `created_at` is too
coarse (all 69 rows in one 4.5h window). Approved per `extraction_strategy.md` §6.

## D43 — Short-session handling (Architect-approved)

Sessions with <3 observations are **emitted** with `below_window_threshold=True`
and zero windows, never dropped — the methodology validator wants a complete
inventory. Approved per §6.

## D44 — Missing `session_id` handling (Architect-approved)

Rows lacking `session_id` group under sentinel `"<no-session-id>"` and are
flagged in metadata (defensive; moot for the current corpus where all rows carry
`session_id`). Approved per §6.

## D45 — Bypass `ObservationBuffer.sample()` (Architect-approved)

The extractor reads via direct read-only SQL ordered by `exchange_index`, NOT
`sample()` — `sample()` orders anchor by `RANDOM()` and organic by `priority
DESC` (`observation_buffer.py:93-138`), which would destroy trajectory order.
Approved per §6.

## D46 — v1 `actual` convention (Architect-approved)

With no horizon (D38), `actual` = state at the window's final observation, so
`predicted ≈ actual` by construction in v1. Documented explicitly in every
artifact rather than hidden. Approved per §6.

## D47 — Reuse `src` encoder by import (Architect-approved)

The extractor imports `src.train_predictor._encode_observation` and
`src.predict.CognitivePredictor` for byte-identical feature parity, rather than
reimplementing. Importing is read-only and does not violate Article 1. Approved
per §6.

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
| D30 | Baseline: collection fixed; deterministic USD+tqdm segfault (NEXT.md:80) | Commandment 1 |
| D31 | `[CONTRADICTION]` baseline run mutated corpus 69→72; read-only breach by side-effect | Article 1 — HALT |
| D32 | One-time authorized deletion of 3 test rows = corpus restoration (Architect) | resolves D31 / Article 1 |
| D33 | `[RELITIGATION-REQUEST]` no full-suite pytest vs analytic data/ (Architect) | Article 1 amended |
| D34 | D30 segfault accepted as known drift; canonical 1,365/11 on .venv314 (Architect) | Commandment 1 |
| D35 | `[RELITIGATION-REQUEST]` corpus = N=69 organic; v1 reframed as methodology validator (Architect) | Article 4 amended |
| D36 | TI-002 filed: test suite non-hermetic with analytic corpus (Architect) | tracking_issues.md |
| D37 | Phase 1 unblocked by reframe; graceful handling of absent fields (Architect) | Handoff Phase 1 |
| D38 | Trajectory Deflection premise INVALIDATED for v1 (leakage + no horizon) (Architect) | Article 2 |
| D39 | `[RELITIGATION-REQUEST]` v1 = self-validating harness; no deflection claim (Architect) | Article 2/3 amended |
| D40 | TI-003: predictor target leakage = core/RSI surgery, not path_d (Architect) | tracking_issues.md |
| D41 | Prereq: confirm no alternative forecaster before locking D38–D40 (Architect) | Phase 1 gate |
| D42 | Ordering: exchange_index primary, then observation_index/created_at/obs_id | extractor design |
| D43 | Short sessions (<3 obs) emitted with flag, not dropped | extractor design |
| D44 | Missing session_id → sentinel group + flag | extractor design |
| D45 | Bypass ObservationBuffer.sample(); direct ordered read-only SQL | extractor design |
| D46 | v1 `actual` = state at window's final obs; predicted ≈ actual by construction | extractor design |
| D47 | Reuse src encoder via import (read-only); no reimplementation | extractor design |

---

*Phase 0 Gate 0 FAILed (D20–D25). Architect resolutions filed (D26–D29) and
applied: predictor materialized (D26), substrate installed (D27), branch synced
with origin/master. Re-run results: predictor loads (D21 confirmed, 111 feats),
collection fixed, but baseline execution hits a documented pre-existing segfault
(D30) AND the run mutated the analytic corpus 69→72 (D31, Article 1 breach by
side-effect). Architect CLOSE decisions D32–D37: corpus restored to 69 (D32),
Article 1 forward rule (D33), segfault accepted as drift (D34), corpus reframe to
N=69 methodology validator + Article 4 amendment (D35), TI-002 filed (D36),
Phase 1 unblocked (D37). Gate 0 verdict at CLOSE: PASS-WITH-DOCUMENTED-DRIFT.
Phase 1 NOT started — awaiting CLOSE sign-off.*
