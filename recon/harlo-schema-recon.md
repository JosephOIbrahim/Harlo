# Harlo Schema Recon — Pre-Flight Scout

**Repo:** `C:\Users\User\Harlo` &nbsp;|&nbsp; **Branch:** `master` &nbsp;|&nbsp; **Date:** 2026-04-28
**Mode:** READ-ONLY. No source edits, no git ops, no schema changes.

---

## TL;DR — Framing Mismatch (read this first)

The mission brief is written as if Harlo uses **Pixar OpenUSD** with formal
schema artifacts (`plugInfo.json`, codeful vs codeless, `typeName`,
`allowedTokens`, `IsA`). **Harlo does not.** It ships a hand-rolled
mini-USD called **USD-Lite** that lives entirely in
`python/harlo/usd_lite/`. That changes the meaning of every section
below. Specifics:

| Mission concept | Reality in Harlo |
|---|---|
| `plugInfo.json` registering schemas | **Does not exist.** Zero hits in repo. |
| Codeful vs codeless schema | **Neither.** Schema = Python `@dataclass` definitions. No `usdGenSchema`-derived C++/codeless layer. |
| `typeName` on a USD prim | **Implicit.** The class name (`TracePrim`, `BrainStage`, …) is emitted as the literal text token after `def` in `.usda` output by `usd_lite/serializer.py`, then matched in `_BlockParser.parse()` via `if type_name == "..."` branches. |
| `allowedTokens` enums | **None declared.** Token-valued attrs (e.g. `arc_type`, `gate_status`) are validated only by `Enum(value)` constructor lookups in `_build_*` helpers. |
| `IsA` schema inheritance | **None.** All prim classes are independent dataclasses; structure is composition only. |
| Pixar USD runtime (`pxr.Sdf`, `pxr.Usd`) | **Not imported anywhere.** `usd_lite/__init__.py:1-5` calls itself "Not full OpenUSD (2GB C++ dependency). Implements ~5% of USD." |
| Moneta / "Moneta-Q5 equivalent" | **Not in this repo.** Zero matches for `moneta`/`Moneta`/`MONETA`. |

**Implication for the codeless-surgery harness draft:** there is no
codeful → codeless conversion to script, because there is no formal
USD schema layer. What can be migrated is the *text format emitted by
`usd_lite/serializer.py`* — i.e. what `def TypeName "..."` blocks get
written/parsed. Treat the harness as a **mini-USD format migration
tool**, not a USD schema-registry migration tool.

[AMBIGUOUS: if "Moneta" is a sibling repo Joe owns elsewhere on disk
that the harness will sit between, this report has no visibility into
it. The Moneta-Q5 read-path comparison and `plugInfo.json` collision
analysis cannot be performed from inside this repo alone.]

---

## Section 1 — Prim Type Inventory

**Single source:** `python/harlo/usd_lite/prims.py` (589 lines) plus
`python/harlo/usd_lite/stage.py` (131 lines, defines `BrainStage`
root).

**Actual count: 21 schema-emitting types** (mission expected ~17;
reporting actual rather than padding/trimming. The drift is small
enough that the mission's "stop and report if 8 or 25" check does
not trigger).

"Format" column reads:
- **dataclass+serializer**: dataclass body in `prims.py`/`stage.py`,
  hand-written emitter in `serializer.py`. This is the only format in
  use — there is no codeful or codeless USD-schema source for these.

