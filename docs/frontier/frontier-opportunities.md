# Frontier Opportunities Brief — Harlo

**Date:** 2026-06-10 · **Role:** frontier opportunity scout (product-strategy MOE) · **Status:** PROPOSED — nothing here is binding until the architect accepts it
**Grounding:** `README.md`, `docs/CTO_REVIEW_2026-06-09.md` (D49–D83), `docs/adr/0001`, `docs/adr/0002`, `docs/usd-proof-trial.md`, `PATENTS.md`, `NEXT.md` · Branch `master`, clean
**Scope:** everything beyond HealthKit (HealthKit/biometrics is settled by ADR-0002 + D60–D68 and is referenced here only where it intersects)

---

## 0 · The single sequencing rule

Every opportunity below is a **visibility play**, and visibility multiplies whatever is true at the moment of exposure. The CTO review's root finding (D49) is that Harlo's docs describe more than what ships; D50 (plaintext `--encrypted` export) and D53 (demo tools + demo scenes in user data dirs) are exactly the findings an auditor, registry reviewer, or AOUSD-forum skeptic would hit first.

> **Rule for this brief: TIER 0 (D50–D55) ships before any external visibility push.** Estimated cost is small (it was scoped as v0.1.4). Every item in §5 assumes it.

Timing context that makes this brief urgent rather than evergreen: **WWDC 2026 ran this week (keynote June 8)** and it moved three of Harlo's tectonic plates at once — App Intents became the sole Siri integration path, MCP went platform-adjacent inside Apple's tooling, and the on-device Foundation Models framework grew a multi-provider protocol. The fall iOS 27 / macOS 27 ship window (~September 2026) is the natural deadline for the Apple-facing items.

---

## 1 · macOS 27 "Golden Gate" — platform features to ride

### 1.1 What WWDC 2026 actually changed (confidence-tagged)

| Change | Status | Source quality |
|---|---|---|
| Apple Intelligence rebuilt; **App Intents is THE integration point** for Siri AI / natural-language access to app capabilities | Confirmed | Apple PSOTU takeaways (primary) |
| **SiriKit formally deprecated**; App Intents is the only way Siri calls third-party apps going forward (~2–3 yr sunset reported) | Confirmed deprecation; sunset window is press-reported | Apple PSOTU + press |
| **Foundation Models framework**: image input, cloud model support, **Dynamic Profiles** for building agents/skills with less code; a `LanguageModel` protocol reportedly spanning Apple on-device, Gemini, and Claude | Framework expansion confirmed (primary); multi-provider protocol details press-reported | Apple PSOTU, WWDC26 session 241, press |
| **Core AI framework** — built into the OS, optimized for Apple silicon, "best way to run on-device models in apps" (press frames it as the Core ML successor) | Confirmed existence (primary) | Apple PSOTU |
| **Xcode 27 ships agentic coding + Agent Client Protocol + MCP tool support**; an `mcpbridge` binary reportedly exposes Xcode capabilities to external MCP agents | ACP/MCP support confirmed (primary); `mcpbridge` details press-reported | Apple PSOTU + press |
| New Siri AI is reportedly powered by a **custom Google Gemini model**; iOS 27 beta gates it behind a waitlist | Widely reported, not in Apple's own copy | Apple Newsroom (vague) + press |
| **New Shortcuts app builds workflows with AI** | Reported | TechCrunch |

Earlier groundwork still in force: Apple began wiring **MCP support into the App Intents framework** in the macOS 26.1 / iOS 26.1 betas (Sept 2025) — i.e., App Intents you expose are on a path to being callable by third-party AI systems at the OS level.

### 1.2 What this means for Harlo, concretely

**(a) App Intents is the cheapest path from "Harlo works" to "Harlo is perceivable."** D60's complaint was that the HealthKit signal produced *nothing the user can perceive*. The same critique applies to cognitive state generally: it lives in `.usda` files and an MCP tool response. A handful of **read-only App Intents** on Harlo.app — `HarloStatusIntent` (burnout level, momentum phase, energy), `HarloCoachIntent` (one coaching line) — makes Harlo's state addressable by Siri AI, Spotlight, and the new AI-workflow Shortcuts app, with zero new cognitive machinery: the intents shell into the existing daemon/CLI surface. Because App Intents is also Apple's MCP on-ramp, **one investment buys two futures**: Siri today, OS-level agent interop when Apple's MCP bridge matures.

