# Design — Biometric-Driven macOS Ambient Effectors

- **Date:** 2026-06-19
- **Status:** Approved (brainstorm) — pending spec review
- **Branch:** `review/p0-seam-fixes-2026-06-18`
- **Depends on:** v0.2.0 (HealthBridge/XPC + HarloPulse biometric loop), `AllostasisTracker`
  (incl. respiratory-rate scoring, `fe94e8e`), the Motor Cortex (`premotor` /
  `basal_ganglia` / `executor`, currently inert).

---

## 1. Problem & Goal

Harlo now ingests live biometrics (HR · HRV · RR · sleep · …) through the
`biometric_barrier` and derives a cognitive state (NORMAL / DEPLETED / RED).
Today that state only informs *coaching* and *motor gating*. The goal is to let
that state **act on the host OS** — e.g. when sleep + live signals say you're
depleted, the screen warms and winds down — **without** violating Harlo's
inhibition-default, consent-gated, local-first contract.

This is the **first real effector** for the Motor Cortex on macOS.

## 2. The Apple Constraint (why this architecture)

macOS has **no public API** for a third-party app to set Screen Time / Downtime,
Focus, Night Shift, or brightness:

- The Screen Time API (`FamilyControls` / `ManagedSettings` / `DeviceActivity`)
  is **iOS/iPadOS-only** and parental-controls/MDM-scoped.
- Focus / Night Shift / brightness have **no public setter**; private frameworks
  (`CBBlueLightClient`, `DisplayServices`) exist but are App-Store-rejected,
  fragile across OS versions, and need a non-sandboxed helper.
- The **sanctioned** surface is **Shortcuts + App Intents**: an app *vends* a
  signal/intent; a user-authored Shortcut *performs* the change.

So the honest architecture is **Harlo produces the signal; actuation happens
through user-authorized Shortcuts (or, opt-in, a direct helper)** — never a
silent OS override. The non-sandboxed daemon can shell out to `/usr/bin/shortcuts
run "<name>"`, which is the clean Tier-2 bridge and sidesteps all entitlement
problems.

## 3. Architecture — rides the existing Motor Cortex

No new motor framework is needed for Phase 1. The effector plugs into machinery
that already exists:

- `executor.register_handler(action_type, handler)` — a handler registry.
- `executor.execute_one(action, session_state, consent_state)` — RED-halts
  (Rule 28), runs `basal_ganglia.gate()`, then dispatches to the handler.
- `premotor.create_plan(intent, raw_steps, *, is_depleted)` — builds an
  `ActionPlan`, computing each step's consent level from `action_type` +
  reversibility (Rule 29).
- `consent.get_consent_level` / `effective_consent_level` / `ConsentState`.

```
biometric_ingest  (router, event-driven — Rule 1, no polling)
  └─ AllostasisTracker → is_depleted() transitions False→True
       └─ premotor.create_plan(intent="ambient_wind_down", reversible=True)
            └─ executor.execute_one()
                 ├─ cognitive_state == "RED"? → HALTED (Rule 28)   [nudge-only]
                 ├─ basal_ganglia.gate()  → the 5 checks, inhibition-default
                 └─ DISINHIBIT → handler "display_warmth" (etc.)
                      └─ TIERED BACKEND: nudge | shortcuts run | direct-helper
```

## 4. The Ownership Model — three bands

The split is not by *mechanism* but by **what Harlo is allowed to own**:

- **Tier 2** — Harlo owns the **WHEN**, you own the **WHAT**. Harlo fires the
  trigger; your Shortcut decides what happens.
- **"Harlo decides"** — Harlo owns **WHEN and WHAT**, inside a tight envelope.
- **Locked** — Harlo owns **neither**; explicit consent each time, or never.

### The five-part test for "Harlo decides"

A capability may be owned end-to-end by Harlo only if it passes **all five**:

1. **Reversible** — can be undone.
2. **Self-reverting** — *should* auto-undo when the state clears.
3. **Ambient** — touches only your senses, not your workflow or inbox.
4. **Zero social blast** — no one else experiences the change.
5. **Cheap false-positive** — if Harlo is wrong, undoing is a shrug.

Fail any one → **Tier 2**. Touches other people / irreversible → **Locked**
(Rule 25). This test is *precisely the carve-out that makes an action safe to
take in a depleted state* — see §8.

### Mapping onto `ConsentLevel`

| Band | `ConsentLevel` | Fires when DEPLETED? | Safety source |
|---|---|---|---|
| Harlo decides | `AUTONOMOUS (0)` | yes, no per-action consent | the four rails (§5) + capability opt-in |
| Tier 2 | `PER_ACTION (2)` | yes, with consent (nudge-to-confirm or pre-grant) | user authored the Shortcut |
| Locked | `LOCKED (3)` | never | Rule 25 — structural |

`AUTONOMOUS` is the only level Rule 27 will **not** escalate when DEPLETED
(it bumps `SESSION→PER_ACTION`), so it is the correct home for actions we *want*
Harlo to take precisely when depleted. Reversible actions are also exempt from
the Rule 29 irreversible bump. See §8 for the semantic justification.

### Starter partition (Phase 1 defaults)

| Capability | `action_type` | Band | Why |
|---|---|---|---|
| Display warmth / Night Shift | `display_warmth` | Harlo decides | reversible · ambient · self-reverts · no social blast |
| Gentle brightness cap (≤ ~70%) | `brightness_cap` | Harlo decides | same, bounded magnitude |
| Dark Mode (evening) | `dark_mode` | Harlo decides | reversible · ambient |
| Enable a Focus | `set_focus` | Tier 2 | *which* Focus + allowances is personal |
| Screen Time Downtime | `start_downtime` | Tier 2 | which apps to block is personal; interrupts work |
| Mute / route notifications | `mute_notifications` | Tier 2 | only you know what's urgent |
| Wind-down routine (Hue, music, reminders) | `wind_down_routine` | Tier 2 | personal orchestration |
| Auto-reply / "I'm resting" | `auto_reply` | Locked | other people experience it (Rule 25) |
| Decline / silence calls | `decline_calls` | Locked | social |
| Move/cancel others' calendar events | `modify_others_calendar` | Locked | social + ~irreversible |

## 5. The Four Safety Rails (for "Harlo decides")

1. **Self-revert contract** — record the prior value, apply a *bounded* change,
   and **auto-restore** when DEPLETED clears or a max duration elapses.
   Autonomous changes are **leases, not commits**. The revert obligation is
   persisted (see §7) so a later short-lived daemon process honors it (Rule 31
   spirit). Event-driven on the next `biometric_ingest` — Rule 1 holds.
2. **Bounded magnitude** — a notch warmer, not max; 70%, not 10%. Bounds are
   constructor/profile params (like `hr_red_bpm`).
3. **Announce + one-tap undo** — every autonomous change surfaces
   `[keep] [undo] [stop doing this]`.
4. **Back off on override** — if you manually re-brighten after Harlo dimmed,
   Harlo reads it as a **rupture (S3)**, does not re-apply, and lowers
   confidence. Three strikes → **de-compile the reflex** (Rule 32).

## 6. Tiered Actuation Backend

A single handler per `action_type` resolves to the highest tier available,
falling back gracefully. New module: `python/harlo/motor/effectors/macos.py`.

| Tier | Mechanism | Motor level |
|---|---|---|
| 2 (default for actuation) | `/usr/bin/shortcuts run "<name>"` (user-authored) | per-action consent |
| 3 (opt-in, non-sandboxed build only) | direct via private-framework helper | structural opt-in |
| 1 (fallback) | coach line / `UNUserNotification` nudge | not a gated motor action |

A **nudge is the coach talking, not a gated motor action**, so Tier 1 is always
available — including the RED recovery menu.