| # | typeName (text token) | file path | line range | format | one-line purpose |
|---|---|---|---|---|---|
| 1 | `BrainStage` | `python/harlo/usd_lite/stage.py` | 76–131 | dataclass+serializer | Root stage container; holds all subsystem subtrees. |
| 2 | `Provenance` | `python/harlo/usd_lite/prims.py` | 58–83 | dataclass+serializer | Source/origin metadata for composition layers (Phase 3). |
| 3 | `TracePrim` | `python/harlo/usd_lite/prims.py` | 96–136 | dataclass+serializer | Single memory trace at `/Association/Traces/{id}` — SDR + decay + Hebbian masks. |
| 4 | `CompositionLayerPrim` | `python/harlo/usd_lite/prims.py` | 139–171 | dataclass+serializer | LIVRPS opinion layer at `/Composition/Layers/{id}`. |
| 5 | `GateStatusPrim` | `python/harlo/usd_lite/prims.py` | 174–196 | dataclass+serializer | Elenchus verification gate state at `/Elenchus/GateStatus`. |
| 6 | `MerkleRootPrim` | `python/harlo/usd_lite/prims.py` | 199–218 | dataclass+serializer | Merkle hash over `/Association/Traces`. |
| 7 | `SessionPrim` | `python/harlo/usd_lite/prims.py` | 221–252 | dataclass+serializer | Session metadata + retrieval-path routing state. |
| 8 | `InquiryPrim` | `python/harlo/usd_lite/prims.py` | 255–274 | dataclass+serializer | Active DMN hypothesis. |
| 9 | `MotorPrim` | `python/harlo/usd_lite/prims.py` | 277–296 | dataclass+serializer | Pending motor action with basal-ganglia gate status. |
| 10 | `SkillPrim` | `python/harlo/usd_lite/prims.py` | 299–330 | dataclass+serializer | Per-domain competence tracking. |
| 11 | `MultipliersPrim` | `python/harlo/usd_lite/prims.py` | 333–361 | dataclass+serializer | Personal calibration scalars (intake-derived). |
| 12 | `InjectionPrim` | `python/harlo/usd_lite/prims.py` | 364–395 | dataclass+serializer | Behavioral modulation state (Digital Injection Framework). |
| 13 | `IntakeHistoryPrim` | `python/harlo/usd_lite/prims.py` | 398–421 | dataclass+serializer | Intake administration log + answer embeddings. |
| 14 | `AssociationPrim` | `python/harlo/usd_lite/prims.py` | 429–445 | dataclass+serializer | Container at `/Association` → dict of `TracePrim`. |
| 15 | `CompositionPrim` | `python/harlo/usd_lite/prims.py` | 448–467 | dataclass+serializer | Container at `/Composition` → dict of `CompositionLayerPrim`. |
| 16 | `ElenchusPrim` | `python/harlo/usd_lite/prims.py` | 470–491 | dataclass+serializer | Container at `/Elenchus` → optional `GateStatusPrim` + `MerkleRootPrim`. |
| 17 | `InquiryContainerPrim` | `python/harlo/usd_lite/prims.py` | 494–510 | dataclass+serializer | Container at `/Inquiry` → list of `InquiryPrim`. |
| 18 | `MotorContainerPrim` | `python/harlo/usd_lite/prims.py` | 513–529 | dataclass+serializer | Container at `/Motor` → list of `MotorPrim`. |
| 19 | `SkillsContainerPrim` | `python/harlo/usd_lite/prims.py` | 532–548 | dataclass+serializer | Container at `/Skills` → dict of `SkillPrim`. |
| 20 | `InjectionContainerPrim` | `python/harlo/usd_lite/prims.py` | 551–567 | dataclass+serializer | Container at `/Injection` → list of `InjectionPrim`. **BLOCKER — see §2.** |
| 21 | `CognitiveProfilePrim` | `python/harlo/usd_lite/prims.py` | 570–589 | dataclass+serializer | Container at `/CognitiveProfile` → `MultipliersPrim` + `IntakeHistoryPrim`. |

**Companion enum types (token-valued, NOT separately emitted as prims; declared in `prims.py` 22–50):**
`SourceType`, `VerificationState`, `RetrievalPath`, `MotorGateStatus`. Plus `ArcType` in `usd_lite/arc_types.py`.
These behave like `allowedTokens` would in real USD, but are enforced only at
parse time by `EnumClass(value)` calls.

