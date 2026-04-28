# Mile 2 — Phase 1 Schema Design

**Role:** Architect &nbsp;|&nbsp; **Date:** 2026-04-28
**Phase:** 1 — Schema authoring (design-only this session)
**Branch:** `harness-path-c` &nbsp;|&nbsp; **Authority binding:** D1–D5 in `harness/path_c/05_DECISIONS.md`

This document is the **sole authoritative design source** for Phase 2
Forge work. Phase 2 implements the schema artifacts (`schema.usda`,
`plugInfo.json`, `generatedSchema.usda`) verbatim against this design.
Forge does **not** redesign; deviations require Architect re-engagement.

---

## 0. Inputs honored

- **D2:** IsA hierarchy parallel-to-containment.
- **D3:** Moneta `plugInfo.json` is the canonical collision source. Done.
  Read at `C:\Users\User\Moneta\schema\plugInfo.json`. Single Moneta
  typeName: `MonetaMemory` (alias `MonetaMonetaMemory`). **Zero
  collisions** with Harlo's set.
- **D4:** Sync policy table fixed for orphan prims (Phase 3 work).
  This Phase 1 design notes per-prim sync policy intent in §6.
- **D5:** `InjectionPrim` and `InjectionContainerPrim` evicted from
  `schema.usda`; retained in runtime tier dataclasses only.
- **Commandment 11:** `arc_type` token convention fixed at
  **lower-case** (matches existing emitter output and current
  on-disk `data/hebbian_seeded.usda`).

---

## 1. IsA hierarchy (D2 — parallel-to-containment)

### 1.1 The tree

```
Typed (USD built-in)
└── HarloPrim                                          [abstract — Harlo's root metadata base]
    ├── HarloContainer                                 [abstract — composite holders]
    │   ├── BrainStage                                 [concrete; root of cognitive state]
    │   ├── AssociationPrim                            [holds TracePrim by hex content-hash key]
    │   ├── CompositionPrim                            [holds CompositionLayerPrim by layer_id]
    │   ├── ElenchusPrim                               [holds GateStatusPrim + MerkleRootPrim]
    │   ├── InquiryContainerPrim                       [ordered InquiryPrim list]
    │   ├── MotorContainerPrim                         [ordered MotorPrim list]
    │   ├── SkillsContainerPrim                        [holds SkillPrim by domain key]
    │   └── CognitiveProfilePrim                       [holds MultipliersPrim + IntakeHistoryPrim]
    │
    └── (HarloPrim concrete leaves — direct children)
        ├── TracePrim                                  [single memory trace; hot path]
        ├── CompositionLayerPrim                       [LIVRPS opinion layer]
        ├── Provenance                                 [layer source metadata, nested under CompositionLayerPrim]
        ├── GateStatusPrim                             [Elenchus verification gate]
        ├── MerkleRootPrim                             [Association subtree audit hash]
        ├── SessionPrim                                [session/routing state]
        ├── InquiryPrim                                [DMN hypothesis]
        ├── MotorPrim                                  [pending motor action + gate status]
        ├── SkillPrim                                  [per-domain competence]
        ├── MultipliersPrim                            [intake-derived calibration]
        └── IntakeHistoryPrim                          [intake admin log]
```

### 1.2 Type counts

- **Abstract types (USD `abstractTyped`):** 2 — `HarloPrim`, `HarloContainer`
- **Concrete types (USD `concreteTyped`):** 19
  - 8 containers (incl. `BrainStage` as the root container)
  - 11 leaves
- **Total typeNames declared in `schema.usda`:** 21
- **Mile 1 prims excluded per D5:** 2 (`InjectionPrim`, `InjectionContainerPrim`) — declared in runtime `prims.py` only, never in schema.

This **incidentally** gives the same "21 prim types" total as Mile 1's
inventory — the 2 evicted Injection types are replaced 1-for-1 by the 2
new abstract types. The composition is different but the count matches.

### 1.3 Why this shape

D2 mandates "parallel-to-containment." Three reasonable interpretations
existed, only one survives scrutiny:

| Interpretation | What it means | Verdict |
|---|---|---|
| Every containment edge is an IsA edge | E.g., `TracePrim IsA AssociationPrim` because `AssociationPrim` *contains* `TracePrim` | **Rejected.** Containment is composition, not type-relation. Encoding it as IsA gives `TracePrim` the storage attributes of `AssociationPrim`, which is wrong. |
| Containment **levels** map to IsA tiers | Three containment levels (root → containers → leaves) get three IsA tiers via abstract bases | **Adopted.** This preserves the conceptual mirror without conflating containment with inheritance. |
| Containment is irrelevant to IsA; design IsA independently | Every concrete prim inherits `Typed` directly | Rejected. This is the no-IsA-design alternative D2 already excluded. |

