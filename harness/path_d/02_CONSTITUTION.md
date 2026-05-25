# Path D Constitution — Predictive Validation Harness

**Status:** Authoritative for all path_d work.
**Conflict resolution:** On any conflict between this document and `03_HANDOFF.md`, this wins. On any conflict between this document and the in-repo `CLAUDE.md` 33 rules, `CLAUDE.md` wins.
**Amendment:** Articles are amended only by `[RELITIGATION-REQUEST]` filed in `05_DECISIONS.md` with rationale. Silent amendment is forbidden.

---

## Articles — the locked architecture

### Article 1 — Read-Only Discipline

PVH does not write to:

- `data/observations.db`
- `data/stages/*.usda` or any USD stage
- The Merkle ledger (direct or indirect)
- `models/cognitive_predictor_v1.joblib`
- Any production code path under `python/harlo/` or `src/`

PVH writes only to:

- `harness/path_d/pvh/outputs/` (analytic artifacts)
- `harness/path_d/*.md` (governance and decision documents)
- `tests/test_path_d/` (test fixtures and assertions)

Phase 2 includes an explicit Crucible test (`test_pvh_readonly.py`) verifying that running the harness produces zero mutations to any production data path.

### Article 2 — Predictor as Un-Intervened Baseline (Option δ)

The XGBoost `cognitive_predictor_v1.joblib` provides the counterfactual reference for trajectory analysis. Trained on 10K synthetic trajectories via Profile-Driven Markov Biasing modeling cognitive state evolution *before* Harlo scaffolding was deployed, the predictor's output at time `t` represents the expected un-intervened trajectory.

**Trajectory Deflection** is defined as: predicted state at `t+horizon` is sufficiently divergent from actual state at `t+horizon` AND a scaffolding event fired between `t` and `t+horizon`.

**`[PENDING-RSI-ITEM-2]`** This article's validity depends on whether `delegate_id` (or any LABRE-affected feature) is present in the 111-feature XGBoost set. If yes: baseline is robust post-LABRE-deployment. If no: PVH analysis is bounded to a pre-LABRE-epoch of organic observations, and this article will be amended to specify the epoch boundary.

### Article 3 — Cassandra-Aware Attribution

A predicted crash that does not materialize is NOT model error if scaffolding fired between prediction and outcome. The harness must distinguish:

- **Model overshoot** — predicted RED, actual YELLOW, *no scaffolding fired* → counted as model error
- **Trajectory deflection** — predicted RED, actual YELLOW, *scaffolding fired* → counted as positive predictive error (signal of multiplier effect)

Both rates are reported. The headline signal is the *delta* between them, not raw deflection count. If the rates are statistically indistinguishable, the artifact says so plainly.

### Article 4 — Aggressive Scope Cut for v1

Out of scope (v1):

- Writing analytical Overs back to USD stages — held in Python memory, output to JSON/MD
- NLP coherence parsing of exchange content — proxied by Observation Density (gap-based heuristic)
- Complex causal ML for intervention attribution — naive boolean heuristic per Article 3
- Real-time / streaming analysis — batch replay only
- Multi-user analysis — single-architect dataset (the 458 organic observations)
- Visualization beyond ASCII sparklines and Markdown tables — no D3, Plotly, or HTML templates

In scope (v1):

- Read `observations.db`, group by session, reconstruct trajectories
- Run predictor inference for each observation's `t+horizon` state
- Compute drift math, lead-time distribution, deflection rate, overshoot baseline
- Emit JSON metrics + Markdown evidence document

### Article 5 — Coordination with RSI Workstream

The cross-workstream coordination memo (`pvh-rsi-coordination.md`, 2026-05-25) is authoritative for all PVH ↔ RSI interactions.

Seven open items in that memo:

