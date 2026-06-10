# App Intents Adoption Plan — Harlo × Siri × Apple Intelligence

**Date:** 2026-06-10 · **Source:** WWDC26 "Explore advanced App Intents
features for Siri and Apple Intelligence" (architect's session notes) ·
**Status:** P0 implemented in PR #13; this doc is the decision surface
for P1–P3.

**The strategic frame in one sentence:** App Intents is now BOTH the only
Siri door (SiriKit deprecated at WWDC26) AND Apple's MCP on-ramp — which
means Harlo's MCP tools and its App Intents are **two front doors to the
same spine**, and every entity we define for one should be vocabulary for
both.

---

## 1 · Pattern-by-pattern applicability matrix

Verdicts: **ADOPT-NOW** (P0, shipped in PR #13) · **ADOPT-NEXT** (P1/P2,
planned) · **GATED** (needs privacy/counsel review before any build) ·
**REJECT** (with rationale — these are decisions, not omissions).

| # | Session pattern | Verdict | Harlo application |
|---|---|---|---|
| 1 | `IntentDialog(full:supporting:)` | **ADOPT-NOW** ✅ | Every Pulse intent answers voice-first ("Synced 3 data types… Mac said accepted=12") with a glanceable supporting line ("Synced"). P1: the Mac-side `HarloStatusIntent` speaks burnout state the same way — "You're in YELLOW, 14 exchanges without a break" / "YELLOW". |
| 2 | `$param.requestValue()` clarification | **ADOPT-NOW** ✅ | `TogglePulseTypeIntent` asks "Which data type?" instead of failing. P2: consent-style clarifications for any future actuating intent — but note Rule 23: clarification is UX, **the Basal Ganglia is still the authority**. Siri may ask; the gate still answers. |
| 3 | Enhanced `DisplayRepresentation` (title/subtitle/image) | **ADOPT-NOW** ✅ | `PulseStatusEntity` today. P1: `CognitiveStateEntity` (state + since-when + SF-symbol color ramp GREEN→RED) is the marquee use — the burnout light as a system-wide entity. |
| 4 | Custom snippet views (`ShowsSnippetView`) | **ADOPT-NOW** ✅ | Pulse status card in Siri results today. P1: the **burnout-light snippet** (momentum/burnout/energy mini-dashboard) is the highest-visibility Harlo surface Apple will ever render for us. |
| 5 | Intent donation (`IntentDonationManager`) | **ADOPT-NOW** ✅ (payload-free only) | Manual syncs donated so Siri learns cadence. **Policy line:** Harlo donates *action intents with no content payloads* — never anything carrying trace text, biometric values, or cognitive verdicts. Donation metadata lives in the system; our content does not. |
| 6 | `OwnershipProvidingEntity` (.shared/.public) | **REJECT (by design)** | Harlo entities are constitutionally personal — there is no shared/public cognitive state, ever. Declaring ownership semantics would imply a sharing model Rule 9's philosophy forbids. The correct implementation is its absence. |
| 7 | `IndexedEntity` / `CSSearchableIndex` | **REJECT for traces · GATED for neutral entities** | **Privacy landmine.** Indexing memory traces puts cognitive content into the system-wide Spotlight index — outside Harlo's container, outside the Blood-Brain Barrier, harvestable by anything reading search. This is the App-Intents twin of the D54 lesson (content leaking through a side door). Neutral, content-free entities (the status singleton) could be indexed later, but nothing that carries user content without an explicit architect+counsel gate. |
| 8 | `IntentValueQuery` (structured search → entities) | **GATED** | "Hey Siri, what does Harlo remember about X" is the single most magical demo Harlo could ship — and it routes memory content through the Siri/Apple-Intelligence pipeline. Same gate as #7, plus patent-counsel review (recall mechanics are filed matter). Park until the privacy story is written; revisit with the March-2027 counsel session. |
| 9 | `.system.searchInApp` re-run | **ADOPT-NEXT (P2)** | Needs an app with a search UI. Pulse has none; the Mac menu-bar app (P1) might grow one. Defer until a search surface exists — adopting it before then is ceremony. |
| 10 | Onscreen-awareness annotations (`NSUserActivity` / `appEntityIdentifier`) | **ADOPT-NEXT (P1)** | Annotate Pulse's status screen and the future menu-bar popover with `CognitiveStateEntity` so "add this to my journal" / "remind me about this" ground correctly. Read-only exposure of an entity *identifier* (not content) — privacy-clean. Deferred from P0 only to keep the PR reviewable. |
| 11 | Component-based `displayRepresentations` query | **ADOPT-NEXT (P2)** | Perf optimization that matters once entity lists exist (e.g., per-type trend entities). Premature with one singleton entity. |
| 12 | Entity annotations on notifications / NowPlaying / AlarmKit | **ADOPT-NEXT (P1 for notifications)** | The notifications half is hot: when Pulse (or the Mac app) posts "Harlo says: break time," annotating with the entity lets Siri act on it. NowPlaying is N/A. **AlarmKit is sneaky-relevant**: burst-protocol body-check timers ("20 rapid exchanges — water break") as real system alarms with a `DismissBodyCheckIntent` — fits the coach's enforcement surface. P2. |

