# Path D — Extraction Strategy (Phase 1 Architect Output)

**Date:** 2026-05-25
**Authority:** Subordinate to `02_CONSTITUTION.md` (as amended by D38/D39).
**Scope:** v1 = **self-validating methodology harness** (D35 + D39). The extractor
reconstructs organic trajectories and produces predictor-ready windows; it does
**not** support a deflection claim (D38). Design only — no code (Phase 2 implements).
**Status:** Authored after the D41 investigation confirmed no alternative
forecaster. Decisions surfaced in §6 are **candidates** (D42+) pending sign-off.

---

## Section 1 — Data Source Contract

**Source:** `data/observations.db`, table `observation_buffer`, opened
**read-only** via SQLite URI: `sqlite3.connect("file:data/observations.db?mode=ro", uri=True)`.
Read-only is mandatory (Article 1; the D33 amendment forbids any mutation of this
file — note that even the *test suite* mutated it, D31, so PVH must never open it
read-write).

**Columns** (`PRAGMA table_info`):

| Column | Type | Use |
|---|---|---|
| `obs_id` | TEXT (PK) | row identity; carried into Session for traceability |
| `observation_json` | TEXT | the serialized `CognitiveObservation` (parse with `CognitiveObservation.model_validate_json`) |
| `priority` | REAL | buffer priority; **not** used for trajectory order |
| `partition` | TEXT | `'organic'` or `'anchor'` |
| `surprise_score` | REAL | metadata only in v1 |
| `created_at` | TIMESTAMP | order tiebreak + inventory; **not** the primary order key |

**`observation_json` structure** (matches `src/schemas.py` `CognitiveObservation`,
verified against all 69 rows): top-level `schema_name, version, session_id,
observation_index, exchange_index` + nested blocks `state, action, dynamics,
injection, delegate, allostasis, schedule`. Every block is fully populated
(Pydantic-defaulted) — no missing keys in the corpus.

**Partition handling:** v1 corpus is `organic=69, anchor=0`. The extractor
processes the **organic** partition as the analytic trajectory set; `anchor` is
read and counted but (per Article 2) would only ever serve predictor-baseline
calibration — with 0 anchor rows this is inert. Design handles `anchor>0`: anchor
rows are grouped/ordered identically but tagged `partition='anchor'` in Session
metadata so downstream code can include/exclude them. **Do not** use
`ObservationBuffer.sample()` — it orders anchor by `RANDOM()` and organic by
`priority DESC` (`observation_buffer.py:93-138`), destroying trajectory order.

---

## Section 2 — Feature Engineering Mapping

The predictor consumes a **111-feature** vector = **37 features/observation × a
3-observation window** (`train_predictor.py:_encode_observation` +
`_build_sliding_window`, `window_size=3`). Per-observation 37 features:

| # | Group | Features (in encode order) |
|---|---|---|
| 1–7 | state (ordinal) | momentum, burnout, energy, altitude, exercise_recency_days, sleep_quality, context |
| 8–17 | action (one-hot) | `ActionType` ×10 (SESSION_START…SESSION_END) |
| 18–26 | dynamics | exchange_velocity, topic_coherence, session_exchange_count, burst_phase, tangent_budget_remaining, exchanges_without_break, adrenaline_debt, tasks_completed, frustration_signal |
| 27–33 | injection | `InjectionProfile` one-hot ×5, alpha, phase |
| 34–37 | allostasis | load, trend, sessions_24h, override_ratio_7d |

Window layout: block A = obs[t-2] (feat 1–37), block B = obs[t-1] (38–74), block
C = obs[t] (75–111).

**Target leakage (D38), documented explicitly.** Training target =
`_encode_targets(obs[t])` = `[momentum, burnout, energy, burst_phase]` of the
window's final observation. Those four values are **already inputs** in block C:
- block C momentum → global index **75**
- block C burnout → global index **76**
- block C energy → global index **77**
- block C dynamics.burst_phase → global index **95**

(1-indexed; 0-indexed 74/75/76/94.) The model is handed its target as input.
**Therefore: "predicted output from this reference model is not a forecast; it is
an approximation of the current state influenced by features that include the
current state."** The extractor encodes windows faithfully but the harness treats
predictor output as *reference characterization*, never as a t+horizon forecast.

**Feature parity decision:** the extractor will **import**
`src.train_predictor._encode_observation` and `src.predict.CognitivePredictor`
rather than reimplement encoding — guaranteeing byte-identical features. Importing
is read-only and does not violate Article 1 (§6 candidate D47).

