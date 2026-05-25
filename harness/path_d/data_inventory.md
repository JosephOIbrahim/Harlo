# Path D — Data Inventory (Phase 0 Architect Output)

**Date:** 2026-05-25
**Authority:** Empirical baseline. Subordinate to `02_CONSTITUTION.md`.
**Method:** Direct read-only inspection via `.venv312` (Python 3.12.11).
**Tree:** updated to post-merge `defab04` (synced with `origin/master`). Original
capture was on pre-merge `0498ee1`.
**Status:** Re-run after architect fixes D26 (git-lfs predictor) + D27 (substrate).
Predictor now loads; baseline now collects. One known pre-existing flake remains
(see §6). See `05_DECISIONS.md` (D20–D30) and `corpus_investigation.md`.

This document synthesizes Forge tasks 3 (predictor) and 4 (observations) plus
the `src/schemas.py` field inventory, and cross-references declared schema vs.
stored data. It is the empirical input for resolving RSI coordination items 1 & 2.

---

## 1. `data/observations.db`

| Property | Value |
|---|---|
| Table | `observation_buffer` |
| Columns | `obs_id` TEXT, `observation_json` TEXT, `priority` REAL, `partition` TEXT, `surprise_score` REAL, `created_at` TIMESTAMP |
| **Total rows** | **69** |
| Partition split | `organic` = 69, `anchor` = 0 |
| Distinct `session_id` | **1** (all 69 observations belong to a single session) |
| Access mode used | `file:...?mode=ro` (read-only URI) |

**[CONTRADICTION — dataset cardinality]** Every governance doc references
"the 458 organic observations" (Constitution Article 4; Deep Think Brief;
coordination memo). The DB holds **69** organic observations, 0 anchor, across
a **single** session. The 458-observation corpus is not present in this working
tree. Filed as **D24**.

### Observation JSON structure (sample, top-level keys)

`action, allostasis, delegate, dynamics, exchange_index, injection,
observation_index, schedule, schema_name, session_id, state, version`

Nested blocks:

| Block | Keys |
|---|---|
| `state` | altitude, burnout, context, energy, exercise_recency_days, momentum, sleep_quality |
| `action` | action_type, detail |
| `dynamics` | adrenaline_debt, burst_phase, exchange_velocity, exchanges_without_break, frustration_signal, session_exchange_count, tangent_budget_remaining, tasks_completed, topic_coherence |
| `injection` | alpha, phase, profile |
| `delegate` | **active, task_type** |
| `allostasis` | load, override_ratio_7d, sessions_24h, trend |
| `schedule` | kind, override_reason |

---

## 2. `models/cognitive_predictor_v1.joblib`

**RESULT: PASS — predictor loads (post-fix).** See `predictor_inventory.txt`.

| Property | Value |
|---|---|
| model type | `MultiOutputRegressor` |
| outputs | 4 (`XGBRegressor` per target) |
| inner estimator | `XGBRegressor` |
| `n_features_in_` | **111** |
| `feature_names_in_` | absent (trained on unnamed numpy array) |
| artifact | 377K; LFS `oid sha256:dde0dfd8…`, `size 385803` |

- **History:** on the original checkout (`0498ee1`) this FAILED with
  `FileNotFoundError` (D22) — the LFS-tracked predictor was absent because the
  local branch was 13 commits behind origin. Architect resolution **D26**
  authorized `git lfs pull`; merging `origin/master` brought the
  `.gitattributes` LFS tracking + `!models/...joblib` un-ignore, and the pull
  materialized the 377K artifact. PVH did not train it.

### Feature set (confirmed: static inference == loaded `n_features_in_`)

The loaded model reports **111** features, matching the reconstruction from
`_encode_observation()` + the 3-step sliding window:

```
per observation = 7 (state ordinals)
                + 10 (ActionType one-hot)
                + 9 (dynamics)
                + 5 (InjectionProfile one-hot) + 1 (alpha) + 1 (phase)
                + 4 (allostasis)
                = 37 features
window = 37 x 3 observations = 111 features   [matches documented 111]
```

The `delegate` block is **not encoded**. There is **no `delegate_id`** in the
feature vector. Filed as **D21**.

---

## 3. `src/schemas.py` — `CognitiveObservation` field inventory

Top-level fields (12): `schema_name, version, session_id, observation_index,
exchange_index, state, action, dynamics, injection, delegate, allostasis,
schedule`.

`DelegateBlock` declares exactly: `active: bool`, `task_type: str`.
There is **no** `delegate_id`, **no** `scaffolding_requirements`, **no**
`intervention_type` anywhere in the schema.

---

## 4. Cross-reference — declared schema vs. stored data

| Check | Verdict |
|---|---|
| Top-level keys: `schemas.py` ↔ DB rows | **Exact match** (all 12 present in both) |
| Nested block keys ↔ DB rows | **Exact match** for every block |
| `delegate_id` present? | **No** — absent from schema AND data |
| `scaffolding_requirements` present? | **No** — absent from schema AND data |
| `intervention_type` present? | **No** — absent from schema AND data |

