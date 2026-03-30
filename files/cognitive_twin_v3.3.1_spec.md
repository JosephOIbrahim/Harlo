# Cognitive Twin — Architecture Specification

**Version:** 3.3.1 (Claude Code Handoff — Gemini R3 Patched)  
**Author:** Joseph O. Ibrahim  
**Date:** March 30, 2026  
**Classification:** CONFIDENTIAL — Patent Pending  
**Lineage:** v3.1 (OpenExec-native) → Gemini R1 (5 structural fixes) → v3.2 (Trinity-RFT synthesis) → Gemini R2 (5 semantic fixes) → v3.3 (final) → **Gemini R3 (4 pre-flight patches)**  
**Purpose:** Claude Code autonomous execution via Sequential MoE agent teams  
**Companion:** AGENTS.md (execution protocol with binary phase gates)  

---

## Gemini Round 2 Corrections Integrated

| Directive | Change | Section |
|-----------|--------|---------|
| Replace HMM with XGBoost | Cognitive state is fully observable (MDP, not HMM). XGBoost predicts State_{t+1} from N-step history window. | §8 |
| Monotonic exchange_index as TimeCode | Wall-clock time collides during burst. Use strictly monotonic integer. Physical time gaps become authored attributes. | §5.1 |
| Out-of-Band user_consent_token | Resolves autonomy vs. immunity paradox. Permission grants authored from application layer, outside LLM context. | §5.4 |
| Rewrite P1 routing claim | Don't claim delegate separation (obvious from Hydra). Claim dynamic cognitive-to-hardware resource translation. | §11 |
| Stratified PER in learning buffer | Locked synthetic anchor partition prevents catastrophic forgetting during organic data accumulation. | §8.3 |

## Gemini Round 3 Pre-Flight Patches (Agentic Execution Traps)

| Patch | Change | Section |
|-------|--------|---------|
| INV-14 RED event exception | Burnout doesn't skip levels under normal accumulation. EXCEPTION: Exogenous RED event triggers ANY → RED immediately. Without this, the trajectory generator deadlocks trying to hit the 5% crisis distribution target. | §5.2 |
| Adrenaline masking | Energy decrements SUSPEND during active burst phases (detected, protected, winding). Accumulated energy debt applies on transition to exit_prep or none. Without this, deep flow states self-destruct at 30 exchanges — making burst winding (50+) and exit_prep (70+) unreachable. | §5.2 |
| XGBoost encoding fix | Ordinal encoding for progressive states (GREEN=0..RED=3) preserves progressivity for tree splits. MultiOutputClassifier wraps XGBClassifier for multi-dimensional Y target. One-hot encoding destroys ordinality and crashes single-output XGBoost. | §8.2 |
| Context budget hysteresis | Promote Payload→Reference when compression > 4.2x. Demote when < 3.8x. Dead zone prevents thrashing when effective context hovers at exactly 4.0x boundary. | §7.1 |

---

## 1. What This Is

The Cognitive Twin is an AI system that models how you think, not just what you know. It remembers your projects across sessions, detects burnout before you notice, routes tasks to the right AI model, and adapts to your energy, context, and momentum — against a single, inspectable, debuggable state representation that you own.

The architecture applies three VFX infrastructure patterns to cognitive AI:

- **USD composition** (Pixar) — LIVRPS priority resolution for cognitive state conflicts
- **OpenExec** (Pixar, USD 26) — the central router. Every cognitive decision is an OpenExec computation.
- **Hydra delegates** (Pixar) — model-agnostic LLM orchestration

Plus three AI/ML components:

- **XGBoost sequence prediction** — forecasts next cognitive state from observable history (Sprint 1). JEPA reserved for raw-input future milestone.
- **TurboQuant KV compression** (ICLR 2026) — 4x floor / 6x burst for delegate context capacity
- **Autoresearch synthetic data** (Karpathy) — eliminates cold start via agentic trajectory generation

---

## 2. Design Principles