**Out-of-scope schemas seen in repo (reported for context, not part of inventory):**

- `src/schemas.py` — Pydantic `BaseModel` schema for `CognitiveObservation`
  used by trajectory generation / XGBoost. Different surface entirely. Not
  USD-Lite. Includes its own `IntEnum`s (`Momentum`, `Burnout`, `Energy`, …).
- `data/stages/cognitive_twin.usda` — uses `def Scope "..."` typeNames with
  `timeSamples`, **not** `def TracePrim`/`def BrainStage`. Sublayers
  reference `C:\Users\User\Cognitive_Twin\...`, the pre-rename package path
  (commit `f830aeb`), and there is **no Python writer for this format in the
  current tree**. [AMBIGUOUS: this file appears to be stale demo data from
  before the package rename — likely orphaned. The harness should decide
  whether to migrate or evict it.]
- `config/barrier_schema.json` — JSON-Schema for the Blood-Brain Barrier
  (Rule 8 / Modulation layer). Not USD.

---

## Section 2 — Surgery Cost Per Type

Cost signals applied:

- **Typed property count** — counted from each `@dataclass` body
  (excluding `to_dict`/`from_dict` plumbing, which is *itself* a cost
  multiplier; see "custom logic").
- **Token-encoded enum?** `+1 tier` if any field is an `Enum`
  serialized as `token` in the emitter.
- **Custom Python logic that won't survive codeless conversion?** Every
  type has paired `to_dict`/`from_dict` *and* there are
  per-type `_serialize_*` and `_build_*` functions in `serializer.py`.
  This logic encodes a custom **hex SDR codec** (2048-bit boolean
  array ↔ 512-char hex), JSON-as-string blob attrs (`dict`-typed
  USD-Lite attrs), float reformatting, and ISO-datetime token
  conversion. None of this maps cleanly to a `usdGenSchema`-style
  codeless schema; flagged as **codec-blocker** where present.
- **IsA inheritance** — none in this codebase (see §3); column omitted.

**Sorted heaviest first:**

