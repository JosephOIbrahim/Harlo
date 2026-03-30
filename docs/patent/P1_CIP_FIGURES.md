# P1 CIP Figures — Descriptions for FIG. 10-16

**Classification:** CONFIDENTIAL — Patent Pending
**Author:** Joseph O. Ibrahim
**Date:** March 30, 2026

---

## FIG. 10: Cognitive Computation DAG

**Title:** Topologically-Sorted Computation DAG for Cognitive State Evaluation

**Description:** A directed acyclic graph showing the dependency-ordered evaluation of cognitive state computations. The graph contains seven computation nodes: `compute_burst`, `compute_energy`, `compute_momentum`, `compute_burnout`, `compute_allostasis` (dependent chain), plus `compute_injection_gain` and `compute_context_budget` (independent). Directed edges encode dependencies: burst → energy → momentum → burnout → allostasis. Each node reads authored USD time samples at exchange_index t-1 and writes computed results at exchange_index t. Post-DAG enforcement nodes apply invariants: INV-11 (RED burnout forces CRASHED momentum) and INV-15 (RED burnout kills active burst). The stage stores results as JSON strings in USD `data` attributes with `Usd.TimeCode(exchange_index)` time samples.

---

## FIG. 11: Delegate Exchange Cycle

**Title:** Hydra-Pattern Delegate Sync/Execute/CommitResources Cycle

**Description:** A sequence diagram showing the per-exchange delegate lifecycle. (1) MCP tool call received. (2) CognitiveEngine authors exchange data to USD stage. (3) MockCogExec evaluates full DAG. (4) `compute_routing` outputs capability requirements (supported_tasks, latency_max, context_budget, requires_coding). (5) DelegateRegistry matches requirements to registered delegates. (6) Selected delegate receives `sync(stage_view, computed_values, task_context)`. (7) Delegate executes, producing `DelegateResult` with response, proposed_mutations, observation_data. (8) Delegate commits mutations to its own `.usda` sublayer. (9) CognitiveObservation emitted to buffer. (10) XGBoost prediction authored to `/prediction/forecast`. (11) Stage saved to disk.

---

## FIG. 12: Capability-Requirement Routing

**Title:** Separation of Cognitive Requirements from Delegate Binding

**Description:** A two-phase routing diagram. Phase 1 (DAG-side): `compute_routing` evaluates cognitive signals (frustration, coherence, velocity, burnout, energy) and outputs an expert classification (validator, scaffolder, restorer, socratic, direct) plus capability requirements dict. The requirements specify what is needed, never who provides it. Phase 2 (Bridge-side): DelegateRegistry filters registered delegates by requires_coding, supported_tasks overlap, context_budget minimum, and latency_max. Candidates sorted by latency (lower preferred), then context window (higher preferred). Best match selected. Safety overrides shown: RED burnout always forces restorer (consent ignored), ORANGE without valid consent forces restorer.

---

## FIG. 13: Context Budget Hysteresis

**Title:** Hysteresis-Based Context Budget Management Preventing Payload/Reference Thrashing

**Description:** A state diagram with two states: PAYLOAD and REFERENCE. Transition PAYLOAD → REFERENCE occurs when compression_factor > 4.2x (promote threshold). Transition REFERENCE → PAYLOAD occurs when compression_factor < 3.8x (demote threshold). The dead zone between 3.8x and 4.2x maintains the current state, preventing oscillation when effective context hovers near the 4.0x boundary. An annotated timeline shows a compression_factor that oscillates between 3.9x and 4.1x — without hysteresis this causes infinite promote/demote cycling; with hysteresis the state remains stable.

---

## FIG. 14: OOB Consent Token Flow

**Title:** Out-of-Band Cryptographic Consent Token Lifecycle

**Description:** A three-lane swimlane diagram. Lane 1 (Application Layer): User clicks acknowledgment in native UI → application generates HMAC-signed consent token with scope and TTL → token authored to `/sessions/consent` on USD stage as Reference arc. Lane 2 (OpenExec DAG): `compute_routing` reads consent token → validates signature (HMAC-SHA256), checks TTL (current_exchange ≤ granted_exchange + ttl_exchanges), checks scope → if valid, respects user override of ORANGE burnout; if invalid or absent, forces restorer. Lane 3 (Delegate): Delegate cannot read signing key → cannot forge token → cannot self-authorize override. RED burnout shown as unconditional override that ignores consent entirely. Revocation path shown: application sets `revoked=True`, subsequent validation fails immediately.

---

## FIG. 15: Stratified PER Buffer

**Title:** Stratified Prioritized Experience Replay with Locked Synthetic Anchor Partition

**Description:** A partitioned buffer diagram. Left partition (20%): Anchor — synthetic trajectories from autoresearch, locked (never deleted, never overwritten), contains full state-space coverage including rare transitions (RED events, burst crashes, injection interactions). Right partition (80%): Organic — live CognitiveObservations from delegates, priority-scored by surprise (|predicted - actual|), high-surprise observations ranked higher, lowest-priority evicted at capacity. Training batch composition: 20% sampled from anchor, 80% sampled from organic (priority-weighted). Arrows show: autoresearch → anchor (one-time seed), live sessions → organic (continuous), combined batch → XGBoost trainer. Catastrophic forgetting prevention annotated: even during 10,000 stable-GREEN exchanges, the anchor partition ensures the model retains rare-state prediction capability.

---

## FIG. 16: Adrenaline Masking Timeline

**Title:** Energy State Suspension During Burst Phases with Debt Application on Exit

**Description:** A dual-track timeline. Top track: Burst phase progression (NONE → DETECTED → PROTECTED → WINDING → EXIT_PREP → NONE) across 80 exchanges. Bottom track: Energy level. During NONE phase (exchanges 0-15): energy decrements normally from HIGH to MEDIUM at exchange 10. At exchange 15, burst DETECTED: energy track shows a "suspended" annotation — the value is frozen at MEDIUM. Burst progresses through PROTECTED (exchange 16) and WINDING (exchange 50). Accumulated debt counter increments each exchange during burst: 35 exchanges of debt. At exchange 70, EXIT_PREP → NONE: debt of 35 exchanges applied. Energy drops from MEDIUM(2) to DEPLETED(0) (capped at floor). Without adrenaline masking (dashed line): energy would have hit DEPLETED at exchange 30, making burst WINDING at exchange 50 unreachable — the user would have been forced out of flow state by energy exhaustion. The masking mechanism preserves deep flow states by deferring the energy cost to burst exit.