1. **OpenExec is the router.** Every cognitive decision flows through the exec network. Deterministic. Cacheable. Inspectable.
2. **Stage-first.** All cognitive state is USD prims. No shadow state.
3. **Delegate-agnostic.** The stage never names a specific LLM.
4. **Prediction is off-DAG.** Neural/ML inference never blocks the exec network. Predictions are authored to the stage as Payloads, asynchronously.
5. **Lossless-always.** `output = clean + α × δ`. Clean signal always recoverable.
6. **Compression-aware.** 4x hard floor. Composition arc choices adapt to effective context capacity.
7. **Parameterized, not hardcoded.** C++ callbacks read thresholds from stage attributes. Personality tuning via USDA, not recompilation.
8. **Ships in sprints.** Each sprint delivers standalone value.

---

## 3. The Problem

Current AI assistants are stateless. Every conversation starts from zero. The tools that attempt persistence (Mem0, Letta, Zep) use vector databases with three structural limitations:

1. **No composition semantics.** Conflicting memories → last-write-wins or relevance-score-wins.
2. **No evaluable state.** Burnout isn't computed — it's at best a tag on a memory chunk.
3. **No prediction.** These systems look backward, never forward.

**Prior art:** arXiv:2602.19320 surveyed 100+ agentic memory architectures. Zero use USD. arXiv:2603.10062 confirmed this for multi-agent systems.

---

## 4. The Substrate: USD 26

### 4.1 Composition Arc Mapping

| Arc | Priority | Cognitive Role |
|-----|----------|---------------|
| **L** (Local) | Strongest | Session override. OpenExec computed values. Safety overrides (with OOB consent gate). |
| **I** (Inherit) | ↓ | Role defaults. Delegate capabilities. |
| **V** (Variants) | ↓ | Injection profiles, work/family mode. |
| **R** (References) | ↓ | External truth: calendar, patents, documents. |
| **P** (Payloads) | ↓ | Lazy-loaded: holding projects, predictions. Promoted to Reference when 4x compression floor allows. |
| **S** (Specialize) | Weakest | Base patterns: ADHD architecture, constitutional values. |

### 4.2 Stage Structure

```
/cognitive_twin.usda
├── /identity/              [Specialize]  constitutional, roles, patterns
├── /state/                 [Local]       momentum, burnout, energy, altitude, body, injection, allostatic
├── /routing/               [Inherit]     expert registry, capability→expert cascade
├── /injection/             [Variants]    profiles, anchors (structurally immune), modulated phases
├── /sessions/              [Reference]   active session, delegate sublayers, consent tokens
├── /projects/              [Payload]     focus (loaded), holding (payloaded)
├── /memory/                [Reference]   episodic, semantic, procedural, decisions
├── /prediction/            [Payload]     forecasts (authored async, never computed in-DAG)
└── /delegates/             [Inherit]     registry, capabilities, context budget
```

### 4.3 Schemas (USDA → usdGenSchema → C++)

**CognitiveStatePrimAPI:**
```
token momentum = "cold_start"
token burnout = "GREEN"
token energy = "high"
token altitude = "10k"
int exercise_recency = 0
token sleep_quality = "unknown"
token context = "desk"
# Thresholds — tunable via USDA, read by OpenExec callbacks
int building_task_threshold = 3
float rolling_coherence_threshold = 0.7
int burst_detection_velocity = 3
float burnout_yellow_exchange_threshold = 30
```

**InjectionPrimAPI:**
```
token profile = "none"
float s_nm = 0.0
float alpha = 0.0
token phase = "baseline"
int exchange_count = 0
token routing_mode = "standard"
float cross_expert_bleed = 0.0
```

**DelegatePrimAPI:**
```
token delegate_id = "claude"
token status = "idle"
token[] supported_tasks
token latency_class = "interactive"
string active_sublayer = ""
int raw_context_tokens = 200000
float compression_factor = 1.0       # 1.0 = none, 4.0 = TurboQuant floor
int effective_context_tokens = 200000 # raw × compression
token context_budget_mode = "fixed"   # fixed | adaptive
```