**Assistant-schema caveat (applies to everything above):** the session
examples use `@AppIntent(schema: .audio.addToPlaylist)` etc. Assistant
schemas are domain-locked and **Apple ships no coaching/biometrics
domain** — so Harlo uses plain `@AppIntent`/`@AppEntity`, which still get
Siri, Shortcuts, Spotlight, and onscreen awareness. If Apple ever ships a
health/journaling assistant schema, we map our vocabulary onto it then.

---

## 2 · The intent vocabulary (shared across Pulse, Mac, OTTO)

One vocabulary, three surfaces. Entities mirror the MCP tool nouns so
Siri-Harlo and Claude-Harlo speak the same domain:

| Entity | Backing truth | Surfaces |
|---|---|---|
| `PulseStatusEntity` ✅ | Pulse-local state | Pulse (shipped, PR #13) |
| `CognitiveStateEntity` (P1) | `modulation_state` + engine verdict via `harlo status` | Mac menu-bar app, Pulse (mirrored), OTTO |
| `CoachAdviceEntity` (P2) | `coach` MCP tool output (advice line only, no trace content) | Mac, Siri dialog |
| `BiometricTrendEntity` (P2) | derived trend only (load curve, never samples) | Pulse, Mac |

Intents follow the same read/act split as the constitution:
**read intents are free** (status, advice); **act intents route through
the same gates as everything else** — an App Intent that would author a
MotorPrim hits the identical `gate_status="inhibited"` clamp (D52). Siri
is a client, not a privilege level.

---

## 3 · The Mac problem (and the P1 answer)

App Intents metadata is extracted at build time by Xcode tooling — **a
py2app bundle cannot host App Intents.** The Mac play is therefore a
small native shim:

**`HarloGlance`** (P1): a Swift menu-bar app (the scout's "burnout light")
that (a) renders GREEN/YELLOW/ORANGE/RED from `harlo status` (the D60
modulation block finally becomes *perceivable*), (b) hosts the Mac's App
Intents (`HarloStatusIntent` with the snippet view), (c) annotates its
popover for onscreen awareness, and (d) shares its Swift entity
definitions with OTTO — every hour spent here double-counts for the
iOS-27 Siri Extensions work.

Build pipeline note from PR #13's trenches, applies to HarloGlance too:
**explicit `AppIntents.framework` dependency or metadata extraction
silently skips** (autolink is not enough), and **never give xcodegen an
`info:` block for a hand-maintained plist** — it regenerates (overwrites)
the file on every `xcodegen generate`.

---

## 4 · Privacy gates (binding for all phases)

1. **Nothing biometric and no trace content ever enters:** Spotlight
   indexes, donation payloads, snippet views shown on the lock screen,
   or entity display representations. Identifiers and derived verdicts
   only.
2. **IntentValueQuery over memories (#8) and trace indexing (#7)**
   require an explicit architect decision + the patent-counsel gate
   (filed-matter exposure) before a line of code.
3. **Donations are payload-free action intents only** (#5 policy).
4. **Act-intents inherit Rule 23/26** — inhibition-default applies to
   Siri exactly as it applies to the MCP `decision` tool.

---

## 5 · Phased roadmap

| Phase | Scope | Effort | Exit criteria |
|---|---|---|---|
| **P0** ✅ | Pulse intents (PR #13): sync, status+snippet, toggle w/ clarification, donations, shortcuts | done | compiles clean on iOS 26.5 SDK, metadata extracted — **verify on-device once PR merges + architect runs Xcode deploy** |
| **P1** | `HarloGlance` menu-bar app: burnout light + `HarloStatusIntent` + `CognitiveStateEntity` + onscreen-awareness annotations (#10) + notification annotations (#12a) on Pulse | M (1–2 wk) | "Hey Siri, Harlo status" answers with the burnout snippet on the Mac; light visible in menu bar |
| **P2** | `CoachAdviceEntity` + AlarmKit body-check timers (#12c) + component display-representation queries (#11) + searchInApp if Glance grows search (#9) | M | coach advice reachable from Siri; body-check alarm dismissible via intent |
| **P3 (gated)** | Memory surfaces: IntentValueQuery recall (#8), neutral-entity indexing (#7) | L + gates | only after the privacy story doc + counsel session (≤ March 2027) |

**Sequencing logic:** P0 proves the pipeline on the device we control
least (iOS). P1 is where the *product* changes — cognitive state becomes
perceivable at OS level, and the OTTO synergy starts paying. P2 deepens.
P3 is the magic demo, deliberately last because it's the one that can
hurt us done early.

---

## 6 · How this sets Harlo up (CTO summary)

- **Distribution leverage:** Siri/Shortcuts/Spotlight are zero-marginal-
  cost surfaces once the vocabulary exists — the same entities feed the
  MCP Registry listing (scout TOP-5 #1) and the `.mcpb` bundle.
- **The two-door thesis:** Apple is routing its agent story through App
  Intents (MCP on-ramp); Anthropic's runs through MCP. Harlo is natively
  bilingual with ONE spine — almost nobody else in the agent-memory
  field can say that.
- **OTTO synergy:** every entity, every intent pattern, and both build-
  pipeline gotchas transfer directly to the iOS-27 Siri Extensions work.
- **Constitutional differentiation extends to Siri:** "the coach Siri
  can ask but never override" is a *feature claim* competitors without
  an inhibition-default architecture cannot copy.

---

## 7 · ADDENDUM (2026-06-10): Siri code-along learnings

The code-along session refines four §1 verdicts; two became code the same
day (PR #15, verified with a signed device build):

- **`system.*` schemas are not domain-locked** — `system.open` applies to
  any app with entities. Adopted as plain `OpenIntent` (iOS 16+, fits our
  17.0 target without assistant-schema availability): Siri/Spotlight
  entity results now tap-through into Pulse. ✅ shipped
- **Onscreen awareness is literally two modifiers** —
  `.appEntityIdentifier()` for lists, `.userActivity` + `EntityIdentifier`
  for a primary entity. Pulse's status screen now annotates under
  `#available(iOS 18.2)` (`AppEntityAnnotatable` availability per the
  iOS 27 SDK). Pattern #10's "P1" status → shipped for Pulse; Glance/OTTO
  inherit the recipe. ✅ shipped
- **`TransientAppEntity`** — the protocol for momentary, non-queryable,
  non-indexed entities. This is the privacy-aligned shape for the P2
  `BiometricTrendEntity` (derived, momentary, must never be indexed):
  the platform now has a first-class way to say "this entity has no
  lookup path," which is exactly Rule 9's posture.
- **`valueState` (.set(value) / .set(nil) / .unset)** — the idiom for
  optional parameters in update-style intents ("don't change" vs
  "clear"). Required reading for any future Harlo update-intent.
- **AppIntentsTesting framework** — new automated-testing surface for
  intents. Roadmap change: P1's exit criteria gain "Pulse intent tests
  via AppIntentsTesting" (test target + simulator runtime needed; the
  Pulse project currently ships no test target).
- The code-along's centerpiece — `IndexedEntity` + semantic Spotlight
  donation — remains **GATED/REJECTED per §1 #7**: it is precisely the
  content-into-system-index mechanism the privacy gates exist to stop.
  The session demonstrates its power; the power is the problem.
