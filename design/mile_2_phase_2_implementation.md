# Mile 2 — Phase 2 Implementation Plan

**Role:** Architect &nbsp;|&nbsp; **Date:** 2026-04-28
**Authority:** subordinate to `design/mile_2_phase_1_schema_design.md`. On any conflict, Phase 1 design wins.
**Sole authoritative input for Forge.** Forge implements this plan verbatim; deviations require Architect re-engagement.

---

## 0. Inputs honored

- **Phase 1 design** (`design/mile_2_phase_1_schema_design.md`) — schema shape, IsA tree, attribute tables, allowedTokens, plugInfo.json shape, codec-blocker boundary plan, subprocess SchemaRegistry test spec.
- **Phase 2 scout** (`design/mile_2_phase_2_scout_src.md`) — confirmed zero collisions vs `src/`. STAY-SEPARATE recommendation locked.
- **Locked decisions:** D2 (IsA parallel-to-containment), D3 (zero Moneta collisions confirmed), D5 (Injection evicted from disk), D7 (`HarloSchema.usda`), D8/D9 (string sidecars deferred), D10 (Provenance as apiSchema), D11 (propertyOrder mandatory), D12 (this scout completed), D14 (1,133 baseline).

---

## 1. Storage-file decision (locked here)

**Phase 2 Forge writes the persistence layer's primary `.usda` to: `data/stages/brain.usda`.**

Per scout §3.4 + §4. Avoids any conceivable name collision with:
- Sprint 4's `data/stages/harlo.usda` (dormant, written by `src/cognitive_stage.py` if reactivated)
- Stale `data/stages/cognitive_twin.usda` (no current writer)

The persistence layer's `write()` API takes the target path as a parameter; `data/stages/brain.usda` is the *default* used by tests and the round-trip suite. Production callers may override.

---

## 2. Work breakdown — Forge tasks in order

Forge executes these in order. Each task ends with a verification step (Commandment 2). Estimated wall-clock per task:

| # | Task | Files written | Est. wall-clock |
|---|---|---|---|
| F1 | Author `schema/HarloSchema.usda` | 1 file | 60 min |
| F2 | Author `schema/plugInfo.json` | 1 file | 15 min |
| F3 | Author `schema/generatedSchema.usda` (hand-authored from §3.3 below; usdGenSchema not invoked this session) | 1 file | 30 min |
| F4 | Implement persistence layer at `python/harlo/usd_lite/persistence/` | 3 files | 90 min |
| F5 | Author Crucible tests at `tests/test_path_c/` | 3 files | 60 min |

**Total estimated: ~4h.** Within Phase 2 target of 4h, ceiling 5h.

---

## 3. Schema artifacts — Forge implementation

### 3.1 `schema/HarloSchema.usda`

**Path:** `schema/HarloSchema.usda` (new directory `schema/`)

**Header pattern** (from Moneta `MonetaSchema.usda` adapted):

```
#usda 1.0
(
    subLayers = [
        @usd/schema.usda@
    ]
)

over "GLOBAL" (
    customData = {
        string libraryName = "harlo"
        string libraryPath = "./"
        bool skipCodeGeneration = true
    }
)
{
}
```

**Class declaration order** (Forge writes top-to-bottom):

