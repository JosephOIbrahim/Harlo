# Foundation Models Provider Review — Harlo × the LanguageModel Protocol

**Date:** 2026-06-10 · **Source:** WWDC26 "Bring an LLM provider to the
Foundation Models framework" (architect's session notes) · **Status:**
CTO advisory; companion to the App Intents adoption plan (same PR).

**One-sentence verdict:** Apple just shipped a pluggable `LanguageModel`
protocol whose error taxonomy, usage channel, and transcript model map
almost line-for-line onto Harlo's constitution — turning "the coach that
can say no" into something any Foundation-Models app on the platform can
consume. This is the third door (after MCP and App Intents) onto the
same spine, and the one with the least competition standing in it.

---

## 1 · Two opposite-direction opportunities

### A. Harlo as CONSUMER — `HdAppleFM` delegate (cheap, P1 line item)

`SystemLanguageModel()` gives the native shims (HarloGlance, OTTO,
HarloPulse) a fully-local reasoning tier with zero provisioning. First
use: Glance phrases coach advice on-device ("long stretch without a
break — YELLOW since 2:14") without any network call.

Validation worth savoring: `LanguageModelCapabilities([.toolCalling,
.guidedGeneration, .reasoning])` is **exactly** the v9 engine's
capability-matched delegate registry (`harlo.engine.delegate_registry`,
`compute_routing` — "requirements, not names"). Apple converged on the
shape Harlo already built. An `HdAppleFM` delegate slots into the
registry with no architectural change — the framework is Swift-only, so
it lives behind the native shim and reports availability to the engine,
exactly like HdClaude reports today.

### B. Harlo as PROVIDER — `HarloLanguageModel` (the strategic one, P2)

A Swift package conforming `LanguageModel`/`LanguageModelExecutor` that
routes generation through Harlo's daemon — Claude (or any registered
delegate) behind the constitutional layer. Any FM-consuming app gets a
model that is *governed*.

**The mapping table that makes this a "build" and not a "maybe":**

| FM protocol surface | Harlo implementation — already exists |
|---|---|
| `LanguageModelError.refusal` | Rule 18: RED overrides everything — full stop is a *typed error* now |
| `.rateLimited` | Allostatic load (Rule 9) — DEPLETED refuses to wake System 2 |
| `.guardrailViolation` | Anchors (Rule 10) + Blood-Brain Barrier (Rule 8) |
| `.contextSizeExceeded` | `harlo.engine.computations.compute_context_budget` — a pure function, on the shelf |
| `channel.send(.updateUsage(input:output:))` | Token velocity is **the** Rule-9 software signal — the provider *generates* allostatic telemetry as a by-product of serving |
| `Transcript` entries (instructions/prompt/toolCalls/toolOutput/response) | `session/manager.py` history_json is role/content — direct map; toolCalls ↔ the MCP tool surface |
| `executor.respond(...)` transport | **Already shipped:** the daemon speaks 4-byte BE length-prefixed frames on `twind.sock` since D61 — the executor is one more client of the existing protocol |
| `prewarm(model:transcript:)` | Deliberate no-op — Rule 1 (0W idle) holds; launchd socket activation *is* our prewarm |
| Custom segments (`Transcript.CustomSegment`) | **`CognitiveStateSegment`** — stream the modulation verdict (GREEN→RED + load) inline with every response. The burnout light rendered *inside any FM app's response stream*. Highest-novelty item in this doc. |
| Server-side tools pattern | `coach`/`store` as Harlo server tools — `recall` is **P3-GATED** (memory content through third-party apps = the same gate as IntentValueQuery) |
| Custom error taxonomy | `HarloModelError.depletedRefusal`, `.familyHours` (schedule FAMILY routing), `.consentRequired` — localized, honest |
| `.metadataUpdate` perf channel | `tokensPerSecond`, `timeToFirstToken`, plus `cognitiveState` and `exchangeIndex` |

**Why this wins strategically:** MCP door (Anthropic's ecosystem) +
App Intents door (Siri/Shortcuts) + FM provider door (every Apple-
platform app that adopts the framework) — three distribution surfaces,
one spine, one constitution. Competitors shipping "a memory server"
have nothing to put behind doors two and three. The pitch line:
**"the first LanguageModel provider with a constitution — a model that
can refuse because *you* need it to."**

---

## 2 · Reality checks (before anyone gets excited in code)

1. **Xcode 27 beta required.** The provider `Package.swift` targets
   `.macOS(.v27)/.iOS(.v27)`. Installed Xcode is 26.5 (brew already
   complained about the skew). Download this week's beta before any
   provider build. The App-Intents work (PR #13) is untouched by this —
   it targets iOS 17+.
2. **Prototype against MLX first.** `MLXFoundationModels` +
   a small local model exercises the executor mechanics (channel
   streaming, transcript mapping, error paths) with zero Harlo wiring —
   a weekend-sized spike that de-risks the protocol before the daemon
   RPC integration.
3. **Capability honesty (the session's own rule).** v1 declares ONLY
   what the daemon path actually honors: no `.guidedGeneration` until
   schema-constrained output is real end-to-end; throw
   `.unsupportedCapability` with a useful debugDescription otherwise.
   This is the D49 honesty baseline applied to a new surface.
4. **Patent gate (binding).** A constitutionally-gated LanguageModel
   provider is **new post-provisional matter** (the five filings predate
   this framework). Internal builds: fine. Publishing the package, the
   repo, or a deep-dive post: counsel first — fold into the ≤ March 2027
   conversion conversation alongside the HarloPulse transport and D60.
5. **Latency posture.** Daemon-routed generation adds the socket hop +
   activation; fine for coach-grade interactions, wrong for keystroke-
   grade completion. Position the provider as the *deliberate* model,
   not the fast one.

---

## 3 · Sequencing (slots into the existing P-phases)

| Phase | Addition from this review |
|---|---|
| **P1** (HarloGlance) | + `HdAppleFM` consumer: SystemLanguageModel phrases advice locally in Glance; registry-reported like any delegate |
| **P1.5 spike** (weekend) | MLX executor prototype: protocol mechanics only, no Harlo wiring; requires Xcode 27 beta |
| **P2** | `HarloLanguageModel` provider v1: respond() → twind.sock (D61 framing) → coach-routed generation; errors mapped per §1B table; `CognitiveStateSegment`; capabilities = text-only honest set |
| **P3 (gated)** | recall as a server tool · `.guidedGeneration` · public package release (counsel) |

**Exit criterion for P2:** a third-party sample app using stock
`LanguageModelSession(model: HarloLanguageModel())` receives a coach
response with an inline `CognitiveStateSegment`, and receives a typed
`.refusal` when the modulation state is RED — demonstrated end-to-end
on this Mac.
