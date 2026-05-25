# PVH Evidence Artifact — v1 (Methodology Validator)

**Generated:** 2026-05-25
**Commit:** 5c0106d3aeae11fa33ee0474159b7a15994873b0
**Scope:** path_d v1 — validates harness mechanics, not Harlo's multiplier effect.

## ⚠️ v1 limitations (read first)

- (a) The corpus is N=69 organic observations in a single session — insufficient for any statistical claim.
- (b) The reference predictor has target leakage (train_predictor.py:113-135): the prediction targets are present in its input window, so its output approximates the current state rather than forecasting.
- (c) No deflection claim is asserted from v1 output. Deflection/overshoot rates are reported as not-asserted (scaffolding signal absent, D20).
- (d) v1 validates the harness mechanics (extract -> feed reference model -> compute -> emit), NOT Harlo's multiplier effect. The evidence-harness ambition is v2 (TI-003).

## Corpus

- Sessions analyzed: **1**
- Windows (3-observation): **67**
- Session `live` (`organic`): 67 windows
- Corpus details: see `harness/path_d/corpus_investigation.md`

## Session `live`

- **Leakage:** confirmed: predicted == actual for all windows (target leakage, D38)
- **Mean |drift| per target:** {'momentum': 0.0, 'burnout': 0.0, 'energy': 0.0, 'burst_phase': 0.0}

**Burnout (actual) over windows:**

```
▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁   (min=0, max=0)
```

**Burnout drift (predicted − actual) over windows:**

```
▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁   (flat at 0 confirms target leakage — predicted reproduces actual)
```

### Lead-time distribution

- Status: **undefined_v1** — no forecasting horizon in reference predictor (D38); lead time requires a t+horizon forecast

| target | actual transitions |
|---|---|
| momentum | 1 |
| burnout | 0 |
| energy | 1 |
| burst_phase | 0 |

### Deflection vs overshoot (overshoot computed first — Commandment 5)

- **Overshoot baseline:** status `not_asserted_v1`, rate `None` — scaffolding_requirements absent (D20); no un-scaffolded crash-prediction set
- **Deflection rate:** status `not_asserted_v1`, rate `None` — no deflection claim asserted in v1 (D39); scaffolding signal unavailable (D20)

### Observation density (signal-weakness proxy)

- mean gap: 0.2206, max gap: 1 exchange, weak-signal fraction (gap>2 exchanges): 0.0

## Headline

**Methodology proven; no multiplier verdict.** The harness extracts the organic
trajectory, feeds the reference model, computes the drift/lead-time/deflection
schema, and emits this artifact end-to-end. The reference predictor's target
leakage and the N=69 single-session corpus mean **no claim about Harlo
multiplying the user is supported by v1**. A leakage-free, horizon-defined
forecaster (TI-003) and a larger corpus are the prerequisites for the v2
evidence harness.