| typeName | typed props | token enums? | custom logic | base cost | adjusted | notes |
|---|---|---|---|---|---|---|
| `TracePrim` | 9 | none direct (but `last_accessed` is a token-formatted datetime) | hex SDR codec on 3 fields, JSON-as-string on 2 fields, datetime token on 1 | heavy (9+) | **HEAVY (codec-blocker)** | Hot path. Highest read-fanout (see §4). The hex-SDR codec is bespoke and has no USD-native analogue. |
| `BrainStage` | 9 child container fields | n/a | per-child dispatch in `serialize()` and `_BlockParser.parse()` | heavy (9+) | **HEAVY** | Root. Any new container type requires touching both serialize and parse switch-blocks. |
| `CompositionLayerPrim` | 6 | yes (`arc_type` token via `ArcType.name.lower()`) | nested `Provenance` block, JSON-as-string `opinion`, datetime token | medium (4–8) | **MEDIUM+1 → HEAVY** | Asymmetric token convention: emits `arc_type.name.lower()`, parses via `ArcType[name.upper()]`. Brittle. |
| `SkillPrim` | 6 | none | typed `float[]` array, two datetime tokens | medium (4–8) | **MEDIUM** | `float[]` array token is the only place in the schema using a typed-array attribute syntax. |
| `SessionPrim` | 6 | yes (`last_retrieval_path`) | none beyond standard | medium (4–8) | **MEDIUM+1 → HEAVY (lite)** | Multiple production readers (see §4). |
| `InjectionPrim` | 6 | yes (`profile`, `transition` are *string-valued*, not Enum-backed; only conventionally tokenized) | none beyond standard | medium (4–8) | **MEDIUM+1 → HEAVY (lite)** + **BLOCKER** | **Never emitted by `serializer.serialize()` and never parsed by `_BlockParser.parse()`.** Defined and held on `BrainStage.injection`, but the on-disk round-trip drops it silently. Any harness migration must either (a) finish the implementation or (b) explicitly choose to drop it. |
| `InjectionContainerPrim` | 1 | n/a | none | light (0–3) | **LIGHT + BLOCKER** | Same orphan status as `InjectionPrim`. |
| `MultipliersPrim` | 5 | none | none beyond standard | medium (4–8) | **MEDIUM** | All-`float` block; cleanest type in the schema. |
| `Provenance` | 4 | yes (`source_type`, plus token-formatted datetime) | nested-block emitter (`_serialize_provenance`), only emitted as a child of `CompositionLayerPrim` | medium (4–8) | **MEDIUM+1 → HEAVY (lite)** | Only non-`*Prim`-suffixed type emitted. Naming inconsistency. |
| `GateStatusPrim` | 3 | yes (`verification_state`) | none beyond standard | light | **MEDIUM** | |
| `IntakeHistoryPrim` | 3 | none | optional datetime, JSON-as-string `list` | light | **LIGHT+1 → MEDIUM (lite)** | Two of three fields are `Optional`; emitter omits when `None` (asymmetric round-trip). |
| `MerkleRootPrim` | 2 | none | none beyond standard | light | **LIGHT** | |
| `InquiryPrim` | 2 | none | none beyond standard | light | **LIGHT** | |
| `MotorPrim` | 2 | yes (`gate_status`) | none beyond standard | light | **LIGHT+1 → MEDIUM** | |
| `CognitiveProfilePrim` | 2 nested children | n/a | nested-emit logic | light | **LIGHT** | Container only. |
| `ElenchusPrim` | 2 optional children | n/a | optional-emit logic | light | **LIGHT** | Container only. |
| `AssociationPrim` | 1 (dict) | n/a | iterates sorted children | light | **LIGHT** | Container only; cost lives in `TracePrim`. |
| `CompositionPrim` | 1 (dict) | n/a | iterates sorted children | light | **LIGHT** | Container only. |
| `InquiryContainerPrim` | 1 (list) | n/a | indexed `hypothesis_{i}` naming | light | **LIGHT** | |
| `MotorContainerPrim` | 1 (list) | n/a | indexed `action_{i}` naming | light | **LIGHT** | |
| `SkillsContainerPrim` | 1 (dict) | n/a | iterates sorted children | light | **LIGHT** | |

**Cross-cutting cost concerns the harness should plan for:**

1. **Custom hex-SDR codec** (`usd_lite/hex_sdr.py`, ~57 LOC). Not USD-native.
   Lives only on `TracePrim`. Any "codeless" target that lacks string-attr
   plus a callout codec will break this round-trip.
2. **JSON-as-string blob attrs** (`dict`, `list` "types" in the emitter).
   Not real USD types. Used by `TracePrim.co_activations`,
   `TracePrim.competitions`, `CompositionLayerPrim.opinion`,
   `IntakeHistoryPrim.answer_embeddings`. These are data smell — they
   bypass schema entirely.
3. **Optional-field omission** (most `from_dict` and `_build_*` paths
   default missing fields). Round-trip is **asymmetric**: serialize
   drops `None`/empty, parse fills defaults. A migration that adds a
   field is safe; one that *renames* a field will silently degrade
   to default. Any harness rename step needs an explicit
   `migrate_field(old, new)` pass before parse.

---

## Section 3 — Dependency Graph

### IsA (schema inheritance)

**None.** Searched all `*Prim`, `Provenance`, `BrainStage` class
declarations in `usd_lite/`: every one inherits `object` (or only
implicit dataclass). There is no Harlo-internal type hierarchy to
order around.

### Composition / containment (parent → child)