**(b) Menu-bar extra + widget: the glanceable burnout light.** A macOS widget / menu-bar item showing GREEN · YELLOW · ORANGE · RED (and momentum phase) is the lowest-effort "ambient coach" surface and the most demo-able artifact Harlo could ship. It reads the D60 `modulation_state` store / `harlo status` — no new state, pure presentation. This is also the honest answer to D55 (silent app launch): the app's "window" *is* the menu-bar presence.

**(c) Foundation Models = a fully local reasoning tier.** Harlo's philosophy is "cloud models provide reasoning; your machine provides memory and safety." Apple's on-device ~3B model (no API key, no network, no per-token cost) is the first credible chance to make even *reasoning* local for small jobs — coach phrasing, intake summarization, inquiry tone checks. Architecturally this is a new **Hydra delegate** (`HdAppleFM`) — the delegate registry was built for exactly this (capability-matched routing, never naming a specific LLM). The reported multi-provider `LanguageModel` protocol is philosophically identical to Harlo's delegate pattern; that convergence is itself a talking point.

**(d) Notarization-era trust signals — close D66, then say so out loud.** Gatekeeper/notarization requirements are unchanged in kind (Developer ID + notarization for non-MAS distribution), but the *trust bar* has risen: privacy manifests (`PrivacyInfo.xcprivacy` — currently absent repo-wide, per D66), correct entitlements (App Group fix, D62), and a privacy-respecting story are becoming what reviewers, journalists, and security-conscious users check. Harlo's honest claim — *local state, no analytics SDKs, no phone-home (after D58 cuts the silent HuggingFace fetch)* — is rare and marketable, but only after the D-items that contradict it are closed. A short `docs/PRIVACY.md` ("what leaves your machine: nothing, here's how to verify with Little Snitch/`harlo doctor`") is a trust signal no notarization ticket provides.

### 1.3 OTTO synergies (flag for the architect)

The sister project **OTTO targets iOS 27 Siri Extensions in the WWDC June 2026 window** — which, post-keynote, concretely means **App Intents** (SiriKit is deprecated; App Intents is the only door). Synergies:

1. **One shared Swift package of App Intents patterns** (intent definitions, entity modeling, Shortcuts donation, Apple Intelligence schema annotations) serves OTTO on iOS and Harlo.app on macOS. Build it once, in whichever project moves first.
2. **HarloPulse (ADR-0002) is an iOS app** — the same App Intents scaffolding, signing pipeline, and provisioning knowledge OTTO needs. Sequencing HarloPulse after OTTO's first intent milestone converts OTTO's learning curve into Harlo's discount.
3. **Foundation Models Dynamic Profiles** (agents/skills with less code) is directly relevant to OTTO's assistant ambitions and to Harlo's coach projection — one evaluation spike can serve both.
4. Risk note: the Siri-AI rebuild reportedly runs on a Gemini-derived model behind a beta waitlist — **don't couple either project's fall milestone to Siri AI availability**; App Intents + Shortcuts work regardless.

---

## 2 · MCP ecosystem positioning — Harlo as the memory/coach MCP server

### 2.1 Landscape (June 2026)

- **MCP is now a neutral industry standard**: Anthropic donated MCP to the **Agentic AI Foundation under the Linux Foundation** (Dec 2025). OpenAI, Google, Microsoft, and Amazon have all adopted it; ecosystem trackers report 10,000+ public servers and ~16k `mcp-server` GitHub repos as of May 2026.
- **The official MCP Registry** (`registry.modelcontextprotocol.io`) is live in preview: reverse-DNS namespacing (`io.github.<user>/<server>`), GitHub-verified, requires a public install method (PyPI/npm/Docker) or a public remote.
- **Claude Desktop Extensions (`.mcpb`)**: one-click local MCP server install — zip bundle + manifest, `@anthropic-ai/mcpb` CLI, and an **Anthropic-reviewed extension directory** inside Claude Desktop. This is the distribution channel for non-terminal users, i.e., the actual coach audience.
- **Multi-client reality**: local stdio servers run today under Claude Desktop/Code, VS Code/Copilot, Cursor, and Gemini-family CLIs; **Xcode 27 just became an MCP-aware host**. ChatGPT's MCP support is remote-first (hosted servers) — a poor fit for Harlo's local-first posture; park it.
- **Security is the ecosystem's open wound**: a widely cited 2026 analysis found ~92% of public MCP servers carry at least one high-severity vulnerability. The field is huge and mostly careless.
- **Community calendar**: MCP Dev Summit NA happened (NYC, April 2026); **MCP Dev Summit Europe is reported for Amsterdam, Sept 17–18, 2026** — a realistic talk target.