1. `HarloPrim` (abstract) — `inherits = </Typed>`, `schemaKind = "abstractTyped"`
2. `HarloContainer` (abstract) — `inherits = </HarloPrim>`, `schemaKind = "abstractTyped"`
3. **8 container types** (alphabetical by typeName): `AssociationPrim`, `BrainStage`, `CognitiveProfilePrim`, `CompositionPrim`, `ElenchusPrim`, `InquiryContainerPrim`, `MotorContainerPrim`, `SkillsContainerPrim` — each inherits `</HarloContainer>`, `schemaKind = "concreteTyped"`
4. **10 leaf types** (alphabetical): `CompositionLayerPrim`, `GateStatusPrim`, `InquiryPrim`, `IntakeHistoryPrim`, `MerkleRootPrim`, `MotorPrim`, `MultipliersPrim`, `Provenance`, `SessionPrim`, `SkillPrim`, `TracePrim` — each inherits `</HarloPrim>`, `schemaKind = "concreteTyped"`. Wait, that's 11; SkillPrim and TracePrim included. Provenance is special:
5. **Provenance is an applied API schema** per **D10** (overrides Phase 1 design §1.1's "leaf with `inherits = </Typed>`" pattern). Schema declaration:
   ```
   class "Provenance" (
       inherits = </APISchemaBase>
       customData = {
           string className = "Provenance"
           string schemaKind = "singleApplyAPI"
           token apiSchemaType = "singleApply"
       }
       doc = """Source/origin metadata applicable to any prim that needs origin tracking..."""
   )
   {
       token source_type (allowedTokens = [...])
       double origin_timestamp
       string event_hash
       string session_id
   }
   ```

   D10 explicitly converts Provenance from `typedSchema` (Phase 1 design's default) to `apiSchema (singleApply)`. Forge writes the API form, not the Typed form.

   So the count becomes: 2 abstract + 8 containers + 10 typed leaves + 1 API schema = **21 typeNames declared**.

**Attribute declaration per concrete type:** verbatim from Phase 1 design §2.3. Each concrete class declares its attributes per the per-prim tables. Defaults included where Phase 1 design specified; absent (`—`) attributes have no `= default` clause.

**`propertyOrder` is MANDATORY (D11).** Each concrete class declares:

```
class TypeName "TypeName" (
    inherits = </HarloPrim>
    customData = {
        string className = "TypeName"
        string schemaKind = "concreteTyped"
        token[] propertyOrder = ["attr1", "attr2", "attr3", ...]   # alphabetical
    }
    ...
)
{
    ...attributes in propertyOrder order...
}
```

**Casing convention for tokens** (Commandment 11 / Phase 1 §4.6): all `allowedTokens` entries are **lower_case_with_underscores**. Verbatim:
- `SourceType.allowedTokens` = `["user_direct", "external_reference", "system_inferred", "hebbian_derived", "intake_calibrated"]`
- `VerificationState.allowedTokens` = `["trusted", "contested", "refuted", "pending"]`
- `RetrievalPath.allowedTokens` = `["system_1", "system_2"]`
- `MotorGateStatus.allowedTokens` = `["inhibited", "approved", "executing"]`
- `ArcType.allowedTokens` = `["local", "inherit", "variant", "reference", "payload", "sublayer"]`

**Default values** (per Phase 1 §2.3 + §4):
- `GateStatusPrim.verification_state` = `"pending"`
- `SessionPrim.last_retrieval_path` = `"system_1"`
- `MotorPrim.gate_status` = `"inhibited"`
- `CompositionLayerPrim.arc_type` = `"local"`
- (Plus numeric defaults per Phase 1 §2.3 attribute tables.)

**Inline `doc = "..."` per attribute** matching Moneta's pattern: short single-line description from Phase 1 §2.3 row. Where Phase 1 §2.3 has no doc, Forge uses the dataclass docstring or a one-line description derived from the field name.

### 3.2 `schema/plugInfo.json`

**Path:** `schema/plugInfo.json`

**Verbatim shape** from Phase 1 design §5 (filling in the abbreviated `"...": "..."` rows). Each of the 21 typeNames gets a top-level entry under `"Plugins"[0]"Info"["Types"]` with this structure:

```json
"Harlo<ClassName>": {
    "alias": {"UsdSchemaBase": "<ClassName>"},
    "autoGenerated": true,
    "bases": ["<ParentName>"],
    "schemaIdentifier": "<ClassName>",
    "schemaKind": "<schemaKind>"
}
```

Where:
- `<ClassName>` = the typeName (e.g., `BrainStage`, `TracePrim`)
- `<ParentName>` = `"UsdTyped"` for `HarloHarloPrim`, `"HarloHarloPrim"` for `HarloHarloContainer` and leaf types, `"HarloHarloContainer"` for container types, `"UsdAPISchemaBase"` for `HarloProvenance` (applied schema)
- `<schemaKind>` = `"abstractTyped"` for `HarloHarloPrim`/`HarloHarloContainer`, `"concreteTyped"` for typed leaves and containers, `"singleApplyAPI"` for `HarloProvenance`

**Per-typeName parent map** (bases column) — Forge fills this exactly:

| Prefixed name | bases |
|---|---|
| `HarloHarloPrim` | `["UsdTyped"]` |
| `HarloHarloContainer` | `["HarloHarloPrim"]` |
| `HarloBrainStage` | `["HarloHarloContainer"]` |
| `HarloAssociationPrim` | `["HarloHarloContainer"]` |
| `HarloCompositionPrim` | `["HarloHarloContainer"]` |
| `HarloElenchusPrim` | `["HarloHarloContainer"]` |
| `HarloInquiryContainerPrim` | `["HarloHarloContainer"]` |
| `HarloMotorContainerPrim` | `["HarloHarloContainer"]` |
| `HarloSkillsContainerPrim` | `["HarloHarloContainer"]` |
| `HarloCognitiveProfilePrim` | `["HarloHarloContainer"]` |
| `HarloTracePrim` | `["HarloHarloPrim"]` |
| `HarloCompositionLayerPrim` | `["HarloHarloPrim"]` |
| `HarloGateStatusPrim` | `["HarloHarloPrim"]` |
| `HarloMerkleRootPrim` | `["HarloHarloPrim"]` |
| `HarloSessionPrim` | `["HarloHarloPrim"]` |
| `HarloInquiryPrim` | `["HarloHarloPrim"]` |
| `HarloMotorPrim` | `["HarloHarloPrim"]` |
| `HarloSkillPrim` | `["HarloHarloPrim"]` |
| `HarloMultipliersPrim` | `["HarloHarloPrim"]` |
| `HarloIntakeHistoryPrim` | `["HarloHarloPrim"]` |
| `HarloProvenance` | `["UsdAPISchemaBase"]` (applied schema per D10) |

**Plugin metadata** (footer):

```json
"LibraryPath": "",
"Name": "harlo",
"ResourcePath": ".",
"Root": ".",
"Type": "resource"
```

### 3.3 `schema/generatedSchema.usda`

**Path:** `schema/generatedSchema.usda`

USD's codeless schema model expects a `generatedSchema.usda` alongside `plugInfo.json`. It's the "compiled" form that USD's plugin loader actually consumes. Hand-authored from `HarloSchema.usda` for this phase (avoiding the `usdGenSchema --codeless` invocation, which requires extra environment setup).

**Pattern:** identical attribute/class declarations as `HarloSchema.usda`, but **without** `subLayers`, `over "GLOBAL"`, or `customData.skipCodeGeneration`. Each `class` is preceded by an inline doc string (preserved from `HarloSchema.usda`).

Forge replicates the `class` blocks 1:1, omitting the schema-authoring metadata that's only relevant to `usdGenSchema`.

**Why hand-authored:** `usdGenSchema --codeless` is a separate invocation step that Phase 2 doesn't include in the workflow. Hand-authoring `generatedSchema.usda` produces the same bits and stays within the substrate-only install. If a future phase wants to invoke `usdGenSchema`, the hand-authored file is regenerated and diffed; any diff is a bug to fix.

---

## 4. Persistence layer — Forge implementation

### 4.1 Module shape

```
python/harlo/usd_lite/persistence/
├── __init__.py        # exports write(), read(); guards pxr import
├── writer.py          # imports pxr; writes BrainStage to .usda via Usd.Stage
└── reader.py          # imports pxr; reads .usda back to BrainStage
```

### 4.2 `__init__.py` — pxr-import guard

```python
"""Path C persistence layer — real OpenUSD canonical storage.

Imports pxr only here. If [substrate] extra is not installed, the module
import fails with a clear error pointing to the install command.
"""
from __future__ import annotations

try:
    from pxr import Sdf, Usd, Plug  # noqa: F401
except ImportError as exc:
    raise ImportError(
        "harlo.usd_lite.persistence requires the [substrate] extra. "
        "Install via: pip install -e .[substrate]"
    ) from exc

from .writer import write
from .reader import read

__all__ = ["write", "read"]
```

Rationale: Constitution Law 3 (`pxr` install stays optional). Importing `harlo.usd_lite.persistence` without `[substrate]` fails clearly. Importing `harlo.usd_lite` (parent) does NOT touch persistence — runtime tier stays pxr-free.

### 4.3 `writer.py`

**Public API:**

```python
def write(stage_obj: BrainStage, output_path: str) -> None:
    """Write a BrainStage dataclass to a real-USD .usda file at output_path.
    
    Writes 21 prim types under /Brain root per Phase 1 design §3 path scheme.
    Codec-blocker fields written as string sidecars per D8/D9 defaults.
    """
```

**Schema plugin registration** (called once at module import, idempotent):

```python
_SCHEMA_REGISTERED = False

def _ensure_schema_registered() -> None:
    global _SCHEMA_REGISTERED
    if _SCHEMA_REGISTERED:
        return
    schema_dir = Path(__file__).resolve().parents[3] / "schema"
    Plug.Registry().RegisterPlugins(str(schema_dir))
    _SCHEMA_REGISTERED = True
```

**Per-prim write order** (matches Phase 1 design §3 path scheme):

1. Define root `/Brain` as `BrainStage`
2. Define `/Brain/Association` as `AssociationPrim`; iterate `stage_obj.association.traces.values()` writing each `TracePrim` at `/Brain/Association/Traces/<trace_id>` with attributes per Phase 1 §2.3 TracePrim row
3. Define `/Brain/Composition` as `CompositionPrim`; iterate layers writing each `CompositionLayerPrim`; for each layer with non-None `provenance`, apply the `Provenance` API schema to the layer prim and set its 4 attributes
4. Define `/Brain/Elenchus` as `ElenchusPrim`; if `gate_status` is not None, define `/Brain/Elenchus/GateStatus` as `GateStatusPrim`; if `merkle_root` is not None, define `/Brain/Elenchus/MerkleRoot` as `MerkleRootPrim`
5. If `stage_obj.session` is not None, define `/Brain/Session` as `SessionPrim`
6. Define `/Brain/Inquiry` as `InquiryContainerPrim`; iterate `stage_obj.inquiry.active` writing each as `/Brain/Inquiry/hypothesis_<i>` typed `InquiryPrim`
7. Define `/Brain/Motor` as `MotorContainerPrim`; iterate `stage_obj.motor.pending` writing each as `/Brain/Motor/action_<i>` typed `MotorPrim`
8. Define `/Brain/Skills` as `SkillsContainerPrim`; iterate `stage_obj.skills.domains.items()` writing each at `/Brain/Skills/<domain>` typed `SkillPrim`
9. Define `/Brain/CognitiveProfile` as `CognitiveProfilePrim`; define `/Brain/CognitiveProfile/Multipliers` as `MultipliersPrim` and `/Brain/CognitiveProfile/IntakeHistory` as `IntakeHistoryPrim`
10. **Skip Injection** per D5
11. `stage.GetRootLayer().Save()` if not in-memory

**Codec invocations (D8/D9 boundary handlers):**

| Schema attribute | Source dataclass field | Codec |
|---|---|---|
| `TracePrim.sdr_hex` | `TracePrim.sdr` (list[int] 2048-bit) | `harlo.usd_lite.hex_sdr.sdr_to_hex(sdr)` |
| `TracePrim.hebbian_strengthen_mask_hex` | `.hebbian_strengthen_mask` | `sdr_to_hex(mask)` |
| `TracePrim.hebbian_weaken_mask_hex` | `.hebbian_weaken_mask` | `sdr_to_hex(mask)` |
| `TracePrim.co_activations_json` | `.co_activations: dict[str, int]` | `json.dumps(d, sort_keys=True)` (default `"{}"` if empty) |
| `TracePrim.competitions_json` | `.competitions: dict[str, int]` | same |
| `CompositionLayerPrim.opinion_json` | `.opinion: dict[str, object]` | `json.dumps(d, sort_keys=True)` (default `"{}"`) |
| `IntakeHistoryPrim.answer_embeddings_json` | `.answer_embeddings: list[float]` | `json.dumps(list, sort_keys=True)` (default `"[]"`) |
| `*.last_accessed`, `*.last_verified`, `*.timestamp`, `*.first_seen`, `*.last_seen`, `*.last_intake`, `*.origin_timestamp` | `datetime` fields | `dt.timestamp()` (Python `float`) → USD `double` |

### 4.4 `reader.py`

**Public API:**

```python
def read(input_path: str) -> BrainStage:
    """Read a real-USD .usda file into a BrainStage dataclass.
    
    Inverse of write(). Reads 21 prim types from /Brain hierarchy.
    Codec-blocker sidecars decoded via runtime-tier codecs.
    """
```

**Per-prim read order:** same path traversal as writer, but reading each typed prim and constructing its dataclass via the existing `from_dict` methods after extracting attributes from the prim. For each prim:

1. `Usd.Stage.Open(input_path)`
2. `_ensure_schema_registered()` (same as writer)
3. For each Phase 1 design §3 path: `stage.GetPrimAtPath(path)`; if valid, extract attributes via `prim.GetAttribute(<name>).Get()`; construct dataclass
4. Codec inversions:
   - `TracePrim.sdr_hex` → `hex_sdr.hex_to_sdr(...)` → `list[int]`
   - JSON-string → `json.loads(...)` → `dict`/`list`
   - `double` timestamp → `datetime.fromtimestamp(..., tz=timezone.utc)` (UTC for round-trip)

### 4.5 Inverse-codec asymmetry note

Phase 1 design's existing serializer (`usd_lite/serializer.py`) uses ISO-format datetime strings. Path C writer uses `double` Unix seconds. **Round-trip between the two formats is not byte-equal but is value-equal** (Phase 1 design §9 documented this trade-off). The Crucible round-trip test (F5 below) compares values via `BrainStage.__eq__`, which is float-tolerant.

---

## 5. Crucible tests — Forge implementation

### 5.1 New test directory: `tests/test_path_c/`

```
tests/test_path_c/
├── __init__.py
├── test_schema_registry_gate.py    # subprocess registry test, per Phase 1 §8
└── test_persistence_roundtrip.py   # per-prim round-trip
```

### 5.2 `test_schema_registry_gate.py`

Verbatim from Phase 1 design §8.1, with the typeName list updated to match the actual 21 typeNames declared in `HarloSchema.usda`. Forge does not deviate from the §8.1 outline.

**Critical:** the test runs in a fresh subprocess (Commandment 4). Asserts:
- All 21 typeNames load via `Plug.Registry().RegisterPlugins(...)`
- `MonetaMemory` is NOT visible (negative collision check)
- USD built-in `Xform` is still resolvable (no registry corruption)
- 60-second timeout

### 5.3 `test_persistence_roundtrip.py`

Per Phase 1 design §11 (the Phase 2 Forge deliverable list).

**Test cases:**

```python
def test_empty_stage_roundtrip():
    """An empty BrainStage round-trips to .usda and back."""

def test_single_trace_roundtrip():
    """A BrainStage with one TracePrim round-trips."""

def test_full_stage_roundtrip():
    """A BrainStage with all 19 concrete prim types populated round-trips.
    
    Uses BrainStage.__eq__ (float-tolerant) for comparison.
    """

def test_codec_blocker_fidelity():
    """SDR hex codec + JSON-string sidecars round-trip without data loss."""

def test_provenance_apischema_attaches():
    """Provenance applied to CompositionLayerPrim survives round-trip."""

def test_no_injection_in_schema():
    """InjectionPrim and InjectionContainerPrim are NOT in the .usda
    output (D5 eviction)."""

def test_lower_case_arc_type_token():
    """arc_type token is lower-case in .usda output (D11 / Cmd 11)."""
```

Adversarial cases per Commandment 7:

```python
def test_round_trip_byte_stability():
    """Two consecutive writes of an identical stage produce byte-equal
    .usda output (D11 propertyOrder enforcement)."""
```

---

## 6. Forge work order

Strict order. Each step verified before the next begins (Commandment 2).

| Step | Task | Verification |
|---|---|---|
| F1 | Author `schema/HarloSchema.usda` | Manual review: 21 class blocks, all attributes declared, propertyOrder on every concrete class, lower-case allowedTokens |
| F2 | Author `schema/plugInfo.json` | `python -c "import json; json.load(open('schema/plugInfo.json'))"` exits 0; 21 entries under `Types` |
| F3 | Author `schema/generatedSchema.usda` | File exists; structurally parallels `HarloSchema.usda` |
| F4a | Author `python/harlo/usd_lite/persistence/__init__.py` | `python -c "from harlo.usd_lite.persistence import write, read"` succeeds (with `[substrate]`) |
| F4b | Author `writer.py` | Importable; minimal smoke test (write empty BrainStage, no crash) |
| F4c | Author `reader.py` | Importable; minimal smoke test (read what writer wrote) |
| F5a | Author `tests/test_path_c/__init__.py` (empty package marker) | File exists |
| F5b | Author `tests/test_path_c/test_schema_registry_gate.py` | `pytest tests/test_path_c/test_schema_registry_gate.py -v` passes |
| F5c | Author `tests/test_path_c/test_persistence_roundtrip.py` | `pytest tests/test_path_c/test_persistence_roundtrip.py -v` passes |
| F6 | Run full baseline | `pytest tests/ --tb=no -q` reports **≥1,133 + new test count green** |

If any verification step fails, Forge halts and escalates per Commandment 3 (3-retry budget).

---

## 7. Crucible Phase 2 gate criteria

Crucible Phase 2 verifies (Gate 2 per 03_HANDOFF):

| Criterion | Source |
|---|---|
| Subprocess `SchemaRegistry` test passes | F5b |
| 21 typeNames resolve | F5b |
| No collision with built-in USD or Moneta `MonetaMemory` | F5b negative check |
| Round-trip fidelity per prim (modulo declared codec-blockers) | F5c suite |
| 1,133 baseline tests still green (D14) | F6 |

---

## 8. Out of scope (Phase 2 explicit non-goals)

- **Sync layer** — Phase 3, separate session work next.
- **Migration script** — Phase 4.
- **Codec-blocker typed migration** — D8/D9 say deferred; sidecar default holds.
- **`src/cognitive_stage.py` modifications** — STAY-SEPARATE per scout §5.
- **Eviction of `data/stages/cognitive_twin.usda`** — Phase 5 work.
- **Performance tuning** — Phase 3 latency check is the gate; Phase 2 just produces correct output.

---

## 9. Architect handoff to Forge

**Forge greenlit.** Begin with F1 (`schema/HarloSchema.usda`).

**Forge does NOT:**
- Redesign anything (Architect re-engages for design changes).
- Use `usdGenSchema` (hand-author per §3.3).
- Touch `src/`.
- Touch the runtime tier (`python/harlo/usd_lite/{prims.py, stage.py, serializer.py, composer.py, hex_sdr.py, arc_types.py}`) — those are unchanged.
- Add tests outside `tests/test_path_c/`.

**Forge produces:** `forge/mile_2_phase_2_report.md` with per-file status + verification results.

*End of Phase 2 implementation plan. Forge enters next.*