```
BrainStage
├── AssociationPrim
│   └── dict[str, TracePrim]
├── CompositionPrim
│   └── dict[str, CompositionLayerPrim]
│                  └── Optional[Provenance]                (nested-emit child)
├── ElenchusPrim
│   ├── Optional[GateStatusPrim]
│   └── Optional[MerkleRootPrim]
├── Optional[SessionPrim]                                  (root-level field, not a container)
├── InquiryContainerPrim
│   └── list[InquiryPrim]
├── MotorContainerPrim
│   └── list[MotorPrim]
├── SkillsContainerPrim
│   └── dict[str, SkillPrim]
├── CognitiveProfilePrim
│   ├── MultipliersPrim
│   └── IntakeHistoryPrim
└── InjectionContainerPrim                                 (BLOCKER: declared, never serialized)
    └── list[InjectionPrim]                                (BLOCKER: declared, never serialized)
```

### Cross-references via attributes / relationships

- `TracePrim.co_activations: dict[str, int]` — keys are *other* `TracePrim`
  IDs; **stored as JSON-encoded string**, not as a USD relationship. No
  schema-level link.
- `TracePrim.competitions: dict[str, int]` — same pattern.
- `Provenance.session_id: str` — references `SessionPrim.current_session_id`
  by string value; no schema-level link.
- `InjectionPrim.session_id: str` — same pattern.

**Cycles:** none in containment. The `co_activations`/`competitions` cross-link
is a same-type (`TracePrim` ↔ `TracePrim`) string-keyed reference — it can
form a logical cycle in trace data but does not affect schema dependency
ordering.

### Ordering implication for surgery

Because there is no `IsA`, **migration ordering is driven by containment, not
inheritance**: leaf prims (`TracePrim`, `CompositionLayerPrim`, …) can be
migrated independently; container prims must follow their leaves; `BrainStage`
must follow all containers.

---

## Section 4 — Read-Path Audit

Conventions:

- **Defining files** (`usd_lite/prims.py`, `usd_lite/stage.py`,
  `usd_lite/__init__.py`) and the **canonical writer/reader pair**
  (`usd_lite/serializer.py`) are listed but not counted as
  "consumer breakage" risks — they're the schema by definition.
- **Test consumers** are listed in compact form (file count) since
  they break loudly when schemas drift.
- **Production consumers** are the migration-safety surface — these
  modules would need read-tolerant logic (handle both old and new
  typeName/field shape) during transition.

| typeName | Production consumers (outside `usd_lite/`) | Test consumers | Migration risk |
|---|---|---|---|
| `TracePrim` | `python/harlo/brainstem/stage_builder.py`, `brainstem/merkle.py`, `brainstem/adapters.py`, `hebbian/learning.py`, `hebbian/reconstruction.py`, `skills/observer.py`, `migrate_v7.py`; `scripts/seed_hebbian.py` | 6 (test_brainstem ×2, test_hebbian ×3, test_skills ×1, test_usd_lite ×4) | **HIGH** — most-read prim, hot path, hex SDR codec |
| `CompositionLayerPrim` | `brainstem/provenance.py`, `brainstem/adapters.py`, `usd_lite/composer.py` | 4 | **HIGH** — composer.py depends on `arc_type` and `permanent` semantics |
| `SessionPrim` | `brainstem/stage_builder.py`, `brainstem/routing.py`, `brainstem/session_updater.py`, `brainstem/adapters.py` | 4 | **MEDIUM** — wide brainstem fan-out |
| `Provenance` | `brainstem/provenance.py`, `intake/multipliers.py`, `hebbian/reconstruction.py` | 2 | **MEDIUM** — nested-only emit; rename of parent breaks discovery |
| `MultipliersPrim` / `IntakeHistoryPrim` / `CognitiveProfilePrim` | `intake/multipliers.py`, `hebbian/training_data.py`, `hebbian/reconstruction.py`, `hebbian/learning.py`, `hebbian/stability.py`*, `brainstem/routing.py`, `brainstem/session_updater.py` | 5+ | **MEDIUM** — Multipliers fan-out is broad |
| `GateStatusPrim` / `MerkleRootPrim` / `ElenchusPrim` | `brainstem/stage_builder.py`, `brainstem/adapters.py` | 3 | **LOW** — narrow consumer set |
| `MotorPrim` / `MotorContainerPrim` | `brainstem/stage_builder.py`, `brainstem/adapters.py` | 1 | **LOW** |
| `InquiryPrim` / `InquiryContainerPrim` | `brainstem/stage_builder.py`, `brainstem/adapters.py` | 1 | **LOW** |
| `SkillPrim` / `SkillsContainerPrim` | `skills/observer.py`, `migrate_v7.py` | 1 | **LOW** |
| `AssociationPrim` | `brainstem/stage_builder.py`, `migrate_v7.py` | 4 | **LOW** (container; risk lives in `TracePrim`) |
| `CompositionPrim` | `brainstem/stage_builder.py` | 4 | **LOW** |
| `BrainStage` | `scripts/seed_demo.py`, `scripts/seed_hebbian.py`, `brainstem/stage_builder.py` (+ all of `usd_lite/`) | 6+ | **MEDIUM** — entry point for scripts and test harnesses |
| `InjectionPrim` / `InjectionContainerPrim` | (none in production code) | 1 (`tests/test_injection/test_injection.py`) | **N/A — BLOCKER** — never serialized; "read path" effectively ends at the in-memory dataclass |

