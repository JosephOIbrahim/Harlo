# P1 CIP Specification Excerpts — Patent-Ready Paragraphs

**Classification:** CONFIDENTIAL — Patent Pending
**Author:** Joseph O. Ibrahim
**Date:** March 30, 2026

Each excerpt is written in patent specification style for direct inclusion in the CIP filing.

---

## Excerpt 1: Cognitive State Computation via Topologically-Sorted DAG

In one embodiment, the system evaluates cognitive state transitions via a directed acyclic graph (DAG) in which computation nodes are topologically sorted to ensure dependency-correct evaluation order. The DAG comprises seven computation nodes: compute_burst, compute_energy, compute_momentum, compute_burnout, and compute_allostasis form a dependent chain, while compute_injection_gain and compute_context_budget operate independently. Each computation node implements a pure function that reads previously-authored time-sampled attributes from a USD stage at exchange_index t-1 and writes computed results at exchange_index t. The DAG is evaluated once per exchange, where an exchange represents a single interaction between the user and an AI delegate. Post-evaluation, structural invariants are enforced: a RED burnout state forces momentum to CRASHED and terminates any active burst phase. The computation DAG is designed for registration as OpenExec computation plugins via the EXEC_REGISTER_COMPUTATIONS_FOR_SCHEMA macro when USD Python bindings become available, with a Python mock (MockCogExec) serving as the functionally-identical interim implementation.

---

## Excerpt 2: Capability-Requirement Routing for Cognitive Delegates

In one embodiment, the system separates cognitive routing decisions from delegate binding through a two-phase process. In the first phase, a compute_routing function within the cognitive computation DAG evaluates current cognitive state signals — including frustration level, topic coherence, exchange velocity, burnout severity, and energy availability — and outputs (a) an expert classification (validator, scaffolder, restorer, socratic, or direct) and (b) a capability requirements dictionary specifying supported_tasks, maximum latency class, context budget, and whether code generation is required. Critically, the routing function outputs requirements rather than delegate identifiers, ensuring that the DAG remains model-agnostic. In the second phase, a DelegateRegistry receives the capability requirements and filters registered delegates by supported task overlap, latency compatibility, context window sufficiency, and code generation capability. Candidates are sorted by latency (lower preferred) then context window (higher preferred). Safety overrides intervene when burnout severity exceeds a threshold: ORANGE burnout without a valid out-of-band consent token forces the restorer expert regardless of computed routing; RED burnout forces restorer unconditionally, ignoring any consent token.

---

## Excerpt 3: Dynamic Cognitive-to-Hardware Resource Translation

In one embodiment, the system translates computed psychological metrics into hardware resource allocation decisions. An allostatic load computation produces a scalar value in [0.0, 1.0] from a weighted composite of six factors: exchange frequency (w=0.20), interaction intensity (w=0.15), crisis severity (w=0.25), override compliance (w=0.15), recovery recency (w=0.15), and sleep quality (w=0.10). This allostatic load value feeds into a context budget computation that uses hysteresis-based state transitions: when the compression factor exceeds 4.2x, holding projects are promoted from Payload to Reference arc (loaded into active context); when the compression factor drops below 3.8x, projects are demoted from Reference to Payload arc (lazy-loaded on demand). The hysteresis dead zone between 3.8x and 4.2x prevents oscillation when effective context capacity hovers near the 4.0x boundary. This mechanism constitutes a novel translation from simulated psychological state to hardware resource management, with no prior art identified for the translation of psychological metrics to GPU memory allocation decisions.

---

## Excerpt 4: Sublayer-Per-Delegate Concurrency Resolution

In one embodiment, each cognitive delegate writes to its own isolated USD sublayer file. When multiple delegates are active concurrently — for example, an interactive reasoning delegate and a batch implementation delegate — each writes its proposed state mutations to a separate .usda file within a delegates/ directory. The root USD stage references these sublayer files via sublayerPaths. Composition follows LIVRPS (Local, Inherit, Variant, Reference, Payload, Specialize) priority ordering, where the interactive delegate's sublayer is strongest by default, overriding the batch delegate's opinions on any conflicting attribute. This per-delegate isolation ensures that (a) no delegate can read another delegate's uncommitted writes, (b) conflict resolution is deterministic via composition priority, and (c) any delegate's contributions can be independently inspected, reverted, or archived as standard USD layers.

---

