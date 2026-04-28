# Path C Harness — Deep Think Adversarial Review Brief

**Status:** Mile 1 deliverable, requested before Mile 2 begins.
**Distinct from:** the path-selection Deep Think (already answered;
Path C is locked).
**Reviewer:** external Deep Think model (Gemini, GPT-5-Pro, or
peer-reviewer of choice). Reviewer must be independent of the
Mile 2 execution session.

---

## 1. Role

Adversarially review **this harness package** (the four documents
in `harness/path_c/`) before Claude Code begins Mile 2 execution.
The goal is not to re-litigate path selection — Path C is locked —
but to find ways the **harness itself** could fail to enforce its
own laws, miss a load-bearing decision, or produce a surgery that
ships red.

You are explicitly asked to be hostile. Identify:

- Gaps and hand-waves.
- Laws that look binding but have escape hatches.
- Gates that look binary but admit partial-pass interpretations.
- Decisions that should have been made in this package but were
  deferred to Mile 2 in ways that compound risk.
- Phase boundaries that look clean but actually leak state across.

If you cannot find anything wrong, say so explicitly — but a
clean bill of health from an adversarial review is itself a
meaningful signal and we will treat it skeptically.

---

## 2. What's locked, what's open

### Locked (do not re-litigate)

- Path C as the architectural choice (Fabric pattern: real
  OpenUSD persistence + USD-Lite runtime tier).
- Substrate-unification with Moneta as the strategic motivation.
- Send window 2026-06-02 → 2026-06-16.
- Mile structure (1 = package, 2 = surgery, 3 = Crucible + commit).
- The eight Laws and twelve Commandments in
  `02_CONSTITUTION.md`.
- The six Q1–Q6 Moneta verdict adaptations
  (`replace / adapt / drop` status).
- Codec-blocker default = `string`-typed sidecar at the
  persistence boundary.

### Open (Mile 1 surfaced these but did NOT resolve them)

You are asked to stress-test these, not pre-decide them:

1. **Memory hypothesis.** Did Sprint 4 (March 30) `pxr.Usd.Stage`
   work ship and get stripped on April 1, or was it never merged?
   Phase 0 resolves it; if confirmed-shipped, Phase 1 has
   reference material and cost drops.
2. **Sync policy per prim.** Defaults proposed in HANDOFF Phase 3
   (write-through for `SessionPrim` / `GateStatusPrim` /
   `MerkleRootPrim`; checkpoint for `TracePrim` /
   `CompositionLayerPrim` / skill+intake prims; pending for
   `InjectionPrim` / `InquiryPrim` / `MotorPrim`). Architect
   picks final at Phase 3.
3. **Codec-blocker default.** String sidecar by default; typed
   migration documented but deferred. Each blocker may override.
4. **P1 patent CIP framing impact.** IP counsel question, NOT a
   Deep Think question. Listed for completeness; do not weigh in
   on patent strategy.

---

## 3. Specific stress-tests requested

Address each as a numbered subsection in your output.

### 3.1 IsA hierarchy survival under `usdGenSchema --codeless`

The recon (`recon/harlo-schema-recon.md` §3) confirmed Harlo has
no current IsA inheritance — only containment. Phase 1 designs an
IsA hierarchy de novo. The default candidate is "parallel to
containment": `BrainStage` as a typed root, container prims
(`AssociationPrim`, `CompositionPrim`, `ElenchusPrim`,
`InquiryContainerPrim`, `MotorContainerPrim`,
`SkillsContainerPrim`, `InjectionContainerPrim`,
`CognitiveProfilePrim`) as a middle tier, leaf prims as the
bottom tier.

Stress-tests:

- Does this survive `usdGenSchema --codeless` (or the codeless
  registry validation if usdGenSchema is bypassed) cleanly, or
  does containment-driven IsA produce circular references,
  schema conflicts, or attribute name shadowing?
- If the hierarchy needs to be designed independently of
  containment, what are the candidate alternatives, and which one
  minimizes surgery cost?
- Does `BrainStage` belong as an IsA root, a typed `Scope`, or
  outside the schema entirely (i.e., as a session-managed object,
  not a schema-registered prim)?
- `Provenance` is the only non-`*Prim`-suffixed type and is
  emitted only as a nested child of `CompositionLayerPrim`. Should
  it be a typed prim, an `apiSchema`, or inlined as attributes on
  `CompositionLayerPrim`?

### 3.2 Sync policy defensibility

For each prim in HANDOFF Phase 3's table:

- Is the default policy load-bearing for **correctness**, or is
  it a **performance** optimization that could be revised later
  without breaking semantics?
- Identify any prim where the default is **wrong** (e.g., a
  consistency-critical prim misclassified as checkpoint, or a
  high-write-rate prim misclassified as write-through).
- The three `[NEEDS DECISION]` rows (`InjectionPrim`,
  `InquiryPrim`, `MotorPrim`) — propose defaults with rationale.