**SessionConsentAPI** (new — resolves autonomy/immunity paradox):
```
token user_consent_token = ""         # authored by application layer, outside LLM context
int consent_timestamp = 0            # exchange_index when consent was granted
token consent_scope = "none"          # none | override_burnout | override_safety
int consent_ttl_exchanges = 10        # consent expires after N exchanges
```

**CognitiveObservationAPI:**
```
int exchange_index = 0               # monotonic integer — THE temporal key
float wall_clock_delta = 0.0          # seconds since previous exchange (authored attribute)
token action_type = "query"
float exchange_velocity = 0.0
float topic_coherence = 0.0
token burst_phase = "none"
float allostatic_load = 0.0
token allostatic_trend = "stable"
```

---

## 5. OpenExec Computation Layer

### 5.1 Temporal Indexing: exchange_index, Not Wall-Clock

**Problem (Gemini R2):** Wall-clock UsdTimeCodes collide during rapid burst phases. Multiple exchanges within the same second produce identical floating-point time values, destroying t vs. t-1 cycle avoidance.

**Fix:** All UsdTimeCodes use a strictly monotonic integer `exchange_index`. Physical time gaps are authored as attributes at that index:

```
Exchange happens (exchange_index = 42)
    → Bridge authors: /state.exchange_index = 42
    → Bridge authors: /state.wall_clock_delta = 1.3  (seconds since index 41)
    → Bridge authors: /state.task_completions[42] = 5
    → Bridge authors: /state.momentum_phase[41] = "building"  (previous state)
    → OpenExec evaluates computeMomentum
        → reads task_completions[42] (current authored)
        → reads momentum_phase[41] (previous authored)
        → reads building_task_threshold (stage attribute = 3)
        → computes: tasks(5) >= threshold(3) → "rolling"
    → Bridge authors result: /state.momentum_phase[42] = "rolling"
```

No self-reference. No cycles. No wall-clock collisions. Topologically safe at any exchange velocity.

### 5.2 Registered Computations

| Computation | Inputs (authored at exchange_index) | Output | Notes |
|------------|--------------------------------------|--------|-------|
| **computeRouting** | momentum, energy, burnout, signal_class, injection_gain, consent_token | Capability requirements + expert | Outputs requirements, NOT delegate binding. Safety override if burnout ≥ ORANGE and no valid consent. |
| **computeInjectionGain** | profile, exchange_count, receptor_density | Gain per phase, alpha, mixing state | Anchor callback: separate schema, returns 1.0 unconditionally. |
| **computeMomentum** | task_completions[t], momentum_phase[t-1], exchange_velocity, wall_clock_delta, thresholds | Momentum phase | Reads t-1 from authored history. Thresholds from stage attributes. |
| **computeBurnout** | exchange_count, velocity, allostatic, frustration_signals[t], burnout[t-1] | Burnout level | Never skips levels under normal accumulation. **EXCEPTION (R3): Exogenous RED event triggers ANY → RED immediately, bypassing sequential rule.** |
| **computeEnergy** | sleep, exercise_recency, exchange_count, breaks, energy[t-1], burst_phase[t] | Energy level | Event-driven. Exercise = high. 30+ exchanges without break = decrement. **ADRENALINE MASKING (R3): Energy decrements SUSPEND while burst_phase ∈ {detected, protected, winding}. Accumulated debt applies on transition to exit_prep or none.** |
| **computeBurst** | exchange_velocity, topic_coherence, response_length, burst[t-1] | Burst phase | none→detected→protected→winding→exit_prep. Sequential only. |
| **computeAllostatic** | sessions_24h, duration, RED_events_7d, override_ratio, exercise, sleep | Load [0,1] + trend | Weighted sum. 4x floor for context budget decisions. |
| **computePermission** | burnout, momentum, energy, allostatic, override_history, consent_token | Grants + override status | 80/20 model. Reads OOB consent token for override validation. |
| **computePredictionAudit** | /prediction/forecast[t-1] (authored Payload), actual computed state[t] | Delta, accuracy, confidence | Deterministic comparison. In-DAG. Fast. No neural inference. |

### 5.3 Anchor Immunity

Four phases use separate registered callbacks on a separate schema (AnchorPhaseAPI):

