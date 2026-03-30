# P1 CIP Evidence — Cognitive Twin v3.3.1

**Classification:** CONFIDENTIAL — Patent Pending
**Author:** Joseph O. Ibrahim
**Date:** March 30, 2026
**Prior Filing:** P1 Provisional — USD Cognitive Substrate

---

## A. NEW MATTER SUMMARY

The P1 provisional covers: Kahan compensated summation, fixed-size evaluation tiling, non-destructive layered composition, Experience Accumulator, Cognitive World Model, counterfactual simulation, Simulation Arbiter.

The following mechanisms are NEW in v3.3.1 and form the basis for CIP claims:

### 1. OpenExec Cognitive State Machines as USD Computation Plugins

Cognitive state transitions (momentum, burnout, energy, burst, allostasis) are implemented as pure computation functions evaluated via a topologically-sorted DAG. Each computation reads authored time-sampled USD attributes at exchange_index t-1 and writes computed results at t. The architecture is designed for OpenExec `EXEC_REGISTER_COMPUTATIONS_FOR_SCHEMA` registration when Python bindings ship.

**Source:** `src/mock_cogexec.py`, `src/computations/*.py`
**Tests:** `tests/test_sprint1/test_cogexec.py` (41 tests)

### 2. Hydra-Pattern Cognitive Delegates (Capability-Requirement Routing)

LLM delegates implement a Hydra-pattern interface (`HdCognitiveDelegate` ABC with `Sync/Execute/CommitResources`). The computation DAG outputs **capability requirements** (not delegate names). A `DelegateRegistry` matches requirements to registered delegates by supported_tasks, latency_class, context_budget, and requires_coding. The DAG never names a specific LLM.

**Source:** `src/delegate_base.py`, `src/delegate_registry.py`, `src/delegate_claude.py`, `src/delegate_claude_code.py`
**Tests:** `tests/test_sprint3/test_delegate_base.py` (16), `tests/test_sprint3/test_delegates.py` (14)

### 3. Dynamic Cognitive-to-Hardware Resource Translation

Allostatic load (a computed psychological metric: 6-weight composite of frequency, intensity, crisis, compliance, recovery, sleep) dynamically adjusts delegate context budget. Rising allostatic load triggers USD Payload demotion via context budget hysteresis (promote >4.2x, demote <3.8x). This translates a simulated psychological state into hardware resource management decisions.

**Source:** `src/computations/compute_allostasis.py`, `src/computations/compute_context_budget.py`
**Tests:** `tests/test_sprint1/test_cogexec.py::TestComputeAllostasis` (3), `tests/test_sprint1/test_cogexec.py::TestComputeContextBudget` (3)

### 4. Sublayer-Per-Delegate Concurrency

Each delegate writes to its own real `.usda` sublayer file. The root stage composes all delegate sublayers via USD sublayer mechanics. Interactive delegate opinions (strongest) override batch delegate opinions (weakest) via LIVRPS-ordered priority. No cross-contamination between delegates.

**Source:** `src/mock_usd_stage.py` (sublayer methods), `src/cognitive_stage.py` (real `.usda` sublayers)
**Tests:** `tests/test_sprint3/test_concurrency.py` (11), `tests/test_sprint4/test_cognitive_stage.py::TestDelegateSublayers` (6)

### 5. Monotonic exchange_index as UsdTimeCode

All USD time samples use a strictly monotonic integer `exchange_index` instead of wall-clock time. This prevents floating-point collisions during rapid burst phases and guarantees cycle-free t vs. t-1 reads in the computation DAG. Physical time gaps are authored as separate attributes.

**Source:** `src/schemas.py` (exchange_index field), `src/mock_usd_stage.py` (author/read by exchange_index), `src/cognitive_stage.py` (Usd.TimeCode(exchange_index))
**Tests:** `tests/test_sprint1/test_schemas.py::TestMockUsdStage` (12), `tests/test_sprint4/test_cognitive_stage.py::TestCoreAPI` (7)

### 6. OOB Cryptographic Consent Tokens

Out-of-Band consent tokens are HMAC-signed, scoped, and TTL-limited. They are authored by the application layer (native code, outside LLM context). Delegates cannot forge consent. `computeRouting` validates consent before allowing burnout override. RED state ignores consent entirely.

**Source:** `src/consent.py`
**Tests:** `tests/test_sprint3/test_routing.py::TestConsentManager` (6)

### 7. Stratified Prioritized Experience Replay (PER)

The observation buffer maintains two partitions: anchor (20%, locked synthetic trajectories from autoresearch) and organic (80%, surprise-weighted live observations). This prevents catastrophic forgetting of rare state transitions during organic distribution shift.

**Source:** `src/observation_buffer.py`
**Tests:** `tests/test_sprint1/test_integration.py::TestObservationBuffer` (5), `tests/test_sprint3/test_live_e2e.py::TestLiveE2E::test_buffer_maintains_anchor_ratio`