(*) `test_hebbian/test_stability.py` is the test that imports `IntakeHistoryPrim`; the module
`hebbian/stability.py` itself was not confirmed present. [AMBIGUOUS: did not enumerate
`hebbian/` directory at file-name level for this report.]

### Modules that need read-tolerant migration logic

If the harness migrates a typeName, the modules below all match prim
type strings either via Python imports (which auto-update) **or** via
literal string comparison in serializer/parser. The string-comparison
sites are the brittle ones:

- **`python/harlo/usd_lite/serializer.py`** — `if type_name == "..."`
  switch in `_BlockParser.parse()` (lines 388–403) and matching emit
  helpers `_serialize_*`. **This is the canonical migration site.**
- **`python/harlo/migrate_v7.py`** — already a migration script
  for a previous version; will need updating in lockstep with any
  schema rename.
- **`python/harlo/brainstem/stage_builder.py` + `adapters.py`** —
  central construction/adaptation layer; touches the most prim types
  by import. Pure-Python imports update automatically on rename, but
  any string-keyed dispatch should be checked.

### Modules that read `.usda` files via *non-USD-Lite* code paths

[AMBIGUOUS] Did not exhaustively confirm whether anything outside
`usd_lite/` opens an `.usda` file directly (e.g. via `pxr.Usd.Stage.Open`
or a different parser). On a quick survey: no `pxr` imports found,
no other `.usda` parsers found. Read paths appear to flow through
`usd_lite.parse()` only. **If the harness will share data with
external tools (e.g. a Houdini USD inspector or Moneta), this needs
re-checking before migration**, because external readers using real
USD will see the literal `def TracePrim "..."` syntax and try to
resolve `TracePrim` against their own schema registry — which is
exactly the collision risk §5 addresses.

---

## Section 5 — Plugin Registration Footprint

### Current state

**There is no `plugInfo.json`, no schema plugin, and no USD plugin
registry in this repo.** Verified by:

- `**/plugInfo.json` glob → 0 matches.
- `import pxr` / `from pxr` grep → 0 matches.
- `Sdf.Schema`, `UsdSchemaRegistry`, `usdGenSchema` grep → 0 matches.

USD-Lite's "registration" is **implicit, dispatch-table style**:

- The writer (`usd_lite/serializer.py:244-265` `serialize()`) hardcodes
  one emit call per known root-level type.
- The reader (`usd_lite/serializer.py:367-405` `_BlockParser.parse()`)
  matches incoming type tokens against a hardcoded `if/elif` chain.
- Unknown types fall through both paths silently (the parser's catch-all
  at line 364–365 `# Skip unknown lines` will skip mismatched blocks).

