# TRIAL HARNESS — refactored to first principles
*A long-horizon work loop. Two failure modes, two defenses. Everything else is in service, or it's cut.*

---

## ROOT — the two defenses
Everything below traces to one of these or it's ceremony. The test applies to these two as well.

1. **Nothing advances on unverified state.** — vs *hallucinated completion*
2. **No path is privileged; stalls get reframed, not pushed.** — vs *premature convergence*

> For any rule (including this harness's own): *which defense does it serve?* No answer → cut it.

---

## THE BAR — falsifiability
State the disproof **before** you build. A claim with no disproof is decoration, not progress.
Holds for the whole artifact (SPEC) and for every individual change.

Falsifiability isn't only a bar — it's a **loop exit**. If a disproof you wrote down comes true,
you're done in the failure direction: stop and report. Grinding past it is the convergence trap.

---

## THREE LAWS  (the six old principles, compressed — each maps to a defense)

- **L1 · Verified champion or nothing.**
  One current-best artifact + the exact recipe to reproduce and re-check it. Nothing moves forward
  on state no verifier passed. New work earns its place only by beating the champion on the contract.
  A noisy win gets replicated on a fresh run before you believe it.
  *(absorbs: verifiers-gate-progress, one-champion)*

- **L2 · Kill cheap, remember always.**
  Critique proposals on paper before you build — weak ideas die on the record, free. Killing a built
  branch isn't free; killing an idea is. Log every dead end (`DEAD-END | what | why rejected`).
  Read the log before proposing. Never pay for a dead end twice.
  *(absorbs: critique-before-build, failures-are-memory)*

- **L3 · No privileged path; stall = reframe.**
  More than one viable approach → hold them in parallel and let evidence pick; don't partition once
  and march the partition. A line that stops beating the champion (N tries, no gain) is a *framing*
  problem — reopen, then retire / merge / split / replace it. Pushing harder is the trap.
  *(absorbs: don't-privilege-one-path, stall→reorganize)*

---

## STATE — three files (irreducible)

- **`SPEC.md`** — the contract: Outcome · Acceptance predicates (the checkable bar) · Out of scope ·
  Falsification conditions.
- **`CHAMPION.md`** — current verified best + the exact recipe to reproduce and re-check it.
- **`LOG.md`** — append-only, failures included. Tag dead ends.

> Split these further only when a trial grows large enough to need it — not before.
> Premature splitting is its own scope trap.

---

## THE LOOP — three gates + one engine

    FRAME --> [ engine ]* --> SHIP
                 |              ^
                 +-- reframe on stall;  exit: SHIP (SPEC clears) | FALSIFIED (a disproof fires)

**GATES — cannot be skipped:**

- **FRAME** — restate the brief, tagging each line **ASSERTED** (they said it) / **INFERRED**
  (you're guessing). Write `SPEC.md`. Confirm the contract before anything is built. Never cross on a guess.

- **INTEGRATE + STRESS** — *the gate before SHIP, where hallucinated completion hides.* Pieces passing
  alone does NOT mean the whole passes. Re-run checks at the system level, targeting every seam where
  state crosses a boundary (INTEGRATE); then attack the *realized* artifact with every risk you flagged
  plus the new ones the realized thing introduced (STRESS). Sort findings: showstopper → reopen engine ·
  bounded weakness → document, continue · out of scope → note.

- **SHIP** — report predicate-by-predicate SPEC compliance · how the champion was reached + what was
  abandoned · known limits · checked-vs-not. Produce the deliverable. Ask: ship / iterate / escalate?

**ENGINE — the core cycle, not a march:**

  **PROPOSE → CRITIQUE → BUILD → CHECK**, always against the champion.
  - *Propose* candidate moves; cross-check each against the dead-end log.
  - *Critique* — kill the weak ones now, on paper.
  - *Build* the top survivor: state the change + the verifier you'll run + the effect you expect.
  - *Check* — climb the verifier ladder only as high as the contract demands. Beats the champion?
    Promote (replicate first if noisy), update CHAMPION + LOG. Doesn't? Log it; if the direction's
    exhausted, mark DEAD-END.
  - *Stall* (N, no gain) → stop pushing, reopen Propose, restructure the lines.

  **SKETCH = the engine's seed:** the most compressed end-to-end shape that could satisfy SPEC
  (one file or diagram). That's CHAMPION v0 — weak but real. Name its 3–5 load-bearing pieces + the
  riskiest unknown in each; score confidence 0–1 per predicate.

  > No verifier for a predicate yet? Then **building the verifier is the first engine move** — and
  > sometimes the verifier is the deliverable.

---

## VERIFIER LADDER — climb only as high as the contract demands

1. **Well-formed** — parses / lints / no broken refs — *(mandatory)*
2. **Behaves** — checks written straight from the predicates — *(mandatory)*
3. **Robust** — invariants, edge cases, fuzzing — *(contract-dependent)*
4. **Intent / seams** — satisfies what the contract *meant*; system-level — *(INTEGRATE lives here)*
5. **Adversarial** — stress, scale, failure-mode sim — *(STRESS's artillery)*

Any check can be noisy. A within-noise gain isn't a gain until a fresh run confirms it.

---

## TOPOLOGY — be honest about what you're actually running
A *readout* of how many genuinely independent lines exist — not an ambition setting. Trigger is
**breadth × independence**, not difficulty: a hard problem that's one dependency chain is SOLO.

- **SOLO** *(default — start here)* — one line, serial; you switch between proposing / building /
  critiquing in turn. Discipline is internal: genuinely red-team your own proposals before building;
  keep the log honest because future-you reads it.
- **SIMULATED** — 2–3 independent lines, no launcher. Round-robin attention; report which line you're
  on. Interleaved, not parallel.
- **ORCHESTRATED** — 4+ independent lines + real rework cost + a real launcher. A **handoff**, not
  something one context fakes.

> **Honesty constraint (the load-bearing part):** one context cannot spawn parallel agents. If the
> work wants ORCHESTRATED with no launcher, downshift to SIMULATED and say so — or emit the launch
> spec and stop. Never narrate parallelism you don't have. That's hallucinated progress: the exact
> thing the ROOT forbids.

Orchestration is **deployment detail**, earned only after a SOLO run produces a champion that beats
its seed. Standing it up first is the premature-scope trap your own SPEC would flag. *(The `ant`
managed-agents CLI is the operator for this stage — appendix, not core: each independent line becomes
a declarative agent reading/writing the shared three files; a deterministic outer loop drives them;
resolve claim/lock + log-contention + last-write-wins before launch.)*

---

## ON-RAMP
Paste this, then your brief, then:

    Brief: <your problem here>
    Begin FRAME. Topology: SOLO unless you find ≥2 genuinely independent lines.

FRAME makes you write the contract before anything gets built. That's the point.
