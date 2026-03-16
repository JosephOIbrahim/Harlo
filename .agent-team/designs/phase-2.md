# Phase 2 Design: `brainstem/` — Lossless Translation + Metacognitive Routing

**Author:** Architect
**Phase:** 2 (Core Transport)
**Gates:** 2a (Fidelity), 2b (Isolation), 2c (Metacognitive Routing)

---

## 1. Module Location & File Layout

```
python/cognitive_twin/brainstem/
├── __init__.py          # Public API exports
├── adapters.py          # Per-subsystem to_stage/from_stage adapters
├── stage_builder.py     # full_stage(), aletheia_stage()
├── merkle.py            # Merkle hash over /Association/Traces
├── routing.py           # Surprise Z-score + dual-process routing
└── session_updater.py   # /Session prim updates after recall

tests/test_brainstem/
├── __init__.py
├── conftest.py          # Hypothesis strategies for all native types
├── test_fidelity.py     # from_stage(to_stage(x)) == x (Hypothesis 1000+)
├── test_isolation.py    # aletheia_stage() contains zero traces
├── test_routing.py      # Z-score, dual-process, profile-aware, cold-start
├── test_merkle.py       # Merkle hash correctness
└── test_session.py      # Session prim update correctness
```

---

## 2. Adapters (`adapters.py`)

Each subsystem gets one adapter pair: `native → TracePrim/LayerPrim/etc` and back.

### 2.1 Association Adapter

```python
def recall_to_traces(recall_result: dict) -> dict[str, TracePrim]:
    """Convert hippocampus RecallResult dict to TracePrim dict.

    Maps:
      TraceHit.trace_id → TracePrim.trace_id
      TraceHit.distance → (used for surprise, not stored in prim)
      TraceHit.strength → TracePrim.strength
      TraceHit.domain → (metadata, not in prim schema)
      SDR from SQLite → TracePrim.sdr (bytes→list[int])

    Returns: {trace_id: TracePrim}
    """

def traces_to_recall(traces: dict[str, TracePrim], query_sdr: list[int]) -> dict:
    """Convert TracePrims back to RecallResult-shaped dict.

    Recomputes hamming distances from query_sdr.
    Returns dict matching RecallResult structure.
    """
```

### 2.2 Composition Adapter

```python
def layers_to_composition(layers: list[Layer]) -> dict[str, CompositionLayerPrim]:
    """Convert composition.Layer list to CompositionLayerPrim dict.

    Maps:
      Layer.arc_type (IntEnum) → CompositionLayerPrim.arc_type (usd_lite ArcType)
      Layer.data → CompositionLayerPrim.opinion
      Layer.timestamp (int) → CompositionLayerPrim.timestamp (datetime)
      Layer.source → (stored as provenance.session_id)
      Layer.layer_id → CompositionLayerPrim.layer_id
    """

def composition_to_layers(prims: dict[str, CompositionLayerPrim]) -> list[Layer]:
    """Convert CompositionLayerPrims back to composition.Layer list."""
```

### 2.3 Aletheia Adapter

```python
def verification_to_aletheia(result: VerificationResult) -> AletheiaPrim:
    """Convert VerificationResult to AletheiaPrim.

    Maps:
      result.state → gate_status.verification_state (enum mapping)
      result.cycle_count → gate_status.cycle_count
      (timestamp from current time)
    """

def aletheia_to_verification(prim: AletheiaPrim) -> dict:
    """Convert AletheiaPrim back to VerificationResult-shaped dict."""
```

### 2.4 Session Adapter

```python
def session_to_prim(session: dict) -> SessionPrim:
    """Convert session manager dict to SessionPrim.

    Maps:
      session_id → current_session_id
      exchange_count → exchange_count
      (surprise fields initialized to 0.0 on first conversion)
    """

def prim_to_session(prim: SessionPrim) -> dict:
    """Convert SessionPrim back to session manager dict."""
```

### 2.5 Motor Adapter

```python
def motor_to_prims(actions: list[dict]) -> list[MotorPrim]:
    """Convert PlannedAction dicts to MotorPrim list."""

def prims_to_motor(prims: list[MotorPrim]) -> list[dict]:
    """Convert MotorPrim list back to PlannedAction dicts."""
```

### 2.6 Inquiry Adapter

```python
def inquiries_to_prims(inquiries: list[dict]) -> list[InquiryPrim]:
    """Convert Inquiry dicts to InquiryPrim list."""

def prims_to_inquiries(prims: list[InquiryPrim]) -> list[dict]:
    """Convert InquiryPrim list back to Inquiry dicts."""
```

### Round-trip contract

For every adapter pair: `from_stage(to_stage(native_data)) == native_data`
(modulo expected lossy fields documented per adapter).

---

