# HealthKit Collaboration Frontier — CTO Report

- **Date**: 2026-06-10 (two days after WWDC 2026)
- **Role**: HealthKit frontier research (MOE domain-research expert)
- **Context**: ADR-0002 (iPhone sidecar / HarloPulse) accepted 2026-06-10; ADR-0001 (Rule 9 amendment) accepted 2026-05-22; D60–D67 (CTO review 2026-06-09)
- **Ships to**: `docs/frontier/healthkit-collaboration-report.md`

---

## Executive Summary

WWDC 2026 (June 8) did **not** ship Health on Mac — macOS 27 "Golden Gate" is a Siri/AI release, and Health-for-Mac remained a community wishlist item (9to5Mac ran the "hopes" piece two weeks before the keynote; no recap mentions it). **ADR-0002's iPhone-sidecar bet is validated by the keynote, not just by D67's empirical check.** HealthKit's 2026 additions are a Workout Zones API and a Menopause API — neither touches Harlo's core, though Workout Zones is a free enrichment for exercise-as-infrastructure coaching.

The single most Harlo-shaped surface remains **HKStateOfMind** (WWDC 2024, iOS 18): a momentary-emotion/daily-mood sample type with a continuous valence scale, ~38 emotion labels, and 18 life-area associations — **readable and writable by third-party apps**, stable for two release cycles, surfaced in Apple's Health app, Journal app, and Journaling Suggestions with per-app attribution. Harlo can both **read** the user's self-logged moods as a Modulation Layer signal and — with a consent gate — **write** its cognitive verdicts back, making Apple Health a system-of-record *mirror* of Harlo's state engine. One architectural inversion applies: there is no Health data layer on any Mac, so all writes must execute on the phone via HarloPulse.

The regulatory ground shifted in March 2026: any app in the Health & Fitness category distributed in the EEA/UK/US must now declare regulated-medical-device status in App Store Connect (new apps immediately; existing apps by early 2027). HarloPulse declares "No" and stays wellness-positioned.

Competitively, the Athlytic/Bevel/Welltory/Gyroscope class is converging on cloud-LLM coaching over HealthKit scores (Gyroscope is explicitly OpenAI-powered). Nobody is local-first, nobody's coach knows the user's *work* state, and nobody has an auditable substrate. Harlo should consume HRV/RHR/sleep **trends** and refuse to compete on readiness-score polish.

---

## 0. WWDC 2026 Headline Scan

What shipped, health-wise, in the OS 27 generation (announced June 8, 2026):

