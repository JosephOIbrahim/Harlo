# Phase 1 Design: `usd_lite/` — USD Container Format

**Author:** Architect
**Phase:** 1 (Foundation)
**Gate:** 1
**Status:** PENDING HUMAN REVIEW

---

## 1. Module Location & File Layout

```
python/cognitive_twin/usd_lite/
├── __init__.py          # Public API exports
├── prims.py             # All dataclasses (prim types)
├── arc_types.py         # LIVRPS ArcType enum (mirrors composition/layer.py pattern)
├── serializer.py        # .usda text serialization (serialize / parse)
├── hex_sdr.py           # Hex encoding/decoding for 2048-bit SDR arrays
├── composer.py          # LIVRPS composition engine with permanent-prim handling
└── stage.py             # BrainStage container (holds all prims, implements __eq__)

tests/test_usd_lite/
├── __init__.py
├── test_prims.py        # All prim types instantiate, to_dict/from_dict round-trip
├── test_arc_types.py    # ArcType ordering, precedence
├── test_serializer.py   # .usda serialize/parse round-trip for every prim type
├── test_hex_roundtrip.py  # Patch 9: hex SDR encoding lossless round-trip
├── test_float_eq.py     # Patch 11+: BrainStage.__eq__ with math.isclose
├── test_composer.py     # LIVRPS composition, permanent prims, recency tie-breaking
└── test_coverage.py     # Meta-test: assert 100% coverage on usd_lite/
```

---

## 2. ArcType Enum (`arc_types.py`)

Matches existing `composition/layer.py` pattern exactly (IntEnum, lower = stronger).

```python
class ArcType(IntEnum):
    """LIVRPS arc types. Lower numeric value = stronger opinion."""
    LOCAL = 1       # [L] Strongest — direct local opinion
    INHERIT = 2     # [I] Inherited from parent prim
    VARIANT = 3     # [V] Variant layer (Hebbian deltas live here)
    REFERENCE = 4   # [R] Reference to external data
    PAYLOAD = 5     # [P] Payload data
    SUBLAYER = 6    # [S] Sublayer (weakest — in-memory projection from SQLite)
```

**Design note:** This is intentionally a separate enum from `composition.layer.ArcType` because `usd_lite` is a standalone module. Phase 3 will unify them during cutover.

---

## 3. Prim Dataclasses (`prims.py`)

All dataclasses follow existing codebase pattern:
- `@dataclass` with type hints on all fields
- `to_dict() -> dict` instance method
- `from_dict(cls, d: dict) -> Self` classmethod
- `Optional[T] = None` for nullable fields
- `field(default_factory=...)` for mutable defaults

### 3.1 Forward-Declared / Phase-Boundary Types

These types are structurally complete but will be populated by later phases.

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, IntEnum
from typing import Optional


# --- Phase 3: Provenance ---

class SourceType(Enum):
    """Provenance source classification."""
    USER_DIRECT = "user_direct"
    EXTERNAL_REFERENCE = "external_reference"
    SYSTEM_INFERRED = "system_inferred"
    HEBBIAN_DERIVED = "hebbian_derived"
    INTAKE_CALIBRATED = "intake_calibrated"


@dataclass
class Provenance:
    """Structured provenance for composition layers (Phase 3)."""
    source_type: SourceType
    origin_timestamp: datetime
    event_hash: str             # Deterministic hash of originating event
    session_id: str
```

### 3.2 Leaf Prim Types

```python
# --- /Association/Traces/{trace_id} ---

@dataclass
class TracePrim:
    """A single memory trace in the Association Engine."""
    trace_id: str
    sdr: list[int]                          # 2048-bit SDR (boolean array)
    content_hash: str
    strength: float                         # Lazy decay: initial * e^(-λt) + Σ(boosts)
    last_accessed: datetime
    co_activations: dict[str, int] = field(default_factory=dict)   # Phase 5: {trace_id: count}
    competitions: dict[str, int] = field(default_factory=dict)     # Phase 5: {trace_id: count}
    hebbian_strengthen_mask: list[int] = field(default_factory=lambda: [0] * 2048)  # Phase 5 Patch 7
    hebbian_weaken_mask: list[int] = field(default_factory=lambda: [0] * 2048)      # Phase 5 Patch 7
