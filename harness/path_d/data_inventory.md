# Path D — Data Inventory (Phase 0 Architect Output)

**Date:** 2026-05-25
**Authority:** Empirical baseline. Subordinate to `02_CONSTITUTION.md`.
**Method:** Direct read-only inspection via `.venv312` (Python 3.12.11).
**Status:** Captured with material contradictions — see "Contradictions" and `05_DECISIONS.md` (D20–D25).

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

**RESULT: FAIL — artifact does not exist.** (`FileNotFoundError`; see
`predictor_inventory.txt`.)

- `models/` is gitignored (`.gitignore:15`); the predictor is a locally-generated
  artifact, never committed and absent here.
- `models/` currently holds only the BGE embedding model
  (`bge-small-en-v1.5.onnx` + tokenizer) — not the cognitive predictor.
- Generator exists: `src/train_predictor.py` (`joblib.dump`, default
  `--output models/cognitive_predictor_v1.joblib`).
- **PVH did not generate it.** Article 1 makes `models/` read-only for PVH.
  Filed as **D22**.

### Feature set (inferred statically from `src/train_predictor.py`)

Because the artifact is absent, `feature_names_in_` could not be read. The
feature vector is reconstructed from `_encode_observation()` + the 3-step
sliding window:

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

See `baseline_tests.txt`. **Suite did not run**: `.venv312` lacks the `pxr`
(OpenUSD) module, causing 3 collection errors in `tests/test_schedule/`
(`test_migration.py`, `test_reload.py`, `test_usd_roundtrip.py` — all
`from pxr import ...`). pytest aborts the whole session on collection errors,
so 0 of 1174 collected items executed (4 skipped). Expected: 1,365 passed /
11 skipped. `.venv312` is **not** USD-compatible despite the setup note. → **D23**.

---

## 7. Contradictions summary (all surfaced, none silently resolved)

1. **Predictor artifact missing** — Gate 0 Commandment 3 fails. (D22)
2. **Baseline suite cannot run** — `pxr` missing in `.venv312`; 0 passed vs
   expected 1,365. (D23)
3. **Dataset cardinality** — 69 organic / single session vs. documented 458. (D24)
4. **`.venv312` not USD-compatible** — contradicts the "USD-compatible venv per
   NEXT.md" setup note; `NEXT.md` does not exist. (folded into D23)
5. **Schema gap** — `delegate_id` / `scaffolding_requirements` /
   `intervention_type` absent. (D20)