The adopted interpretation introduces 2 abstract types
(`HarloPrim`, `HarloContainer`). They carry no attributes; they
exist purely to (a) make `HarloContainer` schemas distinguishable
from leaf schemas at the registry level and (b) provide a
namespace-scoped abstract root so `Plug.Registry` queries can
enumerate "all Harlo types" without name-prefixing tricks.

### 1.4 Trade-offs explicitly named

- **+** Abstract bases let consumer code use `Usd.SchemaRegistry.IsConcrete()` to filter to working prims.
- **+** Future Harlo prims slot in cleanly: leaf → `HarloPrim`; container → `HarloContainer`.
- **−** Adds 2 typeNames that have no attributes and no test coverage in this surgery. Phase 6 must add a tiny "abstract types are registered" test.
- **−** A reader expecting Moneta-style flat hierarchy (single concrete schema with `Typed` parent) will be surprised. Documented in Phase 4 migration script comments.

### 1.5 [NEEDS DECISION] residual — **none on IsA shape.**

D2 + the analysis above resolves this completely. The Phase 2
Forge implementation has a deterministic target.

---

## 2. Per-prim attribute table

Conventions:
- **USD type column** matches Pixar OpenUSD's accepted attribute types.
- **Default** column: USD-style default; `—` means no default declared (USD's "absent" semantics).
- **Optional?** column: `Y` if the runtime tier marks the field
  `Optional[...]` and the writer omits when `None`.
- **Codec-blocker?** column: `Y` if the attribute carries an existing
  codec-encoded payload (hex SDR or JSON-as-string blob), per
  Commandments 7–8. Default plan: `string`-typed sidecar.

### 2.1 Abstract types

`HarloPrim` and `HarloContainer` declare **zero attributes**. They
exist for IsA-tier organization only.

### 2.2 Container types (IsA `HarloContainer`)

Containers carry **no scalar attributes**. They hold child prims at
fixed sub-paths (paths declared in §3). The storage of the children
themselves is handled by USD's prim-tree mechanics.

| typeName | Children at fixed paths | Notes |
|---|---|---|
| `BrainStage` | `Association`, `Composition`, `Elenchus`, `Session?`, `Inquiry`, `Motor`, `Skills`, `CognitiveProfile` | Root prim at `/Brain`. `Session` is optional (absent if no active session). |
| `AssociationPrim` | `Traces/<trace_id>` (TracePrim, dict-by-id) | `<trace_id>` is hex content hash. |
| `CompositionPrim` | `Layers/<layer_id>` (CompositionLayerPrim, dict-by-id) | |
| `ElenchusPrim` | `GateStatus?` (GateStatusPrim), `MerkleRoot?` (MerkleRootPrim) | Both optional. |
| `InquiryContainerPrim` | `hypothesis_<i>` (InquiryPrim, ordered list) | Index-named per existing serializer. |
| `MotorContainerPrim` | `action_<i>` (MotorPrim, ordered list) | Index-named per existing serializer. |
| `SkillsContainerPrim` | `<domain>` (SkillPrim, dict-by-domain) | Prim name = domain string. |
| `CognitiveProfilePrim` | `Multipliers` (MultipliersPrim), `IntakeHistory` (IntakeHistoryPrim) | Both required. |

### 2.3 Leaf types (IsA `HarloPrim`)

#### `TracePrim`
| Attr | USD type | Default | Optional? | Codec-blocker? |
|---|---|---|---|---|
| `sdr_hex` | `string` | — | N | **Y** (hex SDR sidecar; codec at runtime tier) |
| `content_hash` | `string` | — | N | N |
| `strength` | `float` | `0.0` | N | N |
| `last_accessed` | `double` | — | N | N (Unix seconds) |
| `co_activations_json` | `string` | `"{}"` | Y | **Y** (JSON blob sidecar) |
| `competitions_json` | `string` | `"{}"` | Y | **Y** (JSON blob sidecar) |
| `hebbian_strengthen_mask_hex` | `string` | — | N | **Y** (hex SDR sidecar) |
| `hebbian_weaken_mask_hex` | `string` | — | N | **Y** (hex SDR sidecar) |

Naming change: existing dataclass fields (`sdr`, `co_activations`, `competitions`, `hebbian_strengthen_mask`, `hebbian_weaken_mask`) are renamed in the schema to `*_hex`/`*_json` for clarity that these carry codec-encoded sidecar payloads. Sync layer (Phase 3) translates between dataclass names and schema attr names.

#### `CompositionLayerPrim`
| Attr | USD type | Default | Optional? | Codec-blocker? |
|---|---|---|---|---|
| `arc_type` | `token` | `"local"` | N | N (uses `allowedTokens` — see §4.5) |
| `opinion_json` | `string` | `"{}"` | N | **Y** (JSON blob sidecar) |
| `timestamp` | `double` | — | N | N (Unix seconds) |
| `permanent` | `bool` | `false` | N | N |

`Provenance` lives as a **child prim** at `<layer>/provenance` (typed `Provenance`), not as a flattened attribute set. Optional via prim absence.

#### `Provenance`
| Attr | USD type | Default | Optional? | Codec-blocker? |
|---|---|---|---|---|
| `source_type` | `token` | — | N | N (allowedTokens — §4.1) |
| `origin_timestamp` | `double` | — | N | N (Unix seconds) |
| `event_hash` | `string` | — | N | N |
| `session_id` | `string` | — | N | N (string FK to `SessionPrim.current_session_id`; not a USD relationship — see §7) |

#### `GateStatusPrim`
| Attr | USD type | Default | Optional? |
|---|---|---|---|
| `verification_state` | `token` | `"pending"` | N (allowedTokens — §4.2) |
| `cycle_count` | `int` | `0` | N |
| `last_verified` | `double` | — | N |

#### `MerkleRootPrim`
| Attr | USD type | Default | Optional? |
|---|---|---|---|
| `root_hash` | `string` | — | N |
| `trace_count` | `int` | `0` | N |

#### `SessionPrim`
| Attr | USD type | Default | Optional? |
|---|---|---|---|
| `current_session_id` | `string` | — | N |
| `exchange_count` | `int` | `0` | N |
| `surprise_rolling_mean` | `float` | `0.0` | N |
| `surprise_rolling_std` | `float` | `0.0` | N |
| `last_query_surprise` | `float` | `0.0` | N |
| `last_retrieval_path` | `token` | `"system_1"` | N (allowedTokens — §4.3) |

#### `InquiryPrim`
| Attr | USD type | Default | Optional? |
|---|---|---|---|
| `hypothesis` | `string` | — | N |
| `confidence` | `float` | `0.0` | N |

#### `MotorPrim`
| Attr | USD type | Default | Optional? |
|---|---|---|---|
| `action` | `string` | — | N |
| `gate_status` | `token` | `"inhibited"` | N (allowedTokens — §4.4) |

#### `SkillPrim`
| Attr | USD type | Default | Optional? | Codec-blocker? |
|---|---|---|---|---|
| `trace_count` | `int` | `0` | N | N |
| `first_seen` | `double` | — | N | N (Unix seconds) |
| `last_seen` | `double` | — | N | N (Unix seconds) |
| `growth_arc` | `float[]` | `[]` | N | **N (typed)** — clean migration; no codec |
| `hebbian_density` | `float` | `0.0` | N | N |

`domain` is the prim name, not an attribute (matches dataclass `from_dict` behavior).

#### `MultipliersPrim`
| Attr | USD type | Default | Optional? |
|---|---|---|---|
| `surprise_threshold` | `float` | `2.0` | N |
| `reconstruction_threshold` | `float` | `0.3` | N |
| `hebbian_alpha` | `float` | `0.01` | N |
| `allostatic_threshold` | `float` | `1.0` | N |
| `detail_orientation` | `float` | `0.5` | N |

Cleanest leaf in the schema; all `float` with declared defaults.

#### `IntakeHistoryPrim`
| Attr | USD type | Default | Optional? | Codec-blocker? |
|---|---|---|---|---|
| `last_intake` | `double` | — | Y | N (Unix seconds) |
| `intake_version` | `string` | — | Y | N |
| `answer_embeddings_json` | `string` | `"[]"` | Y | **Y** (JSON list sidecar) |

`[NEEDS DECISION (deferred to Phase 5)]: `answer_embeddings` is structurally a vector of floats — a clean migration target to `float[]`. The recon flagged this as "cheap migration." This Phase 1 design defaults to JSON-string sidecar per Commandment 8, but the typed-`float[]` upgrade is a documented Phase 5 candidate.

---

## 3. Prim path scheme

Root: `/Brain` (typed `BrainStage`).

| Path | Type |
|---|---|
| `/Brain` | `BrainStage` |
| `/Brain/Association` | `AssociationPrim` |
| `/Brain/Association/Traces/<trace_id>` | `TracePrim` |
| `/Brain/Composition` | `CompositionPrim` |
| `/Brain/Composition/Layers/<layer_id>` | `CompositionLayerPrim` |
| `/Brain/Composition/Layers/<layer_id>/provenance` | `Provenance` (optional) |
| `/Brain/Elenchus` | `ElenchusPrim` |
| `/Brain/Elenchus/GateStatus` | `GateStatusPrim` (optional) |
| `/Brain/Elenchus/MerkleRoot` | `MerkleRootPrim` (optional) |
| `/Brain/Session` | `SessionPrim` (optional — absent if no active session) |
| `/Brain/Inquiry` | `InquiryContainerPrim` |
| `/Brain/Inquiry/hypothesis_<i>` | `InquiryPrim` |
| `/Brain/Motor` | `MotorContainerPrim` |
| `/Brain/Motor/action_<i>` | `MotorPrim` |
| `/Brain/Skills` | `SkillsContainerPrim` |
| `/Brain/Skills/<domain>` | `SkillPrim` |
| `/Brain/CognitiveProfile` | `CognitiveProfilePrim` |
| `/Brain/CognitiveProfile/Multipliers` | `MultipliersPrim` |
| `/Brain/CognitiveProfile/IntakeHistory` | `IntakeHistoryPrim` |

These paths preserve the existing USD-Lite serializer's output shape
(see `python/harlo/usd_lite/serializer.py` `_serialize_*` functions),
so the migration script (Phase 4) has a 1-to-1 path mapping with the
old text format.

---

## 4. `allowedTokens` enum declarations

All five enums declared as USD `token` attributes with explicit
`allowedTokens` lists. **Lower-case casing convention** chosen
(Commandment 11) to match (a) existing emitter output, (b) on-disk
data in `data/hebbian_seeded.usda`, and (c) the Python `Enum.value`
strings already in use.

### 4.1 `SourceType` (used by `Provenance.source_type`)

```
allowedTokens = ["user_direct", "external_reference", "system_inferred", "hebbian_derived", "intake_calibrated"]
```

### 4.2 `VerificationState` (used by `GateStatusPrim.verification_state`)

```
allowedTokens = ["trusted", "contested", "refuted", "pending"]
```

Default: `"pending"`.

### 4.3 `RetrievalPath` (used by `SessionPrim.last_retrieval_path`)

```
allowedTokens = ["system_1", "system_2"]
```

Default: `"system_1"`.

### 4.4 `MotorGateStatus` (used by `MotorPrim.gate_status`)

```
allowedTokens = ["inhibited", "approved", "executing"]
```

Default: `"inhibited"` (matches Constitution Rule 23 — Basal Ganglia defaults to INHIBIT ALL).

### 4.5 `ArcType` (used by `CompositionLayerPrim.arc_type`)

```
allowedTokens = ["local", "inherit", "variant", "reference", "payload", "sublayer"]
```

Default: `"local"` (LIVRPS strongest opinion — matches `ArcType.LOCAL = 1`).

### 4.6 Cross-cutting note: token-casing fix (Commandment 11)

Existing emitter writes `arc_type.name.lower()` (e.g. `"local"`).
Existing parser reads via `ArcType[name.upper()]` (expects `"LOCAL"`).
This is the asymmetry recon flagged. **Fix:** lower-case wins
(matches data already on disk). Phase 5 Forge updates the parser to
read lower-case directly:

```python
# old (buggy):
arc_type=ArcType[arc_name.upper()]
# new:
arc_type=ArcType(arc_name)  # uses the lowercase value, not the upper-case name
```

This is a **runtime-tier change in Phase 5**, not Phase 2. Phase 2
schema authoring just declares the lower-case `allowedTokens`.

---

## 5. `plugInfo.json` shape

Mirrors Moneta's pattern at scale. Single plugin named `"harlo"`,
separate from Moneta's `"moneta"` plugin (Commandment 2). All 21
typeNames listed under `"Types"`.

```json
{
    "Plugins": [
        {
            "Info": {
                "Types": {
                    "HarloHarloPrim": {
                        "alias": {"UsdSchemaBase": "HarloPrim"},
                        "autoGenerated": true,
                        "bases": ["UsdTyped"],
                        "schemaIdentifier": "HarloPrim",
                        "schemaKind": "abstractTyped"
                    },
                    "HarloHarloContainer": {
                        "alias": {"UsdSchemaBase": "HarloContainer"},
                        "autoGenerated": true,
                        "bases": ["HarloHarloPrim"],
                        "schemaIdentifier": "HarloContainer",
                        "schemaKind": "abstractTyped"
                    },
                    "HarloBrainStage": {
                        "alias": {"UsdSchemaBase": "BrainStage"},
                        "autoGenerated": true,
                        "bases": ["HarloHarloContainer"],
                        "schemaIdentifier": "BrainStage",
                        "schemaKind": "concreteTyped"
                    },
                    "HarloAssociationPrim": { "...": "..." , "bases": ["HarloHarloContainer"], "schemaKind": "concreteTyped" },
                    "HarloCompositionPrim": { "bases": ["HarloHarloContainer"], "schemaKind": "concreteTyped" },
                    "HarloElenchusPrim": { "bases": ["HarloHarloContainer"], "schemaKind": "concreteTyped" },
                    "HarloInquiryContainerPrim": { "bases": ["HarloHarloContainer"], "schemaKind": "concreteTyped" },
                    "HarloMotorContainerPrim": { "bases": ["HarloHarloContainer"], "schemaKind": "concreteTyped" },
                    "HarloSkillsContainerPrim": { "bases": ["HarloHarloContainer"], "schemaKind": "concreteTyped" },
                    "HarloCognitiveProfilePrim": { "bases": ["HarloHarloContainer"], "schemaKind": "concreteTyped" },
                    "HarloTracePrim": { "bases": ["HarloHarloPrim"], "schemaKind": "concreteTyped" },
                    "HarloCompositionLayerPrim": { "bases": ["HarloHarloPrim"], "schemaKind": "concreteTyped" },
                    "HarloProvenance": { "bases": ["HarloHarloPrim"], "schemaKind": "concreteTyped" },
                    "HarloGateStatusPrim": { "bases": ["HarloHarloPrim"], "schemaKind": "concreteTyped" },
                    "HarloMerkleRootPrim": { "bases": ["HarloHarloPrim"], "schemaKind": "concreteTyped" },
                    "HarloSessionPrim": { "bases": ["HarloHarloPrim"], "schemaKind": "concreteTyped" },
                    "HarloInquiryPrim": { "bases": ["HarloHarloPrim"], "schemaKind": "concreteTyped" },
                    "HarloMotorPrim": { "bases": ["HarloHarloPrim"], "schemaKind": "concreteTyped" },
                    "HarloSkillPrim": { "bases": ["HarloHarloPrim"], "schemaKind": "concreteTyped" },
                    "HarloMultipliersPrim": { "bases": ["HarloHarloPrim"], "schemaKind": "concreteTyped" },
                    "HarloIntakeHistoryPrim": { "bases": ["HarloHarloPrim"], "schemaKind": "concreteTyped" }
                }
            },
            "LibraryPath": "",
            "Name": "harlo",
            "ResourcePath": ".",
            "Root": ".",
            "Type": "resource"
        }
    ]
}
```

(Forge expands the `"...": "..."` shorthand and fills in all
`alias`, `autoGenerated`, `schemaIdentifier` fields per the same
pattern as `HarloBrainStage` above. Forge does not deviate from this
shape; specifically: `alias.UsdSchemaBase = <ClassName>`, `autoGenerated = true`, `schemaIdentifier = <ClassName>`.)

### 5.1 Filename decision

[NEEDS DECISION resolved]: schema file is named **`schema/HarloSchema.usda`** (parallel to Moneta's `MonetaSchema.usda`), with `schema/plugInfo.json` and `schema/generatedSchema.usda` alongside. The 03_HANDOFF doc said `schema.usda`; this design overrides for naming consistency with Moneta. Forge writes both paths if the human prefers strict 03_HANDOFF compliance.

[NEEDS DECISION at human gate]: `schema/HarloSchema.usda` vs
`schema/schema.usda`. Architect proposes `HarloSchema.usda` for
parallel naming with Moneta. Human picks at gate.

### 5.2 Collision check vs Moneta

Moneta declared typeNames: `MonetaMonetaMemory` (with alias `MonetaMemory`).
Harlo declared typeNames (prefixed): `HarloHarloPrim`, `HarloHarloContainer`,
plus 19 `Harlo<ClassName>` for each concrete prim.

Set intersection: **∅**. **No collisions.**

---

## 6. Sync policy intent (Phase 3 work — declared here for design completeness)

Per D4 + recon §3 inheritance:

| Prim | Sync policy (D4 / recon) | Phase 3 work |
|---|---|---|
| `BrainStage` | inherit (root container) | Phase 3 |
| `AssociationPrim`, `CompositionPrim`, `ElenchusPrim` | inherit from contained leaves | Phase 3 |
| `SessionPrim` | **write-through** (D4 default) | Phase 3 |
| `GateStatusPrim` | **write-through** (D4 default) | Phase 3 |
| `MerkleRootPrim` | **write-through** (D4 default) | Phase 3 |
| `TracePrim` | **checkpoint** (D4 default; high write rate) | Phase 3 |
| `CompositionLayerPrim` | **checkpoint** (D4 default) | Phase 3 |
| `Provenance` | inherits parent `CompositionLayerPrim` policy | Phase 3 |
| `SkillPrim` / `SkillsContainerPrim` | **checkpoint** | Phase 3 |
| `MultipliersPrim` | **checkpoint** | Phase 3 |
| `IntakeHistoryPrim` | **checkpoint** | Phase 3 |
| `CognitiveProfilePrim` | **checkpoint** (inherit) | Phase 3 |
| `InquiryPrim` / `InquiryContainerPrim` | **checkpoint** (D4 ruling) | Phase 3 |
| `MotorPrim` / `MotorContainerPrim` | **write-through** (D4 ruling — safety) | Phase 3 |

This Phase 1 design **does not implement the sync policy** but ensures
the schema's typed-attribute layout supports it: write-through prims
have small per-prim write payloads (small int/float/string sets);
checkpoint prims with larger payloads (TracePrim's hex SDRs) are
appropriate for batched persistence.

---

## 7. Codec-blocker boundary plan

Per Commandments 7 and 8, codec-blockers are handled at the
persistence boundary as **`string`-typed sidecar attributes**. Typed
upgrades are documented but deferred to a follow-on surgery unless
Phase 5 overrides per blocker.

| Blocker | Affected attr(s) | Default plan (this surgery) | Typed-upgrade path (deferred) |
|---|---|---|---|
| Hex SDR (2048-bit boolean ↔ 512-char hex) | `TracePrim.sdr_hex`, `TracePrim.hebbian_strengthen_mask_hex`, `TracePrim.hebbian_weaken_mask_hex` | `string` sidecar, codec lives in runtime tier (`hex_sdr.py`) | Migrate to `int[]` (size 2048) or `bool[]`. Trade-off: `int[]` ~16 KB per attr in .usda text vs ~512 B for hex string. Sticking with sidecar. |
| `co_activations` JSON dict | `TracePrim.co_activations_json` | `string` sidecar carrying `json.dumps(..., sort_keys=True)` | Migrate to USD `relationship` (target paths) + parallel `int[]` for counts. Cost: requires the Phase 4 migration script to resolve trace IDs to prim paths. Defer. |
| `competitions` JSON dict | `TracePrim.competitions_json` | Same as above | Same as above. |
| `opinion` JSON blob (free-form `dict[str, object]`) | `CompositionLayerPrim.opinion_json` | `string` sidecar | Structurally untyped (free-form opinion); Architect proposes leaving this as string sidecar permanently. The "typed migration" deferred ticket can be closed as wontfix. [NEEDS DECISION: confirm at human gate] |
| `answer_embeddings` (float vector) | `IntakeHistoryPrim.answer_embeddings_json` | `string` sidecar | Migrate to `float[]`. Cleanest target — recon §3.3 flagged as cheap. Architect proposes Phase 5 override here: skip the JSON sidecar, declare `float[] answer_embeddings` directly. [NEEDS DECISION at human gate.] |

### 7.1 String FK note

Three attrs hold cross-prim string keys:
- `Provenance.session_id` → `SessionPrim.current_session_id`
- `TracePrim.co_activations_json` keys → other `TracePrim.content_hash` (or trace_id prim names)
- `TracePrim.competitions_json` keys → same

These are **string foreign keys, not USD relationships.** The runtime
tier (`prims.py` dataclasses) uses string lookups. This Phase 1 design
preserves that — no `rel`-typed attributes added — to avoid making
Phase 2 reader/writer handle relationship target resolution. Future
schema migration can introduce `rel` if useful.

---

## 8. Subprocess `SchemaRegistry` gate test (specified, not yet executed)

Per Commandment 4, before any prim operation in CI, validation runs
in a fresh subprocess. Phase 2 Forge will implement; this Phase 1
design specifies the test.

### 8.1 Test outline (Forge implements verbatim)

File: `tests/test_path_c/test_schema_registry_gate.py`

```python
"""Subprocess-isolated SchemaRegistry gate test (Commandment 4)."""

import subprocess
import sys
from pathlib import Path

import pytest


HARLO_TYPENAMES = [
    "HarloPrim",                # abstract
    "HarloContainer",           # abstract
    "BrainStage",
    "AssociationPrim", "CompositionPrim", "ElenchusPrim",
    "InquiryContainerPrim", "MotorContainerPrim",
    "SkillsContainerPrim", "CognitiveProfilePrim",
    "TracePrim", "CompositionLayerPrim", "Provenance",
    "GateStatusPrim", "MerkleRootPrim", "SessionPrim",
    "InquiryPrim", "MotorPrim", "SkillPrim",
    "MultipliersPrim", "IntakeHistoryPrim",
]


def test_schema_registry_loads_all_harlo_types_in_subprocess():
    """Validates schema/plugInfo.json registers all 21 typeNames."""
    schema_dir = Path("schema").absolute()
    code = f"""
from pxr import Plug, Usd
import sys

reg = Plug.Registry()
reg.RegisterPlugins({str(schema_dir)!r})

schema_reg = Usd.SchemaRegistry()
expected = {HARLO_TYPENAMES!r}
missing = []
for typename in expected:
    if not schema_reg.IsTyped(typename) and not schema_reg.IsConcrete(typename):
        # Try IsAppliedAPISchema for abstract bases
        ti = schema_reg.GetTypeFromName(typename)
        if not ti:
            missing.append(typename)

if missing:
    print('MISSING:', missing)
    sys.exit(1)

# Negative: confirm Moneta's typeName does NOT collide
if schema_reg.IsTyped('MonetaMemory') or schema_reg.GetTypeFromName('MonetaMemory'):
    print('UNEXPECTED MonetaMemory in registry')
    sys.exit(2)

# Confirm a built-in USD type is still resolvable (registry not corrupted)
if not schema_reg.GetTypeFromName('Xform'):
    print('USD built-in Xform not resolvable — registry corrupted')
    sys.exit(3)

print('OK')
sys.exit(0)
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, (
        f"Schema registry subprocess failed:\\n"
        f"stdout: {result.stdout}\\n"
        f"stderr: {result.stderr}"
    )
    assert "OK" in result.stdout
```

### 8.2 What this test guarantees

- All 21 typeNames load via `Plug.Registry().RegisterPlugins(...)`
  on a fresh subprocess (no parent-process pollution).
- Moneta's `MonetaMemory` is NOT visible in the harlo-only registry
  (would indicate accidental cross-plugin loading).
- USD built-in types (`Xform`) remain resolvable after harlo plugin
  registration (no registry corruption).
- A 60-second timeout on the subprocess catches infinite loops or
  registration deadlocks.

### 8.3 What this test does NOT cover

- Per-attribute schema correctness (typed attrs, defaults,
  allowedTokens) — covered by separate Phase 2 round-trip tests.
- Container/leaf semantics — covered by Phase 2 round-trip tests.
- Sync policy — covered by Phase 3 tests.

---

## 9. Trade-offs explicitly named (cross-cutting)

| Decision point | Tradeoff |
|---|---|
| 2 abstract types vs flat hierarchy | + Cleaner querying via `IsConcrete`. − 2 extra typeNames with no attributes; tiny test-coverage burden. **Adopted.** |
| `string` sidecar codec defaults | + Surgery scope minimized. − Performance & schema purity sacrificed at the persistence boundary. **Adopted with two override candidates surfaced (§7).** |
| Lower-case enum tokens | + Matches existing on-disk data and emitter output. − Requires runtime-tier parser update (Phase 5). **Adopted (Commandment 11).** |
| `double` for timestamps (Unix seconds) | + Matches Moneta. + Compact. − Loses the human-readable ISO format. Sync layer translates. **Adopted.** |
| `Provenance` as child prim, not flattened attrs | + Preserves nesting structure of existing serializer. − Slightly more prim-tree overhead. **Adopted.** |
| String FKs (no `rel`) | + No cross-prim resolution complexity in Phase 2. − Loses USD relationship semantics. **Adopted (status-quo preserving).** |
| Filename `HarloSchema.usda` vs `schema.usda` | + Parallels Moneta's naming. − Diverges from 03_HANDOFF spec. **Architect proposes; human picks.** |

---

## 10. Open `[NEEDS DECISION]` markers (human gate input)

Three items the human should rule on before Phase 2:

1. **Schema filename** — `schema/HarloSchema.usda` (Architect's
   proposal) vs `schema/schema.usda` (03_HANDOFF spec). §5.1.
2. **`opinion_json` typed migration** — leave as permanent string
   sidecar (Architect's proposal: it's structurally untyped) or keep
   the typed-upgrade as a Phase 5+ candidate. §7.
3. **`answer_embeddings` typed migration** — Architect proposes
   declaring `float[] answer_embeddings` in `IntakeHistoryPrim`
   directly (skip the JSON sidecar) since the float-vector typing is
   trivial. Confirm or veto. §7.

These are NOT pre-decided. Phase 2 Forge halts on whichever Architect
position the human contradicts.

---

## 11. Phase 1 deliverable inventory (this session)

- `design/mile_2_phase_1_schema_design.md` (this file) — sole
  authoritative design source.

**Phase 1 does NOT write this session:**
- `schema/schema.usda` (or `HarloSchema.usda`) — Phase 2 Forge.
- `schema/plugInfo.json` — Phase 2 Forge.
- `schema/generatedSchema.usda` — Phase 2 Forge (output of
  `usdGenSchema --codeless` if used; otherwise hand-authored from
  the §5 shape).
- `tests/test_path_c/test_schema_registry_gate.py` — Phase 2 Forge,
  per §8 spec.

---

## Human Review Gate — Pending

**Session-end status (per session override format):**

### Design decisions made (one-paragraph summary)

Architect adopts: a 3-tier IsA hierarchy (`Typed → HarloPrim →
{HarloContainer, leaves}`) with 2 abstract bases and 19 concrete
prims, parallel to containment per D2. All 5 enum types declared as
`token` attributes with lower-case `allowedTokens` (Commandment 11
fix). Codec-blockers handled as `string` sidecars by default
(Commandments 7–8), with two override candidates surfaced
(`opinion_json`: keep as permanent string; `answer_embeddings`:
upgrade to `float[]` in this surgery). `plugInfo.json` registers under
the `harlo` namespace, separate from Moneta's `MonetaMemory`; zero
typeName collisions (D3 confirmed). Schema filename proposed
`HarloSchema.usda` for parallelism with Moneta. Subprocess
`SchemaRegistry` gate test fully specified for Phase 2 Forge.

### Phase 0 blockers routed here from Crucible (`verify/mile_2_phase_0_crucible.md`)

- **B1 (low):** Strict `pip install -e .[substrate]` failed on a
  `.pyd` file lock from a concurrent Python process. Workaround
  (`pip install usd-core>=24.05` direct) succeeded; `pxr 26.5`
  importable. Future Forge sessions must verify the strict command
  succeeds before Phase 2 begins.
- **B2 (high — structural):** Test baseline is **1,065 green** (with
  48 failed, 17 errored, 1 skipped out of 1,131 collected), not 1,140.
  The Mile 1 Constitution Law 2 ("1,140 tests stay green at every
  gate") was authored on an unverified premise. The delta is
  pre-existing and pre-Phase-0; mostly missing dev dependencies
  (`sentence_transformers`, mcp test deps) and pre-existing provider
  test failures. Mile 2 Phase 2 cannot begin until baseline is either
  (a) restored to ~1,140 by installing missing dev deps, (b) revised
  in `02_CONSTITUTION.md` to match measured reality, or (c) explicitly
  scoped to a different test subset.

### Bulleted list of trade-offs the human must confirm

- IsA hierarchy: 3-tier with `HarloPrim`+`HarloContainer` abstract
  bases (vs flat `Typed`-direct).
- Codec-blocker default: `string` sidecar (vs typed migration in
  this surgery).
- Token casing: lower-case (vs upper-case).
- Timestamp encoding: `double` Unix seconds (vs ISO `token` string).
- `Provenance` shape: child prim under `CompositionLayerPrim` (vs
  flattened attribute set).
- Cross-prim links: string FKs (vs USD `rel`).

### `[NEEDS DECISION]` markers requiring human input

1. **Schema filename:** `HarloSchema.usda` (Architect's proposal) or
   `schema.usda` (03_HANDOFF text)?
2. **`opinion_json` typed migration:** keep as permanent string
   sidecar (Architect: structurally untyped, wontfix the typed-upgrade
   ticket) or retain as Phase 5+ candidate?
3. **`answer_embeddings` typed migration in this surgery:** upgrade to
   `float[]` (Architect: cheap migration, do it now) or stick with
   string-sidecar default (defer)?

### Specific question for the human

**Approve design as-is, request changes, or escalate to Deep Think?**

If approve: Phase 2 Forge (next session) implements §1–§5 and §8
verbatim, with the three [NEEDS DECISION] resolutions plus B1/B2
remediation noted above.

If request changes: surface specific section refs (e.g., "revise §1
IsA shape to flat" or "§7 — yes, migrate `answer_embeddings` to
`float[]`"). Architect re-engages for a delta design pass.

If escalate to Deep Think: send this design doc + Phase 0 scout +
Crucible verdict to the external reviewer per
`harness/path_c/04_DEEP_THINK_BRIEF.md`. This was the original
intended path; B2 makes external review more important, not less.

*End of Phase 1 schema design. Architect exits role. Halt at human gate.*