```

```python
# --- /Composition/Layers/{layer_id} ---

@dataclass
class CompositionLayerPrim:
    """A single opinion layer in the composition system."""
    layer_id: str
    arc_type: ArcType
    opinion: dict                           # Arbitrary opinion data
    timestamp: datetime
    provenance: Optional[Provenance] = None # Phase 3: structured provenance
    permanent: bool = False                 # Amygdala reflexes = immutable
```

```python
# --- /Aletheia/GateStatus ---

class VerificationState(Enum):
    """Aletheia verification states."""
    TRUSTED = "trusted"
    CONTESTED = "contested"
    REFUTED = "refuted"
    PENDING = "pending"

@dataclass
class GateStatusPrim:
    """Current Aletheia verification gate status."""
    verification_state: VerificationState
    cycle_count: int
    last_verified: datetime
```

```python
# --- /Aletheia/MerkleRoot ---

@dataclass
class MerkleRootPrim:
    """Merkle hash over /Association/Traces subtree."""
    root_hash: str
    trace_count: int
```

```python
# --- /Session ---

class RetrievalPath(Enum):
    """Dual-process retrieval path (Phase 2)."""
    SYSTEM_1 = "system_1"    # Fast association (hamming)
    SYSTEM_2 = "system_2"    # Deliberative (LIVRPS)

@dataclass
class SessionPrim:
    """Session metadata and routing state."""
    current_session_id: str
    exchange_count: int
    surprise_rolling_mean: float = 0.0      # Phase 2: rolling mean hamming
    surprise_rolling_std: float = 0.0       # Phase 2: rolling std dev
    last_query_surprise: float = 0.0        # Phase 2: Z-score of last recall
    last_retrieval_path: RetrievalPath = RetrievalPath.SYSTEM_1  # Phase 2
```

```python
# --- /Inquiry/Active ---

@dataclass
class InquiryPrim:
    """An active DMN hypothesis."""
    hypothesis: str
    confidence: float
```

```python
# --- /Motor/Pending ---

class MotorGateStatus(Enum):
    """Basal ganglia gate status for motor actions."""
    INHIBITED = "inhibited"
    APPROVED = "approved"
    EXECUTING = "executing"

@dataclass
class MotorPrim:
    """A pending motor action proposal."""
    action: str
    gate_status: MotorGateStatus
```

```python
# --- /Skills/{domain} (Phase 4) ---

@dataclass
class SkillPrim:
    """Competence tracking for a single domain."""
    domain: str
    trace_count: int
    first_seen: datetime
    last_seen: datetime
    growth_arc: list[float] = field(default_factory=list)   # Strength trajectory
    hebbian_density: float = 0.0   # Phase 5: co-activation richness
```

```python
# --- /CognitiveProfile/Multipliers (Phase 4) ---

@dataclass
class MultipliersPrim:
    """Personal calibration multipliers derived from intake."""
    surprise_threshold: float = 2.0          # Z-score threshold
    reconstruction_threshold: float = 0.3    # Strength threshold for reconstruction
    hebbian_alpha: float = 0.01              # Learning rate
    allostatic_threshold: float = 1.0        # Allostatic load ceiling
    detail_orientation: float = 0.5          # [0.0, 1.0]: big-picture ↔ granular
```

```python
# --- /CognitiveProfile/IntakeHistory (Phase 4) ---

@dataclass
class IntakeHistoryPrim:
    """Intake administration history."""
    last_intake: Optional[datetime] = None
    intake_version: Optional[str] = None
    answer_embeddings: list = field(default_factory=list)  # For future reprocessing
```

### 3.3 Container Prim Types

```python
# --- /Association ---

@dataclass
class AssociationPrim:
    """Container for all memory traces."""
    traces: dict[str, TracePrim] = field(default_factory=dict)  # trace_id → TracePrim
```

```python
# --- /Composition ---

@dataclass
class CompositionPrim:
    """Container for all composition layers."""
    layers: dict[str, CompositionLayerPrim] = field(default_factory=dict)  # layer_id → Prim