- Specifically: is the `MotorPrim` candidate of "write-through
  for safety" defensible given Harlo's basal-ganglia gating
  semantics, or does write-through here just mask the real
  question (which is whether motor actions are persisted at all
  before gate approval)?

### 3.3 String-sidecar default for codec-blockers

Per blocker, evaluate whether the string-sidecar default is
actually defensible or whether a typed-attribute path is cheap
enough to do **in this surgery** that we'd regret deferring:

- **Hex SDR on `TracePrim`.** Is `int[]` or `bool[]` (2048
  elements) a real option, or does the .usda text-encoding
  overhead make string-sidecar genuinely better? Quantify if
  possible: what's the .usda file-size delta, and does it
  affect Phase 3 latency?
- **`co_activations` / `competitions` on `TracePrim`.** Real USD
  has `relationship` types (typed prim-to-prim links). Does it
  cost less to migrate now to a proper relationship than to
  keep the JSON-string blob? Note that the current
  encoding is `dict[str, int]` — count, not just link.
- **`CompositionLayerPrim.opinion`.** This is structurally a
  free-form `dict[str, object]`; can it even be typed without
  losing expressiveness? If yes, what shape?
- **`IntakeHistoryPrim.answer_embeddings`.** Float vector;
  arguably typed naturally as `float[]`. Cheap migration?

### 3.4 Phase 1 human-review gate tightness

The HANDOFF declares Joe must sign off on `schema_design.md`
before Phase 2. Listed criteria: IsA shape, `allowedTokens`
choices, codec-blocker default, naming inconsistency
resolution, Moneta typeName collision check.

Stress-tests:

- What would a malicious or sloppy Architect smuggle past this
  gate that the listed criteria don't catch?
- Are there schema decisions that look local but have global
  blast-radius (e.g., choice of `apiSchema` vs `typedSchema`,
  `inherits` vs `references`, `class` vs `over`,
  default-value declarations, `propertyOrder` declarations)
  and aren't on the criteria list?
- Should the human-review gate require subprocess test output
  as a required artifact, or is the binary pass/halt of Gate 1
  enough?
- Is "no collision with Moneta's `MonetaMemory`" verifiable
  without actually loading Moneta's plugin? If not, how should
  the surgery handle the case where Moneta's typeName list is
  not directly inspectable?

### 3.5 `InjectionPrim` finish vs evict

Recommend a position with one-paragraph justification.

Inputs:

- **Current state:** dataclass exists in `prims.py`,
  instantiated as a default field on `BrainStage` in `stage.py`,
  but **never round-trips to disk** — `serializer.serialize()`
  has no `_serialize_injection_*` branch and `_BlockParser.parse()`
  has no `InjectionContainerPrim` branch (recon §2 BLOCKER).
- **Test consumer:** 1 file
  (`tests/test_injection/test_injection.py`).
- **Production consumers:** 0 (recon §4).
- **Schema commitment:** `BrainStage.injection` field exists;
  eviction is a public-API change at the `BrainStage`
  dataclass level.
- **Strategic context:** the Digital Injection Framework is part
  of P1 patent claim coverage; eviction has IP-claim
  implications even if no current code uses the prim on the
  read path.

Tradeoffs to weigh:

- **Finish** preserves the patent claim's public embodiment but
  pays the cost of authoring serializer/parser branches and
  round-trip tests for code with zero current production use.
- **Evict** simplifies the surgery, removes orphan tech debt,
  but breaks the public dataclass shape and may weaken IP
  claim coverage. Re-introducing the prim later is a separate
  CIP cost.

Recommend with rationale; do not punt.

---

## 4. Output format

Single Markdown document. Sections fixed (do not rename or
reorder):

```
## Verdict on harness fitness

(One paragraph. State whether the harness is fit for Mile 2 as
written, fit-with-changes, or unfit. State the single most
load-bearing concern.)

## Stress-test results

### 3.1 IsA hierarchy survival
(your finding)

### 3.2 Sync policy defensibility
(your finding)

### 3.3 String-sidecar default for codec-blockers
(your finding)

### 3.4 Phase 1 human-review gate tightness
(your finding)

### 3.5 InjectionPrim finish vs evict
(your finding)

## Recommended changes before Mile 2

(Numbered list. Each item: file to change, change to make,
one-sentence justification. Order by load-bearingness, heaviest
first.)

## Dealbreakers

(Numbered list, possibly empty. Each item: an issue serious enough
that Mile 2 must NOT begin without resolving it. State precisely
what would change your "fit" verdict if the dealbreaker were
fixed.)
```

Halt at end of document. Do not propose Mile 2 surgery actions —
that's not your scope. Do not write code. Do not produce
`schema.usda` or `plugInfo.json` content; the harness defers
those to Phase 1, and pre-deciding them is itself a finding to
flag, not a service to provide.
