# Path D — Corpus Investigation (Step 5 diagnostic)

**Date:** 2026-05-25
**Status:** EVIDENCE ONLY. Feeds the deferred **D24** (corpus 69 vs 458). Per
**D29**, the corpus decision and any reframe of Constitution Article 2/4 remain
with the architect. This document does not decide.
**Tree:** post-merge `defab04` (local `harness-path-d` synced with
`origin/master` 092f420).

---

## The question

Governance docs and the README cite **"458 organic observations"** as PVH's
analytic corpus. `data/observations.db` holds **69**. Where are the 458?

---

## Evidence

### E1 — `data/observations.db` (the live buffer)

| Property | Value |
|---|---|
| Total rows | **69** |
| Partition | `organic` = 69, `anchor` = **0** |
| Distinct `session_id` | **1** (`'live'`) |
| `created_at` range | **2026-05-11 17:21:55 → 21:48:14** (~4.5h, single day) |

All 69 observations come from one ~4.5-hour `'live'` session on 2026-05-11.

### E2 — No alternate observation surface

- `data/observations/` directory: **absent**.
- All `.db` files in the repo (excl. venvs): `data/observations.db`,
  `data/twin.db`.

### E3 — `data/twin.db` does NOT hold the 458

Tables: `traces, reflexes, graph_edges, sessions, patterns, trust_ledger,
elenchus_pending, hot_traces, hot_traces_fts*`. Row counts: `traces`=1,
`sessions`=17, `reflexes`=0, `patterns`=0, `hot_traces`=1, rest 0. This is the
hippocampal memory store, **not** an observation corpus. No `observation`-like
table.

### E4 — `data/trajectories_10k.jsonl` is SYNTHETIC training data, not organic

- LFS file, **226 MB, 10,000 lines**.
- Matches Constitution Article 2: the predictor was "Trained on 10K synthetic
  trajectories via Profile-Driven Markov Biasing." This is the **predictor
  training set**, categorically distinct from organic observations.

### E5 — README documents 458 with a DIFFERENT composition than reality

- `README.md:27` — "458 organic observations collected · 5 sprints shipped ·
  Path C closed (Step 3)"
- `README.md:411` — diagram: "Observation Buffer / anchor 20% · organic 80% /
  458 observations"

Documented: **458 total, ~20% anchor / ~80% organic** (≈92 anchor / ≈366
organic). Actual DB: **69 total, 0% anchor / 100% organic, single session.**

### E6 — git history

Observation-buffer paths were touched only in `a16b707` (Initial public release
v9.0.0) and `ebcbb0b` (Sprint 1 Phase 5). The `.db` itself is gitignored/local;
no committed history of a 458-row corpus.

---

## Discrepancies (vs. documented 458)

1. **Count:** 69 actual vs 458 documented.
2. **Composition:** 100% organic / 0 anchor actual vs documented 80% organic /
   20% anchor.
3. **Structure:** a single `'live'` session (69 obs, one afternoon) vs an
   implied multi-sprint corpus ("collected · 5 sprints shipped").

---

## Candidate explanations (NOT decided — for architect)

- **(a) Buffer reset / consolidation.** A prior 458-observation corpus may have
  been reduced to the current 69-observation `'live'` session by APOPTOSIS
  (Rule 5 physically deletes) or a buffer reset. All 69 rows date to a single
  2026-05-11 session; an earlier corpus would predate this and is not present.
- **(b) Documentation drift.** 458 (with anchor/organic split) may be a
  historical/aspirational figure in README + path_d governance docs that the
  working tree no longer matches.
- **(c) Off-tree corpus.** The 458 could live in an un-committed/un-synced
  location (another machine, backup, or a regen output). No local evidence
  found. Note: `origin/master` adds `make regen-trajectories` /
  `regen-predictor` targets — those regenerate **synthetic** trajectories, not
  organic observations, so they would not restore the 458 organic corpus.

---

## Open question for the architect (D24, deferred per D29)

What is PVH's analytic target?

1. The **current 69-observation single `'live'` session** (accept reality; amend
   Article 4's "458" and the anchor/organic assumption via
   `[RELITIGATION-REQUEST]`); OR
2. A **restored/re-collected 458 corpus** (locate or rebuild it before Phase 1); OR
3. A **documentation correction** if 458 was never a literal local artifact.

Constitution Article 2 (predictor-as-baseline) and Article 4 (scope = "the 458
organic observations") both hinge on this. **No reframe until architect
sign-off (D29).** With only 69 single-session observations, note the standing
risk (D24) that the eventual evidence artifact may honestly report "not
statistically distinguishable."
