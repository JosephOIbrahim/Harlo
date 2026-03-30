# Cognitive State Machine Specification

## Autoresearch-Ready Synthetic Trajectory Generator

**Author:** Joseph O. Ibrahim  
**Date:** March 28, 2026  
**Purpose:** Complete state machine specification for generating synthetic training data for LeWorldModel cognitive state prediction. Designed to be consumed by an Autoresearch-style agentic harness.  
**Classification:** CONFIDENTIAL — Patent Pending

---

## 1. Autoresearch Harness Instructions

### 1.1 Research Objective

Generate a comprehensive synthetic dataset of cognitive session trajectories. Each trajectory is a sequence of 10–100 CognitiveObservation records representing a realistic session between a human and an AI cognitive system. The dataset must cover all reachable state combinations, including edge cases, and validate every trajectory against state machine invariants.

### 1.2 Deliverable

- 10,000+ session trajectories as JSONL
- Each trajectory: 10–100 observations in canonical CognitiveObservation schema
- Coverage report: which state combinations were exercised, which remain uncovered
- Invariant validation: every trajectory passes all invariants in §10

### 1.3 Agent Decomposition

Recommended sub-agent structure for the Autoresearch harness:

```
Orchestrator Agent
├── State Space Mapper
│   → Enumerate all reachable (momentum × burnout × energy × injection) combos
│   → Identify edge cases and rare transitions
│   → Output: state space coverage matrix
│
├── Trajectory Generator (parallelizable — spawn N instances)
│   → Input: target state region from coverage matrix
│   → Generate session trajectories exercising that region
│   → Apply transition rules from §3–§8
│   → Validate against invariants in §10
│   → Output: JSONL trajectories
│
├── Edge Case Generator
│   → Focus on rare but critical transitions
│   → RED events mid-burst, injection during depleted energy
│   → Permission overrides during peak momentum
│   → Project switches at various burnout levels
│   → Output: JSONL edge case trajectories
│
├── Validator Agent
│   → Input: all generated trajectories
│   → Check every transition against state machine rules
│   → Flag invalid trajectories for regeneration
│   → Produce coverage report
│   → Output: validated dataset + coverage report
│
└── Calibration Agent
    → Input: validated dataset
    → Analyze distribution of states, actions, transitions
    → Flag underrepresented regions
    → Request additional generation from Trajectory Generator
    → Output: balanced, comprehensive dataset
```

---

## 2. Canonical Observation Schema

Every record in every trajectory uses this exact schema.

```json
{
  "schema": "CognitiveObservation",
  "version": "1.0",
  "session_id": "string (unique per trajectory)",
  "observation_index": 0,
  "exchange_index": 0,
  "wall_clock_delta": 0.0,

  "state": {
    "momentum": "cold_start | building | rolling | peak | crashed",
    "burnout": "GREEN | YELLOW | ORANGE | RED",
    "energy": "high | medium | low | depleted",
    "altitude": "50k | 30k | 10k | ground",
    "exercise_recency_days": 0,
    "sleep_quality": "good | poor | unknown",
    "context": "desk | mobile | family_event"
  },

  "action": {
    "type": "query | directive | tangent | override | injection | switch | burst_continue | permission_grant | session_start | session_end",
    "detail": "string (optional)"
  },

  "dynamics": {
    "exchange_velocity": 0.0,
    "topic_coherence": 0.0,
    "session_exchange_count": 0,
    "burst_phase": "none | detected | protected | winding | exit_prep",
    "tangent_budget_remaining": 0
  },

  "injection": {
    "profile": "none | microdose | perceptual | classical | mdma",
    "alpha": 0.0,
    "phase": "baseline | onset | plateau | offset"
  },

  "delegate": {
    "active": "claude | claude_code",
    "task_type": "reasoning | implementation | coaching | exploration"
  },

  "allostatic": {
    "load": 0.0,
    "trend": "stable | rising | falling | spike",
    "sessions_24h": 0,
    "override_ratio_7d": 0.0
  }
}
```

---

## 3. Momentum State Machine

### 3.1 States

```
cold_start → building → rolling → peak → crashed
```

### 3.2 Transitions