| Item | Detail | Harlo relevance |
|---|---|---|
| **No Health app for Mac** | macOS 27 "Golden Gate" = Siri AI, design refinements, Apple Intelligence. No Health/HealthKit data layer on Mac. | **Confirms ADR-0002.** HarloHealthBridge stays dormant (D63/D68 gating unchanged). |
| **HealthKit Workout Zones API** | `HKWorkoutZoneGroup`, `HKWorkoutZoneConfiguration`, `HKHealthStore.preferredWorkoutZoneConfiguration(for:)`, live zone updates via `HKLiveWorkoutBuilderDelegate`. HR + cycling power zones, time-in-zone. | Optional enrichment: post-exercise "peak window" detection gets zone-quality data, not just "a workout happened." |
| **Menopause API** | `HKCategoryTypeIdentifier.menopausalState`, `bleedingAfterMenopause`. | Not relevant. |
| **Health app: faster data updates** | iOS 27 Health app touts faster data refresh (Tom's Guide live blog). | Worth re-measuring Watch→iPhone sync latency on iOS 27 beta — could tighten ADR-0001's 5–20 min latency assumption. |
| **Journal app: incremental** | Streaks, attachments, iCloud sync status, timestamps. No new developer API. | No change to the Journaling Suggestions picture (§2). |
| **watchOS 27** | Workout Buddy insights, more accurate indoor tracking, battery efficiency. | Watch app remains out of scope (ADR-0002 §5). |
| **No State of Mind changes** | Nothing announced at WWDC25 or WWDC26 touched `HKStateOfMind`. | API is **stable two full cycles** — low churn risk for building on it. |

For the record, the WWDC25 (iOS 26) HealthKit additions were the Medications API (`HKUserAnnotatedMedicationQueryDescriptor`) and live workout sessions on iOS — also orthogonal to Harlo.

---

## 1. HKStateOfMind — the Harlo-shaped API

### What it is

`HKStateOfMind` (iOS 18.0+, iPadOS 18.0+, watchOS 11.0+, visionOS 2.0+, Mac Catalyst 18.0+, macOS 15.0+ **API surface only** — see caveat) is an `HKSample` subclass introduced at WWDC24 alongside the clinical screeners `HKPHQ9Assessment` and `HKGAD7Assessment`:

- **`kind`**: `.momentaryEmotion` (how you feel right now) or `.dailyMood` (the day overall)
- **`valence`**: continuous `Double`, −1.0 → +1.0, with a 7-step `ValenceClassification` (Very Unpleasant → Very Pleasant)
- **`labels`**: ~38 emotion words — including, notably for Harlo: *Drained, Overwhelmed, Frustrated, Stressed, Discouraged, Anxious, Irritated, Passionate, Confident, Content, Calm, Excited, Hopeful, Proud, Ashamed*
- **`associations`**: 18 life areas — `community, currentEvents, dating, education, family, fitness, friends, health, hobbies, identity, money, partner, selfCare, spirituality, tasks, travel, weather, work`
- Created via plain initializer, saved with `healthStore.save(_:)`; queried with `predicateForStatesOfMind(withValence:operatorType:)`, `…(with: label)`, `…(with: association)`

Third-party samples appear in Health's Mental Wellbeing section and in Journal **with source-app attribution** (e.g. "Arising — Momentary Emotion"). Apple even ships a sample project visualizing State of Mind on visionOS.

**Mac caveat (binding)**: the SDK marks availability `macOS 15.0+`, but D67 established empirically that no Mac through macOS 27 has a Health data store (`isHealthDataAvailable() == false`). **Every read and write happens on the iPhone, inside HarloPulse.**

### The taxonomy maps almost embarrassingly well

| Harlo state | `kind` | valence (suggested) | labels | associations |
|---|---|---|---|---|
| Burnout GREEN / rolling | momentaryEmotion | +0.3 → +0.6 | Content, Confident | work, tasks |
| Momentum peak / flow | momentaryEmotion | +0.6 → +0.9 | Passionate, Excited | work |
| Burnout YELLOW | momentaryEmotion | −0.1 → −0.25 | Drained, Indifferent | work |
| Burnout ORANGE | momentaryEmotion | −0.4 → −0.6 | Frustrated, Stressed, Overwhelmed | work, tasks |
| Burnout RED | momentaryEmotion | −0.8 | Overwhelmed, Drained | work, health |
| DEPLETED (allostatic) | dailyMood | −0.3 | Drained | health, work |
| crashed | dailyMood | −0.5 | Discouraged, Drained | work |
| Imposter-voice (destructive) | momentaryEmotion | −0.5 | Discouraged, Ashamed | **identity**, work |

Apple shipping `identity` as a first-class association is a direct hook for the imposter-voice / identity-friction patterns Harlo already models. The mapping table should live in `config/` as data, not code.

### Direction 1 — READ: self-reported mood as a Modulation signal

The user already logs moods via Watch/iPhone/Journal prompts. Those samples are a *self-reported affect channel* that Harlo currently lacks (its sincerity-gated self-reports come only through conversation). HarloPulse reads State of Mind alongside the 9 biometric types and ships them in the same wire format.

- **Rule 9 note**: clean. Samples enter through `biometric_barrier`, live in the Modulation Layer only, decay on the freshness window, never touch traces/reflexes. Treat valence+labels as a gain input to allostatic load (a "Very Unpleasant / Drained / work" sample is corroborating evidence for DEPLETED). Filter out Harlo's own writes on read (exclude own `HKSource`/bundle ID) to prevent a feedback loop with Direction 2.
- **Effort**: **S** (on top of HarloPulse v1 — one more type in `biometric_sample_schema.json`, one more opt-in toggle, a valence→gain mapping in `AllostasisTracker`).
- **First step**: add `state_of_mind` to `config/biometric_sample_schema.json` (fields: kind, valence, labels[], associations[], source_bundle_id) behind a per-type opt-in, and write the barrier test that rejects it everywhere outside `modulation/`.

### Direction 2 — WRITE: Apple Health as the system-of-record mirror

Yes — Harlo can write `HKStateOfMind` samples from its cognitive verdicts, and this is the frontier move. The Mac daemon computes a verdict (state transition: GREEN→ORANGE, DEPLETED onset, peak entered); the verdict is mirrored to the phone; HarloPulse saves a State of Mind sample. Consequences:

1. Apple Health's Mental Wellbeing timeline becomes a longitudinal mirror of Harlo's cognitive-state engine — charted by Apple, synced to all the user's devices, exportable, visible to the user **outside** Harlo.
2. Journal's Suggested Moments will offer "HarloPulse — Momentary Emotion" cards (see §2) — free, Apple-rendered presence in the user's reflection workflow.
3. It is the strongest possible "your memory, your device, your health record" story: the coach's verdicts land in the user's own health store, not a vendor cloud.

Two design constraints:

- **App Review 5.1.3 prohibits writing "false or inaccurate data" into HealthKit.** An AI-inferred mood written silently is gray-zone. The compliant shape is **suggest-then-confirm**: HarloPulse surfaces "Harlo read your last hour as ORANGE — log 'Frustrated / work' to Health?" and writes only on tap (or under a standing per-state-class consent the user can audit and revoke). This also happens to be the *coach-correct* shape — Harlo proposing, the human owning the record. Sincerity gate S8 energy, inverted.
- **Transport inversion**: ADR-0002 v1 is phone→Mac push. The mirror needs Mac→phone delivery of pending verdicts. Cheapest v1: piggyback pending mirror-suggestions on the ACK frame of the existing push session (phone connects, pushes samples, receives queued verdict-suggestions, prompts user). No new listeners, no persistent connections, Rule 1 intact. v2 USB inverts direction anyway.

- **Rule 9 note**: Rule 9 governs *ingress* (biometrics must not enter traces). This is *egress* of a derived verdict — exactly the D60 derived-verdict-only class that already persists in `modulation_state`. No trace content, no memory text, ever crosses; the sample carries kind/valence/labels/associations + a metadata key (e.g. `HarloVerdictID`) only. Needs a short **ADR-0003** because it creates a new outbound data flow and a standing consent surface.
- **Effort**: **M** (verdict→sample mapping table, reverse-queue on the pairing channel, consent UI, revocation; the state engine and pairing already exist).
- **First step**: draft ADR-0003 ("State-of-Mind mirror: derived-verdict egress to HealthKit"), with the mapping table above and the suggest-then-confirm consent model as binding constraints.

---

## 2. JournalingSuggestions API

**Reality**: the framework (iOS 17.2+, iPadOS 26.0+, entitlement `com.apple.developer.journal.allow`) is a **picker for journaling apps to consume Apple's suggestions** — an out-of-process sheet listing 15 content types (`StateOfMind`, `Workout`/`WorkoutGroup`, `Photo`, `LivePhoto`, `Video`, `Contact`, `Location`/`LocationGroup`, `MotionActivity`, `Song`, `Podcast`, `GenericMedia`, `EventPoster`, `Reflection`). Apps receive only what the user explicitly picks. **Third-party apps cannot register as suggestion sources directly** — the sources are system pipelines.

**But the back door is the front door**: data a third-party app saves to HealthKit (State of Mind, workouts) *does* surface in Journal's suggestions, attributed by app name — the documented "Arising — Momentary Emotion" pattern. So §1 Direction 2 automatically buys Harlo a Journal presence: every confirmed verdict-mirror becomes a potential "HarloPulse — Momentary Emotion" reflection card. SiriKit/CallKit donations are the other documented surfacing route (not Harlo-shaped today).

Note Journal now runs on **macOS 26+** ("Suggested Moments" included) and the user's confirmed Harlo states will appear there on the Mac — Apple closing a loop Harlo can't reach directly, since the JournalingSuggestions *API* has no Mac surface.

- **Opportunity**: ambient presence in the user's reflection ritual; the user journaling *about* a Harlo-logged ORANGE afternoon is exactly the co-evolution spiral, run through Apple's UI.
- **Rule 9 note**: nothing ingresses. (Becoming a journaling *app* that consumes the picker would route journal content toward traces — that's a Blood-Brain Barrier / Rule 8 design, explicitly out of scope here.)
- **Effort**: **S** — zero marginal code beyond §1 Direction 2; the work is naming/iconography so the attribution line reads well.
- **First step**: none independent — inherit from ADR-0003; verify the attribution string renders as desired on an iOS 27 device once HarloPulse writes its first sample.

---

## 3. SensorKit — reality check

**Park it.** `com.apple.developer.sensorkit.reader.allow` is a private, per-study entitlement: IRB/Ethics-Committee approval meeting regulatory standards, a compliant Informed Consent Form, per-data-type participant consent, and Apple review of the specific study before even the *distribution* entitlement is granted (a development entitlement gates the start, application via researchandcare.org). It is structurally unavailable to a consumer wellness product — and that is unlikely to change; it has been research-only since 2020.

- **Opportunity**: none for shipping Harlo. The only future angle: if Harlo's substrate ever underpins a formal ADHD/burnout research study (academic collaboration), SensorKit's ambient-behavior streams (device usage, ambient light, speech metrics) would be the gold-standard validation dataset for the allostatic model. That's a paper, not a product.
- **Rule 9 note**: moot today; if ever pursued, SensorKit streams are raw behavioral telemetry and would be the most radioactive ingress Harlo ever handled — Modulation-only containment would need its own ADR and probably its own process.
- **Effort**: n/a (gated externally).
- **First step**: none. Record the verdict here so it isn't re-litigated every quarter.

---

## 4. visionOS / iPadOS — the Mac-adjacent surfaces

- **iPadOS**: Health app + HealthKit since iPadOS 17; Health data syncs across iPhone/iPad/Watch. The iPad is the closest thing to a "desk-class" HealthKit host that exists. HarloPulse built with modern SwiftUI runs there nearly for free, and an iPad sitting on the same desk as the Mac Studio is a legitimate always-on sidecar (more screen for consent/confirm flows, same LAN transport).
- **visionOS**: HealthKit since visionOS 2 (WWDC24), sharing iPadOS authorization semantics; Apple's own sample app is literally *"Visualizing HealthKit State of Mind in visionOS."* Apple's newsroom has been explicitly courting health developers on Vision Pro. A spatial render of the cognitive-state timeline is a USD-native demo Harlo is uniquely equipped to build — but it's a showcase, not infrastructure.
- **Mac Catalyst trap**: HealthKit symbols mark Catalyst 13.0+/macOS 13.0+, but with no Health data layer on the Mac a Catalyst HarloPulse would compile and then report `isHealthDataAvailable() == false` — the exact D67 failure, one layer up. Don't ship a Catalyst target expecting data.

- **Opportunity**: iPad as a second-class sidecar target (resilience if the phone leaves the desk); visionOS as a patent-adjacent demo of the USD twin rendered spatially.
- **Rule 9 note**: unchanged on both — same HarloPulse code, same barrier on the Mac side.
- **Effort**: iPad **S–M** (mostly target/UI work on HarloPulse); visionOS **L** (park until HarloPulse v1 ships).
- **First step**: set HarloPulse's Xcode project to a universal iPhone/iPad target from day one; cost is near-zero now and an iPad target later becomes a checkbox instead of a port.

---

## 5. Background delivery & anchored-query cadence (trend-grade ingestion realities)

The ingestion loop HarloPulse should run, and what iOS will actually allow:

**The canonical pattern** — `HKObserverQuery` registered at app launch + `enableBackgroundDelivery(for:frequency:)` + an `HKAnchoredObjectQuery` whose `HKQueryAnchor` is serialized across launches (NSSecureCoding) for delta-only pulls. Observer wakes the app; anchored query fetches exactly the new/deleted samples since the anchor; frames push to the Mac.

**The realities**:

1. **Entitlement**: `com.apple.developer.healthkit.background-delivery` is mandatory since iOS 15 — without it, `errorAuthorizationDenied`. Standard provisioning (team 233JSS4X69 fine); no special approval.
2. **Frequency is a ceiling, not a promise**: `.immediate/.hourly/.daily/.weekly` — and the system silently enforces per-type maxima. `stepCount` is capped hourly on iOS; most Watch-originated types arrive in **sync batches** anyway (the 5–20+ min Watch→iPhone latency ADR-0001 already encodes). HRV (`heartRateVariabilitySDNN`) lands when the Watch syncs, not when the heart beats.
3. **Completion-handler discipline**: fail to call the background update's completion handler and HealthKit retries with exponential backoff, then **stops delivering after three failures**. The observer handler must be bulletproof and fast — hand off to the push queue, complete immediately.
4. **Locked-device window**: the Health store is encrypted while the device is locked; a background wake during lock may not read protected data. Design for "wake → try → defer to next unlock," never "wake → assume data."
5. **Simulator**: background delivery untestable there; physical-device testing only.
6. **watchOS budgets** (4 wakes/hour, complication required) are irrelevant — no watch app, per ADR-0002.
7. **iOS 27**: "faster Health data updates" was on Apple's WWDC26 slide — re-benchmark Watch→iPhone latency on beta; if sync latency drops materially, the freshness window default could tighten.

**Verdict**: hourly-grade trend ingestion is comfortably realistic; minute-grade freshness is **not guaranteed** and must never be assumed. This is precisely ADR-0001 constraint 4 / ADR-0002 constraint 1 ("trend, not stream") — the platform agrees with the architecture.

- **Rule 9 note**: cadence lives entirely phone-side; Mac-side containment unchanged. Batched pushes + listener-exits keep the Rule 1 spirit.
- **Effort**: **M** — this *is* HarloPulse v1's core loop.
- **First step**: in the HarloPulse PR, implement observer + anchored-query for **one** type (HRV SDNN) end-to-end with anchor persistence and a logged wake/latency histogram over 48h on-device — empirical cadence data before generalizing to all 9 types.

---

## 6. Privacy manifest & App Review expectations (2026)

What a HealthKit app faces at review time this year:

1. **Guideline 5.1.3 (Health & Health Research)** — the load-bearing clauses:
   - HealthKit-context data may **not** be used for advertising or use-based data mining (5.1.2(vi) extends this to third parties);
   - apps **must not write false or inaccurate data** into HealthKit → drives the suggest-then-confirm design in §1;
   - **no personal health information stored in iCloud**;
   - privacy policy detailing health-data use is mandatory.
2. **Privacy manifest** (`PrivacyInfo.xcprivacy`): required when the app collects data or uses required-reason APIs. `NSPrivacyCollectedDataTypes` defines "collection" as transmission off-device in a developer-accessible way — HarloPulse's LAN push to the *user's own Mac* (no developer-accessible server, no cloud relay) supports a minimal manifest: Health & Fitness data **not collected** in Apple's defined sense, `NSPrivacyTracking = false`, no tracking domains. Verify wording against Apple's "Describing data use in privacy manifests" before submission; if in doubt, declare Health & Fitness / not-linked / not-tracking — still a top-decile privacy label.
3. **Regulated medical device declaration (NEW, March 26, 2026)**: apps with Health & Fitness or Medical as primary/secondary category in EEA/UK/US must declare regulated-medical-device status in App Store Connect — **new apps immediately**, existing apps by early 2027 (then update-blocked). HarloPulse declares **No** and the product page shows it. Keep all copy wellness-framed: no diagnosis, prevention, monitoring-of-disease, or treatment claims — that language is the regulator trigger (and the FTC's, in the US).
4. **Stay away from PHQ-9/GAD-7** (`HKPHQ9Assessment`/`HKGAD7Assessment`) in v1: clinical screeners invite clinical-adjacent review scrutiny that a coach does not need.

- **Rule 9 note**: the manifest is Rule 9 made public — "biometrics never leave the Modulation Layer" becomes a checkable App Store privacy label. Containment as marketing.
- **Effort**: **S** (declarations and copy discipline, not engineering).
- **First step**: write `ios/HarloPulse/PrivacyInfo.xcprivacy` and a one-page review-posture note (category choice, medical-device "No" rationale, 5.1.3 mapping) in the HarloPulse PR — before any UI exists, so copy is constrained from day one.

---

## 7. Competitive scan — HRV-trend coaching class

| App | Model | Coaching surface | Cloud posture |
|---|---|---|---|
| **Athlytic** | ~$25–30/yr; Watch-data recovery/exertion scores (WHOOP-without-the-band) | Recovery + exertion targets, numbers-first | Cloud analytics |
| **Bevel** | Multi-wearable breadth: recovery, strain, sleep, nutrition | "Bevel Intelligence" conversational AI — "Why was my recovery low?" answered from journal + physio | Cloud LLM |
| **Welltory** | Camera-PPG HRV (95%+ accuracy claims) + Watch; stress/energy reserves | Stress/energy dashboards, measurement-centric | Cloud analytics |
| **Gyroscope** | V8: $39/mo G1 membership; Health Score, fat-loss protocol, "Health Camera" | "G1 Coach" — **explicitly OpenAI-partnered** LLM coach, voice, extended reasoning | Cloud LLM, by design |

**The convergent pattern**: read HealthKit → compute a proprietary readiness/health score → bolt a cloud LLM on top → subscription. The coaching is generic wellness ("recovery is low, take it easy") because the apps know the user's body but nothing about the user's *work*.

**Harlo's differentiation (real, defensible):**

1. **Local-first is structural, not a toggle.** Every competitor ships physiology to cloud inference; Gyroscope advertises the OpenAI pipe. Harlo's biometrics terminate at a schema barrier on the user's own hardware — and after March 2026's medical-device transparency push, privacy posture is now *visible on the product page*.
2. **The coach knows the work state.** Token velocity, momentum phase, burnout level, RSD surfaces — biometrics *modulate* a cognitive system rather than render a score. "Your HRV trend plus your last 90 minutes of output says stop before the crash" is a sentence no readiness app can form.
3. **Rule 9 as product**: biometrics influence behavior but are constitutionally barred from memory. No competitor can even express that invariant.
4. **USD-composed twin substrate**: longitudinal, auditable, user-owned state — versus opaque proprietary scores. (Joe's surveyed 100+ agentic-memory papers: zero USD substrates.)
5. **Verification (Elenchus)**: coaching claims are gated, not vibes.

**The honest gap**: these apps have years of HRV-baseline tuning and polished score UX. Harlo should **consume trends and coach behavior**, not manufacture a competing readiness number. If a score is ever wanted, read *theirs* (their HealthKit writes are readable samples) rather than rebuilding one.

- **Rule 9 note**: differentiation #1–3 *is* Rule 9. The moat is the constraint.
- **Effort**: n/a (positioning).
- **First step**: a one-paragraph positioning block in HarloPulse's README/App Store copy: "Harlo doesn't score your body. It coaches your work with your body's consent."

---

## Priority Matrix

| # | Opportunity | Effort | Rule 9 | First step |
|---|---|---|---|---|
| 1 | HarloPulse v1 trend ingestion (HRV-first observer/anchored-query loop) | **M** | Clean — existing barrier path | One-type end-to-end + 48h cadence histogram on device |
| 2 | State of Mind **READ** (self-logged mood → Modulation gain) | **S** | Clean — Modulation-only; filter own writes | Add `state_of_mind` to biometric schema + barrier test |
| 3 | State of Mind **WRITE** (verdict mirror, suggest-then-confirm) | **M** | Clean egress (D60 verdict class) — needs ADR-0003 | Draft ADR-0003 with mapping table + consent model |
| 4 | Journal presence via HealthKit attribution | **S** (byproduct of #3) | No ingress | Verify attribution rendering on iOS 27 device |
| 5 | Privacy manifest + medical-device "No" + 5.1.3 posture | **S** | Rule 9 made public | `PrivacyInfo.xcprivacy` + review-posture note in HarloPulse PR |
| 6 | iPad as secondary sidecar | **S–M** | Unchanged | Universal target checkbox in HarloPulse Xcode project |
| 7 | Workout Zones enrichment (post-exercise peak-window quality) | **S** | Modulation-only | Backlog until HarloPulse v1 ships |
| 8 | visionOS State-of-Mind spatial demo (USD twin showcase) | **L** | Unchanged | Park; revisit post-v1 |
| 9 | SensorKit | — | Moot | None. Research-only (IRB). Recorded; don't re-litigate. |

Recommended order: **1 → 2 → 5 (parallel) → 3 → 4**, with 6 as a day-one checkbox. Items 7–8 are post-v1; item 9 is closed.

---

## Sources

**Fetched directly (Apple documentation — canonical pages, retrieved via their JSON data endpoints):**

- https://developer.apple.com/documentation/healthkit/hkstateofmind — availability, properties, initializer
- https://developer.apple.com/documentation/healthkit/hkstateofmind/association — 18 association cases
- https://developer.apple.com/documentation/updates/healthkit — WWDC23→26 framework changelog (Workout Zones, Menopause, Medications, State of Mind/PHQ-9/GAD-7, visionOS)
- https://developer.apple.com/documentation/journalingsuggestions — framework availability + entitlement
- https://developer.apple.com/documentation/journalingsuggestions/journalingsuggestion — 15 suggestion content types
- https://developer.apple.com/documentation/healthkit/hkhealthstore/enablebackgrounddelivery(for:frequency:withcompletion:) — frequency caps, entitlement, backoff behavior
- https://developer.apple.com/documentation/bundleresources/privacy-manifest-files — manifest contents and requirements
- https://developer.apple.com/news/?id=nyqbfz1y — regulated medical device apps (March 26, 2026; EEA/UK/US; early-2027 deadline)
- https://developer.apple.com/news/?id=xqk627qu — 5.1.2(vi) HealthKit no-marketing/data-mining clause

**Fetched directly (press / community):**

- https://www.macrumors.com/2026/06/08/wwdc-2026-recap/ — WWDC 2026 recap; macOS 27 "Golden Gate"; no Health-for-Mac
- https://techcrunch.com/2026/06/09/wwdc-2026-everything-announced-on-siri-ai-os-27-apple-intelligence-and-more/ — WWDC 2026 full recap; confirms absence of Health/Journal announcements
- https://www.iclarified.com/101152/here-are-the-263-new-features-revealed-in-apples-massive-wwdc-2026-slide — 263-feature slide (health/Journal items)
- https://rudrank.com/exploring-healthkit-working-with-state-of-mind — State of Mind API deep dive (kinds, valence, 38 labels)
- https://www.rudrank.com/exploring-journaling-suggestions-emotions-and-moods-with-state-of-mind/ — JournalingSuggestion.StateOfMind + third-party attribution ("Arising — Momentary Emotion")

**Corroborating (surfaced in search, not independently fetched):**

- https://the5krunner.com/2026/06/08/watchos-27-features-compatibility/ — WWDC26 Training Zones API report
- https://9to5mac.com/2026/05/25/hopes-for-wwdc-2026-health-for-mac-wallet-everywhere-and-other-os-27-dreams/ — Health-for-Mac as pre-WWDC wishlist
- https://www.tomsguide.com/news/live/wwdc-2026-live-news-updates — iOS 27 Health app "faster data updates"
- https://9to5mac.com/2026/03/26/new-app-store-policy-requires-medical-device-disclosures-for-some-health-apps/ — medical-device disclosure policy coverage
- https://developer.apple.com/help/app-store-connect/manage-app-information/declare-regulated-medical-device-status — App Store Connect declaration procedure
- https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.developer.sensorkit.reader.allow — SensorKit entitlement
- https://www.researchandcare.org/resources/accessing-sensorkit-data/ — SensorKit research-study application process (IRB/ICF requirements)
- https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.developer.healthkit.background-delivery — background-delivery entitlement
- https://developer.apple.com/videos/play/wwdc2024/10109/ — "Explore wellbeing APIs in HealthKit" (WWDC24)
- https://developer.apple.com/videos/play/wwdc2024/10209/ — "Enhanced suggestions for your journaling app" (WWDC24)
- https://developer.apple.com/videos/play/wwdc2025/321/ — "Meet the HealthKit Medications API" (WWDC25)
- https://developer.apple.com/videos/play/wwdc2024/10083/ — "Get started with HealthKit in visionOS" (WWDC24)
- https://developer.apple.com/documentation/healthkit/visualizing-healthkit-state-of-mind-in-visionos — Apple visionOS State of Mind sample
- https://www.apple.com/newsroom/2024/03/apple-vision-pro-unlocks-new-opportunities-for-health-app-developers/ — Vision Pro health developer push
- https://www.apple.com/newsroom/2023/06/apple-provides-powerful-insights-into-new-areas-of-health/ — Health app on iPad (iPadOS 17)
- https://www.techradar.com/computing/websites-apps/macos-tahoe-26-finally-brings-journal-to-mac-and-i-might-use-it-now — Journal on macOS 26
- https://support.apple.com/en-am/guide/journal/dev7c1a9b879/mac — Journal on Mac user guide
- https://askvora.com/blog/bevel-vs-athlytic-apple-watch-recovery-apps — Bevel vs Athlytic comparison
- https://lifetrails.ai/blog/welltory-ai-wellness-coach — Welltory accuracy review
- https://insider.fitt.co/press-release/gyroscope-app-launch-new-ai-health-camera-for-optimized-fat-loss/ — Gyroscope V8 / OpenAI partnership
- https://gyrosco.pe/one/ — Gyroscope One pricing
- https://developer.apple.com/app-store/review/guidelines/ — App Review Guidelines (5.1.3)
- https://developer.apple.com/documentation/healthkit/protecting-user-privacy — HealthKit privacy guidance

**Repo references:** `docs/adr/0001-healthkit-allostatic.md`, `docs/adr/0002-iphone-sidecar.md`, `docs/CTO_REVIEW_2026-06-09.md` (D60–D68), `CLAUDE.md` Rule 1 / Rule 9, `config/biometric_sample_schema.json`.