There is no version field on the format itself; the `#usda 1.0` header
is the OpenUSD format-version magic, not a Harlo schema version.

### Fallback behavior

- **On unknown type at parse time:** silently dropped (the dispatch
  switch has no `else` branch; the type is consumed by
  `_parse_attrs_and_children` but its data isn't built into any
  `BrainStage` field).
- **On missing optional fields:** filled with dataclass defaults
  (`MultipliersPrim.from_dict` line 354–361, etc.).
- **On unknown enum value:** raises `ValueError` from the `Enum(value)`
  call. This is the closest thing to `allowedTokens` enforcement and
  it's a runtime-only check.

### Moneta plugin-sharing collision analysis

[AMBIGUOUS — primary input not in repo.] If "Moneta" is a separate
project that:

1. Uses **real OpenUSD** (i.e. `pxr.Usd`), and
2. Registers a schema plugin via `plugInfo.json` declaring types named
   `TracePrim`, `BrainStage`, `CompositionLayerPrim`, etc., and
3. Shares filesystem space or `PXR_PLUGINPATH_NAME` with Harlo when
   loaded by a third tool…

…then yes, there would be a literal `typeName` collision because
USD-Lite emits *the exact same text tokens* into `.usda` files that
real USD would interpret as schema references. Real USD would try to
resolve them against Moneta's plugin and could either succeed (with
Moneta's semantics, not Harlo's) or fail loudly.

Inside the Harlo repo as it stands today, no such collision is possible
because **no real USD runtime ever touches Harlo's `.usda` output** —
the regex parser in `usd_lite/serializer.py` is the only consumer.

The harness should validate this assumption by listing Moneta's
declared types (its `plugInfo.json` is needed) and intersecting with
the Section 1 inventory before any migration is staged.

### What "plugin registration" looks like if the harness adopts real USD

If the harness's eventual goal is to convert USD-Lite → real OpenUSD
codeless schemas, the migration would create:

- A `plugInfo.json` in a new `schema/` (or similar) directory.
- A `schema.usda` with `class TracePrim` / `class BrainStage` /
  etc., each carrying typed attribute definitions.
- A `generatedSchema.usda` produced by `usdGenSchema --codeless`.

None of these exist today. **No file in the repo would need to be
*moved* — only new files written.** That makes the migration
additive on the schema side; the destructive-edit risk lives entirely
in the writer/reader replacement step (replacing the regex parser
with `Usd.Stage.Open`) and in any custom-codec migration (the hex
SDR encoding must be ported to a USD-supported attribute type or
sidecarred).

---

## Open Questions for the Harness Draft

These are not surgery proposals — they are gaps the harness session
will need to resolve before any code is written:

1. **What is "Moneta" in this context?** Sibling repo? Parallel package?
   External tool? Without its `plugInfo.json` (or equivalent) the
   collision question cannot be answered.
2. **Is the migration target real OpenUSD codeless schemas, or a
   versioned evolution of USD-Lite?** The recon supports either, but
   the cost profile is very different. Real USD requires plugin
   registration and a runtime swap; USD-Lite v2 just needs a serializer
   bump and a `migrate_v7.py`-style script.
3. **`InjectionPrim` / `InjectionContainerPrim` — finish or evict?**
   They're declared and instantiated on `BrainStage` but never
   round-trip to disk. Pre-existing tech debt that any migration step
   must take a position on.
4. **`data/stages/cognitive_twin.usda` — reformat or evict?** Uses
   `def Scope` typeNames and references the old package path. Likely
   stale demo data from before the package rename.
5. **JSON-as-string blob attrs (`dict`, `list` in the emitter) —
   tolerate or migrate to typed attrs?** Affects `TracePrim`,
   `CompositionLayerPrim`, `IntakeHistoryPrim`. They're the biggest
   "not really USD" smell in the schema.

---

*End of recon. No surgery proposed — that's the next session's job.*
