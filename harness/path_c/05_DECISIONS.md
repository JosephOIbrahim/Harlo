# Path C Harness — Locked Decisions

**Status:** Mile 1 closer &nbsp;|&nbsp; **Authority:** supersedes
`[NEEDS DECISION]` markers in 01–04 &nbsp;|&nbsp; Date: 2026-04-28

These five decisions resolve every open flag from the Mile 1
package. Mile 2 execution treats them as binding. Any conflict
between this file and 01–04 is resolved in favor of this file.

---

## D1 — Surgery wall-clock cap

**Decision:** Mile 2 surgery has a hard cap of **2.5 weeks**.
If Mile 2 is not complete by **2026-05-15**, halt and replan.

**Rationale:** Send window is 2026-06-02 → 2026-06-16.
Steps 4 (ComfyCozy × Moneta demo), 5 (benchmark), and 6
(Mile 2 stretch) need their own runway after Step 3 closes.
Letting Step 3 consume more than 2.5 weeks starves the rest
of the stack. Halting at the cap protects the send window.

**Supersedes:** `[NEEDS DECISION]` in `01_KICKOFF.md` §6.

---

## D2 — IsA hierarchy design

**Decision:** IsA hierarchy is **parallel-to-containment**.
The hierarchy declared in `schema/schema.usda` mirrors the
containment structure documented in
`recon/harlo-schema-recon.md` §3.

**Rationale:** Recon §3 already mapped containment cleanly.
Reusing that structure as the IsA frame minimizes novel design
surface, reduces ways to be wrong in Phase 1, and keeps the
mental model consistent between persistence and runtime tiers.
Independent IsA design is a Mile-2-doesn't-recover-from-cheaply
risk; not worth the optionality.

**Implication for Phase 1:** Architect produces IsA tree by
walking recon §3's containment graph. Each container becomes
a parent type; each child relationship becomes an IsA edge
where it makes semantic sense, otherwise a typed attribute or
relationship.

**Supersedes:** `[NEEDS DECISION]` in `03_HANDOFF.md` Phase 1.

---

## D3 — Moneta typeName collision check — source of truth

**Decision:** **Moneta's `plugInfo.json`** is the canonical
source of truth for collision checking. Phase 1 reads
Moneta's `plugInfo.json` directly from Moneta's repo path
(local filesystem) and intersects declared typeNames with
Harlo's 21-prim inventory.

**Rationale:** Moneta is a sibling repo, not a dependency.
There's no published artifact to consume. Reading the file
in place is the only authoritative check.

**Pre-Mile-2 prerequisite:** Confirm Moneta repo path is
accessible to the Mile 2 session. If Moneta lives outside
`C:\Users\User\` or is on a different machine, surface that
before Mile 2 begins. Halt-and-recover applies.

**Supersedes:** `[NEEDS DECISION]` in `03_HANDOFF.md` Phase 1.

---

## D4 — Sync policy for the three orphan prims

**Decision:**

| Prim | Sync policy |
|---|---|
| `InjectionPrim` | **N/A — see D5** |
| `InjectionContainerPrim` | **N/A — see D5** |
| `InquiryPrim` | **checkpoint** |
| `MotorPrim` | **write-through** |

**Rationale:**

- `InquiryPrim`: DMN hypothesis state. Not hot-path, no
  durability requirement mid-session. Checkpoint is the
  cheapest policy that preserves cross-session continuity.
- `MotorPrim`: motor gate state. Every gate transition is
  consequential and should be durable immediately. Writes are
  rare enough that write-through doesn't risk hot-path
  regression.
- `InjectionPrim` / `InjectionContainerPrim`: resolved by D5.

**Supersedes:** `[NEEDS DECISION]` in `03_HANDOFF.md` Phase 3.

---

## D5 — InjectionPrim: evict from disk, retain in-memory

**Decision:** **Evict `InjectionPrim` and
`InjectionContainerPrim` from `schema.usda`.** Retain the
dataclass definitions and the `BrainStage.injection` field in
the runtime tier. Injection state is **session-scoped, not
persisted**.

**Rationale:** Saying "evict" without qualification risks
ripping out the dataclass entirely, which would break
`/inject` command flows at runtime. Injection state is used
*within* a session (microdose modulation, classical mode
perspective shift, etc.); it doesn't yet need to survive
across sessions. Until cross-session injection persistence is
designed (does microdose decay across sessions? does
classical mode persist?), forcing a half-baked persistence
shape into Path C widens scope without strategic reason.

**Implications:**

- `schema/schema.usda` does not declare `InjectionPrim` or
  `InjectionContainerPrim`
- `python/harlo/usd_lite/prims.py` retains both dataclasses
  unchanged
- `BrainStage.injection` field stays in `usd_lite/stage.py`
- Phase 5 documents this decision; no orphan-prim surgery
- A tracking issue is filed: **"InjectionPrim cross-session
  persistence — design decision deferred until post-Step-6"**

**Supersedes:** `[NEEDS DECISION]` in `03_HANDOFF.md` Phase 5
and the stress-test request in `04_DEEP_THINK_BRIEF.md` §3.5.

**Note for Deep Think reviewer:** This decision is locked.
Stress-test §3.5 in `04_DEEP_THINK_BRIEF.md` should now read
as "stress-test the *eviction* decision, not the
finish-vs-evict fork." Reviewer is welcome to flag risks of
session-scoped injection state, but should not propose
re-opening the persistence question for Path C.

---

## Decision summary table

| # | Decision | Authority |
|---|---|---|
| D1 | Surgery wall-clock cap = 2.5 weeks; halt 2026-05-15 | KICKOFF §6 |
| D2 | IsA hierarchy = parallel-to-containment | HANDOFF Phase 1 |
| D3 | Moneta `plugInfo.json` = collision source of truth | HANDOFF Phase 1 |
| D4 | InquiryPrim → checkpoint; MotorPrim → write-through | HANDOFF Phase 3 |
| D5 | InjectionPrim evicted from disk, retained in memory | HANDOFF Phase 5 + Deep Think §3.5 |

---

## Mile 1 closes with this file

When `05_DECISIONS.md` is committed alongside `01–04` in
`harness/path_c/`, Mile 1 of Step 3 (Harlo codeless schema
surgery) is complete. Next: send `04_DEEP_THINK_BRIEF.md`
(updated by D5's stress-test note) to external reviewer.
Mile 2 begins after the reviewer verdict returns.

*End of decisions.*
