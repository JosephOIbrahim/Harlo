# Path C Harness — Phase 4 Gate Decisions (D15–D19)

**Status:** Phase 4 human-gate closer (gate pre-approved before this session)
**Authority:** explicit documentation of clarifications already accepted via the gate review (`design/mile_2_phase_4_gate_review.md`). NOT new design — codifies what's already on disk.
**Date:** 2026-04-28
**Sibling files:** `05_DECISIONS.md` (D1–D5, Mile 1), `06_DECISIONS_PHASE_1.md` (D6–D14, Phase 1 gate)

These five decisions (D15–D19) explicitly document the Forge clarifications that the human gate review approved. Phase 5 onward treats them as binding.

---

## D15 — propertyOrder via alphabetical declaration order

**Decision:** Schema attributes are declared in **alphabetical order** within each prim type's `class` block in `schema/HarloSchema.usda` and `schema/generatedSchema.usda`. The byte-stability test (`tests/test_path_c/test_persistence_roundtrip.py::test_roundtrip_byte_stability`) enforces deterministic output. Future schema edits MUST maintain alphabetical declaration order.

**Why this is not D11 verbatim:** D11 mandated `propertyOrder = [...]` as customData metadata. USD 26.5's text parser rejects `propertyOrder` at the metadata location with `"propertyOrder" is registered as a non-metadata field`. The body-level alternative (`reorder properties`) is functionally equivalent to declaration order. D15 codifies "we use declaration order, the byte-stability test catches drift."

**Implications:**
- Future TracePrim attribute additions go in alphabetical position (e.g., adding `decay_rate` would slot between `content_hash` and `hebbian_strengthen_mask_hex`).
- The byte-stability test is the regression-defense floor; do not relax it.
- If a future USD version supports metadata-level `propertyOrder`, D15 can be revisited.

**Supersedes:** Phase 1 design §1 + Phase 2 implementation plan §3.1 specification of metadata-level `propertyOrder`. D11's intent (deterministic .usda output) is achieved by D15's mechanism.

---

## D16 — Scalar float types resolve to USD `double`

**Decision:** Every scalar `float` field declared in Phase 1 design §2.3 is bound to USD `Sdf.ValueTypeNames.Double` (64-bit). Every `float[]` field is bound to `DoubleArray`. Future fields default to `double` unless an explicit performance reason for `float32` is documented in a follow-on decision.

**Affected fields** (current schema, Phase 2 application):
- `TracePrim.strength` → `double`
- `CompositionLayerPrim.timestamp` → `double` (timestamp; was already `double` per Phase 1)
- `MultipliersPrim.{surprise_threshold, reconstruction_threshold, hebbian_alpha, allostatic_threshold, detail_orientation}` → `double`
- `SessionPrim.{surprise_rolling_mean, surprise_rolling_std, last_query_surprise}` → `double`
- `InquiryPrim.confidence` → `double`
- `SkillPrim.{first_seen, last_seen, hebbian_density}` → `double`; `growth_arc` → `double[]`
- (and other `double` fields that were already correctly typed in Phase 1)

**Why:** Python `float` is 64-bit. USD `Sdf.ValueTypeNames.Float` is 32-bit. Round-tripping `0.3` through float32 produces `0.30000001192092896` — exceeds `BrainStage.__eq__`'s `rel_tol=1e-9`. The round-trip-fidelity gate would fail for every concrete prim.

**Implications:**
- `.usda` files are 4 bytes larger per scalar than they would be with `float32`. Negligible at expected stage sizes (16 traces × ~1 KB = ~16 KB; double-vs-float adds ~50 bytes).
- Disk-cost / numerical-precision trade-off is documented: precision wins.
- If a future field genuinely benefits from float32 (e.g., embedding storage where 7-decimal precision is sufficient), the field's design entry must explicitly document the override.

**Supersedes:** Phase 1 design §2.3 column "USD type" wherever it said `float`. The Python-type annotation in that column was implicit; D16 makes the USD-type binding explicit.

---

## D17 — TracePrim trace_id sanitization pattern

**Decision:** `TracePrim` has a `string trace_id` attribute (Forge clarification C3). The prim's last path component is a TF-identifier-safe sanitized form of the canonical trace_id. The reader uses the `trace_id` attribute as the dataclass dict key, with prim-name fallback for legacy stages predating C3.

**Sanitization rules** (writer-side, in `python/harlo/usd_lite/persistence/writer.py::_sanitize_prim_name`):
- Empty string → `"t_empty"`
- Each non-identifier character (`isalnum` false and not `_`) → replaced with `_`
- If the result starts with a digit → prefixed with `"t_"`
- Otherwise: returned as-is

