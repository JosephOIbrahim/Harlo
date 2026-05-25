# Path D Handoff — Phase-by-Phase Execution Plan

**Audience:** Claude Code session executing this against `/Users/josephibrahim/Harlo`
**Authority:** Subordinate to `02_CONSTITUTION.md`. On any conflict, the Constitution wins.

Each phase declares **Architect output**, **Forge tasks**, **Crucible gate**. Phases run strictly sequentially. No phase begins until the prior gate is signed off green.

---

## Phase 0 — Pre-flight verification

**Status:** Startable now. Does not depend on RSI coordination items.

### Architect output

1. **`harness/path_d/data_inventory.md`** — direct inspection of the data surfaces PVH will read.
   - `data/observations.db` row count, schema (column names, types), partition counts (anchor vs organic)
   - `models/cognitive_predictor_v1.joblib` load-and-introspect: model type, output shape, feature count, feature names if accessible
   - `src/schemas.py` `CognitiveObservation` field inventory
   - Cross-reference: which schema fields are present in actual `observations.db` rows vs declared in `schemas.py`

   This document is the empirical baseline against which RSI coordination items 1 and 2 are resolved. If `delegate_id` / `scaffolding_requirements` / `intervention_type` are present in actual rows, RSI item 1 is resolved by observation. If `delegate_id` appears in the predictor feature list, RSI item 2 is resolved by observation.

2. **`harness/path_d/baseline_tests.txt`** — captured baseline from `pytest tests/ -v --tb=no -q`. Expected count: 1,365 passed / 11 skipped. Any deviation is documented inline.

### Forge tasks

1. Create directory structure:

   ```
   harness/path_d/
   ├── pvh/
   │   ├── __init__.py        # empty, package marker
   │   ├── cli.py             # stub: imports + argparse skeleton
   │   ├── extractor.py       # stub
   │   ├── evaluators.py      # stub
   │   ├── reporters.py       # stub
   │   └── outputs/           # gitkeep, empty
   └── (governance .md files already present)
   ```

2. Capture test baseline:

   ```bash
   cd /Users/josephibrahim/Harlo
   pytest tests/ -v --tb=no -q > harness/path_d/baseline_tests.txt 2>&1
   ```

3. Verify predictor loads in `.venv312`:

   ```bash
   .venv312/bin/python -c "
   from joblib import load
   m = load('models/cognitive_predictor_v1.joblib')
   print(type(m).__name__)
   print(m.estimators_[0].feature_names_in_ if hasattr(m.estimators_[0], 'feature_names_in_') else 'no feature_names_in_')
   "
   ```

   Save output to `harness/path_d/predictor_inventory.txt`.

4. Count observations and inspect schema:

   ```bash
   .venv312/bin/python -c "
   import sqlite3
   conn = sqlite3.connect('data/observations.db')
   c = conn.cursor()
   c.execute('SELECT COUNT(*) FROM observation_buffer')
   print('total:', c.fetchone()[0])
   c.execute(\"SELECT partition, COUNT(*) FROM observation_buffer GROUP BY partition\")
   for row in c.fetchall(): print(row)
   c.execute('SELECT observation_json FROM observation_buffer LIMIT 1')
   import json
   sample = c.fetchone()
   if sample: print('keys:', sorted(json.loads(sample[0]).keys()))
   "
   ```

   Save output to `harness/path_d/observation_inventory.txt`.

5. Author `harness/path_d/data_inventory.md` synthesizing outputs of (3) and (4) into a single reference document.

### Crucible Gate 0 — binary

All must pass:

- `harness/path_d/pvh/` directory structure exists with stub files
- `baseline_tests.txt` shows 1,365 passed / 11 skipped (or documented drift count enumerated; any pre-existing red test listed)
- `predictor_inventory.txt` shows predictor loads and feature list captured (or explicit `no feature_names_in_` if attribute unavailable)
- `observation_inventory.txt` shows row count, partition split, and observed JSON keys for a sample observation
- `data_inventory.md` synthesizes the above into a referenceable document

A failure on any halts Phase 0. The data inventory is the empirical input to resolving RSI coordination items 1 and 2 — if those items can be resolved by observation rather than waiting for RSI response, the assumption-set for Phase 1 is documented in `05_DECISIONS.md` as D20, D21, etc.

**Phase 0 explicitly does NOT require RSI coordination resolution. Phase 1 does.**

### Decisions likely to be filed in Phase 0

- **D20** — observation schema completeness verdict (resolves RSI item 1 by observation OR documents waiting state)
- **D21** — predictor feature-set inclusion of `delegate_id` (resolves RSI item 2 by observation OR documents waiting state)
- **D22** — if schema or features are incomplete: assumption-set for Phase 1 entry, OR explicit halt awaiting RSI

---

## Phase 1 — Extractor Design (Architect-heavy)

**Status:** `[PENDING-RSI-COORDINATION]`

Depends on:

- RSI item 1 resolved (observation schema completeness) — affects what fields the extractor surfaces per row
- RSI item 2 resolved (predictor feature-set / epoch boundary) — affects whether extractor processes full 458 or bounded subset
- RSI item 7 resolved (variant observability) — affects whether extractor must condition on variant identity

Architect output once unblocked:

- `harness/path_d/extraction_strategy.md` — narrative spec
- Session-grouping policy (group rows by `session_id` or equivalent; ordering by `timestamp` or `exchange_index`)
- Trajectory reconstruction policy (how to fill gaps, handle missing fields, define horizon offsets)
- Anchor vs organic handling (PVH analyzes organic primarily; anchor used for predictor-baseline-calibration only)
- Edge case enumeration (sessions with <3 observations, sessions with prediction gaps, observations with missing `delegate_id`)

Forge tasks once Architect output signed:

- (Detailed in Phase 1 amendment to this document, post-RSI-coordination)

Crucible Gate 1 once Forge complete:

- (Detailed in Phase 1 amendment)

---

## Phase 2 — Extractor Implementation

**Status:** `[PENDING — depends on Phase 1]`

Anticipated shape:

- `extractor.py` implements `iter_sessions(db_path) -> Iterator[Session]` reading `observations.db` read-only (SQLite URI `?mode=ro`)
- `Session` dataclass carries reconstructed trajectory with fields per Phase 1 spec
- Hand-authored test `tests/test_path_d/test_pvh_readonly.py` runs the full extractor and verifies database file mtime is unchanged

Crucible Gate 2: read-only verified, extractor passes against actual `observations.db`, 1,365 tests still green.

---

## Phase 3 — Evaluators

**Status:** `[PENDING — depends on Phase 1 (output shape)]`

Anticipated shape:

- `evaluators.py` implements four metrics:
  - **Drift Schema** — per-observation `[timestamp, actual, predicted, lead_time, signal_proxy, deflection_flag, overshoot_baseline_flag]`
  - **Lead-time distribution** — per state-transition, distribution of (prediction-fire-time, actual-transition-time) gaps
  - **Deflection rate** — predicted-crash + scaffolding-fired + actual-not-crash, divided by predicted-crash + scaffolding-fired
  - **Overshoot baseline** — predicted-crash + scaffolding-NOT-fired + actual-not-crash, divided by predicted-crash + scaffolding-NOT-fired
- Signal weakness proxy: Observation Density (gap-based heuristic from Gemini Round 3)
- Cassandra heuristic per `02_CONSTITUTION.md` Article 3

Crucible Gate 3: hand-authored Cassandra fixture passes (5-row trajectory with known averted-crash flagged correctly), 1,365 tests still green.

---

## Phase 4 — Reporters

**Status:** `[PENDING — depends on Phase 3 outputs]`

Anticipated shape:

- `reporters.py` implements two writers:
  - `write_pvh_metrics(rows, path)` — flat JSON array of evaluator output
  - `write_evidence_artifact(summary, path)` — Markdown with summary statistics, lead-time distribution table, ASCII sparkline of drift over time, headline metric (deflection rate vs overshoot baseline with statistical significance call)
- No D3, Plotly, HTML templates. Markdown is the human surface.

Crucible Gate 4: emitted Markdown is parseable, renders correctly in GitHub preview, contains all required sections per `02_CONSTITUTION.md` Article 4.

---

## Phase 5 — Crucible Final Gate

**Status:** `[PENDING — integration]`

Anticipated shape:

- Full end-to-end run: `python -m harness.path_d.pvh.cli --output harness/path_d/pvh/outputs/run_001/`
- Artifact produced: both `pvh_metrics.json` and `evidence_artifact.md`
- Cassandra-fixture regression test still passes
- All 1,365 baseline tests still pass
- `read-only` test passes (`test_pvh_readonly.py`)
- `05_DECISIONS.md` complete with all D20+ filings
- `session_close_YYYY-MM-DD.md` written (mirroring path_c precedent)

Crucible Gate 5 final: human review of the evidence artifact. Architect signs off in writing that the artifact is interpretable — either Harlo demonstrably multiplies, demonstrably doesn't, or the artifact honestly says "not statistically distinguishable from chance with this data."

---

## Pending RSI-coordination resolution

Phases 1–5 are stubbed at intent-level only. Detailed Architect outputs, Forge tasks, and Crucible gates for Phases 1–5 are written *after* RSI coordination items 1 and 2 close.

When coordination resolves:

1. This document is amended with detailed Phases 1–5 specifications
2. Amendment is filed as a decision block in `05_DECISIONS.md`
3. Phase 0 Crucible gate is re-verified (baseline tests, predictor load, observation inventory) before Phase 1 begins

If RSI coordination does not resolve in a timeframe compatible with Joe's working schedule, Phase 0's `data_inventory.md` may be sufficient to document an assumption-set unilaterally and proceed. That choice is filed as a D-block in `05_DECISIONS.md`.

---

## Notes for the executing session

- **Read this entire document and `02_CONSTITUTION.md` before touching any file in the repo.**
- **`pvh-rsi-coordination.md`** is also required reading — the seven open items affect Phase 1 entry.
- Progress markers required throughout: `[Phase N / Step M: ...]`, `[still working: ...]`, `[Crucible Gate N: PASS/FAIL]`.
- Capsule emit at every phase close to allow cross-workstream sync per shared discipline.
- Any contradiction between this document, the Constitution, the in-repo CLAUDE.md, or actual repo state surfaces as `[CONTRADICTION: ...]` and halts pending architect decision.