**Band selects mechanism (ownership ≠ mechanism).** The §4 *band* decides which
mechanisms a capability may use; the table above is the *mechanism* ladder. The
real distinction is **who authors the Shortcut's content**:

- **"Harlo decides"** band → a **Harlo-defined** Shortcut (Harlo authors the
  content — e.g. "warm the display", a universal action) in the default build,
  or the direct helper when the user opts into the non-sandboxed build. Harlo
  owns the *what*.
- **Tier-2** band → the **user-defined** named Shortcut (the user authors the
  content — which Focus, which apps). Harlo owns only the *when*.
- **Locked** band → nudge only; never actuates.

Both actuating bands fall back to a Tier-1 nudge when their mechanism is
unavailable (no Shortcut installed, helper absent). So Phase 1's `display_warmth`
actuates via a Harlo-defined "warm display" Shortcut in the default build.

## 7. Triggering & Reverting (event-driven, Rule 1)

- **Trigger:** edge-triggered in `router._handle_biometric_ingest` on the
  `is_depleted()` False→True transition (compare persisted prior state). Never
  level-triggered (would re-apply every sample).
- **Apply:** build a one-step `ActionPlan` (Rule 24) and `execute_one`.
- **Revert obligation:** persisted alongside the derived modulation verdict
  (extend `modulation/state.py` / `state_store.py` with a `pending_reverts`
  record: `action_type`, `prior_value`, `applied_at`, `max_duration`). Raw
  biometric values are **never** stored (Rule 9) — only the prior *setting*
  value and derived state.
- **Revert** fires at the FIRST of: state recovered (`is_depleted()` False on a
  later `biometric_ingest`) · `max_duration` (90 min default) elapsed · user
  override detected · **session teardown** (Rule S6 DMN hook) · **next daemon
  startup** with an already-expired lease. The inverse effector runs and the
  obligation clears. Tier-2 reverts are the user's Shortcut's responsibility (or
  a paired "undo" Shortcut); "Harlo decides" reverts restore the recorded prior
  value. A setting is never left silently changed across sessions.

## 8. Constitutional Compliance

- **Rule 1 (0W idle):** trigger + revert are event-driven off `biometric_ingest`;
  no polling, no timers, no background threads.
- **Rule 9 / ADR-0001:** raw biometrics never leave the Modulation Layer; the
  effector consumes only the *derived* state. Gated behind a profile flag
  `ambient_effectors_enabled` (**default OFF**, per-capability opt-in — mirrors
  the biometric default-OFF pattern).
- **Rules 23/26:** every actuation goes through `basal_ganglia.gate()`, always,
  even when compiled as a reflex.
- **Rule 25 (Level 3 structural):** the social/irreversible band is `LOCKED`
  and never opens.
- **Rule 27 vs the feature (the key tension):** Rule 27 says DEPLETED should make
  Harlo *more* cautious. The five-part test is the reconciliation — a reversible,
  self-reverting, bounded, non-social ambient action is *care, not risk*; it is
  the **only** class safe enough to take in a depleted state. These effectors
  register at `AUTONOMOUS(0)`, which Rule 27 leaves un-escalated; everything
  consequential stays `PER_ACTION`/`LOCKED` and is escalated as Rule 27 intends.
- **Rule 28 (RED kills motor):** enforced for free — `execute_one` returns
  `HALTED` when `cognitive_state == "RED"`. RED → nudge-only recovery menu.
- **Rule 29 (reversibility):** "Harlo decides" effectors are `reversible=True`,
  so they are not bumped; an irreversible variant would auto-promote to
  `PER_ACTION` (Tier 2).
- **Rule 31 (plan persistence) / Rule 32 (reflex zero-tolerance):** the revert
  obligation persists across activations; an effector failure or three user
  overrides de-compile the reflex back to a nudge.