**Round-trip semantics:**
- Dataclass `TracePrim.trace_id` = `"26ab7b0812da44b4"` (canonical)
- On disk: prim path = `/Brain/Association/Traces/t_26ab7b0812da44b4` (sanitized — leading-digit prefix); attribute `trace_id = "26ab7b0812da44b4"` (canonical)
- On read: dataclass `TracePrim.trace_id = "26ab7b0812da44b4"` (from attribute, NOT from prim name)

**Mixed-stage compatibility:** stages written before C3 (no `trace_id` attribute) are read by falling back to the prim name. F2 mixed-stage Crucible test (Phase 6) verifies the legacy + new co-existence path.

**Why:** USD requires prim names to match `^[A-Za-z_][A-Za-z0-9_]*$`. Hebbian-seeded fixtures and arbitrary content hashes do not satisfy this. C1/C2-style separations (presentation vs canonical) preserve dataclass shapes and migration fidelity.

**Implications:**
- `co_activations` / `competitions` JSON blobs reference other traces by their *canonical* IDs (not the sanitized prim names). The dispatcher in the runtime tier uses canonical IDs as dict keys, so cross-trace references stay correct.
- A future requirement to enumerate trace_ids by walking the prim hierarchy must read the `trace_id` attribute, not the prim name.
- Sanitization is one-way (lossy: `26ab` and `t_26ab` would both produce `t_26ab` if naively re-sanitized, but the canonical attribute breaks the tie). D17 explicitly does NOT support reversing the sanitized name back to a canonical ID — readers always consult the attribute.

**Supersedes:** Phase 1 design §3 path scheme `/Brain/Association/Traces/<trace_id>` — the angle-brackets now denote a sanitized form, with the canonical ID on the attribute.

---

## D18 — Phase 2–4 Forge clarifications closed

**Decision:** Forge clarifications C1, C2, C3 from `design/mile_2_phase_4_gate_review.md` are accepted as-authored. **No reversion.** The schema files on disk (`schema/HarloSchema.usda`, `schema/plugInfo.json`, `schema/generatedSchema.usda`) and the persistence layer (`python/harlo/usd_lite/persistence/writer.py`, `reader.py`) are canonical.

**Per the gate-review-time approval:**
- C1 (float→double) is locked in as D16.
- C2 (propertyOrder→declaration order) is locked in as D15.
- C3 (`trace_id` attribute) is locked in as D17.

**Implications:**
- Phase 5 onward does not revisit C1/C2/C3.
- Future surgeries that wish to revise these clarifications must file new D-block decisions.

**Supersedes:** none (closes the open clarifications set).

---

## D19 — Constitution Law 2 baseline amends to 1,170

**Decision:** Constitution Law 2 amends from "1,133 tests stay green at every gate" (D14) to "**1,170 tests stay green at every gate**." Phase 5, Phase 6, and Mile 3 must maintain or exceed 1,170. Future surgeries continue the lineage.

**Lineage:**
- Mile 1: 1,140 cited (unverified)
- Phase 0 measured: 1,065 / 48 fail / 17 err / 1 skip
- Phase A resolved: 1,133 / 0 fail / 0 err / 1 skip → **D14 amends Law 2 to 1,133**
- Phase 2 added: +11 (test_path_c) → 1,144
- Phase 3 added: +20 (test_sync) → 1,164
- Phase 4 added: +6 (test_migrate_path_c) → 1,170 → **D19 amends Law 2 to 1,170**
- Phase 5 + Phase 6 expected: +N (Phase 6 adds at least 1 mixed-stage test per F2)

**Implications:**
- A new red test relative to 1,170 is a regression and halts the gate.
- The 1 skip (intentional) does not count toward the 1,170 floor and is not a regression target.
- Mile 3 close summary records the final number; future Mile boundary documents amend D19 in turn.

**Supersedes:** D14's 1,133 baseline.

---

## Decision summary table

| #   | Decision                                                          | Authority                            |
|-----|-------------------------------------------------------------------|--------------------------------------|
| D15 | propertyOrder via alphabetical declaration order                  | C2 / D11 reinterpretation            |
| D16 | Scalar floats → USD `double`                                      | C1                                   |
| D17 | TracePrim `trace_id` attribute pattern                            | C3                                   |
| D18 | Phase 2–4 Forge clarifications (C1/C2/C3) closed                  | gate review approval                 |
| D19 | Constitution Law 2 baseline amends 1,133 → 1,170                  | Phase 4 close measurement            |

---

## Phase 5 + Phase 6 + Mile 3 enter under these decisions

When `07_DECISIONS_PHASE_4.md` is committed alongside the Phase 5
artifacts, Phase 5 may proceed. No Phase 5 work depends on these
decisions being newly made; they document existing reality.

*End of Phase 4 gate decisions.*