### 8. Adrenaline Masking During Burst Phases

Energy decrements SUSPEND while burst_phase is in {DETECTED, PROTECTED, WINDING}. Accumulated energy debt applies on transition to EXIT_PREP or NONE. Without this mechanism, deep flow states self-destruct at ~30 exchanges, making burst winding (50+) and exit_prep (70+) unreachable.

**Source:** `src/computations/compute_energy.py`
**Tests:** `tests/test_sprint1/test_cogexec.py::TestComputeEnergy::test_burst_suspends_decrement`, `tests/test_sprint1/test_cogexec.py::TestComputeEnergy::test_adrenaline_debt_on_burst_exit`

### 9. Profile-Driven Markov Biasing for Synthetic Trajectories

The trajectory generator uses weighted session profiles (7 types: normal 40%, deep_work 15%, struggling 15%, recovery 10%, injection 10%, crisis 5%, mobile 5%) with forced parameter skewing. Deep Work sessions forcibly set coherence/velocity to 95%+ to guarantee burst states are reachable. This is NOT uniform random sampling.

**Source:** `src/trajectory_generator.py`
**Tests:** 10,000 sessions, 278,577 exchanges, 0 invariant violations (validated by `src/validator.py`)

### 10. XGBoost as Fully-Observable MDP Predictor

Cognitive state is fully observable (not hidden). XGBoost MultiOutputRegressor with ordinal encoding for progressive states and one-hot for nominals. 3-step sliding window. 111 features. 4 targets (momentum, burnout, energy, burst_phase). Trained on synthetic data, predicts live. Features exclude exchange_index and session_id (temporal leakage prevention).

**Source:** `src/train_predictor.py`, `src/predict.py`
**Tests:** `tests/test_sprint1/test_integration.py::TestBridgeIntegration::test_session_with_predictor`

### 11. Canonical CognitiveObservation Schema with Telemetry Block

Pydantic model with IntEnum ordinal types. Includes a telemetry block with externally-authored accumulators: `tasks_completed`, `exchanges_without_break`, `frustration_signal`, `adrenaline_debt`. Accumulators are authored by the Bridge/Generator, NOT tracked internally by computation functions (pure function requirement).

**Source:** `src/schemas.py` (CognitiveObservation, StateBlock, DynamicsBlock, etc.)
**Tests:** `tests/test_sprint1/test_schemas.py` (29 tests)

---

## B. CLAIM MAPPING

| New Mechanism | Extends P1 Claim | New Claim Language | Prior Art Argument |
|--------------|-------------------|--------------------|--------------------|
| OpenExec cognitive state machines | Experience Accumulator | "A method for evaluating cognitive state transitions via topologically-sorted computation DAGs registered as USD computation plugins, where each computation reads time-sampled authored attributes at exchange_index t-1 and writes computed results at t" | Zero OpenExec applications outside rigging/animation (arXiv:2602.19320, arXiv:2603.10062) |
| Hydra cognitive delegates | Cognitive World Model | "A system for routing AI model access via capability-requirement matching, where a computation DAG outputs required capabilities and a registry selects delegates without the DAG naming specific models" | Zero Hydra delegates outside rendering pipelines |
| Cognitive-to-hardware translation | Simulation Arbiter | "A method for dynamically translating computed psychological metrics (allostatic load) into hardware resource allocation decisions (context budget, compression factor, USD Payload demotion)" | Zero psychological state → GPU memory management in any domain |
| Sublayer-per-delegate concurrency | Non-destructive composition | "A system for concurrent multi-model access to a shared cognitive stage via per-delegate USD sublayers with LIVRPS-ordered composition resolution" | Novel application of USD sublayer mechanics to LLM orchestration |
| Monotonic exchange_index | Fixed-size evaluation tiling | "A method for temporal indexing of cognitive state using strictly monotonic integers as UsdTimeCodes, preventing floating-point collisions during rapid burst phases" | Novel solution for recursive state in non-recursive DAG |
| OOB consent tokens | (new claim) | "A cryptographic consent mechanism where signed, scoped, TTL-limited tokens are authored by an application layer outside the LLM context, preventing delegates from forging autonomy overrides" | No prior art for OOB consent in cognitive AI systems |
| Stratified PER | (new claim) | "A prioritized experience replay buffer with locked synthetic anchor partition (20%) and surprise-weighted organic partition (80%) for cognitive state prediction training" | Novel combination: PER (Schaul 2015) + locked anchor + cognitive domain |
| Adrenaline masking | (new claim) | "A method for suspending energy state decrements during detected burst phases and applying accumulated debt on burst exit, preventing premature flow state termination" | No prior art for burst-aware energy management in cognitive systems |
| Profile-Driven Markov | Counterfactual simulation | "A method for generating synthetic cognitive trajectories via profile-driven Markov biasing with forced parameter skewing to guarantee reachability of rare states" | Novel: Karpathy Autoresearch pattern applied to cognitive state space |
| XGBoost MDP predictor | (new claim) | "A cognitive state predictor using gradient-boosted trees on ordinal-encoded fully-observable MDP state, with 3-step sliding window and multi-output regression" | Novel domain application of XGBoost to cognitive prediction |
| CognitiveObservation schema | Cognitive World Model | "A canonical observation schema with IntEnum ordinal types and externally-authored telemetry accumulators for pure-function cognitive state evaluation" | No prior art for typed cognitive observation schemas |

