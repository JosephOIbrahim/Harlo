# Harlo PVH ↔ RSI — Cross-Workstream Coordination

**From:** PVH workstream (Joe Ibrahim, Architect + Claude, Implementation Partner)
**To:** RSI workstream lead
**Status:** Response to RSI handoff (2026-05-25). Pre-implementation coordination — both sides paused pending joint resolution of items below.
**Date:** 2026-05-25

---

## Purpose

Coordinate before either side commits. Your handoff identified the integration surface; this memo locks PVH's side, answers your five asks, surfaces our reverse asks, and identifies the items that must be resolved jointly before implementation proceeds.

We accept your reopen criteria. Same applies symmetrically to anything locked here.

---

## What's locked on PVH side

### Architecture

- **PVH is read-only on `data/observations.db`.** No writes to observation buffer, no writes to USD stages, no writes to Merkle ledger, no modification of the predictor.
- **Output artifacts:** JSON metrics + Markdown evidence document under `harness/path_d/pvh/`. Read-only by humans in v1; no automated feedback to any other subsystem.
- **Methodology:** matches the `harness/path_c/` pattern — KICKOFF, CONSTITUTION, HANDOFF, DEEP_THINK_BRIEF, DECISIONS. Decision lineage continues at D20+.
- **Predictor as un-intervened baseline:** XGBoost `cognitive_predictor_v1.joblib` provides counterfactual reference. Trajectory deflection measured as positive predictive error post-scaffolding-event.
- **Overshoot baseline:** un-scaffolded prediction error rate computed alongside scaffolded deflection rate. Signal = delta between them, not raw deflection count.

### Phase 1 scope

Five sequenced phases via Architect/Forge/Crucible:

- **Phase 0** — Pre-flight (predictor loads, `observations.db` has expected row count, baseline tests captured at 1,365)
- **Phase 1** — Extractor design (Architect)
- **Phase 2** — Extractor implementation + read-only constraint test
- **Phase 3** — Evaluators (drift math, lead-time, deflection, overshoot baseline)
- **Phase 4** — Reporters (JSON + Markdown)
- **Phase 5** — Crucible gate (Cassandra-Problem fixture + 1,365 tests still green)

### Integrity constraints (PVH commits to)

- Specializes floor untouched
- LIVRPS ordering deterministic
- O(1) backtrack via `SetVariantSelection` preserved
- Trace exclusion in verification
- Local-first data residency
- Merkle isolation preserved — PVH never reads or writes Merkle directly
- 26-invariant lattice intact
- CMP and dialectic preservation — PVH is read-analytical only, cannot violate by construction

**Out of scope for PVH v1:** producing variants programmatically, modifying the predictor, authoring through any delegate at production time, interacting with shadow rollouts, feeding LABRE.

---

## Answering your five asks

### 1. Codebase conventions

PVH module placement: `harness/path_d/pvh/` (mirrors `harness/path_c/` precedent for surgical work).

Your proposed `harlo/rsi/labre/` is consistent with the layout. Suggest `python/harlo/rsi/labre/` to match the existing `python/harlo/{brainstem, elenchus, composition, hebbian, ...}` convention. The `harness/` tree is reserved for surgery-phase scaffolding; production modules live under `python/harlo/`.

### 2. Canonical test fixtures

PVH does not yet have specific fixtures. Hand-authored Cassandra-scenario fixture is on PVH Phase 5.

`[NEW-DEP: joint fixture coordination]` Propose a post-Phase-0 sync where both workstreams enumerate fixture needs and we design a shared synthetic-trajectory set with delegate annotations serving both. Not a path_d drafting blocker; addressable in 1–2 hours when both sides reach Phase 0 close.

### 3. Merkle root access pattern

PVH does not require Merkle ledger access. Reads only from `data/observations.db` (downstream materialized event log).

**For LABRE:** existing subsystem API is fine from PVH's perspective. PVH ↔ LABRE Merkle isolation is preserved by construction.

### 4. GEPA critique vector pipeline

`[CONTRADICTION: GEPA ownership]` Your handoff says *"If you own the GEPA pipeline, document the output interface."* Scouting the current repo at master `c42e82d`, GEPA does not appear in `python/harlo/`. Either:

- GEPA is planned-but-not-built and ownership has not yet been assigned
- GEPA exists somewhere not surfaced by the standard scout (please point)
- GEPA was previously named something else and renamed in your fuel doc

Cannot answer this ask without resolution. Need clarification before either side load-bears on GEPA in implementation.

### 5. Shadow rollout infrastructure

Same situation as GEPA. Not visible in current repo state at the scout pass we ran. Either planned-not-built or named differently.

`[CONTRADICTION: shadow rollout ownership]` Need clarification.

---

## What we need from you

### 1. `[BLOCKING-NEW]` Observation schema coordination

PVH's deflection analysis requires observations carrying:

- `delegate_id` (who authored)
- `scaffolding_requirements` (what `compute_routing` emitted)
- `intervention_type` (scaffolding vs elevated-scrutiny vs cold-start-probation)

RSI's downstream analysis benefits from the same fields. If the current `CognitiveObservation` in `src/schemas.py` is missing any of these, both workstreams need them added before either ships. This is a joint decision because schema changes affect both observation writers and downstream consumers.

**Surface:** does the current schema carry these? Are you planning to add them as part of LABRE Phase 1?

### 2. `[BLOCKING-NEW]` Pre-RSI epoch boundary

PVH's baseline (predictor as un-intervened counterfactual) holds robustly only if the predictor's feature set is robust to delegate-routing changes introduced by LABRE.