```cpp
EXEC_REGISTER_COMPUTATIONS_FOR_SCHEMA(AnchorPhaseAPI)
{
    RegisterComputation("computeGain", [](auto& inputs) {
        return 1.0;  // Unconditional. receptor_density never evaluated.
    });
}
```

CONSTITUTIONAL, SAFETY, CONSENT, KNOWLEDGE: gain = 1.000 always. Different schema. Different callback. No code path from injection parameters to anchor output.

### 5.4 The Autonomy/Immunity Resolution (OOB Consent Token)

**Problem (Gemini R2):** If the Local-arc safety override bypasses the Permission Engine, user autonomy is destroyed. If it respects the Permission Engine, the indirect injection vector returns (a compromised delegate could hallucinate consent).

**Fix:** Out-of-Band (OOB) cryptographic consent token.

```
Application Layer (OTTO/Orchestra — native UI, outside LLM context)
    → User clicks "I acknowledge burnout, continue anyway"
    → App generates user_consent_token (signed, timestamped)
    → App authors token directly to /sessions/consent.usda [Reference arc]

OpenExec computeRouting:
    → if (burnout >= ORANGE && !isValid(consent_token)):
        → override: force Restorer expert, regardless of injection state
    → if (burnout >= ORANGE && isValid(consent_token)):
        → respect override, log it, feed override_ratio to allostatic
    → if (burnout == RED):
        → override ALWAYS, consent token ignored. RED is non-negotiable.

Consent token properties:
    → Authored by native app, never by LLM delegate
    → Signed (delegate cannot forge)
    → TTL: expires after N exchanges (default: 10)
    → Scope: specific to burnout override (not blanket permission)
```

This preserves:
- **Structural immunity:** Delegates cannot forge consent. The token is authored by the app layer.
- **User autonomy:** The 80/20 model works. User can override ORANGE with explicit acknowledgment.
- **Safety floor:** RED is non-negotiable regardless of consent. Body-first, always.

### 5.5 Lossless Guarantee

```
output = clean + α × δ
reconstruct_clean(output) == clean    (always)
```

Two mechanisms: computational (subtraction) and structural (flatten to base sublayer). RED → α = 0.0 immediately.

---

## 6. The Delegate Layer

### 6.1 Interface

```python
class HdCognitiveDelegate:
    def GetDelegateId(self) -> str: ...
    def GetSupportedTaskTypes(self) -> list[str]: ...
    def GetDelegateCapabilities(self) -> DelegateCapabilities: ...
    def Sync(self, stage_view, computed_values, task_context): ...
    def Execute(self, task) -> DelegateResult: ...
    def CommitResources(self, result) -> list[StageMutation]: ...
```

Delegates consume computed state. They never run OpenExec computations. They never forge consent tokens. They write to their own sublayer.

### 6.2 Capability-Requirement Routing

The DAG outputs capability requirements. The Bridge binds hardware:

```
computeRouting output:
    expert: "scaffolder"
    requirements: { needs_coding: false, latency: "interactive", context: "heavy" }

Bridge:
    candidates = delegate_registry.match(requirements)
    selected = candidates.best_fit(prefer: lower_latency, then: higher_context)
    selected.Sync(stage_view, computed_values)
```

The DAG doesn't know about Claude. It knows about capabilities. The Bridge handles physical binding.

### 6.3 Concurrent Access

Per-delegate sublayers. LIVRPS resolves conflicts. Interactive delegate wins by default.

### 6.4 Shipped Delegates

**HdClaude** — Reasoning, coaching, architecture. Interactive.
**HdClaudeCode** — Implementation, code, debugging. Batch.
**[HdLocal]** — Future. Local model + TurboQuant (4x floor).

---

## 7. KV Compression

### 7.1 Context Budget (with Hysteresis — R3)

```
effective_context = raw_window × compression_factor
compression_factor: 4.0 (hard floor), 6.0 (burst, not guaranteed)

HYSTERESIS (prevents thrashing at boundary):
    Promote Payload → Reference when compression_factor > 4.2x
    Demote Reference → Payload when compression_factor < 3.8x
    Dead zone [3.8, 4.2]: no state change. Maintains current loading.

Without hysteresis, context hovering at exactly 4.0x causes infinite
promote/demote cycling every exchange — fragmenting GPU memory.
```

