# Path D Deep Think Brief — Consolidated Strategic Exchanges

**Source material:** Three rounds of Gemini Deep Think exchanges (2026-05-25) + one cross-workstream coordination round with RSI workstream (2026-05-25).

This document is the canonical input to path_d's Architect work. **Do not relitigate decisions captured here without `[RELITIGATION-REQUEST]` filed in `05_DECISIONS.md`.**

---

## Origin — what initiated this work

Gemini Deep Think (acting as external CTO) produced an initial handoff proposing a "Time-Warp Harness" — Git-log-as-telemetry feeding compressed time simulation of Harlo's burnout algorithms, with VirtualClock dependency injection and stage error gates.

The proposal was reviewed against actual repo state and rejected as misaligned with what Harlo is. The reorientation produced the surgical work captured here.

The reorientation grounding came from the architect:

> *"Push the limits of how an AI assistant like Harlo can help with neuroscience and specifically neurodivergent users over long-running tasks. Imagine an operating system that follows the user's physical and emotional state, scaffolding while helping them accomplish their tasks. That is an all-hands-on-deck approach utilizing USD compositional and long-running tasks. Scaffolding the current direction of Harlo as a multiplier."*

The product is not burnout detection. The product is OS-level scaffolding for neurodivergent cognition during long-horizon work. Evidence that the scaffolding **multiplies** the user is what `path_d` produces.

---

## Round 1 — Reorientation

### Sent to Gemini

A reorientation handoff documenting repo state (S1–S5 sprint history, 1,140+ tests, USD substrate, Hydra delegates, 458 organic observations) and reframing the work from defensive validation to offensive evidence.

### Key positions sent

- The 278K synthetic exchanges are already stress validation; the original Time-Warp Harness duplicated existing work with worse inputs
- Harlo's input domain is structured cognitive observations, not Git activity
- VirtualClock injection is likely already solved at the simulation layer
- USD integrity checks are redundant with S4 backend parity verification

### Four strategic options sent

- **Option A** — Long-Arc Evidence Harness (replay 458 organic observations)
- **Option B** — Predictive Intervention Loop (proactive scaffolding with intervention tracking)
- **Option C** — Body Signal Layer (wearables → USD sublayer)
- **Option D** — Salvaged Time-Warp Harness (long-horizon synthetic stress)

Stated position: A is highest-information, lowest-cost; A feeds B feeds C.

### Five strategic questions sent

1. Long-arc replay design (durability, audience legibility)
2. Intervention surface design (vocabulary, integration with 7-step pipeline)
3. Profile generalization architecture (USD VariantSets candidate)
4. Body signal composition (high-frequency biometric data without USD bloat)
5. Evidence question (what artifact passes skeptical neuroscience/HCI review)

---

## Round 1 Response — Gemini's strategic analysis

### Accepted positions

- Option A is the priority
- Option A must produce predictive validation artifact

### Architectural answers (which became locks in Round 2)

- **Q1** — USD Layer Isolation: existing stage immutable, analytical session layered as non-destructive Overs (later relevant if v2 writes Overs; v1 holds analysis in Python memory)
- **Q2** — Intervention as routing requirements: extend `compute_routing` to emit `Scaffold:CognitiveLoadReduction`, `Scaffold:InhibitionDefault`, etc. Delegate resolves presentation. Engine presentation-blind.
- **Q3** — VariantSets on `/Profiles` prim with `CognitiveProfile` schema; `SetVariantSelection("ProfileName")` switches at runtime. Scales from 7 to 30+ profiles.
- **Q4** — Transient Biometric Sublayer with Low-Pass Gate; rolling avg / Kalman; privacy revocation = mute sublayer
- **Q5** — Allostatic Efficiency: scaffolded burst duration vs un-scaffolded baseline; "not squeezing the sponge harder; making it hold water more efficiently"

### Headline contribution

The "Cassandra Problem" framing — a self-negating prophecy where Harlo accurately predicts a crash, scaffolding fires, the crash is averted, and naive delta accounting penalizes the model for a false positive. This framing survived into the architecture and is now `02_CONSTITUTION.md` Article 3.

---