- **Semantic note on `AUTONOMOUS`:** today its docstring reads "read-only, no
  side effects." Phase 1 broadens it in practice to "no *net* side effects
  (self-reverting) **or** read-only," justified by the four structural rails.
  Phase 2 may formalize a dedicated `AMBIENT` level if the overload proves
  uncomfortable (see §10).

## 9. New Components & Interfaces

- `python/harlo/motor/effectors/__init__.py`, `effectors/macos.py` — the tiered
  backend + handlers registered via `register_handler(...)`.
- `consent.py` — add the new `action_type`s to `_ACTION_CONSENT_MAP` at the
  bands in §4.
- `modulation/state.py` / `state_store.py` — `pending_reverts` persistence.
- `daemon/router.py` — the edge-triggered hook in `_handle_biometric_ingest`.
- `config/default_profile.yaml` — `ambient_effectors_enabled` (default OFF),
  bounds, and a Shortcut-name map for Tier-2 capabilities.

## 10. Phased Roadmap (the agreed 2 → 3 → 1 ordering)

- **Phase 1 — live capacity → ambient (this spec's v1):** prove *one*
  "Harlo decides" effector (`display_warmth`) + *one* Tier-2 effector
  (`set_focus` via a named Shortcut), edge-triggered on DEPLETED, with the four
  rails and self-revert. Smallest end-to-end slice.
- **Phase 2 — extract the effector framework + graduated autonomy:** generalize
  the backend into a capability registry; introduce **graduated autonomy** —
  every capability starts as a Tier-1 nudge and *earns* promotion to "Harlo
  decides" via the reflex curve (10-rep consolidation, Rule 12) **iff** it
  passes the five-part test; social/irreversible capabilities are Amygdala-locked
  (Rule 7) and never graduate. Optionally formalize an `AMBIENT` consent level.
- **Phase 3 — sleep → evening wind-down:** a *seed-driven* capability
  (`wind_down`) on the Phase-2 framework — the morning `biometric_prior` sleep
  signal schedules an evening wind-down. The original example, now riding a
  mature substrate.

## 11. Testing Strategy (TDD)

- Gate inhibits by default (no opt-in → no actuation).
- DEPLETED False→True fires the `display_warmth` handler (edge, not level).
- RED → `execute_one` HALTED → no actuation, nudge only.
- No named Shortcut configured → Tier-2 falls back to a Tier-1 nudge.
- Self-revert: state recovers → prior value restored; obligation cleared.
- Back-off: simulated user override → no re-apply; three overrides de-compile.
- Locked capability never disinhibits regardless of consent state.
- Rule 9 grep stays green (no `biometric` in elenchus/bridge; no raw values in
  the revert store).

## 12. Non-Goals (YAGNI)

- No graduated autonomy in v1 (Phase 2).
- No direct (Tier 3) brightness/Night-Shift control in the default sandboxed
  build; opt-in only, documented separately.
- No iOS effectors (HarloPulse stays read-only for now).
- No multi-step effector chains (Rule 24 — one action at a time).

## 13. Resolved Decisions (CTO)

- **Tier-2 UX → nudge-to-confirm by default.** The nudge IS the PER_ACTION
  consent prompt. A per-capability pre-grant lives in `default_profile.yaml` for
  power users; otherwise autonomy is *earned* via the reflex curve in Phase 2
  (graduated autonomy), never auto-granted in v1.
- **Lease duration → state-recovery first, 90-minute backstop.** Primary revert
  is `is_depleted()` clearing; a 90-min cap (configurable, ~one ultradian cycle)
  bounds a stuck lease, and revert also fires on session teardown and next daemon
  startup (§7). A setting is never left silently changed across sessions.
- **Transparency → notification with `[keep] [undo] [stop]` at apply-time** for
  v1 (satisfies rail #3). A persistent menu-bar indicator is deferred to Phase 2,
  when autonomy is graduated and a standing status surface is warranted (YAGNI).