## 3. Stage Builder (`stage_builder.py`)

### 3.1 `full_stage()`

```python
def full_stage(
    recall_result: Optional[dict] = None,
    composition_layers: Optional[list] = None,
    verification_result: Optional[object] = None,
    session: Optional[dict] = None,
    inquiries: Optional[list[dict]] = None,
    motor_actions: Optional[list[dict]] = None,
    merkle_root: Optional[str] = None,
    trace_count: int = 0,
) -> BrainStage:
    """Build a complete USD stage from all subsystem native data.

    This is Path A — includes /Association with all traces.
    Used for: session capsules, export, skill building.
    """
```

### 3.2 `aletheia_stage()`

```python
def aletheia_stage(
    verification_result: Optional[object] = None,
    merkle_root: Optional[str] = None,
    trace_count: int = 0,
    session: Optional[dict] = None,
) -> BrainStage:
    """Build a restricted USD stage for Aletheia verification.

    This is Path B — structurally CANNOT include /Association.
    The function signature does not accept recall_result or traces.
    Aletheia receives only: its own state, gate status, Merkle root, session.

    Rule 11: Trace exclusion is STRUCTURAL, not filtering.
    """
```

**Key design:** `aletheia_stage()` does not accept any trace parameter. It is structurally impossible to pass traces to it. This is not a filter — it's a different function signature.

---

## 4. Merkle Hash (`merkle.py`)

```python
def compute_trace_merkle(traces: dict[str, TracePrim]) -> str:
    """Compute Merkle hash over /Association/Traces subtree.

    1. Sort traces by trace_id (deterministic order)
    2. Hash each trace: SHA256(trace_id + content_hash + sdr_hex)
    3. Build Merkle tree from leaf hashes
    4. Return root hash

    Uses base SDR only (not effective SDR with Hebbian masks).
    This ensures Hebbian learning doesn't trigger false corruption detection.
    """
```

Reuses the existing `composition.merkle.MerkleTree` class for the tree structure.

---

## 5. Metacognitive Routing (`routing.py`)

### 5.1 Surprise Z-Score (Patch 1)

```python
@dataclass
class SurpriseResult:
    """Result of surprise computation after a recall."""
    z_score: float                # (best_hamming - rolling_mean) / max(rolling_std, 1.0)
    rolling_mean: float           # Updated mean
    rolling_std: float            # Updated std dev
    escalate: bool                # z_score > threshold
    retrieval_path: RetrievalPath # SYSTEM_1 or SYSTEM_2


ROLLING_WINDOW = 100
DEFAULT_SURPRISE_THRESHOLD = 2.0


def compute_surprise(
    best_hamming: int,
    rolling_mean: float,
    rolling_std: float,
    history_count: int,
    threshold: float = DEFAULT_SURPRISE_THRESHOLD,
) -> SurpriseResult:
    """Compute surprise Z-score and routing decision.

    Formula: z_score = (best_hamming - rolling_mean) / max(rolling_std, 1.0)

    The max(rolling_std, 1.0) floor prevents:
    - Division by zero on cold start (< 10 recalls)
    - Blowup when std_dev is near zero

    Escalation: z_score > threshold → SYSTEM_2
    Otherwise: SYSTEM_1
    """


def update_rolling_stats(
    current_mean: float,
    current_std: float,
    history_count: int,
    new_hamming: int,
) -> tuple[float, float, int]:
    """Update rolling mean and std dev with a new hamming distance.

    Uses Welford's online algorithm for numerically stable updates.
    Window size: last ROLLING_WINDOW (100) values.

    Returns: (new_mean, new_std, new_count)
    """
```

### 5.2 Profile-Aware Routing

```python
def get_surprise_threshold(cognitive_profile: Optional[CognitiveProfilePrim]) -> float:
    """Read surprise threshold from cognitive profile.

    If profile exists: return profile.multipliers.surprise_threshold
    If no profile: return DEFAULT_SURPRISE_THRESHOLD (2.0)

    Never crashes on empty/None profile.
    """
```

### 5.3 Routing Decision

```python
def route_recall(
    best_hamming: int,
    session_prim: SessionPrim,
    cognitive_profile: Optional[CognitiveProfilePrim] = None,
) -> tuple[SurpriseResult, SessionPrim]:
    """Full routing pipeline: compute surprise, update session, return decision.

    1. Get threshold from profile (or default 2.0)
    2. Compute surprise Z-score
    3. Update rolling stats via Welford's algorithm
    4. Update SessionPrim with new values
    5. Return (SurpriseResult, updated SessionPrim)
    """
```

---

## 6. Session Updater (`session_updater.py`)

