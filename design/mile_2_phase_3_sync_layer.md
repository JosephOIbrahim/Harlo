# Mile 2 — Phase 3 Sync Layer Design

**Role:** Architect &nbsp;|&nbsp; **Date:** 2026-04-28
**Authority:** subordinate to Phase 1 design §6 + D4. Crucible Gate 3 verifies <10% latency regression.

---

## 0. Inputs honored

- **D4** — sync policies for orphan prims locked: `InquiryPrim` checkpoint, `MotorPrim` write-through, Injection N/A.
- **Phase 1 design §6** — write-side only; hot-path reads stay in runtime tier (Constitution Law 4).
- **Session override file paths** — `python/harlo/sync/` (top-level, not `usd_lite/sync/`).

---

## 1. Architecture — what the sync layer is and isn't

**Is:**

- A **policy table** declaring which sync strategy each of the 19 concrete prim types uses (write-through / write-behind / checkpoint / inherit).
- A **strategy library** implementing the three concrete strategies. Callers invoke explicitly.
- A **dispatcher** that, given a prim type or full BrainStage, routes to the right strategy.

**Is NOT:**

- An automatic mutation observer wired into the runtime tier. The existing `usd_lite/` engine has no mutation-hook surface to attach to without modifying it (Phase 2 scope OUT). Future work may integrate; this surgery declines.
- A read-path component. Reads always hit runtime tier (Constitution Law 4). The sync layer touches `pxr` only via the persistence layer (`harlo.usd_lite.persistence`).
- A coordinator that prevents stale reads. Path C's runtime tier is the canonical fast-tier truth in-session; persistence layer is the canonical durable truth across sessions. Drift between them is bounded by sync policy granularity, not eliminated.

This means Phase 3 produces **library code that callers can invoke**, plus a **policy ground-truth document**. No production code paths automatically use the sync layer this surgery — that integration is post-Step-6.

---

## 2. Sync strategies — three concrete implementations

### 2.1 `write-through` — synchronous persistence on every mutation

```python
# Caller pattern
sync.write_through.persist_prim(brain_stage, "/Brain/Session", target_path)
```

- Calls `persistence.write(...)` (or a per-prim variant) immediately.
- Caller blocks until the write completes.
- Best for low-write-rate, consistency-critical prims (`SessionPrim`, `GateStatusPrim`, `MerkleRootPrim`, `MotorPrim`).

### 2.2 `checkpoint` — deferred persistence; flush on demand

```python
# Caller pattern
sync.checkpoint.mark_dirty("/Brain/Association/Traces/abc")
# ... many mutations ...
sync.checkpoint.flush(brain_stage, target_path)
```

- Caller marks paths dirty during the session.
- Flush is explicit (typically called at session boundary or graceful shutdown).
- Best for high-write-rate prims where per-mutation persistence would dominate cost (`TracePrim`, `CompositionLayerPrim`, `SkillPrim`, `MultipliersPrim`, `IntakeHistoryPrim`, `InquiryPrim`).

### 2.3 `write-behind` — async queue (deferred to future surgery)

The Phase 1 design §6 mentioned write-behind, but no D4 prim uses it as a default. **Phase 3 does NOT implement write-behind.** A `WriteBehindStrategy` stub is exposed in `policy.py` for completeness; it raises `NotImplementedError` when invoked. Future surgery completes.

### 2.4 `inherit` — sentinel for containers

Container prims declare `Policy.INHERIT` to signal "ask the policy table for a contained leaf type." The dispatcher resolves on demand.

Containers in Phase 1 design §3:
- `BrainStage` → root, inherits from any leaf
- `AssociationPrim` → inherits from `TracePrim` (checkpoint)
- `CompositionPrim` → inherits from `CompositionLayerPrim` (checkpoint)
- `ElenchusPrim` → mixed children (`GateStatusPrim` write-through, `MerkleRootPrim` write-through) — both write-through; inherit resolves consistently
- `InquiryContainerPrim` → inherits from `InquiryPrim` (checkpoint)
- `MotorContainerPrim` → inherits from `MotorPrim` (write-through)
- `SkillsContainerPrim` → inherits from `SkillPrim` (checkpoint)
- `CognitiveProfilePrim` → inherits from `MultipliersPrim`/`IntakeHistoryPrim` (checkpoint, both same)
- `Provenance` (apiSchema) → inherits from host `CompositionLayerPrim` (checkpoint)