### 2.2 Positioning: don't compete on memory benchmarks — compete on *constitution*

The agent-memory market (Mem0, Zep/Graphiti, Letta, LangMem, OpenMemory, OMEGA…) is crowded and benchmark-driven (LoCoMo, LongMemEval). Harlo should not enter that arena as "another memory server with better recall." Harlo's differentiated claims are ones no competitor makes:

1. **A coach, not a database.** The MCP surface isn't `remember/recall` — it's `coach`: burnout prediction, momentum protection, RED-state refusal. Memory is the substrate, not the product.
2. **Constitutionally governed.** 33 inviolable rules, inhibition-default motor (Rule 23), verified-only consolidation (Rule 12), trace-excluded verification (Rule 11) — in an ecosystem where 92% of servers can't pass a basic audit, "the MCP server with a constitution and 1,365 tests enforcing it" is a genuinely novel pitch. Publish the compliance greps as part of the story.
3. **Structurally local.** Local-first is OMEGA-style table stakes; *USD-composed, git-trackable, bit-identical-reconstructable* state is unique (see §3).
4. **A pleasing convergence worth one sentence everywhere:** both of Harlo's substrates — MCP and OpenUSD — are now Linux-Foundation-family open standards (AAIF and JDF/AOUSD respectively). Harlo is a two-standard native.

### 2.3 Concrete moves

| Move | Notes |
|---|---|
| **Publish to the official MCP Registry** as `io.github.josephoibrahim/harlo` | Requires a public install method — decide PyPI publish (check name availability) vs pointing at the GitHub release. Gate: Tier 0 + D59 (`harlo` console-script identity — registry metadata must describe what the entry point actually is). |
| **Ship a `.mcpb` bundle; submit to the Anthropic-reviewed directory** | `mcpb init` / `mcpb pack` against the packaged server. Complications to scope honestly: Rust `.so` (platform-specific → macOS-arm64 bundle v1), `[substrate]`/usd-core optionality (lean bundle = USD-Lite tier; be precise per the D49 marketing-precision lesson). Directory review is exactly the audit D50/D53/D54 must precede. |
| **Multi-host compatibility matrix** | One doc, one afternoon per host: Claude Desktop, Claude Code, VS Code, Cursor, Gemini CLI — and the fun one, **Xcode 27** ("your coach watches your burnout while the agent writes code" is a demo nobody else can run). |
| **MCP Dev Summit Europe talk proposal** | Title candidate: *"An MCP server with a constitution: inhibition-default actuation and verified-only memory."* Sept 17–18 Amsterdam (verify CFP dates on the official channel — date sourced from an ecosystem tracker). |

---

## 3 · OpenUSD / AOUSD — the substrate story nobody else can tell

### 3.1 Landscape (June 2026)

- **AOUSD ratified Core Specification 1.0** (Dec 17, 2025) — OpenUSD is now a published open standard with an explicit **ISO path via the Joint Development Foundation**; Core Spec 1.1 (animation, massive-scene scaling, compliance-testing guidelines) is on the 2026 roadmap. Membership has grown to ~50 companies; the *narrative* AOUSD itself is pushing is "beyond film/VFX → digital twins, robotics, industrial data."
- **SIGGRAPH 2026: July 19–23, LA Convention Center** — schedule is live; NVIDIA is running OpenUSD labs/sessions again. Formal-program submission deadlines have passed; BoFs, posters-adjacent presence, and hallway-track demos are the realistic 2026 entry points, with a proper 2027 submission as the planned follow-through.
- **OpenExec remains a preview with C++-only computation registration** (USD 26.05 docs) — the S2 circuit-breaker call ("architecture OpenExec-native; implementation catches up later") remains correct. Re-check each release; the 26.08 dev docs are already up.
- D76's pin (`usd-core>=26.5,<27`) is the right defensive posture while 26.x evolves.