The stored data is fully consistent with the declared schema. The three
PVH-required fields are a genuine **gap** (never modeled), not a schema/data
drift.

---

## 5. Resolution of RSI coordination items by observation

- **Item 1 (observation schema completeness)** — RESOLVED BY OBSERVATION:
  schema is **incomplete** for PVH. None of `delegate_id`,
  `scaffolding_requirements`, `intervention_type` exist. → **D20**.
- **Item 2 (predictor feature-set / pre-LABRE epoch)** — RESOLVED BY STATIC
  INSPECTION: `delegate_id` is **not** in the 111-feature set (the model cannot
  encode a field the schema lacks; `train_predictor.py` confirms the delegate
  block is unencoded). Per the coordination memo, PVH would be bounded to a
  pre-LABRE epoch — but with 69 single-session organic observations and no
  delegate routing represented, the epoch boundary is moot for this corpus.
  Dynamic confirmation via `feature_names_in_` was impossible (artifact absent).
  → **D21**.

---

## 6. Baseline test environment

**Pre-fix (checkout `0498ee1`):** suite aborted at collection — `.venv312`
lacked `pxr`, 3 `tests/test_schedule/` modules failed to import, only 1174 items
collected, 0 executed. → **D23**.

**Post-fix (substrate installed, D27):** collection is **fixed** — pytest now
collects **1376 items / 1 skipped** (= expected 1,365 + 11 total). But the full
single-process run **segfaults deterministically** (exit 139 / SIGSEGV) at ~26%
(around `tests/test_injection/`), so the 1,365/11 tally cannot be captured here.

- Root cause is a **documented pre-existing flake** (`NEXT.md:80`): USD + tqdm
  threading interaction in full-suite runs. Not a PVH regression.
- Confirmed across 3 runs (`baseline_tests.txt`, `baseline_tests_retry.txt`,
  `baseline_tests_tqdmoff.txt`); `TQDM_DISABLE=1` did not avoid it;
  `test_injection` passes 37/37 in isolation.
- Canonical 1,365/11 was produced on **`.venv314`** (absent here) via
  `make verify` (`NEXT.md:13`).
- → **D30** (Commandment 1 baseline integrity is an architect call).

---

## 7. Contradictions summary (status after architect fixes)

1. **Predictor artifact missing** → **RESOLVED.** Materialized via git-lfs after
   merging `origin/master` (D26). Loads; 111 features. (was D22)
2. **Baseline suite** → **PARTIALLY RESOLVED.** `pxr` collection errors gone
   (D27); now collects 1376 items, but execution hits a documented pre-existing
   USD+tqdm segfault. (D23 → D30)
3. **`.venv312` "not USD-compatible" / `NEXT.md` missing** → **RESOLVED by sync.**
   `NEXT.md` and the `substrate` extra exist on `origin/master`; local was 13
   commits behind. `pip install -e ".[substrate]"` makes `.venv312`
   USD-capable (`pxr` imports). (Step 2 observation)
4. **Dataset cardinality** — 69 organic / single `'live'` session vs. documented
   458 (README:27,411). **STILL OPEN, DEFERRED.** (D24, frozen by D29; evidence
   in `corpus_investigation.md`)
5. **Schema gap** — `delegate_id` / `scaffolding_requirements` /
   `intervention_type` absent from schema and data. **STILL OPEN** (resolves RSI
   item 1 as incomplete). (D20)

Of the original four blockers, two are resolved (predictor, venv/NEXT.md), one is
downgraded to a documented pre-existing flake (baseline segfault), and the corpus
gap + schema gap remain for architect/RSI resolution.

---

## 8. Phase 0 CLOSE reconciliation (2026-05-25, D32–D37)

Final reconciled state at Phase 0 close:

| Item | Final state |
|---|---|
| **Corpus** | **69 organic, 0 anchor, single `'live'` session** — RESTORED from the 72-row breached state by deleting 3 test rows (D32; backup `/tmp/observations.db.prebreach.bak`). Date range 2026-05-11 17:21:55 → 21:48:14. |
| **Corpus scope** | "458" was aspirational/incorrect. path_d v1 reframed as a **methodology validator** at N=69 (D35; Constitution Article 4 amended). |
| **Predictor** | Loads; `MultiOutputRegressor`, 4 outputs, **111 features**, no `delegate_id` (D21). |
| **Baseline** | Collection fixed (1376 items). Full-suite run segfaults (USD+tqdm, NEXT.md:80) — **accepted as documented drift** (D34); canonical 1,365/11 is the `make verify` / `.venv314` number. |
| **Read-only rule** | Constitution Article 1 amended (D33): no full-suite `pytest` against the analytic `data/`. TI-002 filed (D36). |
| **Schema gap** | `delegate_id` / `scaffolding_requirements` / `intervention_type` still absent (D20). Phase 1 handles gracefully (D37). |

This document, `corpus_investigation.md`, and `05_DECISIONS.md` (D20–D37)
together are the empirical record for Phase 0. RSI items 1 & 2 are resolved by
observation (D20/D21); items 3–7 are not required for the methodology-validator
scope (D37).