## Round 2 — Architecture Lock + Pushbacks

### Accepted as locked

Q1, Q2, Q3, Q4 from Round 1 response (USD Layer Isolation, Routing Requirements, VariantSets, Transient Biometrics).

### Four pushbacks sent

**Pushback 1 — Decouple A from D.** Gemini argued A must be built with explicit intent to feed Option D. Rejected: YAGNI; pre-optimizing for a hypothetical synthetic stress test adds architectural tax in service of work that may never happen. Build A to serve A.

**Pushback 2 — Rename "Counterfactual."** Gemini titled Q1 "USD Layer Isolation and Counterfactual Execution." The mechanism is predictive validation; calling an observational analysis "counterfactual" implies causal inference (do-calculus, structural causal models) we don't possess. Renamed to **Predictive Validation Harness (PVH)**.

**Pushback 3 — The un-scaffolded baseline problem.** Allostatic Efficiency (Q5) requires comparison against un-scaffolded baseline. The 458 organic observations were all collected with scaffolding active; there is no baseline in the corpus. Three options proposed: α (intra-session variance), β (kill-switch baseline collection), γ (reframe metric).

**Pushback 4 — Model Drift Schema is one slice.** Gemini's drift schema (timestamp, actual, predicted, delta) is necessary but insufficient. Three additional dimensions: lead-time distribution, intervention-success attribution, input signal weakness.

### Status of pushbacks after Round 2 response

All four accepted.

---

## Round 2 Response — MVP spec

### Position on the baseline problem

Gemini rejected α (statistical trap: confounding by indication), deferred β (biologically expensive — architect would have to work without scaffolding for 2 weeks), and proposed **Option δ (Trajectory Deflection)**: the XGBoost predictor *is* the baseline because it was trained on synthetic trajectories before scaffolding deployment.

When the model predicts RED at `t+60`, scaffolding fires at `t+5`, and actual at `t+60` is YELLOW: the positive predictive error is the multiplier effect. Trajectory deflection, not model drift.

Accepted as Article 2 of `02_CONSTITUTION.md`, with the addition of the **overshoot baseline** correction noted next.

### MVP spec accepted

- **File structure:** `harness/path_d/pvh/` with `cli.py`, `extractor.py`, `evaluators.py`, `reporters.py`
- **Entry point:** `python -m harness.path_d.pvh.cli`
- **Output:** dual-target — `pvh_metrics.json` for engineering, `evidence_artifact.md` for external review
- **Scope cuts:** no USD-Over writing in v1, no NLP coherence parsing (use Observation Density proxy), no causal ML (naive boolean heuristic)
- **Test surface:** Cassandra fixture + read-only verification

### Pushbacks sent on the MVP spec (Round 3 question — answered before path_d)

**Overshoot baseline needed.** Option δ's deflection claim works only if it's calibrated against the un-scaffolded model overshoot rate. If the model overshoots on 15% of un-scaffolded RED predictions and "deflects" on 15% of scaffolded RED predictions, that's noise. Signal is the *delta* between rates. Now Article 3.

**Data path resolution.** Gemini's `data/organic_458.usda` entry point assumes a single USD file. Empirically (per scout pass on the repo), the 458 organic observations live in `data/observations.db` (SQLite). USD stage at `data/stages/cognitive_twin.usda` was evicted in path_c Phase 5. PVH reads SQLite as canonical source.

---

## Cross-Workstream Round — RSI Coordination

### Trigger

The architect provided a parallel handoff from the RSI workstream (Recursive Self-Improvement infrastructure: LABRE delegate reputation, Q3 monitoring, DLPL, CSCGAS, PCRV, GEPA). The two workstreams operate on adjacent abstraction layers of the same substrate.

### Synthesis from first principles

Two workstreams operate at different layers:

- **PVH operates on observations** — what the cognitive twin recorded
- **RSI operates on delegates** — who authored variants, their trustworthiness over time

Intersection points identified, triaged by blocking status (full memo: `pvh-rsi-coordination.md`).

### Hard blockers for Phase 1