### 3.2 Why Harlo's angle is genuinely novel here

The v0.1.2 trial proved, on a live `pxr` stage with cold-process re-verification, that **native USD composition semantics carry cognitive priority**: LIVRPS strength order resolves cognitive precedence (§F1), flatten-to-base reconstructs clean state bit-identically (§F2), and anchor immunity is *structural* — an adversarial sublayer authoring `CONSTITUTIONAL.value = "MALICIOUS_OVERRIDE"` is rejected by composition mechanics, not by a check that could be skipped. Nobody in the AOUSD "beyond graphics" tent is doing this. The pitch in one line:

> **The first non-spatial digital twin: a digital twin of a cognitive state, where safety properties are theorems of the composition engine.**

This serves AOUSD's own expansion narrative (they want non-graphics adoption stories for the ISO push) while giving Harlo standards-community legitimacy that no AI-memory competitor can copy without rebuilding on USD.

### 3.3 The visibility ladder (cheap → ambitious)

1. **AOUSD forum post** (free, this month): ~1,500 words — "OpenUSD as a cognitive substrate: composition arcs as cognitive priority," anchored on the v0.1.2 trial's reproducible harness (`wave1_harness.py`, post-D79 move into `harness/`). Results and behavior, **not implementation recipes** (see §4). The forum is the soft-launch that tests reception before anything costlier.
2. **Hydra-render-the-mind demo** (the unfair advantage): `brain.usda` is already a valid USD stage — add a *visualizer sublayer* (pure USD: gprims + primvars driven by state attributes; no engine changes) so **usdview/Storm renders the mind live**: anchors as fixed monoliths, traces as a decaying constellation, burnout as a color ramp, MotorPrims gated at a literal gate. Deliverable: `scripts/render_mind.py` + a 60–90s capture. The architect's 16 years of VFX is precisely the skill that makes this *beautiful* rather than diagrammatic — and a beautiful render is the only artifact that travels in both the graphics community and the AI community. (Stretch: an Omniverse-loaded variant for the NVIDIA-flavored venues.)
3. **SIGGRAPH 2026 presence** (July 19–23): attend with the demo on a laptop; target OpenUSD Day/BoF slots opportunistically. The deliberate goal for 2026 is conversations + forum credibility; the formal submission targets **SIGGRAPH 2027 / GTC 2027 OpenUSD track**.
4. **arXiv preprint** (counsel-gated, see §4): "Composition semantics as cognitive priority: structural safety in a USD-composed agent memory." Establishes dated academic prior art for what's already in the provisionals; cite-able from the patent prosecution too.

---

## 4 · Patent-pending leverage — what strengthens vs. what leaks

Five USPTO provisionals filed **March 2026** (per `PATENTS.md`): Deterministic State-Evolution/Predictive Composition; Falsifiability-Gated Assertion Management; Lossless Residual Injection; Composition-Semantic Combinatorial Search; Sovereign Persistent Agent Memory. Apache-2.0 with §3 patent grant + defensive termination.

**The clock:** provisionals confer a 12-month priority window — **non-provisional and/or PCT filings are due by ~March 2027**. That date should be on the calendar now, with a counsel session well before year-end 2026. *(Everything in this section is strategy framing, not legal advice; route through patent counsel.)*

### Strengthens (publish freely, with discipline)

- **Dated, reproducible evidence of what the provisionals already describe.** The v0.1.2 trial is the model artifact: verifier-first, cold-process re-verified, reproducible by command. Git tags, CI runs, notarized releases, and the LOG in `docs/usd-proof-trial.md` all build a reduction-to-practice record and create prior art *against fast followers* for subject matter already on file.
- **"Patent pending" marking** everywhere the architecture is described (already done in README/PATENTS.md — keep it on new public docs, the registry listing, and the `.mcpb` manifest description).
- **Results-and-behavior publications** (the AOUSD forum post, the Hydra demo, the compatibility matrix): they demonstrate the claims work without handing over the recipe.
- **A provenance pack**: one archived bundle per milestone (tag, harness output, scoreboard, SHA256s) — cheap insurance for both prosecution and any future diligence.