### 7.2 Adaptive Loading

| effective_context vs. stage size | Loading behavior |
|----------------------------------|-----------------|
| > full_stage | Everything as Reference. No Payloads. |
| > focus_stage | Focus + prediction + recent memory as Reference. Holding Payloaded. |
| ≤ focus_stage | Triage: task-relevant prims only. |

### 7.3 Local-First

RTX 4090 (24GB) with TurboQuant: viable local delegate with 4x context expansion.
Mac Studio M1 (128GB): cloud-tier effective context.

---

## 8. Prediction Layer (Off-DAG, Asynchronous)

### 8.1 Architecture

Prediction is **fully decoupled** from the OpenExec DAG. It follows an **Asynchronous Dynamics Modeling** pipeline (not RFT — terminology corrected per Gemini R2):

```
Delegates                    Observation Buffer              Prediction Trainer
(generate observations)      (SQLite priority queue)         (XGBoost, async)
       │                            │                              │
       │  CognitiveObservation      │                              │
       │  (exchange_index keyed)    │                              │
       ▼                            ▼                              │
  ┌─────────┐               ┌──────────────┐                      │
  │ HdClaude│──observation──▶│   Buffer     │──sampled batch──────▶│
  │ HdCode  │               │              │                      │
  └─────────┘               │ Stratified   │              ┌───────▼────────┐
       │                    │ PER:         │              │ XGBoost model  │
  Autoresearch              │  20% anchor  │              │ (Sprint 1)     │
  synthetic data ──inject──▶│  80% organic │              │                │
                            │  (high-      │              │ Trains on:     │
                            │   surprise)  │              │ (state, action,│
                            └──────────────┘              │  next_state)   │
                                                          └───────┬────────┘
                                                                  │
                                                          Predictions authored
                                                          to /prediction/ as
                                                          Payload prims on stage
```

### 8.2 Why XGBoost, Not HMM or JEPA

**HMM is wrong** (Gemini R2): Cognitive states aren't hidden — they're explicitly computed by OpenExec. This is a fully-observable MDP, not a hidden-state inference problem.

**JEPA is overkill** (Gemini R1): ~50-dimensional discrete tabular state. JEPA handles continuous, high-dimensional, pixel-level data. It will overfit on structured synthetic data instantly.

**XGBoost is right:** Tabular data is its native domain. Predicts State_{t+1} from an N-step history window of (computed_state, action) pairs. Trains in seconds on CPU. Evaluates in microseconds. Natively learns the guard-condition thresholds that the state machines already define.

**Encoding (R3 patch):** Progressive states use **ordinal encoding** (Burnout: GREEN=0, YELLOW=1, ORANGE=2, RED=3; Energy: DEPLETED=0..HIGH=3; Momentum: CRASHED=0..PEAK=4). This preserves ordinality for XGBoost tree splits — the model learns that RED > ORANGE, not that they're orthogonal one-hot vectors. Multi-dimensional Y target uses `sklearn.multioutput.MultiOutputClassifier(xgb.XGBClassifier())`. Features exclude `exchange_index` and `session_id` (temporal leakage).

**JEPA becomes justified when:**
- Organic data exceeds 1000+ sessions
- XGBoost accuracy plateaus
- Input expands to raw signals (text embeddings, screen context, biometrics)
- The prediction task shifts from "what structured state comes next?" to "what unstructured pattern is emerging?"

### 8.3 Stratified Prioritized Experience Replay (PER)

**Problem (Gemini R2):** Synthetic data covers state space uniformly. Organic data will be 80%+ "stable GREEN." Unconstrained sampling causes the model to forget edge-case trajectories (RED events, burst crashes, injection interactions).

**Fix:** The SQLite buffer maintains two partitions:

```
Anchor Partition (locked):
    - Synthetic trajectories from Autoresearch
    - Never deleted, never overwritten
    - Contains full state-space coverage including rare transitions
    - Sampled at fixed 20% ratio per training batch

Organic Partition (rolling):
    - Live CognitiveObservations from delegates
    - Priority scoring: surprise = |predicted_state - actual_state|
    - High-surprise observations (state transitions, RED events, overrides)
      ranked higher than routine stable-GREEN exchanges
    - Sampled at 80% ratio per training batch, weighted by surprise score
    - Oldest low-priority observations evicted when buffer reaches capacity
```

Every training batch: 20% synthetic anchor + 80% high-surprise organic. The model never forgets how to predict catastrophic trajectories, even during long stretches of stable operation.

### 8.4 Confidence Gating (unchanged)

| Confidence | Behavior |
|-----------|----------|
| < 0.6 | Silent. Logged only. |
| 0.6 – 0.8 | Surfaced in delegate context. No auto-intervention. |
| ≥ 0.8 | Proactive: crash prevention, permission timing, burst optimization. |

`computePredictionAudit` (in-DAG, deterministic) compares authored prediction Payloads against current computed state. Feeds confidence into computePermission.

---

## 9. Observation Schema

Every exchange emits a CognitiveObservation keyed by `exchange_index` (monotonic integer):

```json
{
  "exchange_index": 42,
  "wall_clock_delta": 1.3,
  "state": {
    "momentum": "rolling",
    "burnout": "GREEN",
    "energy": "medium",
    "altitude": "10k"
  },
  "action_type": "directive",
  "dynamics": {
    "exchange_velocity": 2.1,
    "topic_coherence": 0.85,
    "burst_phase": "detected"
  },
  "injection": { "profile": "none", "alpha": 0.0 },
  "delegate": { "active": "claude", "task_type": "reasoning" },
  "allostatic": { "load": 0.35, "trend": "stable" }
}
```

**Emit now. Before prediction ships.** Append-only JSONL per session. Every session without observations is training data gone forever.

---

## 10. Implementation Sprints

### Sprint 1: Python Mock + USD Stage + XGBoost Prediction (Days)

1. USDA schema descriptions → usdGenSchema (generates classes)
2. `MockCogExec.py` (networkx DAG) — validates all state machine logic
3. USD 26 stage composes on Mac Studio
4. Autoresearch generates 10K+ synthetic trajectories
5. XGBoost trains on synthetic data (seconds, CPU)
6. Predictions authored to stage as Payload prims
7. HdClaude delegate reads computed + predicted state via MCP Bridge
8. CognitiveObservation logging active (exchange_index keyed)
9. Stratified PER buffer seeded with synthetic anchor partition

**Done when:** User query → signal classification → MockCogExec → delegate Sync → response → observation → prediction audit → loop works end-to-end.

### Sprint 2: OpenExec Native (Weeks)

1. USD 26 builds headless on Mac Studio: `build_usd.py --no-imaging --no-usdview --no-ptex --no-embree --openexec`
2. C++ computation callbacks (parameterized, reading thresholds from stage)
3. Time-sampled state history (exchange_index, no cycles)
4. Anchor immunity verified (separate AnchorPhaseAPI callbacks)
5. OOB consent token integration (SessionConsentAPI)
6. MockCogExec tests become OpenExec verification (same inputs → same outputs)

**Done when:** All Sprint 1 tests pass against native OpenExec. MockCogExec.py deleted.

### Sprint 3: Multi-Delegate + Compression + Async Learning (Weeks)

1. HdClaudeCode delegate
2. Sublayer-per-delegate concurrency
3. Capability-requirement routing (DAG outputs requirements, Bridge binds)
4. TurboQuant integration (4x floor, adaptive context budget)
5. Async dynamics modeling pipeline: organic observations → buffer → XGBoost retrain
6. Stratified PER active (20% synthetic / 80% organic)

**Done when:** Two delegates simultaneously. Prediction improves from live data. Audit accuracy trending upward.

---

## 11. Patent Claims (Gemini R2 Corrected)

### P1 CIP: USD Cognitive Substrate

