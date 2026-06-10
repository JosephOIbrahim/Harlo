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

---

## 4 · ADDENDUM (2026-06-10, same day): "What's new in Foundation Models" — the Python SDK changes everything

The companion what's-new session contains the single most codebase-relevant
line of all four WWDC docs: **`import apple_fm_sdk` — Apple ships a Python
SDK for Foundation Models.**

### Empirically verified on this Mac, same hour

```
pip install apple_fm_sdk            # 0.2.0 on PyPI — builds Swift C-bindings
                                    # at install; REQUIRES DEVELOPER_DIR →
                                    # Xcode 27 (fails on CLT/Xcode 26.5)
is_available: (True, None)
RESPONSE: "A cognitive twin is a mental counterpart."
```

The on-device model answered a Harlo-domain prompt from Python, locally,
zero network. Consequence: **§1A is superseded — `HdAppleFM` does NOT need
the Swift shim.** It becomes a first-class v9 delegate
(`harlo.engine.delegate_apple_fm`) in the existing capability-matched
registry, pulled forward from "P1, inside Glance" to "P1, this week, pure
Python." Dependency discipline: `apple_fm_sdk` enters as an optional
`[applefm]` extra (Law 3 / D75 pattern), never a core dep.

### The rest of the what's-new doc, mapped

| New API | Harlo mapping |
|---|---|
| `model.contextSize` + `tokenCount(for:)` | `compute_context_budget` upgrades from heuristics to **exact counts**; Rule 9 token-velocity telemetry gains precision |
| `response.usage` (input/cached/output/**reasoning** tokens) | Allostatic load fed from real usage on the consumer side — the provider review's "Rule 9 as a by-product" now holds in both directions |
| `ContextOptions(reasoningLevel: .light/.deep)` | **The System 1/System 2 dial, literally.** Rule 9's "High = DEPLETED = refuse to wake System 2" becomes enforceable API: `compute_routing` sets reasoningLevel from cognitive state — DEPLETED clamps to `.light`, RED refuses the call entirely (Rule 18) |
| Session routing (`SwitchModeTool`, `transcript.dropFirstInstructions()`, rebuild session per mode) | Apple's pattern for what the expert router (restorer/scaffolder/validator…) already does — adopt as the delegate-side session-management idiom |
| `DynamicProfile` (declarative `Profile { Instructions; Tools }` with per-branch `.model()` / `.reasoningLevel()`) | **Expert profiles as code**: one DynamicProfile per cognitive state, with `.model(PrivateCloudCompute)` + `.reasoningLevel(.deep)` as the System-2 escalation branch — and, post-P2, `.model(HarloLanguageModel)` closes the loop: Harlo's own provider as a profile branch |
| `Attachment(UIImage…)` image input | Parked — future visual-context play (screenshot-of-work burst analysis), no current consumer |

### Sequencing delta

- **P1 gains a new first item, decoupled from Glance:** `delegate_apple_fm`
  spike — register the on-device model in the v9 registry, route advisory
  phrasing through it, wire `reasoningLevel` to the cognitive state. Pure
  Python; the probe above is its proof of feasibility.
- The Glance/OTTO Swift consumer remains P1 for the UI surfaces; it now
  shares semantics with the Python delegate rather than owning them.
- Install gotcha worth a line in any setup doc: the SDK's Swift-binding
  build needs `DEVELOPER_DIR=/Applications/Xcode-beta.app/Contents/Developer`
  until Xcode 27 is the selected toolchain.