```

```python
# --- /Aletheia ---

@dataclass
class AletheiaPrim:
    """Container for verification engine state."""
    gate_status: Optional[GateStatusPrim] = None
    merkle_root: Optional[MerkleRootPrim] = None
```

```python
# --- /Inquiry ---

@dataclass
class InquiryContainerPrim:
    """Container for DMN hypotheses."""
    active: list[InquiryPrim] = field(default_factory=list)
```

```python
# --- /Motor ---

@dataclass
class MotorContainerPrim:
    """Container for motor action proposals."""
    pending: list[MotorPrim] = field(default_factory=list)
```

```python
# --- /Skills ---

@dataclass
class SkillsContainerPrim:
    """Container for all skill domains (Phase 4)."""
    domains: dict[str, SkillPrim] = field(default_factory=dict)  # domain → SkillPrim
```

```python
# --- /CognitiveProfile ---

@dataclass
class CognitiveProfilePrim:
    """Container for personal calibration (Phase 4)."""
    multipliers: MultipliersPrim = field(default_factory=MultipliersPrim)
    intake_history: IntakeHistoryPrim = field(default_factory=IntakeHistoryPrim)
```

---

## 4. BrainStage (`stage.py`)

The top-level container that holds the entire brain state.

```python
@dataclass
class BrainStage:
    """Root container for the entire brain state as a USD stage.

    Every subsystem writes to its own subtree. LIVRPS composition
    determines what wins when subsystems disagree.
    """
    association: AssociationPrim = field(default_factory=AssociationPrim)
    composition: CompositionPrim = field(default_factory=CompositionPrim)
    aletheia: AletheiaPrim = field(default_factory=AletheiaPrim)
    session: Optional[SessionPrim] = None
    inquiry: InquiryContainerPrim = field(default_factory=InquiryContainerPrim)
    motor: MotorContainerPrim = field(default_factory=MotorContainerPrim)
    skills: SkillsContainerPrim = field(default_factory=SkillsContainerPrim)
    cognitive_profile: CognitiveProfilePrim = field(default_factory=CognitiveProfilePrim)
```

### 4.1 `BrainStage.__eq__` (Patch 11+)

Custom equality that uses `math.isclose(rel_tol=1e-9)` for all float fields, exact equality for everything else. This is required because float serialization/deserialization introduces rounding.

**Implementation strategy:**
- Recursive comparison function `_deep_eq(a, b)` that walks both objects
- For `float` values: `math.isclose(a, b, rel_tol=1e-9)`
- For `list` values: element-wise `_deep_eq`
- For `dict` values: key equality + value-wise `_deep_eq`
- For `dataclass` instances: field-wise `_deep_eq`
- For `Enum` values: exact equality
- For everything else: `==`

```python
def __eq__(self, other: object) -> bool:
    if not isinstance(other, BrainStage):
        return NotImplemented
    return _deep_eq(self, other)
```

The `_deep_eq` function is a module-level helper, not a method, so it can be reused by any prim's equality check if needed.

### 4.2 `to_dict()` / `from_dict()`

Standard serialization to/from nested dicts. All prims serialize recursively via their own `to_dict()`. Datetimes serialize to ISO 8601 strings. Enums serialize to `.value`. SDR arrays serialize to hex via `hex_sdr` module.

---

## 5. Hex SDR Serialization (`hex_sdr.py`) — Patch 9

### Problem

A 2048-bit SDR as a JSON/text array of integers consumes ~6KB per trace. With thousands of traces, boot time becomes multi-minute.

### Solution

Pack 2048-bit arrays as 512-character hex strings (4 bits per hex char × 512 = 2048 bits).

```python
def sdr_to_hex(sdr: list[int]) -> str:
    """Convert a 2048-element boolean int array to a 512-char hex string.

    Each element must be 0 or 1. Groups of 4 bits → 1 hex char.
    Big-endian bit ordering within each nibble.

    Raises ValueError if len(sdr) != 2048 or elements not in {0, 1}.
    """

def hex_to_sdr(hex_str: str) -> list[int]:
    """Convert a 512-char hex string back to a 2048-element boolean int array.

    Raises ValueError if len(hex_str) != 512 or contains non-hex chars.
    """