**Missing-field imputation policy.** The three RSI-item-1 fields are **absent**
from schema and data (D20). Crucially, **none of them is a predictor feature** —
the 111-feature vector is fully determined by the always-present
state/action/dynamics/injection/allostasis blocks. So:

| Field | In 111-feature set? | Policy | Justification |
|---|---|---|---|
| `delegate_id` | No (delegate block unencoded) | **No imputation**; surfaced as `null` in Session metadata | It was never a feature (D21); imputing would fabricate signal. v2-relevant for delegate conditioning. |
| `scaffolding_requirements` | No | **No imputation**; `deflection_flag` emitted as `null` with reason `"scaffolding_requirements unavailable"` | This is the field that would say "did scaffolding fire." Absent → deflection un-attributable; consistent with D39 (no v1 deflection claim). |
| `intervention_type` | No | **No imputation**; surfaced as `null` in metadata | Deflection-attribution field; absent; v2 concern. |

**The 111 feature inputs require zero imputation** — every block is present and
schema-defaulted in all 69 rows. This is stated so Phase 2 does not add defensive
imputation that could mask a future schema regression.

---

## Section 3 — Trajectory Reconstruction

**Session grouping:** by `session_id` read from `observation_json` (not a DB
column). Current corpus: one session, `'live'`, 69 rows.

**Within-session ordering:** primary key **`exchange_index` ASC**
(`schemas.py` Commandment 3: "exchange_index is the ONLY temporal key"),
tiebreak **`observation_index` ASC**, final tiebreak **`created_at` ASC**, final
deterministic tiebreak **`obs_id` ASC**. `created_at` is *not* primary because
many rows can share a coarse timestamp (all 69 share a 4.5h window; 3 test rows
shared an identical second before D32 restoration).

**Minimum trajectory length:** the 3-step window needs ≥3 observations
(`predict.py` requires exactly 3). A session with <3 observations yields **zero
windows**; the extractor still emits the `Session` (with its observations and a
`below_window_threshold=True` flag) so the inventory is complete — it does not
silently drop short sessions (§6 candidate D43). Current corpus: 69 obs → **67
windows** (69 − 3 + 1).