```python
def update_session_after_recall(
    session: SessionPrim,
    best_hamming: int,
    cognitive_profile: Optional[CognitiveProfilePrim] = None,
) -> tuple[SessionPrim, SurpriseResult]:
    """Update /Session prim after a recall operation.

    Delegates to routing.route_recall() and returns the updated session
    plus the routing decision.
    """
```

This is a thin orchestration layer — the real logic lives in `routing.py`.

---

## 7. `__init__.py` — Public API

```python
from .adapters import (
    recall_to_traces, traces_to_recall,
    layers_to_composition, composition_to_layers,
    verification_to_aletheia, aletheia_to_verification,
    session_to_prim, prim_to_session,
    motor_to_prims, prims_to_motor,
    inquiries_to_prims, prims_to_inquiries,
)
from .stage_builder import full_stage, aletheia_stage
from .merkle import compute_trace_merkle
from .routing import (
    SurpriseResult, compute_surprise, update_rolling_stats,
    get_surprise_threshold, route_recall,
    ROLLING_WINDOW, DEFAULT_SURPRISE_THRESHOLD,
)
from .session_updater import update_session_after_recall
```

---

## 8. Test Strategy

### `conftest.py` — Hypothesis Strategies

```python
# Strategies for generating random native data
@st.composite
def recall_results(draw): ...          # Random RecallResult dicts
@st.composite
def composition_layers(draw): ...      # Random Layer lists
@st.composite
def verification_results(draw): ...    # Random VerificationResult dicts
@st.composite
def sessions(draw): ...                # Random session dicts
@st.composite
def motor_actions(draw): ...           # Random PlannedAction dicts
@st.composite
def inquiries(draw): ...               # Random Inquiry dicts
```

### `test_fidelity.py` — Gate 2a

- `@given(recall_results())` × 1000: `traces_to_recall(recall_to_traces(x), query_sdr) ≈ x`
- `@given(composition_layers())` × 1000: `composition_to_layers(layers_to_composition(x)) == x`
- `@given(verification_results())`: `aletheia_to_verification(verification_to_aletheia(x)) == x`
- `@given(sessions())`: `prim_to_session(session_to_prim(x)) == x`
- `@given(motor_actions())`: round-trip
- `@given(inquiries())`: round-trip

### `test_isolation.py` — Gate 2b

- `aletheia_stage()` output has zero traces (structural)
- `aletheia_stage()` function signature has no trace parameter
- Inspect the returned BrainStage: `stage.association.traces == {}`
- Even if full_stage was called with traces, aletheia_stage never sees them

### `test_routing.py` — Gate 2c

- Z-score computes correctly for known values
- Cold start (< 10 recalls): max(std, 1.0) floor works
- Escalation at threshold: z > 2.0 → SYSTEM_2, z ≤ 2.0 → SYSTEM_1
- Rolling stats update correctly (Welford)
- Profile multiplier scales threshold
- No profile → default 2.0
- None profile → does not crash

### `test_merkle.py`

- Empty traces → deterministic hash
- Single trace → hash matches manual computation
- Adding trace changes root
- Base SDR used (not effective SDR with masks)
- Sorted by trace_id (deterministic)

### `test_session.py`

- Session prim updates after recall
- surprise_rolling_mean changes
- last_query_surprise reflects Z-score
- last_retrieval_path reflects routing decision

---

## 9. Design Decisions

### D1: Adapters are pure functions
No side effects, no database access. They only transform data structures. This makes them trivially testable with Hypothesis.

### D2: aletheia_stage() is structurally isolated
The function signature does not accept traces. This is Rule 11 enforcement by construction, not by filtering.

### D3: Welford's algorithm for rolling stats
Standard online mean/variance. Numerically stable. O(1) per update. No need to store the full history window — we track mean, M2 (sum of squared differences), and count.

### D4: Merkle over base SDR only
Hebbian masks live in [V] Variant layer. The Merkle hash is computed over pristine base traces. This prevents Hebbian learning from triggering false corruption alarms.

### D5: Adapters handle ArcType mapping
The existing `composition.layer.ArcType` and `usd_lite.arc_types.ArcType` have identical values (1-6). The adapter maps by value, not by identity, so they're decoupled.

---

## 10. Forge Instructions

1. Create `python/cognitive_twin/brainstem/` with all 6 files
2. Implement `adapters.py` first (pure functions, no dependencies beyond prims)
3. Implement `merkle.py` (reuses composition.merkle.MerkleTree)
4. Implement `routing.py` (Welford's algorithm, surprise computation)
5. Implement `session_updater.py` (thin layer over routing)
6. Implement `stage_builder.py` (assembles full_stage/aletheia_stage)
7. Write `__init__.py`
8. Write `conftest.py` with Hypothesis strategies
9. Write all test files
10. Run `pytest tests/test_brainstem/ -v` — all pass
11. Run `pytest tests/ -v` — full regression green