### Leaks (gate behind counsel review)

- **Any new inventive mechanism not described in the March 2026 provisionals.** Publishing it starts the US §102(b)(1) one-year grace clock *and immediately destroys absolute-novelty foreign rights* (EPO and most non-US jurisdictions). Specific items to check against the provisional texts before they appear in public docs: the **HarloPulse transport design** (ADR-0002 post-dates the filings), the **D60 modulation-state pathway**, any refinement of **composition-semantic search** beyond what was filed. If material is new and valuable → either fold it into the non-provisional before publishing, file a fresh provisional, or consciously choose defensive publication (kills everyone's patent on it, including yours).
- **Claim-mapping documents** ("this file implements claim 3") — pure design-around assistance; never publish.
- **Implementation-recipe deep dives** of the patented mechanisms (exact algorithms, data layouts) — remember the Apache-2.0 grant covers *this code as contributed*; a published recipe invites independent reimplementation that the grant does **not** cover but that publication may have armed. Architecture talks: yes. Annotated internals of the five filed mechanisms: counsel first.
- **Marketing that outruns the artifact** (the D49 lesson) — overclaiming is a diligence and credibility leak even when it's not a legal one. The "USD-composed cognitive twin" phrasing must track what the *shipped* binary does (lean bundle = mock/USD-Lite tier) vs. what the source proves.

---

## 5 · TOP-5, ranked

Effort tiers: **S** = days · **M** = 1–2 weeks · **L** = sprint+. All assume Tier 0 (D50–D55) ships first.

| # | Opportunity | Why it wins | Effort | First move (one line) |
|---|---|---|---|---|
| **1** | **Honest v0.1.4 → official MCP Registry + `.mcpb` one-click bundle** | The spine product (D49) meets its two native distribution channels; converts "works on Joe's machine" into installable-by-anyone; everything else inherits the credibility | **S–M** | Close D50/D53/D54, then `mcpb init && mcpb pack` and reserve `io.github.josephoibrahim/harlo` on registry.modelcontextprotocol.io |
| **2** | **macOS 27 App Intents + menu-bar burnout light** (OTTO-shared scaffolding) | App Intents is now the only Siri door AND Apple's MCP on-ramp; the menu-bar GREEN/YELLOW/ORANGE/RED light finally makes cognitive state *perceivable* (the D60 gap); every Swift hour double-counts for OTTO and HarloPulse | **M** | Spike one read-only `HarloStatusIntent` in Harlo.app that shells `harlo status`, while watching this week's WWDC26 App Intents + Foundation Models sessions |
| **3** | **AOUSD forum post + Hydra-render-the-mind demo** | The only claim in the entire agent-memory field nobody can copy; rides AOUSD's own "beyond graphics" / ISO narrative; the VFX-quality render is the artifact that travels everywhere (SIGGRAPH hallway → arXiv → investor deck) | **M** | Draft the 1,500-word forum post around the v0.1.2 trial and a first usdview screenshot of `brain.usda` with a visualizer sublayer |
| **4** | **Multi-host MCP compatibility matrix + "server with a constitution" security story** | Cheap breadth: VS Code, Cursor, Gemini CLI, and Xcode 27 as hosts; positions Harlo against the 92%-vulnerable field on governance, not benchmarks; feeds a Sept MCP Dev Summit Europe talk proposal | **S** | Run the stdio server under VS Code and one non-Anthropic host, and start the matrix table in `docs/` |
| **5** | **Patent provenance pack + counsel gate before the March 2027 conversion** | Protects the asset all four plays above are built on; near-zero effort now vs. unrecoverable loss if a post-filing mechanism (HarloPulse transport, D60 store) leaks into a publication unreviewed | **S** | Archive a dated v0.1.2 evidence bundle (tag + harness output + SHA256s) and book the counsel session that reviews the §3 publication list |

**Honorable mentions** (real, but gated or longer-fuse): **HarloPulse** (ADR-0002 already makes it required; sequence after OTTO's first App Intents milestone to harvest the synergy — L); **`HdAppleFM` Foundation Models delegate** (fully local reasoning tier; wait for the framework to exit beta churn — M); **OpenExec re-check each USD release** (no action until Python registration lands — S, recurring).

---

## Sources

**Apple / WWDC 2026:** [Apple Newsroom — next-gen Apple Intelligence & Siri AI](https://www.apple.com/newsroom/2026/06/apple-unveils-next-generation-of-apple-intelligence-siri-ai-and-more/) · [Apple Developer — 5 takeaways from the Platforms State of the Union](https://developer.apple.com/news/?id=lvart8mq) · [WWDC26 session 241 — What's new in Foundation Models](https://developer.apple.com/videos/play/wwdc2026/241/) · [Foundation Models docs](https://developer.apple.com/documentation/FoundationModels) · [TechCrunch — AI workflows in Shortcuts](https://techcrunch.com/2026/06/08/apple-will-let-you-build-workflows-using-ai-in-its-new-shortcuts-app/) · [Tom's Guide WWDC26 live recap](https://www.tomsguide.com/news/live/wwdc-2026-live-news-updates) · [TechRadar WWDC26 recap](https://www.techradar.com/news/live/apple-wwdc-2026-live) · [9to5Mac — iOS 27 Siri AI waitlist](https://9to5mac.com/2026/06/08/ios-27-beta-1-has-a-waitlist-for-accessing-new-siri-ai/) · [9to5Mac — MCP in macOS 26.1 beta App Intents](https://9to5mac.com/2025/09/22/macos-tahoe-26-1-beta-1-mcp-integration/) · [AppleInsider — MCP in iOS 26](https://appleinsider.com/articles/25/09/22/ios-26-could-get-a-major-ai-boost-with-the-model-context-protocol) · [Google — Gemini models for Apple developers](https://blog.google/innovation-and-ai/technology/developers-tools/bringing-gemini-models-to-apple-developers/) · [Apple — Notarizing macOS software](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution)

**MCP ecosystem:** [Anthropic — Donating MCP / Agentic AI Foundation](https://www.anthropic.com/news/donating-the-model-context-protocol-and-establishing-of-the-agentic-ai-foundation) · [Official MCP Registry](https://registry.modelcontextprotocol.io/) · [MCP Registry — about](https://modelcontextprotocol.io/registry/about) · [MCP blog — Registry preview](https://blog.modelcontextprotocol.io/posts/2025-09-08-mcp-registry-preview/) · [Anthropic — Desktop Extensions](https://www.anthropic.com/engineering/desktop-extensions) · [modelcontextprotocol/mcpb](https://github.com/modelcontextprotocol/mcpb) · [Claude Help — Building Desktop Extensions with MCPB](https://support.claude.com/en/articles/12922929-building-desktop-extensions-with-mcpb) · [MCP adoption statistics 2026 (Digital Applied)](https://www.digitalapplied.com/blog/mcp-adoption-statistics-2026-model-context-protocol)

**OpenUSD / AOUSD:** [AOUSD — Core Specification 1.0 announcement](https://aousd.org/news/core-spec-announcement/) · [Linux Foundation — AOUSD member milestones, March 2026](https://www.linuxfoundation.org/press/aousd_prmarch2026) · [Alliance for OpenUSD — Wikipedia](https://en.wikipedia.org/wiki/Alliance_for_OpenUSD) · [OpenUSD — Introduction to OpenExec](https://openusd.org/dev/intro_to_openexec.html) · [PixarAnimationStudios/OpenUSD CHANGELOG](https://github.com/PixarAnimationStudios/OpenUSD/blob/release/CHANGELOG.md) · [SIGGRAPH 2026 — Programs & Events](https://s2026.siggraph.org/programs-events/) · [NVIDIA at SIGGRAPH 2026](https://www.nvidia.com/en-us/events/siggraph/)

**Agent-memory landscape:** [Mem0 — State of AI Agent Memory 2026](https://mem0.ai/blog/state-of-ai-agent-memory-2026)

*Press-sourced items (Siri-Gemini internals, Xcode `mcpbridge` mechanics, Core ML→Core AI framing, Dev Summit Europe dates) are tagged as reported above; verify against Apple session videos and official MCP channels before building on them.*