**Multi-session future-proofing:** `iter_sessions(db_path) -> Iterator[Session]`
yields one `Session` per `session_id`, lazily. Going from 1 session to N requires
no API change — the evaluators/reporters consume the iterator. No per-session
state is shared, so the design scales without rewrite. (We do **not** pre-build
cross-session aggregation in v1 — YAGNI; that's a reporter concern when N>1.)

---

## Section 4 — Output Shape

```text
@dataclass(frozen=True)
class Window:
    index: int                      # i (the window's final observation index)
    observations: tuple[Obs, Obs, Obs]   # [t-2, t-1, t], ordered
    predicted: dict[str, int]       # reference-model output {momentum,burnout,energy,burst_phase}
    actual:    dict[str, int]       # state at obs[t] (the window's final obs)
    # v2 columns — present, but pipeline-status in v1:
    deflection_flag: None           # always None in v1 (no scaffolding signal, D39)
    overshoot_baseline_flag: None   # always None in v1
    lead_time: None                 # undefined without a horizon (D38)

@dataclass(frozen=True)
class Session:
    session_id: str
    partition: str                  # 'organic' | 'anchor'
    observations: tuple[Obs, ...]   # ordered per Section 3
    windows: tuple[Window, ...]     # empty if below_window_threshold
    metadata: SessionMeta

@dataclass(frozen=True)
class SessionMeta:
    obs_count: int
    window_count: int
    below_window_threshold: bool
    missing_fields: tuple[str, ...]      # ('delegate_id','scaffolding_requirements','intervention_type')
    dropped_rows: int                    # malformed JSON skipped
    ordering_warnings: tuple[str, ...]   # e.g. created_at disagrees with exchange_index
    created_at_range: tuple[str, str]
```

**`predicted` semantics:** reference-model output at the window's final index,
**subject to the target-leakage limitation (D38)** — documented in every emitted
artifact, not a forecast.

**`actual` semantics:** the state at the window's final observation `obs[t]`.
Because there is **no horizon**, "actual" is the same observation whose fields
also leak into `predicted` — so in v1, `predicted ≈ actual` by construction. This
is the honest v1 statement, not a bug to hide.

**Deflection columns** (`deflection_flag`, `overshoot_baseline_flag`, `lead_time`)
are carried in the schema for v2 forward-compatibility but are **always `None` in
v1**, with the reason recorded in `SessionMeta`. The reporter renders them as
"v2-meaningful; v1 pipeline-status only."

---

## Section 5 — Edge Cases (with handling)

| Case | Handling |
|---|---|
| Session with <3 observations | Emit `Session` with `windows=()`, `below_window_threshold=True`. Never dropped. |
| Malformed `observation_json` | `try/except json/ValidationError` → skip the row, increment `metadata.dropped_rows`, record `obs_id` in an extractor log. Never abort the run. |
| Missing critical field (`session_id`) | Group under sentinel `"<no-session-id>"`, flag in metadata. (Current corpus: all rows have `session_id`; defensive only — §6 candidate D44.) |
| Non-monotonic timestamps within a session | Order by `exchange_index` (authoritative). If `created_at` order disagrees, record an `ordering_warnings` entry but trust `exchange_index`. |
| Duplicate `session_id` across rows | Expected — that is how a trajectory is stored. All rows sharing a `session_id` form one `Session`. No collision logic needed. |
| Empty result set | `iter_sessions` yields nothing; CLI/reporter emit an artifact stating "0 sessions, 0 windows" rather than erroring. |
| Database locked / unavailable | `mode=ro` open fails → raise a clear `ExtractorError` with the path; CLI exits non-zero with a human message. No retry loop (Rule 1: no polling). |

---

## Section 6 — Decisions Surfaced for Architect Review (D42+ candidates)

Each is a real choice with viable alternatives; I picked one and want explicit
approval before they become D-blocks (post-sign-off, per the phase rule).

- **D42 (candidate) — Ordering key.** Primary `exchange_index` ASC, tiebreaks
  `observation_index` → `created_at` → `obs_id`. *Alt:* `created_at` primary.
  **Recommend `exchange_index`** (Commandment 3). Approve?
- **D43 (candidate) — Short sessions.** Emit with `below_window_threshold` vs
  drop. **Recommend emit-with-flag** (methodology validator wants full
  inventory). Approve?
- **D44 (candidate) — Missing `session_id`.** Sentinel-group vs skip.
  **Recommend sentinel `"<no-session-id>"` + flag.** Approve? (Moot for current
  corpus.)
- **D45 (candidate) — Bypass `ObservationBuffer.sample()`.** Read via direct
  read-only SQL ordered by `exchange_index`, *not* `sample()` (which randomizes).
  **Recommend direct SQL.** Approve?
- **D46 (candidate) — v1 `actual` convention.** With no horizon, `actual` =
  state at the window's final obs (so `predicted ≈ actual`). **Recommend
  documenting this explicitly** as the v1 convention. Approve?
- **D47 (candidate) — Reuse `src` encoder by import.** Import
  `src.train_predictor._encode_observation` + `src.predict.CognitivePredictor`
  for byte-identical parity (import is read-only). *Alt:* reimplement in
  `pvh/`. **Recommend reuse-by-import.** Approve?

---

## Section 7 — Phase 2 Forge Task Preview (NO code yet)

`extractor.py` will implement:
- `iter_sessions(db_path: str) -> Iterator[Session]` — read-only URI open; group
  by `session_id`; order per §3; build `Window`s reusing the imported `src`
  encoder + `CognitivePredictor`.
- `Session` / `Window` / `SessionMeta` dataclasses (§4).
- Malformed-row skipping + metadata accounting (§5).
- An `ExtractorError` for DB-unavailable.

**Test surface for the Phase 2 Crucible Gate** (`tests/test_path_d/`):
1. `test_pvh_readonly` — run the extractor end-to-end; assert
   `data/observations.db` **mtime and row count unchanged** (the D31/D33 guard).
2. `test_session_grouping` — 69 organic rows → 1 session `'live'`.
3. `test_window_count` — 69 obs → exactly 67 windows.
4. `test_ordering_determinism` — shuffled input rows → identical ordered output.
5. `test_short_session` — a 2-obs fixture → `below_window_threshold`, 0 windows.
6. `test_malformed_json_skip` — a bad-JSON row → skipped, `dropped_rows==1`, run
   completes.
7. `test_empty_db` — empty buffer → 0 sessions, no error.
8. `test_feature_parity` — extractor's window encoding equals
   `train_predictor._build_sliding_window` on the same trajectory (parity guard).
9. `test_missing_fields_metadata` — `metadata.missing_fields` lists the three
   absent fields; deflection columns are `None`.

Phase 2 also adds the hand-authored fixtures (short session, malformed row,
empty DB) under `tests/test_path_d/`. **Per D33, the read-only guard test must
run against a fixture/temp DB, never the canonical `data/observations.db`.**