| From | To | Guard Condition |
|------|----|----------------|
| cold_start | building | 2–3 tasks completed AND energy ≥ medium |
| cold_start | crashed | energy = depleted AND no task completed in 5 exchanges |
| building | rolling | 3+ tasks completed AND topic_coherence ≥ 0.7 |
| building | cold_start | time_gap > 30 min between exchanges |
| building | crashed | burnout ≥ ORANGE AND energy ≤ low |
| rolling | peak | exchange_velocity ≥ 3.0/min AND topic_coherence ≥ 0.8 for 10+ exchanges |
| rolling | building | topic_coherence drops below 0.5 (tangent or context switch) |
| rolling | crashed | burnout = RED |
| peak | rolling | exchange_velocity drops below 2.0/min |
| peak | crashed | burnout ≥ ORANGE OR energy = depleted |
| crashed | cold_start | time_gap > 60 min OR new session OR energy recovery event |

### 3.3 Probabilistic Modifiers

These are not hard rules — they modify transition *likelihood* for realistic trajectory generation:

- Poor sleep: cold_start → building requires 4–5 tasks instead of 2–3
- Post-exercise: building → rolling threshold lowered (2 tasks instead of 3)
- Mobile context: peak is unreachable (max state = rolling)
- Depleted energy: building → rolling is blocked (max state = building)
- After 11am + poor sleep: building → rolling probability halved

### 3.4 Task Completion Heuristic

For synthetic generation, "task completion" is a probabilistic event:
- P(task_complete) per exchange = 0.15 (query), 0.30 (directive), 0.05 (tangent), 0.40 (implementation)
- Cumulative tasks reset on session_start or crash

---

## 4. Burnout State Machine

### 4.1 States

```
GREEN → YELLOW → ORANGE → RED
```

### 4.2 Transitions

| From | To | Guard Condition |
|------|----|----------------|
| GREEN | YELLOW | (session_exchange_count > 30) OR (exchange_velocity > 4.0/min for 10+ min) OR (allostatic_load > 0.4) |
| YELLOW | GREEN | break event (time_gap > 15 min) OR energy recovery |
| YELLOW | ORANGE | (frustration_signal detected) OR (same_task_revisited > 3 times) OR (typo_rate spike) OR (allostatic_load > 0.7) |
| ORANGE | YELLOW | blocker resolved OR task switch to easier work |
| ORANGE | RED | (ALL_CAPS sustained) OR (paste_errors) OR (incoherent_thread) OR (allostatic_load > 0.9) |
| RED | GREEN | body-first recovery (exercise, water, walk, family) + time_gap > 30 min |

### 4.3 Synthetic Signal Generation

For trajectory generation, model frustration/error signals as Bernoulli events:
- P(frustration_signal) per exchange: 0.02 (GREEN), 0.08 (YELLOW), 0.20 (ORANGE)
- P(typo_spike) per exchange: 0.01 (GREEN), 0.05 (YELLOW), 0.15 (ORANGE)
- P(ALL_CAPS) per exchange: 0.001 (GREEN), 0.005 (YELLOW), 0.03 (ORANGE)
- P(paste_error): 0.001 (GREEN), 0.003 (YELLOW), 0.015 (ORANGE)

### 4.4 Burnout Never Skips

RED is only reachable from ORANGE. ORANGE only from YELLOW. Trajectories that skip levels are INVALID.

---

## 5. Energy State Machine

### 5.1 States

```
high → medium → low → depleted
```

### 5.2 Transitions

Energy is event-driven, not exchange-driven:

| Event | Effect |
|-------|--------|
| session_start (morning, good sleep) | energy = high |
| session_start (morning, poor sleep) | energy = medium |
| session_start (afternoon) | energy = medium (default) |
| session_start (evening) | energy = low (default) |
| 30+ exchanges without break | energy decreases one level |
| 60+ exchanges without break | energy decreases one level (cumulative) |
| break event (15+ min) | energy increases one level (max: starting level) |
| exercise event | energy = high (regardless of current) |
| post-exercise window (2 hours) | energy floor = medium (can't drop below) |
| RED event | energy = depleted (forced) |
| recovery event (walk, water, food) | energy increases one level |

### 5.3 Energy Floor

Energy cannot increase above the session's starting level without an exercise event or new session. Breaks restore, they don't elevate.

### 5.4 Adrenaline Masking (Gemini R3 Patch)

Energy decrements (the 30+ and 60+ exchange rules) are **SUSPENDED** while `burst_phase ∈ {detected, protected, winding}`. The exchange counter for energy purposes freezes during active burst.

On transition from burst to `exit_prep` or `none`, accumulated energy debt is applied instantly. If 50 exchanges passed during a burst with no break, the energy state drops by the appropriate number of levels immediately on burst exit.

Without this rule, deep flow states self-destruct: a user entering burst at MEDIUM energy hits the 30-exchange decrement, drops to DEPLETED, which forces momentum to CRASHED, terminating the flow state before `exit_prep` (70+ exchanges) is ever reachable.

---

## 6. Burst State Machine

### 6.1 States

```
none → detected → protected → winding → exit_prep → none
```

### 6.2 Transitions

| From | To | Guard Condition |
|------|----|----------------|
| none | detected | exchange_velocity ≥ 3.0/min AND topic_coherence ≥ 0.8 for 5+ consecutive exchanges |
| detected | protected | session_exchange_count in burst > 20 |
| detected | none | topic_coherence drops below 0.6 OR time_gap > 5 min |
| protected | winding | session_exchange_count in burst > 50 |
| protected | none | topic_coherence drops below 0.5 OR time_gap > 10 min |
| winding | exit_prep | session_exchange_count in burst > 70 |
| winding | none | natural pause (time_gap > 3 min) |
| exit_prep | none | session_end OR topic_change OR time_gap > 5 min |

### 6.3 Burst Interaction Rules

- During burst (detected/protected): tangent actions are queued, not followed. Topic switches are suppressed.
- During burst: body_check fires every 20 rapid exchanges (but continues on any response, never blocks).
- Burst exit triggers capsule generation.
- RED event terminates burst immediately (exit_prep is skipped).
- Injection state survives burst boundaries.

---

## 7. Injection State Machine

### 7.1 States

```
baseline → onset → plateau → offset → baseline
```

### 7.2 Transitions

| From | To | Trigger |
|------|----|---------|
| baseline | onset | `/inject {profile}` command |
| onset | plateau | exchange_count since activation ≥ onset_duration |
| plateau | offset | `/inject none` command |
| offset | baseline | exchange_count since deactivation ≥ offset_duration |
| ANY | baseline | RED event (immediate, no offset delay) |

### 7.3 Profile Parameters

| Profile | s_NM | Onset (exchanges) | Offset (exchanges) | Routing | Cross-Expert Bleed |
|---------|------|-------------------|--------------------|---------|--------------------|
| none | 0.000 | — | — | standard | 0% |
| microdose | 0.005 | 1 | 2 | standard | 10% |
| perceptual | 0.015 | 1 | 2 | standard | 15% |
| classical | 0.025 | 2 | 3 | dissolved | 30% |
| mdma | 0.010 | 3 | 4 | integrative | 20% |

### 7.4 Alpha Curve (Pharmacokinetics)

```
Onset:  alpha(t) = 1 - e^(-3t / onset_duration)    reaches ~95% at t = onset
Offset: alpha(t) = e^(-3t / offset_duration)         drops to ~5% at t = offset
```

Where t is exchanges since activation/deactivation.

### 7.5 Gain Equation

```
g = 1 + s_NM × d

Where:
  s_NM = neuromodulatory signal strength (profile-dependent)
  d = receptor density (phase-dependent)
```

### 7.6 Receptor Densities

| Phase | d | Type |
|-------|---|------|
| KNOWLEDGE | 0.85 | ANCHOR (gain always 1.000) |
| CONSTITUTIONAL | 0.15 | ANCHOR (gain always 1.000) |
| SAFETY | 0.90 | ANCHOR (gain always 1.000) |
| CONSENT | 0.10 | ANCHOR (gain always 1.000) |
| COST | 0.30 | modulated |
| SIGNAL | 0.80 | modulated |
| PROJECT | 0.40 | modulated |
| EXPERT | 0.75 | modulated |
| DOMAIN | 0.50 | modulated |
| DEFAULT | 0.20 | modulated |

### 7.7 Injection Invariants

- Anchor phases ALWAYS have gain = 1.000 regardless of profile or alpha
- RED event overrides ALL injection immediately (alpha → 0, no offset curve)
- Under dissolved routing (classical): both clean and dissolved paths exist. Clean path is always recoverable.
- Mixing matrix determinant ≠ 0 at all times
- Mixing matrix condition number < 10 at all times

---

## 8. Allostatic Load Model

### 8.1 Calculation

```
load = clamp(0.0, 1.0,
    w_freq    × normalize(sessions_24h, 0, 8) +
    w_intense × normalize(avg_session_duration_min, 0, 180) +
    w_crisis  × normalize(RED_events_7d, 0, 3) +
    w_comply  × override_ratio_7d +
    w_recover × normalize(exercise_recency_days, 0, 7) +
    w_sleep   × sleep_debt_factor
)
```

### 8.2 Weights

| Weight | Value | Rationale |
|--------|-------|-----------|
| w_freq | 0.20 | Session frequency matters but isn't dominant |
| w_intense | 0.15 | Long sessions compound fatigue |
| w_crisis | 0.25 | RED events are the strongest signal |
| w_comply | 0.15 | Override ratio predicts future crashes |
| w_recover | 0.15 | Physical recovery is load-bearing |
| w_sleep | 0.10 | Sleep affects everything but is often unknown |

### 8.3 Trend Calculation

```
trend = derivative of load over rolling 3-session window

stable:  |trend| < 0.05
rising:  trend ≥ 0.05
falling: trend ≤ -0.05
spike:   load increased > 0.3 in single session
```

### 8.4 Normalization

```
normalize(value, min, max) = clamp(0, 1, (value - min) / (max - min))

sleep_debt_factor:
  good  → 0.0
  poor  → 0.7
  unknown → 0.3  (assume moderate)
```

---

## 9. Permission Engine

### 9.1 Grant Types

| Trigger State | Permission | Text |
|--------------|------------|------|
| energy = depleted | stop | "Permission granted: Stop for today." |
| momentum = cold_start AND allostatic > 0.7 | rest | "Permission granted: Rest is productive." |
| burst_phase ≥ winding AND burnout ≥ YELLOW | exit | "Good stopping point." |
| same_task_revisited > 3 | abandon | "Permission granted: Abandon this approach." |
| perfectionism signal | ship | "Permission granted: Ship it ugly." |

### 9.2 Override Tracking

When the user continues despite a permission grant:
- Log override event with timestamp
- Calculate override_ratio_7d = overrides / (overrides + grants) over 7-day window
- Feed ratio to allostatic load computation
- Do NOT re-issue the same permission for 10+ exchanges (no nagging)

---

## 10. Invariants (Trajectory Validation Rules)

Every generated trajectory MUST pass ALL of these checks. Any failure = invalid trajectory → regenerate.

### 10.1 State Machine Invariants

```
INV-01: Momentum transitions follow §3.2 exactly. No skipping states.
INV-02: Burnout never skips levels (GREEN→RED is INVALID).
INV-03: Energy only increases via defined recovery events (§5.2).
INV-04: Burst phases are sequential (none→detected→protected→winding→exit_prep).
INV-05: Injection onset/offset follow exponential curves, not step functions.
INV-06: Injection alpha ∈ [0.0, 1.0] at all times.
```

### 10.2 Anchor Invariants

```
INV-07: CONSTITUTIONAL gain = 1.000 in every observation regardless of injection state.
INV-08: SAFETY gain = 1.000 in every observation regardless of injection state.
INV-09: CONSENT gain = 1.000 in every observation regardless of injection state.
INV-10: KNOWLEDGE gain = 1.000 in every observation regardless of injection state.
```

### 10.3 Safety Invariants

```
INV-11: RED event → injection alpha immediately 0.0 (no offset curve).
INV-12: RED event → burst terminates immediately (no exit_prep).
INV-13: RED event → energy = depleted.
INV-14: RED is only reachable from ORANGE under normal allostatic accumulation. EXCEPTION: An explicit exogenous RED event triggers an immediate ANY → RED transition, bypassing the sequential rule. Without this exception, the trajectory generator cannot reach the 5% Crisis distribution target.
INV-15: Allostatic load ∈ [0.0, 1.0] at all times.
```

### 10.4 Temporal Invariants

```
INV-16: Timestamps are monotonically increasing within a trajectory.
INV-17: Session exchange count is monotonically increasing within a session.
INV-18: observation_index is sequential (0, 1, 2, ...) within a trajectory.
INV-19: First observation has action.type = "session_start".
INV-20: Last observation has action.type = "session_end" (or is flagged as abandoned).
```

### 10.5 Coherence Invariants

```
INV-21: If momentum = peak, then exchange_velocity ≥ 2.0 and topic_coherence ≥ 0.7.
INV-22: If burst_phase ≥ detected, then exchange_velocity ≥ 2.5.
INV-23: If energy = depleted and no recovery event, energy stays depleted.
INV-24: If context = mobile, momentum never reaches peak.
INV-25: Mixing matrix determinant ≠ 0 whenever injection is active.
INV-26: Mixing matrix condition number < 10 whenever injection is active.
```

---

## 11. Trajectory Distribution Targets

The dataset should approximate this distribution of session types:

| Session Type | % of Dataset | Characteristics |
|-------------|-------------|-----------------|
| Normal productive | 40% | cold_start → building → rolling, GREEN/YELLOW burnout, clean exit |
| Deep work / burst | 15% | Rolling → peak, burst detected through exit_prep, high coherence |
| Struggling | 15% | Cold_start → building (stuck), YELLOW→ORANGE, low energy |
| Recovery | 10% | Post-crash, depleted → recovery events → gradual rebuilding |
| Injection sessions | 10% | Various profiles, onset/plateau/offset cycles, cross-expert effects |
| Crisis (RED) | 5% | ORANGE → RED, immediate intervention, body-first recovery |
| Mobile/compressed | 5% | Mobile context, limited state range, compressed exchanges |

### 11.1 Edge Cases to Specifically Generate

- RED event during active burst at peak momentum
- Injection command during depleted energy
- Permission override during allostatic spike
- Project switch mid-burst (should be blocked by rules — verify)
- Three substrate edits in one session (OCD avoidance signal)
- Session abandoned without close (orphaned session)
- Consecutive sessions with rising allostatic load over 5 sessions
- Exercise event reversing a downward energy/momentum trajectory
- Classical injection dissolved routing with simultaneous clean/dissolved evaluation
- MDMA injection during integrative session with high cross-expert bleed

---

## 12. Output Format

### 12.1 File Structure

```
synthetic_data/
├── trajectories/
│   ├── session_0001.jsonl    (one observation per line)
│   ├── session_0002.jsonl
│   └── ...
├── coverage_report.json      (state space coverage matrix)
├── validation_report.json    (invariant check results)
├── distribution_report.json  (actual vs target distribution)
└── metadata.json             (generation parameters, agent versions)
```

### 12.2 Trajectory File Format

Each `.jsonl` file contains one CognitiveObservation JSON per line:

```
{"schema":"CognitiveObservation","version":"1.0","session_id":"synth_0001","observation_index":0,"timestamp":"2026-03-28T09:00:00Z","state":{"momentum":"cold_start","burnout":"GREEN",...},...}
{"schema":"CognitiveObservation","version":"1.0","session_id":"synth_0001","observation_index":1,...}
...
```

### 12.3 Coverage Report

```json
{
  "total_trajectories": 10000,
  "total_observations": 450000,
  "state_combinations_possible": 500,
  "state_combinations_covered": 487,
  "uncovered_combinations": ["peak+RED+depleted (unreachable by invariants)", ...],
  "transition_pairs_possible": 89,
  "transition_pairs_covered": 89,
  "edge_cases_generated": 500,
  "edge_cases_validated": 498,
  "edge_cases_failed": 2,
  "invariant_violations_found": 0,
  "regeneration_rounds": 3
}
```

---

## 13. Integration with LeWorldModel Training

### 13.1 Training Pipeline

```
synthetic_data/trajectories/*.jsonl
    → Parse into (observation_t, action_t, observation_{t+1}) tuples
    → Split: 80% train, 10% validation, 10% test
    → Encode observations into state vectors
    → Train LeWorldModel encoder + predictor
    → Evaluate on held-out test set
    → Report prediction accuracy per state field
```

### 13.2 State Vector Encoding

For LeWorldModel training, each CognitiveObservation is encoded as a fixed-length vector:

```
[momentum_onehot(5), burnout_onehot(4), energy_onehot(4), altitude_onehot(4),
 exercise_recency_norm(1), sleep_onehot(3), context_onehot(3),
 exchange_velocity_norm(1), topic_coherence(1), session_exchange_count_norm(1),
 burst_phase_onehot(5), tangent_budget_norm(1),
 injection_profile_onehot(5), injection_alpha(1), injection_phase_onehot(4),
 allostatic_load(1), allostatic_trend_onehot(4),
 sessions_24h_norm(1), override_ratio(1)]

Total: ~50 dimensions
```

Action is encoded separately:

```
[action_type_onehot(10)]
```

### 13.3 Organic Data Integration

Once real sessions begin producing CognitiveObservation logs:

1. Append organic observations to training set
2. Fine-tune model on mixed synthetic + organic data
3. Weight organic data higher (2x–5x) to bias toward personal calibration
4. PredictionAuditComputation provides per-session accuracy for monitoring

---

*Cognitive State Machine Specification v1.0*  
*Autoresearch-Ready Synthetic Trajectory Generator*  
*Patent Pending — JEPA Cognitive State Prediction (P6)*  
*Joseph O. Ibrahim | March 2026*