---

## 3. Final per-prim policy table (no `[NEEDS DECISION]` remaining)

Per D4 + Phase 1 §6 + this design:

| typeName | Policy | Source |
|---|---|---|
| `SessionPrim` | `WRITE_THROUGH` | Phase 1 §6 default |
| `GateStatusPrim` | `WRITE_THROUGH` | Phase 1 §6 default |
| `MerkleRootPrim` | `WRITE_THROUGH` | Phase 1 §6 default |
| `MotorPrim` | `WRITE_THROUGH` | **D4** |
| `MotorContainerPrim` | `INHERIT` | resolves to MotorPrim → write-through |
| `TracePrim` | `CHECKPOINT` | Phase 1 §6 default |
| `CompositionLayerPrim` | `CHECKPOINT` | Phase 1 §6 default |
| `Provenance` | `CHECKPOINT` (inherits host) | apiSchema; host is `CompositionLayerPrim` |
| `SkillPrim` | `CHECKPOINT` | Phase 1 §6 default |
| `MultipliersPrim` | `CHECKPOINT` | Phase 1 §6 default |
| `IntakeHistoryPrim` | `CHECKPOINT` | Phase 1 §6 default |
| `InquiryPrim` | `CHECKPOINT` | **D4** |
| `InquiryContainerPrim` | `INHERIT` | resolves to InquiryPrim → checkpoint |
| `AssociationPrim` | `INHERIT` | resolves to TracePrim → checkpoint |
| `CompositionPrim` | `INHERIT` | resolves to CompositionLayerPrim → checkpoint |
| `ElenchusPrim` | `INHERIT` | resolves to GateStatusPrim/MerkleRootPrim → write-through |
| `SkillsContainerPrim` | `INHERIT` | resolves to SkillPrim → checkpoint |
| `CognitiveProfilePrim` | `INHERIT` | resolves to MultipliersPrim → checkpoint |
| `BrainStage` | `INHERIT` | root; resolves per child |
| `HarloPrim` (abstract) | n/a | abstract base; no instances |
| `HarloContainer` (abstract) | n/a | abstract base; no instances |

**No `[NEEDS DECISION]` rows.** Crucible Gate 3 criterion satisfied.

Note: `InjectionPrim` / `InjectionContainerPrim` are NOT in this table — D5 evicted them from the schema. `policy.py` does NOT include them.

---

## 4. Module shape

```
python/harlo/sync/
├── __init__.py        # exports Policy enum, lookup(), write_through, checkpoint
├── policy.py          # Policy enum + per-prim table; validates completeness on import
├── write_through.py   # WriteThroughSync impl
└── checkpoint.py      # CheckpointSync impl
```

### 4.1 `policy.py` — declarative table