## Excerpt 5: Monotonic Exchange Index for Cycle-Free Cognitive Computation

In one embodiment, all temporal indexing within the cognitive state system uses a strictly monotonic integer (exchange_index) rather than wall-clock time. Each exchange between the user and an AI delegate increments the exchange_index by exactly one. USD time samples are authored using Usd.TimeCode(exchange_index), ensuring that no two exchanges share the same temporal key. Physical time information (wall_clock_delta) is authored as a separate attribute at each exchange_index. This design prevents floating-point collisions that occur during rapid burst phases when multiple exchanges happen within the same wall-clock second, and guarantees that each computation node can safely read exchange_index t-1 without risk of self-referential cycles or temporal ambiguity.

---

## Excerpt 6: Out-of-Band Cryptographic Consent Tokens

In one embodiment, the system resolves the tension between user autonomy and structural safety through cryptographic consent tokens authored outside the LLM context. When a user wishes to override a burnout-level safety intervention, the application layer (native UI, outside the LLM delegate's context) generates an HMAC-SHA256 signed consent token specifying: scope (limited to the specific override type), grant timestamp (exchange_index), and time-to-live (TTL, measured in exchanges, default: 10). The token is authored directly to the USD stage at /sessions/consent as a Reference arc. The compute_routing function validates the token by verifying the HMAC signature, checking that the current exchange_index is within the TTL window, and confirming scope matches the requested override. Delegates cannot forge consent because they lack access to the signing key. RED burnout states ignore consent tokens entirely, maintaining an unconditional safety floor. Tokens are revocable by the application layer at any time.

---

## Excerpt 7: Stratified Prioritized Experience Replay for Cognitive Prediction

In one embodiment, the observation buffer for cognitive state prediction training maintains two partitions: a locked anchor partition (20% of training batches) containing synthetic trajectories generated via autoresearch, and a rolling organic partition (80% of training batches) containing live CognitiveObservation records. The anchor partition is seeded once from a trajectory generator that produces 10,000+ sessions covering the full cognitive state space, including rare transitions (RED events, burst crashes, injection interactions). This partition is never deleted or overwritten. The organic partition accumulates live observations with priority scoring based on surprise (absolute delta between predicted and actual state). High-surprise observations are sampled preferentially; low-priority observations are evicted at capacity. Each training batch combines 20% anchor samples with 80% priority-weighted organic samples, ensuring the prediction model retains capability for rare-state prediction even during extended periods of stable operation.

---

## Excerpt 8: Adrenaline Masking During Hyperfocus Burst Phases

In one embodiment, the compute_energy function implements an adrenaline masking mechanism that suspends energy state decrements during active burst phases. When the burst phase is in {DETECTED, PROTECTED, WINDING}, the energy computation returns the previous energy level unchanged, regardless of session duration or exchange count. An adrenaline debt accumulator (authored by the exchange coordinator, not tracked internally by the pure computation function) increments by one for each exchange during which decrements were masked. When the burst phase transitions to EXIT_PREP or NONE, the accumulated debt is applied: energy decrements by the debt amount (clamped to DEPLETED floor). This mechanism prevents deep flow states from self-destructing through gradual energy exhaustion, enabling burst phases to reach winding (50+ exchanges) and exit_prep (70+ exchanges) thresholds that would otherwise be unreachable.

---

## Excerpt 9: Profile-Driven Markov Biasing for Synthetic Cognitive Trajectories

In one embodiment, a trajectory generator produces synthetic cognitive session data using profile-driven Markov biasing rather than uniform random sampling. Seven session profiles are defined with target distribution percentages: normal (40%), deep_work (15%), struggling (15%), recovery (10%), injection (10%), crisis (5%), and mobile (5%). Each profile specifies biased ranges for exchange velocity, topic coherence, frustration signal, injection state, sleep quality, and exercise recency. Deep Work profiles forcibly set coherence and velocity ranges to 95%+ to guarantee that burst detection thresholds are reachable within the session. Crisis profiles include forced RED events at random positions. Each generated session is a forward-chaining causal simulation evaluated through the full cognitive computation DAG, producing a sequence of 3-100 CognitiveObservation records. The generator authors externally-maintained accumulators (tasks_completed, exchanges_without_break, adrenaline_debt) per exchange, satisfying the pure function requirement. All 10,000 generated sessions are validated against 26 structural invariants with zero violations.