```

**Round-trip guarantee:** `hex_to_sdr(sdr_to_hex(sdr)) == sdr` for all valid SDRs.

**Validation:** Both functions validate input strictly. Invalid input raises `ValueError` with descriptive message.

**Bit ordering:** Big-endian within each nibble: `[b3, b2, b1, b0]` → hex char. This matches the natural reading order and is consistent with Python's `int` hex representation.

---

## 6. `.usda` Text Serializer (`serializer.py`)

### Format

The `.usda` format is a human-readable text representation inspired by Pixar's USD ASCII format but simplified. It uses indented blocks with typed attributes.

```usda
#usda 1.0
def BrainStage "Brain"
{
    def AssociationPrim "Association"
    {
        def TracePrim "trace_abc123"
        {
            string content_hash = "sha256..."
            float strength = 0.87
            token last_accessed = "2026-03-15T12:00:00"
            hex sdr = "a1b2c3d4..."  # 512-char hex string
            hex hebbian_strengthen_mask = "0000..."
            hex hebbian_weaken_mask = "0000..."
            dict co_activations = {}
            dict competitions = {}
        }
    }

    def CompositionPrim "Composition"
    {
        def CompositionLayerPrim "layer_001"
        {
            token arc_type = "variant"
            dict opinion = {"key": "value"}
            token timestamp = "2026-03-15T12:00:00"
            bool permanent = false
        }
    }

    def SessionPrim "Session"
    {
        string current_session_id = "sess_123"
        int exchange_count = 42
        float surprise_rolling_mean = 12.5
        float surprise_rolling_std = 3.2
        float last_query_surprise = 1.8
        token last_retrieval_path = "system_1"
    }
}
```

### Type Tokens

| Python Type | `.usda` Type Token | Serialization |
|---|---|---|
| `str` | `string` | `"quoted"` |
| `int` | `int` | bare number |
| `float` | `float` | bare number (always include decimal point) |
| `bool` | `bool` | `true` / `false` |
| `datetime` | `token` | `"ISO 8601"` |
| `Enum` | `token` | `"value"` |
| `list[int]` (SDR) | `hex` | `"512-char hex"` |
| `dict` | `dict` | JSON-encoded string |
| `list[float]` | `float[]` | `[1.0, 2.0, 3.0]` |
| `list` (generic) | `list` | JSON-encoded string |
| `Optional[T]` (None) | omitted | not written |

### API

```python
def serialize(stage: BrainStage) -> str:
    """Serialize a BrainStage to .usda text format.

    Returns a complete .usda file as a string.
    None/empty optional fields are omitted from output.
    """

def parse(usda_text: str) -> BrainStage:
    """Parse a .usda text string back into a BrainStage.

    Raises ValueError on malformed input.
    Missing optional fields default to their dataclass defaults.
    """
```

### Round-Trip Guarantee

`parse(serialize(stage)) == stage` for all valid `BrainStage` instances.

This relies on:
1. `BrainStage.__eq__` using `math.isclose()` for floats
2. Hex SDR encoding being lossless
3. Deterministic serialization order (sorted keys for dicts)
4. ISO 8601 datetime round-trip

### Serialization Order

Prims within a container are serialized in a deterministic order:
- `Association.traces`: sorted by `trace_id`
- `Composition.layers`: sorted by `layer_id`
- `Inquiry.active`: by list index
- `Motor.pending`: by list index
- `Skills.domains`: sorted by domain name
- Top-level sections: fixed order (Association, Composition, Aletheia, Session, Inquiry, Motor, Skills, CognitiveProfile)

---

## 7. LIVRPS Composition Engine (`composer.py`)

### Purpose

Compose multiple opinion layers on the same prim into a resolved value. This is the brain-wide generalization of the existing `composition/resolver.py`.

### Resolution Rules

1. **Per-attribute:** Each attribute is resolved independently
2. **Arc type priority:** Lower `ArcType` value wins (LOCAL > INHERIT > ... > SUBLAYER)
3. **Timestamp tie-breaking:** For same arc type, later timestamp wins
4. **Permanent override:** If a layer has `permanent=True`, it wins regardless of arc type or timestamp. Among multiple permanent layers, the latest timestamp wins. (Amygdala reflexes are permanent.)

### API

```python
@dataclass
class CompositionResult:
    """Result of LIVRPS composition."""
    outcome: dict[str, object]          # attribute → resolved value
    trace: list[dict]                   # Per-attribute resolution audit
    winning_layers: dict[str, str]      # attribute → winning layer_id