- If `delegate_id` is in the 111-feature XGBoost set → baseline robust post-LABRE; no epoch boundary needed
- If not → PVH analysis bounded to pre-LABRE epoch of organic observations; we need LABRE deployment date to lock the boundary

**Surface:** planned LABRE deployment timeline, AND direct knowledge of the predictor's feature set if you have it.

### 3. Vocabulary clarification

Direct read or summary needed:

- **CMP** — named alongside dialectic preservation. What does it constrain?
- **GEPA / Q3 / SSR / FV_V** — referenced operationally; PVH wants to confirm analytic output won't accidentally trigger Q3 sensors
- **Fuel doc access** — multiple references; PVH would like read access for canonical definitions before path_d Constitution is locked

### 4. LABRE-driven routing dynamics

How dynamic is reputation-weighted selection expected to be?

Concretely: in a session of 50 exchanges, would the same delegate typically be selected throughout, or would Pareto + Thompson Sampling swap delegates frequently as reputation evolves intra-session?

This determines whether `delegate_id` is a *slow* covariate (effectively constant within sessions, PVH analysis works) or a *fast* covariate (changes intra-session, PVH analysis requires conditioning).

### 5. Honcho dialectic — observability

Your Pattern A: *"VariantSet contradictions, SetVariantSelection drives context-dependent belief activation."*

For PVH to analyze observations correctly, each observation likely needs to carry which variant was active at observation time. Is this already captured in the observation layer, or is variant activation transparent to it?

If transparent → PVH may produce misleading deflection signals when context-driven variant switches occur between predicted and actual states. We'd need to surface variant identity into observations OR explicitly condition the analysis on session-level variant stability.

---

## Risks for your awareness

### PVH analytic output could superficially resemble stagnation

PVH produces a Model Drift Schema across the organic observation set. Characterizes where the predictor consistently over- or under-shoots on certain state transitions. Naive readers (or naive sensors) might interpret a structured drift report as evidence of stagnation *in the predictor itself*.

If Q3 monitors any artifact channel automatically, the PVH evidence artifact should be excluded or labeled. **Confirm Q3 doesn't auto-consume from `harness/` output paths.**

### PVH may surface delegate-attributed prediction failures

If observations carry `delegate_id` (per ask 1), PVH analysis will surface patterns like *"predictor systematically under-predicts crash risk when delegate X is active."* Useful signal for both workstreams but may interact with LABRE's reputation updates if signals route back to LABRE.

**Recommend:** PVH evidence artifact is read-only by humans; does not auto-feed LABRE in v1. Automated feedback is a v2 surgery with its own coordination pass.

### Delegate collusion gap inherited

Your section explicitly notes LABRE doesn't catch coordinated multi-delegate attacks. PVH inherits this limit — analyzing prediction drift cannot detect coordinated variant-authoring patterns. Same gap, same v1 acceptance.

---

## Shared discipline — confirming

- **State capsule format:** Use the format defined in the architect's `CLAUDE.md` (preferences-level, not the in-repo `CLAUDE.md` which contains the 33 rules). Both workstreams emit capsules at session/step boundaries in that format.
- **Progress markers:** `[Step N/M: ...]`, `[<role> → <role>: ...]`, `[still working: ...]` — confirmed.
- **Escalation tags:** `[CONTRADICTION: ...]`, `[BLOCKING-NEW]`, `[NEW-DEP: ...]`, `[REGRESSION: ...]`, `[RELITIGATION-REQUEST: ...]` — confirmed and in use throughout this memo.
- **Integrity violations:** Verifier veto immediately. No work-arounds. Confirmed.

---

## Coordination cadence

- Capsule exchange at session boundaries — confirmed.
- Mid-session synchronization on contradiction-tag — confirmed.
- Async by default — confirmed.

**PVH adds:** when `path_d/` reaches its Crucible gate per phase, PVH emits a phase-close capsule that includes any observations relevant to RSI (test fixture deltas, schema findings, predictor feature confirmations). RSI does the same in reverse.

---

## Reopen criteria

Accept your three criteria as written. Applies symmetrically.

**PVH-side adds:** if Phase 0 codebase reads (`schemas.py`, `train_predictor.py`) reveal facts that contradict assumptions in either workstream's locks, that is an automatic `[RELITIGATION-REQUEST]` trigger before Phase 1 begins.

---

## Open items requiring resolution before either side commits

| # | Tag | Item |
|---|-----|------|
| 1 | `[BLOCKING-NEW]` | Observation schema completeness (`delegate_id`, `scaffolding_requirements`, `intervention_type`) |
| 2 | `[BLOCKING-NEW]` | Pre-LABRE epoch boundary OR predictor feature-set confirmation |
| 3 | `[CONTRADICTION]` | GEPA ownership/location |
| 4 | `[CONTRADICTION]` | Shadow rollout location |
| 5 | `[CLARIFICATION]` | CMP definition |
| 6 | `[CLARIFICATION]` | LABRE intra-session routing dynamics |
| 7 | `[CLARIFICATION]` | Honcho dialectic variant observability in `CognitiveObservation` |

Items 1 and 2 are hard blockers for path_d drafting.
Items 3–4 are hard blockers for any code touching those subsystems.
Items 5–7 inform path_d's Constitution but can be resolved in parallel with Phase 0 codebase reads.

---

*Locked by PVH architect sign-off. PVH Phase 0 begins on receipt of items 1–7 resolution OR explicit acceptance that PVH proceeds with a documented assumption-set.*