| Claim | Novelty Argument |
|-------|-----------------|
| OpenExec cognitive state machines on USD prims | New domain (rigging only currently). Deterministic, inspectable cognitive computation. |
| **Dynamic cognitive-to-hardware resource translation** | Allostatic load (simulated psychology) dynamically adjusts delegate context budget, triggering TurboQuant compression and USD Payload demotion. No prior art for psychological state → GPU memory management. |
| Monotonic exchange_index temporal indexing for cycle-free cognitive computation | Novel solution for recursive state in non-recursive DAG. |
| LIVRPS-enforced anchor safety with OOB consent gating | Composition-layer safety + cryptographic user autonomy. |
| Sublayer-per-delegate concurrent multi-model access | Composition-based concurrency resolution. |

### P3 CIP: Digital Injection Framework

| Claim | Novelty Argument |
|-------|-----------------|
| Parameterized OpenExec gain computation (thresholds from stage) | Tunable modulation without recompilation. |
| Structural anchor immunity via separate schema callbacks | Provable exclusion — AnchorPhaseAPI vs. ModulatedPhaseAPI. |
| Lossless reconstruction via USD sublayer flattening | Composition-based reversal. |

### P6 New: Cognitive State Prediction

| Claim | Novelty Argument |
|-------|-----------------|
| **Asynchronous cognitive prediction authored as USD Payloads** | 3D LOD mechanism applied to predictive LLM compute scheduling. Predictions load only when context budget permits. Highly novel. |
| Synthetic trajectory generation from cognitive state machine specifications | Training data from architecture, not usage. |
| Stratified PER with locked synthetic anchor partition | Prevents catastrophic forgetting during organic distribution shift. |
| Confidence-gated proactive coaching | Earned trust via demonstrated accuracy. |
| Model-agnostic prediction (XGBoost → JEPA progression) | Trainer swap without stage changes. |

**Note:** Trinity-RFT relegated to specification as implementation feasibility reference, NOT cited in claims. The pipeline pattern is prior art; the domain application is the invention.

### Prior Art

- Zero USD-based cognitive architectures (arXiv:2602.19320, arXiv:2603.10062)
- Zero OpenExec applications outside rigging/animation
- Zero Hydra delegates outside rendering
- Zero "psychological state → hardware resource translation" in any domain

---

## 12. Build Configuration

### USD 26 Headless Build (Gemini R2 recommendation)

```bash
python build_usd.py \
    --no-imaging \
    --no-usdview \
    --no-ptex \
    --no-embree \
    --openexec \
    /opt/usd-26.03
```

Strips all VFX rendering components. Treats USD as a headless data-substrate. ~15 minute compile on Mac Studio M1. Eliminates TBB/Clang/ARM64 conflicts from graphics modules.

---

## 13. References

| Reference | Role |
|-----------|------|
| OpenExec (Pixar, USD 26) | Central computation engine |
| IrFkController (USD v26.03) | Reference: schema + OpenExec computation pattern |
| TurboQuant (Zandieh et al., ICLR 2026) | KV compression, 4x floor |
| Hydra / Hydra 2.0 (Pixar) | Delegate pattern |
| XGBoost (Chen & Guestrin, 2016) | Sprint 1 prediction model |
| Autoresearch (Karpathy, 2026) | Synthetic data generation |
| Trinity-RFT (Pan et al., arXiv:2505.17826) | Pipeline pattern reference (spec only, not claims) |
| arXiv:2602.19320, arXiv:2603.10062 | Prior art clearance |
| DMF Model (Herzog et al., 2023) | Injection gain modulation |

---

## 14. Companion Documents

1. **Cognitive State Machine Specification** — Full transition tables, guard conditions, 26 invariants, Autoresearch harness instructions. Direct input to synthetic trajectory generation.

2. **Patent Portfolio Matrix** — P1-P6 status, updates needed, new filings. Interactive artifact.

---

*Cognitive Twin v3.3 — Gemini Round 2 Integrated*  
*Two-round adversarial review complete*  
*Ready for Claude Code execution*  
*Patent Pending — Joseph O. Ibrahim | March 2026*