1. `[BLOCKING-NEW]` Observation schema completeness — affects Articles 2, 3
2. `[BLOCKING-NEW]` Pre-LABRE epoch boundary OR predictor feature-set — affects Article 2
3. `[CONTRADICTION]` GEPA ownership/location — affects nothing in path_d v1 (out of scope)
4. `[CONTRADICTION]` Shadow rollout location — affects nothing in path_d v1 (out of scope)
5. `[CLARIFICATION]` CMP definition — informs integrity commitments below
6. `[CLARIFICATION]` LABRE intra-session routing dynamics — affects Article 2 boundary
7. `[CLARIFICATION]` Honcho dialectic variant observability — affects Article 3 attribution

Items 1 and 2 are hard blockers for Phase 1. Items 5–7 inform Constitution finalization. Items 3–4 do not affect this surgery and are noted for completeness.

### Article 6 — Decision Lineage

Decisions encountered during path_d execution are filed in `05_DECISIONS.md` as D20, D21, ... continuing the path_c lineage (D1–D19).

A decision is filed when:

- A choice is made between viable alternatives at runtime
- An assumption is documented in lieu of waiting for RSI resolution
- A `[RELITIGATION-REQUEST]` is filed against an Article
- A Crucible gate produces an unexpected result requiring interpretation

Decisions are filed in real time, not retrospectively. Retroactive D-blocks are forbidden.

### Article 7 — Inheritance from the 33 Rules

The in-repo `CLAUDE.md` 33 rules carry over without modification. Particularly relevant to path_d:

- **Rule 1 (0W idle):** PVH runs once per invocation and exits. No resident process. No daemon. Socket activation is not required because PVH is human-invoked, not event-triggered.
- **Rule 11 (no reasoning_trace):** Harness output contains no internal reasoning traces; only structured metrics and human-readable summary.
- **Merkle isolation rules:** PVH respects Merkle boundaries by never touching the ledger.

If any conflict between path_d operational choices and the 33 rules arises, the rule wins and the path_d choice is amended.

---

## Commandments — testable constraints

These are the binary criteria that gate progression. Each is testable; ambiguous outcomes are forbidden.

1. **Baseline integrity** — Phase 0 captures `baseline_tests.txt` showing 1,365 passed (or documented drift count). Every subsequent Crucible gate verifies this count is preserved.

2. **Read-only verifiability** — Phase 2 includes a test that runs the full harness end-to-end and asserts zero mutations to `data/`, `models/`, `python/harlo/`, `src/`.

3. **Predictor load contract** — Phase 0 verifies `joblib.load('models/cognitive_predictor_v1.joblib')` succeeds and produces a model with the expected `predict()` interface signature.

4. **Observation queryability** — Phase 0 documents row count and partition split (anchor vs organic) of `data/observations.db`. Subsequent phases assume this contract.

5. **Overshoot before deflection** — `evaluators.py` computes the overshoot baseline *before* reporting the deflection rate. The evidence artifact may not present a deflection rate without its paired overshoot baseline.

6. **Cassandra fixture passes** — Phase 5 Crucible gate requires the hand-authored Cassandra-scenario test fixture to pass: a synthetic 5-observation trajectory containing a known averted-crash event must be correctly flagged as deflection-success, not model-error.

7. **Decision lineage closure** — At every phase close, any decisions made during the phase are filed in `05_DECISIONS.md` before the Crucible gate is signed.

---

## Integrity commitments (mirrored from RSI coordination)

PVH commits to these constraints, identical to the RSI-side commitments:

- Specializes floor untouched
- LIVRPS ordering deterministic
- O(1) backtrack via `SetVariantSelection` preserved
- Trace exclusion in verification
- Local-first data residency
- Merkle isolation between subsystems
- 26-invariant lattice intact
- CMP and dialectic preservation (pending CMP clarification — Article 5 item 5)

PVH cannot violate any of these by construction because PVH is read-analytical only. The commitment is documented for symmetry with the RSI workstream.

---

## Authority chain

```
in-repo CLAUDE.md (33 rules)                     [highest authority]
        ↓
02_CONSTITUTION.md (this file)
        ↓
03_HANDOFF.md (phase plan)
        ↓
implementation code in harness/path_d/pvh/       [lowest authority]
```

When operating, prefer the higher authority. When updating, the document with authority files the amendment in its own `[RELITIGATION-REQUEST]` block.
