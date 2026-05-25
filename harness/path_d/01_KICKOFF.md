# Path D Kickoff — Predictive Validation Harness (PVH)

**Created:** 2026-05-25
**Branch:** suggest `harness-path-d`
**Audience:** Future Joe + any Claude Code session executing this
**Authority:** Subordinate to `02_CONSTITUTION.md`

---

## Why this surgery exists

Harlo is positioning to be the OS-level scaffolding layer for neurodivergent cognition during long-horizon work — the system that watches physical and emotional state across days and weeks, uses USD composition to hold persistent cognitive state, and multiplies what the user can do because it holds threads they cannot always hold themselves.

The five production sprints (S1–S5) shipped the substrate, the state machines, the predictor, the delegate pattern, and graceful degradation. They proved the architecture can run. They did not prove the architecture **multiplies** anyone.

That proof needs an evidence artifact. The artifact answers three questions, in the user's own organic data:

1. **Does Harlo predict accurately?** What does the predictor get right, where does it drift, and what's the lead-time distribution on its predictions?
2. **Does Harlo intervene meaningfully?** When scaffolding requirements fire, do trajectories deflect away from predicted crashes — or does the predicted crash arrive anyway?
3. **Does Harlo multiply the user, or just observe them?** Is the deflection rate distinguishable from the predictor's overshoot baseline (model error rate on un-scaffolded predictions)?

`path_d/` ships the harness that produces this artifact.

---

## What ships at the end

- `harness/path_d/pvh/` — Python module: `extractor.py`, `evaluators.py`, `reporters.py`, `cli.py`
- `pvh_metrics.json` — machine-readable drift artifact (per-observation rows: timestamp, actual, predicted, lead_time, signal_proxy, deflection_flag, overshoot_baseline_flag)
- `evidence_artifact.md` — human-readable evidence document (summary stats, lead-time distribution, Cassandra-attributed events, headline metric)
- Hand-authored Cassandra-scenario test fixture in `tests/test_path_d/`
- 1,365 baseline tests still green at every Crucible gate
- D20+ decisions filed in `05_DECISIONS.md` as execution surfaces them

---

## Scope boundaries

**In scope:**

- Read-only analysis of `data/observations.db`
- Loading and inference against `models/cognitive_predictor_v1.joblib`
- Output artifacts under `harness/path_d/pvh/` outputs directory
- Test surface specific to this harness

**Out of scope (v1):**

- Writing analytical Overs back into USD stages
- Modifying the predictor
- Producing variants programmatically
- Authoring through any delegate at production time
- Feeding LABRE or any RSI-side reputation system
- NLP coherence parsing of exchange content
- Causal modeling (do-calculus, structural causal models)
- New observation fields (those are joint with RSI workstream; see coordination)

---

## Coordination context — parallel RSI workstream

A concurrent RSI workstream is building reputation tracking (LABRE), monitoring (Q3), and downstream subsystems (DLPL, CSCGAS, PCRV) that operate on the delegate layer one abstraction above where PVH sits.

Cross-workstream coordination memo: `pvh-rsi-coordination.md` (filed 2026-05-25).

**Seven open items** identified in that memo. Two are hard blockers for path_d Phase 1:

1. `[BLOCKING-NEW]` Observation schema completeness (`delegate_id`, `scaffolding_requirements`, `intervention_type`)
2. `[BLOCKING-NEW]` Pre-LABRE epoch boundary OR predictor feature-set confirmation

Phase 0 of this path can start without RSI resolution. **Phase 1 does not begin until items 1 and 2 are resolved OR an explicit assumption-set is documented in `05_DECISIONS.md`.**

---

## Phase shape

Five sequenced phases via Architect/Forge/Crucible pattern, mirroring `harness/path_c/` precedent.

```
Phase 0 — Pre-flight              [STARTABLE NOW]
Phase 1 — Extractor design        [PENDING-RSI-COORDINATION]
Phase 2 — Extractor implementation [PENDING — depends on Phase 1]
Phase 3 — Evaluators              [PENDING — depends on Phase 1]
Phase 4 — Reporters               [PENDING — depends on Phase 3]
Phase 5 — Crucible final gate     [PENDING — integration]
```

Each phase has binary Crucible gate criteria. Phases run strictly sequentially. No phase begins until the prior gate is signed off green.

---

## What was rejected (so it stays rejected)

Three rounds of Gemini Deep Think exchanges and one cross-workstream coordination round produced the architectural commitments captured in `02_CONSTITUTION.md`. The exchanges also produced explicit rejections worth preserving:

- **Git-log as cognitive telemetry** (Gemini Round 1). Author + timestamp + lines-added is Git velocity, not cognitive telemetry. A 500-line refactor at 2am during a crash and a 500-line burst-mode flow look identical to that parser. Harlo's input domain is structured cognitive observations from MCP tool calls, not Git activity.

- **"Counterfactual Execution" naming** (Gemini Round 2). The mechanism is predictive validation, not counterfactual analysis. Counterfactual analysis would require causal inference modeling (do-calculus, structural causal models) we do not possess. Calling an observational analysis script "counterfactual" loses credibility with skeptical reviewers. Renamed to Predictive Validation Harness (PVH).

- **A-feeds-D coupling** (Gemini Round 2). Pre-optimizing PVH for a hypothetical synthetic stress test (Option D from strategic options) creates architectural tax in service of work that may never happen. Decoupled. Capture patterns that obviously serve D *if* they emerge; do not pre-design for D.

- **Synthetic-only validation as headline evidence** (Gemini Round 2 → 3). The 278K synthetic exchanges from S1 are a stress test of the cognitive physics engine, not evidence the system multiplies a real user. Headline evidence must operate on the 458 organic observations, not synthetic-only.

- **Allostatic Efficiency requiring kill-switch baseline** (Gemini Round 3). Asking the architect to deliberately work without scaffolding for 2 weeks to generate baseline data is biologically expensive and halts the sprint. Rejected in favor of Option δ (Trajectory Deflection) using the predictor itself as un-intervened baseline.

- **Writing analytical Overs back to USD stages in v1** (Gemini Round 3 MVP cut). Wrestling with USD composition API for output writing blows the 3–5 day estimate. v1 holds analysis in Python memory, outputs JSON + Markdown only. USD-Over writing is a v2 consideration.

---

## Predecessor work

- `harness/path_c/` — precedent for this methodology. Path C closed 2026-04-28 with codeless schema surgery, 21 prim types, real OpenUSD as canonical persistence, sync layer, migration script. Decision lineage D1–D19.
- Three Gemini Deep Think strategic exchanges (consolidated in `04_DEEP_THINK_BRIEF.md`).
- `pvh-rsi-coordination.md` cross-workstream handoff (2026-05-25).

Decision lineage continues at D20.

---

## Success criterion

Single sentence: **a skeptical neuroscience or HCI reviewer reads `evidence_artifact.md` and can determine whether Harlo's prediction-and-scaffolding loop is statistically distinguishable from chance.**

If the artifact shows the loop is not distinguishable from chance, that is still a successful outcome of path_d — it is honest evidence that the current predictor/scaffolding loop is not yet a multiplier, which informs whether the next surgery should be predictor improvement, scaffolding redesign, or observation enrichment.

The failure mode is producing an artifact that is *not interpretable* either way. That is the failure path_d exists to avoid.