- **Item 1 `[BLOCKING-NEW]`** — Observation schema completeness. PVH needs `delegate_id`, `scaffolding_requirements`, `intervention_type`. Joint decision because schema changes affect both observation writers and downstream consumers.
- **Item 2 `[BLOCKING-NEW]`** — Pre-LABRE epoch boundary OR predictor feature-set confirmation. If `delegate_id` is in the 111-feature XGBoost set, baseline is robust post-LABRE. If not, PVH analysis is bounded to a pre-LABRE epoch.

### Other open items (non-blocking on path_d)

- Item 3 `[CONTRADICTION]` — GEPA ownership/location
- Item 4 `[CONTRADICTION]` — Shadow rollout location
- Item 5 `[CLARIFICATION]` — CMP definition
- Item 6 `[CLARIFICATION]` — LABRE intra-session routing dynamics
- Item 7 `[CLARIFICATION]` — Honcho dialectic variant observability

---

## Vocabulary lock — terms in canonical use

| Term | Definition |
|------|------------|
| **PVH** (Predictive Validation Harness) | The artifact path_d produces; replaces the earlier "Counterfactual Execution" name |
| **Trajectory Deflection** | Predicted state diverges favorably from actual state when scaffolding fires between prediction and outcome |
| **Cassandra Problem** | A correctly-predicted crash that doesn't materialize because intervention fired — must not be counted as model error |
| **Overshoot baseline** | The rate at which the model predicts crashes that don't materialize *without* scaffolding firing — the noise floor against which deflection is measured |
| **Model Drift Schema** | Per-observation table of `[timestamp, actual, predicted, lead_time, signal_proxy, deflection_flag]` |
| **Observation Density** | Gap-based proxy for input signal weakness — sparse observation periods flagged as weak-signal |
| **Lead-time distribution** | Distribution of (prediction-fire-time, actual-state-transition-time) gaps per state transition |
| **Pre-LABRE epoch** | The subset of organic observations collected before LABRE-driven delegate selection is active; defines temporal validity boundary for Option δ if delegate_id is not in feature set |

---

## Concepts that were rejected (and why)

These do not return without `[RELITIGATION-REQUEST]`:

- **Git-log as cognitive telemetry** — wrong input domain; Harlo ingests structured observations from MCP tool calls, not Git activity
- **"Counterfactual Execution" naming** — oversells what predictive validation can prove; reviewer credibility cost
- **A-feeds-D coupling** — premature optimization; YAGNI
- **Synthetic-only headline evidence** — 278K synthetic exchanges already exist; headline evidence requires real organic data
- **Allostatic Efficiency requiring kill-switch baseline** — biologically expensive; defeats the sprint
- **Writing analytical Overs to USD in v1** — wrestling with USD composition API for output blows the estimate; v1 ships JSON + Markdown
- **Causal inference modeling** — out of scope; naive boolean heuristic for intervention attribution is sufficient for v1
- **Allostatic Efficiency framing as headline metric** — replaced by Trajectory Deflection (Option δ) which doesn't require un-scaffolded baseline data we don't have

---

## What this brief is NOT

- Not a phase plan. That lives in `03_HANDOFF.md`.
- Not an authoritative source of architectural commitments. Those live in `02_CONSTITUTION.md`. This document is the *origin record* of how the Constitution arrived at its current shape.
- Not a final word. New strategic exchanges may produce amendments. Amendments are filed in `05_DECISIONS.md` per the lineage discipline.

---

## Reader's checklist

A future Claude Code session reading this document should be able to answer:

1. What was rejected, and why?
2. What's locked, and where (`02_CONSTITUTION.md` article numbers)?
3. What's blocked on RSI coordination?
4. What does each canonical vocabulary term mean operationally?
5. Where do new decisions get filed?

If any of those questions cannot be answered from this document plus `02_CONSTITUTION.md`, the documents are incomplete and the gap is filed as `[BLOCKING-NEW]` before implementation proceeds.

---

## Phase 0 Discoveries (appended 2026-05-25)

Phase 0 pre-flight tested the assumptions in this brief against actual repo
state. Several were wrong. Recorded here so the origin story stays honest; full
detail in `05_DECISIONS.md` (D20–D37) and `corpus_investigation.md`.