```python
class Policy(Enum):
    WRITE_THROUGH = "write_through"
    CHECKPOINT = "checkpoint"
    WRITE_BEHIND = "write_behind"  # not implemented (NotImplementedError)
    INHERIT = "inherit"

# Single source of truth — keys MUST match the 19 concrete typeNames.
POLICY_TABLE: dict[str, Policy] = {
    "BrainStage": Policy.INHERIT,
    "AssociationPrim": Policy.INHERIT,
    "CompositionPrim": Policy.INHERIT,
    "ElenchusPrim": Policy.INHERIT,
    "InquiryContainerPrim": Policy.INHERIT,
    "MotorContainerPrim": Policy.INHERIT,
    "SkillsContainerPrim": Policy.INHERIT,
    "CognitiveProfilePrim": Policy.INHERIT,
    "TracePrim": Policy.CHECKPOINT,
    "CompositionLayerPrim": Policy.CHECKPOINT,
    "Provenance": Policy.CHECKPOINT,
    "SessionPrim": Policy.WRITE_THROUGH,
    "GateStatusPrim": Policy.WRITE_THROUGH,
    "MerkleRootPrim": Policy.WRITE_THROUGH,
    "InquiryPrim": Policy.CHECKPOINT,
    "MotorPrim": Policy.WRITE_THROUGH,
    "SkillPrim": Policy.CHECKPOINT,
    "MultipliersPrim": Policy.CHECKPOINT,
    "IntakeHistoryPrim": Policy.CHECKPOINT,
}
# 19 entries — abstract types and Injection types deliberately omitted.

# Resolves an INHERIT policy to a concrete strategy by walking the
# containment chain. Returns the effective policy for the prim type.
def resolve_policy(typename: str) -> Policy: ...

# Module-load-time validation: every key has a non-INHERIT resolution.
def _validate_table_completeness() -> None: ...
_validate_table_completeness()
```

### 4.2 `write_through.py` — synchronous strategy

```python
def persist_prim(stage: BrainStage, prim_path: str, target_path: str) -> None:
    """Synchronously persist `stage` to `target_path` after a mutation
    affecting `prim_path`.

    Currently writes the entire stage; future optimization could
    write just the affected subtree once persistence layer supports
    partial writes."""
```

### 4.3 `checkpoint.py` — deferred-flush strategy

```python
class Checkpoint:
    """Per-process dirty-set tracker. Mutations mark prim paths dirty;
    flush() persists when called explicitly."""
    
    def __init__(self) -> None: ...
    def mark_dirty(self, prim_path: str) -> None: ...
    def is_dirty(self) -> bool: ...
    def flush(self, stage: BrainStage, target_path: str) -> None:
        """Persist `stage` to `target_path` if any path is dirty.
        Clears dirty set on success."""
    def clear(self) -> None: ...

# Module-level default checkpoint instance for callers that don't
# need to manage their own.
default_checkpoint: Checkpoint = Checkpoint()
```

### 4.4 `__init__.py`

```python
from .policy import Policy, POLICY_TABLE, resolve_policy
from . import write_through, checkpoint
from .checkpoint import Checkpoint, default_checkpoint

__all__ = [
    "Policy", "POLICY_TABLE", "resolve_policy",
    "write_through", "checkpoint",
    "Checkpoint", "default_checkpoint",
]
```

The sync package does **NOT** import `pxr` directly. The `write_through` and `checkpoint` modules import `harlo.usd_lite.persistence` lazily (inside their function bodies) so importing `harlo.sync` works even without `[substrate]`. Policy lookups are pxr-free entirely.

---

## 5. Crucible Gate 3 criteria

Per session override + 03_HANDOFF Phase 3:

| # | Criterion | How verified |
|---|---|---|
| 1 | Hot-path read latency < 10% regression vs `baseline_latency.json` | Re-run the latency microbenchmark; compare p50 + p95 |
| 2 | Per-prim sync policy table complete (no [NEEDS DECISION]) | `policy.py` table has 19 entries; `_validate_table_completeness()` runs at import |
| 3 | 1,144 baseline preserved (1,133 D14 + 11 Phase 2) | `pytest tests/ --tb=no -q` |
| 4 | Round-trip fidelity preserved through sync layer (write a mutation, force checkpoint, read back, equality holds) | `test_checkpoint_roundtrip` in `tests/test_sync/` |

---

## 6. Test plan (Forge implements)

`tests/test_sync/`:
- `__init__.py`
- `test_policy_table.py` — table coverage + completeness; `resolve_policy` correctness for INHERIT entries
- `test_write_through.py` — synchronous persist; round-trip equality after persist
- `test_checkpoint.py` — dirty-set tracking; `flush()` produces expected file; round-trip equality

---

## 7. Architect handoff to Forge

Forge implements §4 verbatim. Tests per §6. Verification at Crucible Gate 3 per §5.

*End of Phase 3 sync layer design.*