---

## C. CODE-TO-CLAIM TRACEABILITY

| Claim Element | Source File | Key Function/Class | Line (approx) | Test File | Test Count |
|--------------|-------------|---------------------|---------------|-----------|------------|
| DAG topological evaluation | `src/mock_cogexec.py` | `evaluate_dag()`, `build_dag()` | 38-90 | `test_cogexec.py` | 41 |
| compute_momentum | `src/computations/compute_momentum.py` | `compute_momentum()` | 19-70 | `test_cogexec.py::TestComputeMomentum` | 7 |
| compute_burnout + RED exception | `src/computations/compute_burnout.py` | `compute_burnout()` | 17-62 | `test_cogexec.py::TestComputeBurnout` | 6 |
| compute_energy + adrenaline | `src/computations/compute_energy.py` | `compute_energy()` | 18-65 | `test_cogexec.py::TestComputeEnergy` | 5 |
| Anchor immunity | `src/computations/compute_injection_gain.py` | `compute_anchor_gain()` | 29-34 | `test_cogexec.py::TestComputeInjectionGain` | 6 |
| Context budget hysteresis | `src/computations/compute_context_budget.py` | `compute_context_budget()` | 17-41 | `test_cogexec.py::TestComputeContextBudget` | 3 |
| HdCognitiveDelegate ABC | `src/delegate_base.py` | `HdCognitiveDelegate` | 48-80 | `test_delegate_base.py` | 16 |
| DelegateRegistry | `src/delegate_registry.py` | `DelegateRegistry.select()` | 56-110 | `test_delegate_base.py::TestDelegateRegistry` | 10 |
| Capability routing | `src/computations/compute_routing.py` | `compute_routing()` | 23-90 | `test_routing.py` | 10 |
| OOB consent | `src/consent.py` | `ConsentManager` | 40-95 | `test_routing.py::TestConsentManager` | 6 |
| Sublayer concurrency | `src/mock_usd_stage.py` | `create_delegate_sublayer()`, `compose()` | 99-155 | `test_concurrency.py` | 11 |
| Real USD stage | `src/cognitive_stage.py` | `CognitiveStage` | 30-250 | `test_cognitive_stage.py` | 24 |
| Observation buffer | `src/observation_buffer.py` | `ObservationBuffer` | 1-150 | `test_integration.py::TestObservationBuffer` | 5 |
| XGBoost predictor | `src/train_predictor.py` | `train_model()` | 120-170 | integration tests | 3 |
| Trajectory generator | `src/trajectory_generator.py` | `generate_session()`, `generate_trajectories()` | 160-330 | 10K validated | 0 violations |
| 26 invariants | `src/validator.py` | `validate_trajectory()` | 20-140 | implicit (generator) | 26 checks |
| CognitiveObservation | `src/schemas.py` | `CognitiveObservation` | 100-155 | `test_schemas.py` | 29 |
| CognitiveEngine | `src/cognitive_engine.py` | `CognitiveEngine.process_exchange()` | 95-185 | `test_engine.py` + `test_mcp_live.py` | 22 |

---

## D. PRIOR ART CLEARANCE

| Prior Art Source | Searched For | Found | Conclusion |
|-----------------|-------------|-------|------------|
| arXiv:2602.19320 (Survey of 100+ agentic memory architectures) | USD-based cognitive architecture | Zero | Novel |
| arXiv:2603.10062 (Multi-agent memory systems) | USD composition for cognitive state | Zero | Novel |
| OpenUSD GitHub + Pixar documentation | OpenExec applications outside rigging | Zero (all examples: IrFkController, IrGeomConstraint) | Novel domain |
| Hydra 2.0 documentation | Hydra delegates outside rendering | Zero (all examples: Storm, Prman, Arnold, Embree) | Novel domain |
| Google Scholar, ACM DL, IEEE Xplore | "psychological state" + "hardware resource" + "GPU memory" | Zero | Novel translation |
| Google Scholar | "cognitive state" + "USD" + "composition" | Zero | Novel |
| PER literature (Schaul et al., 2015) | Stratified PER with locked anchor partition | Zero (standard PER uses uniform priority) | Novel variant |
| Autoresearch (Karpathy, 2026) | Application to cognitive state space | Zero (applied to code, math, reasoning) | Novel domain |