- **D20 — Schema is incomplete (RSI item 1, resolved by observation).** The
  `CognitiveObservation` schema and every stored row lack `delegate_id`,
  `scaffolding_requirements`, and `intervention_type`. The `delegate` block
  carries only `active` and `task_type`. Deflection attribution must proceed
  with these fields absent (D37: column-aware analysis, bounded deflection with
  explicit caveat).

- **D21 — `delegate_id` is NOT in the 111-feature predictor (RSI item 2,
  resolved).** `train_predictor.py` encodes state/action/dynamics/injection/
  allostasis (37/observation × 3-window = 111); the delegate block is never
  encoded. The loaded model confirms 111 features, no `feature_names_in_`. The
  "pre-LABRE epoch" concern is moot for a single-session corpus with no delegate
  routing.

- **D24 → D35 — The "458 organic observations" do not exist.** Actual corpus:
  **N=69 organic, 0 anchor, single `'live'` session** (2026-05-11, ~4.5h). Not
  in `observations.db` (69), not in `twin.db` (hippocampal store), not the 10K
  synthetic `trajectories_10k.jsonl`. The 458 (and its "20% anchor / 80%
  organic" split) was aspirational. **path_d v1 reframed as a methodology
  validator**; statistical multiplier claims deferred to v2.

- **D31 → D32/D33 — The baseline capture breached read-only discipline.**
  Running the full `pytest tests/` suite (non-hermetic) wrote 3 observations to
  `data/observations.db` (69→72). Restored to 69 under D32; Article 1 amended
  (D33) to forbid full-suite captures against the analytic `data/`. Filed as
  TI-002 (D36) — a Harlo-wide architectural issue.

- **Rejected-concept status:** "Counterfactual Execution" naming stays rejected;
  the data-path resolution (SQLite `observations.db`, not `organic_458.usda`)
  held. The new correction is purely the **corpus size and the v1 scope**, not
  the methodology.

---

## Phase 1 Discoveries (appended 2026-05-25)

Phase 1 source review (`train_predictor.py`, `predict.py`, `observation_buffer.py`)
invalidated the deflection *premise* — a larger correction than Phase 0's
corpus-size finding. Full detail in `05_DECISIONS.md` D38–D41.

- **D38 — the reference predictor does not forecast.** Two compounding flaws:
  - *Target leakage* — `train_predictor.py:113-135` trains on window
    `[t-2,t-1,t]` → target = state of `trajectory[i]` (the same index `i`), and
    `_encode_observation(obs[i])` already contains those four target fields
    (momentum/burnout/energy/burst_phase) at feature indices 74/75/76/94. The
    model is handed the answer; its accuracy is an artifact of leakage.
  - *No horizon* — training target is the current state (horizon 0); `predict.py`
    relabels the output as t+1 (`exchange_index += 1`); the Constitution (Art. 2)
    assumes a tunable `t+horizon` (e.g. t+60). All three layers disagree.

- **D39 — v1 narrowed to a self-validating harness.** "Trajectory Deflection"
  (the headline contribution from the Round 1 Gemini exchange, the "Cassandra
  Problem") is **inapplicable in v1** because there is no genuine forecast to
  deflect. v1 proves pipeline mechanics only; the evidence artifact asserts no
  deflection claim. Article 2 amended ("reference output to characterize, not a
  validated baseline"); Article 3 (Cassandra) parked as a v2 concern.

- **D40 — TI-003: predictor retraining is core/RSI surgery, not path_d.** A
  leakage-free, horizon-defined forecaster is the prerequisite for the original
  evidence-harness ambition. PVH is read-only on `src/`/`models/` and cannot
  retrain; this is the likely highest-leverage surgery after path_d v1 ships.

- **Investigation (D41):** confirmed no alternative non-leaky forecaster exists
  anywhere in the repo (single `.joblib`, single train/predict module pair). So
  D38–D40 stand; they are not artifacts of looking at a stale model.

**Net effect on the original strategy:** the *methodology* (replay organic
observations, characterize predictor behavior, emit a legible artifact) survives.
What collapses is the *evidentiary claim* — the predictor as an un-intervened
baseline (Option δ). That claim moves to v2, contingent on TI-003.
