# Mile 2 — Phase 1 Crucible Verification

**Role:** Crucible (adversarial verification) &nbsp;|&nbsp; **Date:** 2026-04-28
**Phase:** 1 — Schema authoring (design-only this session)
**Branch:** `harness-path-c`

Phase 1 is design-only this session. Crucible verifies the **design
artifact's structural completeness** against the session override
gate criteria, plus adversarial review of the design itself.

---

## Verdict at a glance

**Phase 1 gate: ✅ PASS — design artifact complete; routes to human gate.**

Three `[NEEDS DECISION]` items deliberately surfaced for human input
(per session override format). Two Phase 0 blockers attached
(B1 environmental, B2 structural) per `verify/mile_2_phase_0_crucible.md`.

---

## Per-criterion grading

### G1. `design/mile_2_phase_1_schema_design.md` exists and contains required content

**Required content (per session override):**

| Required item | Present? | Evidence |
|---|---|---|
| Full IsA tree for all 21 prim types, parallel to containment per D2 | ✅ | §1.1 — explicit ASCII tree; 21 typeNames listed (2 abstract + 19 concrete; the 2 evicted Mile-1 types annotated D5) |
| Per-prim attribute table (USD type, default, optional flag) | ✅ | §2.3 — table per leaf type; §2.2 — container type/path table |
| All 5 enums declared with `allowedTokens` lists | ✅ | §4.1–§4.5 — `SourceType`, `VerificationState`, `RetrievalPath`, `MotorGateStatus`, `ArcType`, all lower-case |
| `plugInfo.json` shape under `harlo` namespace (separate from Moneta) | ✅ | §5 — full JSON skeleton with all 21 types; namespace `"harlo"` separate from Moneta's `"moneta"` |
| Codec-blocker boundary plan: hex SDR + 4 JSON-blob attrs as `string` sidecars; typed-upgrade documented | ✅ | §7 — table per blocker with default plan and deferred upgrade path |
| Collision check: explicit confirmation that none of Harlo's typeNames collide with Moneta's | ✅ | §5.2 — set intersection ∅ documented |
| All trade-offs explicitly named | ✅ | §1.4 (IsA), §9 (cross-cutting trade-off table) |
| All open questions surfaced as `[NEEDS DECISION: …]`, never guessed | ✅ | §10 — 3 markers explicitly listed for human input |

### G2. Subprocess `SchemaRegistry` gate test specified (not executed)

✅ **PASS.** §8.1 contains a complete test outline ready for Phase 2 Forge
to commit verbatim. Test:
- Loads schema in fresh subprocess (Commandment 4 — isolation).
- Iterates all 21 expected typeNames via `Usd.SchemaRegistry`.
- Negative-checks `MonetaMemory` is not present.
- Sanity-checks USD built-in `Xform` is still resolvable (no
  registry corruption).
- 60-second timeout.
- Asserts `OK` in stdout and exit code 0.

§8.2 enumerates what the test guarantees; §8.3 enumerates what it
deliberately doesn't cover (per-attribute correctness, sync policy)
— routed to Phase 2/3 work.

### G3. No `schema/schema.usda`, `schema/plugInfo.json`, or `schema/generatedSchema.usda` written this session

✅ **PASS.** `ls /c/Users/User/Harlo/schema/` returns "No such file or
directory." Phase 1 stayed within design-only scope.

### G4. No commits

✅ **PASS.** `git log harness-path-c..HEAD` shows no new commits since
Mile 1's `4fa190e`. Only the harness Mile 1 commit + un-staged Phase 0/1
artifacts visible.

`git status --porcelain` shows:
- `M pyproject.toml` — Phase 0 substrate-extra addition (un-staged)
- `?? design/` — design artifacts (un-staged)
- `?? forge/` — forge report (un-staged)
- `?? harness/path_c/baseline_latency.json` (un-staged)
- `?? harness/path_c/baseline_tests.txt` (un-staged)
- `?? harness/path_c/memory_hypothesis.md` (un-staged)
- `?? harness/path_c/substrate_pin.md` (un-staged)
- `?? verify/` — verify artifacts (un-staged)

---

## Adversarial review of the design itself

Crucible role is to find weakness, not to confirm. Things I tried to
break:

### Adversarial probe 1 — IsA hierarchy survives `usdGenSchema --codeless`?

The 3-tier hierarchy (`Typed → HarloPrim → {HarloContainer, leaves}`)
uses two abstract bases (`abstractTyped`) and concrete subtypes
(`concreteTyped`). USD codeless schemas support `abstractTyped` per
its `schemaKind` in `plugInfo.json`. Moneta's reference uses
`concreteTyped` for the single class only — Architect is extending
the pattern.

**Risk:** if the codeless path doesn't validate `abstractTyped` cleanly
(e.g., `Plug.Registry` rejects abstract types without a corresponding
`UsdSchemaBase` registration in `bases`), Phase 2 will fail at the
subprocess gate test.

