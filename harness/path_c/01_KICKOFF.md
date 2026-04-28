# Path C Harness — Kickoff

**Mile 1 — Package authoring** &nbsp;|&nbsp; Date: 2026-04-28 &nbsp;|&nbsp; Send window: 2026-06-02 → 2026-06-16

---

## 1. Mission

Execute codeless schema surgery on Harlo following the **Path C
(Fabric) pattern**: real Pixar OpenUSD becomes the canonical
persistence layer (codeless `schema.usda`, `plugInfo.json`, `.usda`
files via `pxr.Usd.Stage`), while the existing USD-Lite engine is
preserved as the in-memory runtime tier for hot-path reads. Surgery
substrate-unifies Harlo with sister project Moneta (v1.2.0-rc1) so
both projects share the OpenUSD persistence vocabulary without
colliding on `typeName`. Send window opens 2026-06-02 and closes
2026-06-16; this harness governs Miles 2–3 inside that window.

---

## 2. Why Path C

- **Path A (mock real USD as a USD-Lite facade) compromises P1
  patent CIP framing.** The patent claims a real-USD persistence
  embodiment; a facade undermines public-embodiment claims.
- **Path B (full transplant — `pxr` replaces USD-Lite outright)
  detonates 1,140 tests.** Harlo is read-biased; subprocess IPC into
  a real USD stage blows hot-path latency on every read. Test repair
  cost alone is multi-week.
- **Path C preserves both invariants.** Real USD as canonical truth
  keeps the patent claim defensible; the in-memory tier keeps tests
  green and hot-path latency untouched. The cost moves into a
  sync-layer design problem (Phase 3), which is bounded.

---

## 3. The Fabric Pattern

```
+-----------------------------------------------------------------+
| PERSISTENCE LAYER  (canonical truth)                            |
|                                                                 |
|   real OpenUSD                                                  |
|   - codeless schema (no usdGenSchema C++ wrappers)              |
|   - schema/plugInfo.json registers the harlo namespace          |
|   - schema/schema.usda declares 21 prim types, IsA,             |
|     allowedTokens enums                                         |
|   - .usda data files written/read via pxr.Usd.Stage             |
+-----------------------------------------------------------------+
                ^                                  |
                |  sync at boundaries              |
                |  (write-through / write-behind / |
                |   checkpoint, declared per prim) |
                |                                  v
+-----------------------------------------------------------------+
| RUNTIME LAYER  (hot-path reads)                                 |
|                                                                 |
|   USD-Lite engine (existing; preserved in shape)                |
|   - python/harlo/usd_lite/* unchanged shape                     |
|   - sub-millisecond in-memory reads                             |
|   - 1,140 tests stay green                                      |
+-----------------------------------------------------------------+
```

The boundary between layers is the only place `pxr.Usd` is touched.
Runtime tier never imports `pxr`. This is what makes the optional
`[substrate]` install honest.

---

## 4. Scope — IN

- Codeless schema authoring: `schema/schema.usda`,
  `schema/plugInfo.json`
- IsA hierarchy design (de novo; recon §3 confirmed Harlo has no
  current IsA inheritance)
- `allowedTokens` migration for 5 enum types: `SourceType`,
  `VerificationState`, `RetrievalPath`, `MotorGateStatus`, `ArcType`
- Sync layer: per-prim policy table (write-through / write-behind /
  checkpoint)
- Codec-blocker resolution at the persistence boundary (default:
  `string`-typed sidecar attribute)
- Migration script (`migrate_path_c.py`): read-tolerant, idempotent
- Test repair: minimal, only where runtime tier actually changes
- Cleanup: `InjectionPrim` finish-or-evict; eviction of stale
  `data/stages/cognitive_twin.usda`; fix of asymmetric `arc_type`
  token convention

---

## 5. Scope — OUT

- Runtime tier rewrite — `python/harlo/usd_lite/*` shape preserved
- Hot-path latency regression — must not exceed 10% of Phase 0
  baseline
- ComfyCozy demo (mandatory-stack step 4) — separate workstream
- Benchmark step (mandatory-stack step 5) — separate workstream
- Octavius (mandatory-stack step 6) — separate workstream
- Moneta-side schema work — Moneta owns its own `MonetaMemory`
  registration; this surgery only ensures non-collision
- Patent text changes — IP counsel owns CIP framing

---

## 6. Stop conditions

- 1,140 tests must be green at every gate. Pre-existing red tests
  (if any) are documented in Phase 0 as the baseline; no new red
  test is acceptable at any gate boundary.
- Hot-path read latency must not regress more than 10% relative to
  pre-surgery baseline (Crucible measures at Gate 3 and Gate 6).
- `pxr` install stays optional via `pip install .[substrate]`. Core
  Harlo must import and run without `pxr` present.
- `[NEEDS DECISION: hard wall-clock cap on surgery — e.g. 5 days?
  10 days? — tied to send window 2026-06-02 → 2026-06-16. Default
  proposal: Mile 2 must complete by 2026-06-09 to leave a week of
  Crucible + PR review before close.]`

---

## 7. Mile structure

- **Mile 1 — Package authoring (THIS DOCUMENT, today, 2026-04-28).**
  Write the four-document harness. No surgery. Halt. Joe reviews.
  Adversarial Deep Think pass on the harness itself per
  `04_DEEP_THINK_BRIEF.md`.
- **Mile 2 — Surgery execution.** Claude Code drives Phases 0–6 of
  HANDOFF inside a feature branch `path-c-surgery`. No commits
  during execution. Subprocess CI gate runs at every phase
  boundary. Phase 1 has a mandatory human-review halt before
  Phase 2 begins.
- **Mile 3 — Crucible verification + commit.** Run full test suite,
  latency benchmark, subprocess `SchemaRegistry` gate, round-trip
  fidelity per prim. On all green: single squash commit on
  `path-c-surgery`, push to remote, PR opened against `master` for
  human review.

---

## 8. Pointer to other docs

- `02_CONSTITUTION.md` — eight binding laws, twelve technical
  commandments, three roles (Architect / Forge / Crucible), binary
  phase gates 0–6.
- `03_HANDOFF.md` — phase-by-phase execution plan with Architect
  output / Forge tasks / Crucible gates per phase.
- `04_DEEP_THINK_BRIEF.md` — adversarial review request for an
  external Deep Think reviewer, before Mile 2 begins.
- Upstream context: `recon/harlo-schema-recon.md` — the read-only
  scout report this harness is built on.
