# Phase 3 Design: Subsystem Cutover + Structured Provenance

**Author:** Architect
**Phase:** 3
**Gates:** 3a, 3b, 3c, 3d

---

## 1. Strategy

Bridge functions fall into two categories:
- **Orchestration pipelines** (generate, escalate): Rewire to build USD stages via brainstem
- **Decision gates** (amygdala, consolidation, intent_check, etc.): Pure functions — keep in bridge as thin shims, add provenance tracking

The bridge module becomes a **compatibility shim** that delegates to brainstem for stage building while preserving its public API. All existing tests must pass unchanged.

## 2. Changes

### 2.1 Structured Provenance Integration

Add provenance stamping to `composition/layer.py`:

```python
# New function in brainstem/provenance.py
def stamp_provenance(
    layer: CompositionLayerPrim,
    source_type: SourceType,
    session_id: str,
) -> CompositionLayerPrim:
    """Attach structured provenance to a composition layer."""
```

### 2.2 Bridge Shim

Modify bridge modules to delegate to brainstem:
- `bridge/generate.py`: After generate pipeline, build `full_stage()` with results
- `bridge/escalation.py`: Use brainstem adapters for composition ↔ USD conversion
- `bridge/__init__.py`: Re-export all functions (API unchanged)

### 2.3 New Files

```
python/cognitive_twin/brainstem/provenance.py    # Provenance stamping
tests/test_brainstem/test_provenance.py          # Provenance tests
```

### 2.4 Modified Files

```
python/cognitive_twin/bridge/generate.py         # Add brainstem stage building
python/cognitive_twin/bridge/escalation.py       # Use brainstem adapters
python/cognitive_twin/composition/layer.py       # (unchanged — provenance lives in USD prims)
```

## 3. Gate Coverage

- 3a: generate() and escalate() now produce USD stages via brainstem
- 3b: Composition results flow through brainstem adapters, not raw dicts
- 3c: All existing imports and tests preserved (shim is transparent)
- 3d: Every layer gets Provenance via stamp_provenance()