def compose(layers: list[CompositionLayerPrim]) -> CompositionResult:
    """Resolve a list of composition layers using LIVRPS precedence.

    Permanent prims override normal LIVRPS recency rules.
    Returns the resolved outcome with an audit trace.
    """
```

### Resolution Algorithm

```
for each layer in layers:
    for each (attr, value) in layer.opinion:
        current_winner = best.get(attr)

        if layer.permanent and (current_winner is None or not current_winner.permanent):
            # Permanent always wins over non-permanent
            best[attr] = layer
        elif layer.permanent and current_winner.permanent:
            # Among permanents: latest timestamp wins
            if layer.timestamp > current_winner.timestamp:
                best[attr] = layer
        elif current_winner is not None and current_winner.permanent:
            # Non-permanent never overrides permanent
            pass
        else:
            # Normal LIVRPS: lower arc_type wins, then later timestamp
            if current_winner is None:
                best[attr] = layer
            elif layer.arc_type < current_winner.arc_type:
                best[attr] = layer
            elif layer.arc_type == current_winner.arc_type and layer.timestamp > current_winner.timestamp:
                best[attr] = layer
```

This matches the existing `composition/resolver.py` pattern but adds permanent-prim handling.

---

## 8. `__init__.py` — Public API

```python
"""USD-Lite: Lightweight Universal Scene Description for Cognitive Twin brain state.

Not full OpenUSD (2GB C++ dependency). Implements ~5% of USD:
dataclasses, .usda serialization, and LIVRPS composition.
"""