**Mitigation in design:** §5 declares `bases: ["UsdTyped"]` for
`HarloPrim` and `bases: ["HarloHarloPrim"]` for `HarloContainer` —
proper chain back to USD's typed-schema base. This matches USD's own
pattern for declaring abstract base schemas.

**Adversarial verdict:** likely fine, but **specifically untested by
this design.** The Phase 2 Forge subprocess gate is the first time
this gets exercised. If it fails, Architect must re-engage to drop
to a flat hierarchy.

[NEEDS VERIFICATION in Phase 2: that `abstractTyped` codeless types
register correctly via `Plug.Registry().RegisterPlugins()`.]

### Adversarial probe 2 — codec-blocker default leaks runtime tier into persistence?

Commandment 4 says "hot-path reads stay in fast tier" and "no
`pxr.Usd.Prim.GetAttribute()` on the runtime read path." The design
puts the hex-SDR codec invocation in `persistence/writer.py` and
`persistence/reader.py` (§7). Runtime tier never sees the persistence
layer's encoded form.

**Risk:** if the sync layer (Phase 3) accidentally exposes the
`*_hex` / `*_json` attribute names to runtime callers, the codec
boundary leaks.

**Mitigation in design:** §2.3 explicitly says runtime tier uses
dataclass field names (`sdr`, `co_activations`, etc.); only the
persistence layer uses the schema attribute names (`sdr_hex`,
`co_activations_json`, etc.). Sync layer translates.

**Adversarial verdict:** clean separation in spec. Phase 3 must
preserve this; a sync-policy implementation that returns schema attr
names from a runtime read API is a bug.

### Adversarial probe 3 — cross-prim string FK semantics

Three attributes hold string keys to other prims:
`Provenance.session_id`, `TracePrim.co_activations_json` (keys),
`TracePrim.competitions_json` (keys). The design declines to model
these as USD `rel`-typed attributes (§7.1).

**Risk:** USD tooling that follows relationship targets (e.g., a
GUI inspector, or a future migration script that wants to verify
referential integrity) cannot follow string FKs.

**Mitigation in design:** explicitly declared as status-quo
preservation. Future schema migration can introduce `rel` if needed.

**Adversarial verdict:** acceptable for Phase 2. Phase 4 migration
script must explicitly NOT verify FK integrity (it's not modeled).
Future improvement candidate.

### Adversarial probe 4 — what would a malicious Architect smuggle past the human gate?

Things this design doesn't surface to the human review section that a
strict reading might want:
- Choice of `apiSchema` vs `typedSchema`. **Design uses `typedSchema`
  throughout.** Not flagged in the trade-off table; an adversarial
  human could argue some types (e.g., `Provenance`) are better as
  applied API schemas. Crucible flags this for human attention.
- Default attribute values. Several attrs have `—` (no default). USD
  treats these as "absent" rather than zero-init. **Implication:** a
  reader getting `None` for a `float` attr cannot distinguish "default
  zero" from "explicitly missing." Design doesn't address this.
- `propertyOrder`. Not declared anywhere in §5 plugInfo or the design.
  USD has `propertyOrder` metadata. Default ordering may produce
  inconsistent .usda diffs across runs. Phase 2 should declare
  `propertyOrder` in `customData` for deterministic output.

**Crucible additions to the human gate input** (not in §10 of the
design but added here):
- D6: choose `typedSchema` (current design) vs introduce
  `apiSchema` for `Provenance`.
- D7: declare `propertyOrder` for deterministic .usda output.

These are NOT dealbreakers; they're refinements the human should be
aware of. Architect can address in a delta pass after human review.

### Adversarial probe 5 — does this design address Phase 0's B2 baseline blocker?

**No.** B2 (test baseline 1,065 vs claimed 1,140) is a
Constitution-Law-2 problem, not a schema-design problem. The design
correctly does NOT address it. Crucible verifies the routing is
explicit: §11 closes with the human-gate question that includes B2.

---

## Phase 1 gate decision

**Decision: ✅ PASS — Phase 1 design artifact is complete and structurally
sufficient for Phase 2 Forge work, conditional on human resolution of
the [NEEDS DECISION] markers and the two Phase 0 blockers (B1/B2)
attached from `verify/mile_2_phase_0_crucible.md`.**

Phase 1 has no Forge output this session (design-only). Therefore no
implementation to verify; the only verification surface is the design
artifact's completeness, which passes.

Crucible signs Phase 1.

## What happens next

1. Architect role exits.
2. Files in `design/`, `forge/`, `verify/`, `harness/path_c/*.{md,json,txt}`, and the modified `pyproject.toml` are staged (no commit per Commandment 12 + session override).
3. Human reviews the package and answers the questions in §10/§11 of
   `design/mile_2_phase_1_schema_design.md`.
4. Decision tree (per design §11):
   - **Approve as-is** → Mile 2 Phase 2 (Forge implementation) is the
     next session, but only after B1+B2 resolution.
   - **Request changes** → Architect re-engages for delta design.
   - **Escalate to Deep Think** → send to external reviewer per
     `harness/path_c/04_DEEP_THINK_BRIEF.md`.

*End of Phase 1 Crucible verification.*