from .arc_types import ArcType
from .prims import (
    # Leaf prims
    TracePrim,
    CompositionLayerPrim,
    GateStatusPrim,
    MerkleRootPrim,
    SessionPrim,
    InquiryPrim,
    MotorPrim,
    SkillPrim,
    MultipliersPrim,
    IntakeHistoryPrim,
    # Container prims
    AssociationPrim,
    CompositionPrim,
    AletheiaPrim,
    InquiryContainerPrim,
    MotorContainerPrim,
    SkillsContainerPrim,
    CognitiveProfilePrim,
    # Forward-declared types
    Provenance,
    SourceType,
    # Enums
    VerificationState,
    RetrievalPath,
    MotorGateStatus,
)
from .stage import BrainStage
from .serializer import serialize, parse
from .composer import compose, CompositionResult
from .hex_sdr import sdr_to_hex, hex_to_sdr
```

---

## 9. Design Decisions & Rationale

### D1: Separate from `composition/`
`usd_lite/` is a new, standalone module. It does NOT modify or import from `composition/`. Phase 3 will perform the cutover. This avoids breaking existing tests during Phase 1.

### D2: All prims defined in one file (`prims.py`)
All prim types are in a single file because they cross-reference each other (e.g., `AssociationPrim` contains `TracePrim`). Splitting them would create circular imports. The file is ~250 lines — manageable.

### D3: `dict` for opinions, not nested dataclasses
`CompositionLayerPrim.opinion` is `dict`, not a typed structure. This matches the existing `Layer.data` pattern and allows arbitrary opinion shapes. LIVRPS resolution works at the attribute level regardless of the value type.

### D4: Datetime as `datetime`, not `int`
The existing codebase uses `int` (Unix timestamp) in `Layer.timestamp`. The USD prims use `datetime` for richer semantics. The serializer converts to/from ISO 8601 strings. The composer extracts `.timestamp()` for comparisons.

### D5: SDR as `list[int]`, not `bytes`
In-memory representation stays as `list[int]` (matching the Rust hot path's expectation via PyO3). Only serialization uses hex encoding. The `hex_sdr` module is the sole conversion point.

### D6: `_deep_eq` instead of per-class `__eq__`
A single recursive equality function handles all prim types uniformly. This avoids duplicating float tolerance logic across 15+ dataclasses and ensures consistency.

---

## 10. Gate 1 Checklist (Self-Assessment)

| Check | Design Coverage |
|---|---|
| All prim types instantiate | Section 3: 15 dataclasses, all with defaults |
| LIVRPS correct precedence | Section 7: mirrors resolver.py + permanent override |
| Permanent prims override recency | Section 7: explicit permanent check |
| Round-trip fidelity (all types) | Section 6: serialize/parse + __eq__ |
| Float tolerance via math.isclose | Section 4.1: _deep_eq with rel_tol=1e-9 |
| Hex SDR round-trip | Section 5: sdr_to_hex / hex_to_sdr |
| 100% test coverage | Section 1: 7 test files covering all modules |
| Forward-declared Phase 3-5 types | Section 3.1: Provenance, SourceType |
| Spec-gaming: truly typed | All fields have explicit types, enums, validation |

---

## 11. Test Strategy

### `test_prims.py`
- Every prim type instantiates with defaults
- Every prim type instantiates with all fields populated
- `to_dict()` produces expected keys
- `from_dict(to_dict(prim)) == prim` for every type
- Invalid enum values raise `ValueError`

### `test_arc_types.py`
- `LOCAL < INHERIT < VARIANT < REFERENCE < PAYLOAD < SUBLAYER`
- Comparison operators work correctly
- `.value` and `.name` round-trip

### `test_serializer.py`
- `parse(serialize(stage)) == stage` for:
  - Empty stage
  - Stage with one trace
  - Stage with multiple traces, layers, session data
  - Stage with all prim types populated
  - Stage with empty/None optional fields
- Deterministic output (same stage → same string)
- Malformed input raises `ValueError`

### `test_hex_roundtrip.py` (Patch 9)
- `hex_to_sdr(sdr_to_hex(sdr)) == sdr` for:
  - All-zeros SDR
  - All-ones SDR
  - Random SDR
  - Sparse SDR (3-5% density)
- Length validation: non-2048 input → `ValueError`
- Value validation: non-binary input → `ValueError`
- Hex validation: non-hex chars → `ValueError`

### `test_float_eq.py` (Patch 11+)
- Two stages with identical float values → equal
- Two stages differing by < 1e-9 in a float field → equal
- Two stages differing by > 1e-6 in a float field → not equal
- Integer fields: exact equality required
- String fields: exact equality required
- Mixed: float tolerance + exact string → correct result
- Round-trip: `parse(serialize(stage)) == stage` with various float values

### `test_composer.py`
- LOCAL wins over SUBLAYER (strongest over weakest)
- Same arc type: later timestamp wins
- Permanent prim wins over LOCAL
- Permanent prim wins over later non-permanent
- Among permanents: later timestamp wins
- Non-permanent never overrides permanent
- Multiple attributes resolve independently
- Empty layer list → empty result
- Single layer → passthrough
- Audit trace records all decisions

### `test_coverage.py`
- Assert `pytest --cov` shows 100% on `usd_lite/`
- (This is a meta-test enforced by CI, not runtime)

---

## 12. Dependencies

- **Standard library only:** `dataclasses`, `datetime`, `enum`, `json`, `math`, `re` (for parser)
- **No external dependencies** for `usd_lite/`
- **Test dependencies:** `pytest`, `pytest-cov`

---

## 13. Forge Instructions

1. Create `python/cognitive_twin/usd_lite/` with all 6 files
2. Implement `hex_sdr.py` first (no dependencies)
3. Implement `arc_types.py` (no dependencies)
4. Implement `prims.py` (depends on arc_types, hex_sdr for validation)
5. Implement `stage.py` (depends on prims, implements `_deep_eq`)
6. Implement `serializer.py` (depends on prims, stage, hex_sdr)
7. Implement `composer.py` (depends on prims, arc_types)
8. Write `__init__.py` with all exports
9. Write all test files
10. Run `pytest tests/test_usd_lite/ --cov=python/cognitive_twin/usd_lite --cov-report=term-missing` — must show 100%
11. Run `pytest tests/ -v` — all existing tests must still pass
