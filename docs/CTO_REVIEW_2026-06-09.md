# CTO Review — macOS 27 + Apple HealthKit Readiness

**Date:** 2026-06-09 · **Method:** 6-subsystem multi-agent review, adversarial verification
(38 findings confirmed, 2 refuted, ~3M tokens). **Branch:** master @ `e67c2ae`.

This is a **decision record**, not a changelog. No code was changed producing it.
Decisions are proposed as D49+ (continuing the D-lineage; RELEASE_DECISIONS.md ends at D48).
Nothing here is binding until the architect accepts it.

---

## First principles — the one root finding

**Harlo's docs, the 33 Rules, and the marketing describe a system far more complete than
what ships and runs.** A large, careful architecture — Motor Cortex (Rules 23–33), DMN
teardown (Rule 19/S6), consent tokens, the HealthKit bridge, launchd 0W-idle (Rule 1) —
was built *ahead of being wired*, and **nothing flags the seams as unwired.** That is
"undead code": present, documented, advertised, non-functional. For a privacy-sensitive
HealthKit product heading into macOS 27 + (implied) App Review, undead code is the primary
liability — it is exactly what an audit, a contributor, or a diligence reviewer trips on.

**Meta-decision (D49):** Establish one honest "what Harlo is *today*" baseline. Every shipped
surface must either **work** or **visibly declare itself unwired**. Sequence the
macOS-27/HealthKit work behind that honesty. The product that actually runs today is the
**MCP server for Claude Desktop** — make that the spine; treat the standalone-macOS-app +
daemon + HealthKit stack as Phase-5x that must earn "shipped" one working seam at a time.

### Two corrections from adversarial verification (do not over-react)
- **The signed bundle is NOT broken on USD.** Missing `pxr` in the lean bundle falls back to
  `MockUsdStage` gracefully (`src/cognitive_engine.py:96-127`, `stage_type="mock"`). The app
  runs; it runs *mock* USD, not *real*. The advertised "USD-composed cognitive twin" is true
  of the **source/architecture**, demonstrated by the v0.1.2 trial in `.venv312` — not of the
  shipped `.app`. That's a marketing-precision issue, not a crash.
- Raw biometrics **never** hit disk (verified): the barrier + in-memory tracker hold to Rule 9's
  "Modulation Layer only." The HealthKit problem is that the signal **dies** before it reaches
  the coach — not that it leaks.

---

## TIER 0 — Stop shipping lies (small, do first, mostly safe)

| ID | Decision | Evidence | Why now |
|----|----------|----------|---------|
| **D50** | `harlo export --encrypted` must encrypt or be blocked/renamed. Today it writes a **plaintext** dump of the entire memory store under a flag named `--encrypted`. | `python/harlo/cli/commands/export_import.py:10-15` | Worst finding. A flag that promises encryption and delivers plaintext is actively dangerous for a "your memory, your device" product. Pick: implement (age/Keychain-wrapped key) or hard-fail with "not yet implemented." |
| **D51** | CLI motor commands (`plan`/`execute`/`undo`) must return honest "not implemented," not fabricated success-shaped responses from daemon stubs. | `daemon/router.py:47-51,743-770` | Returning `state:"pending"` with no execution is a lie the LLM Actor will trust. |
| **D52** | `decision` MCP tool clamps `gate_status` to `"inhibited"` at the boundary (reject/clamp `approved`/`executing`) until Basal Ganglia wiring lands. | `mcp_server.py:433-460`, `usd_lite/persistence/__init__.py:35-44` | Rule 23/26 on the only **live** motor path. Benign today (nothing executes MotorPrims from disk) but pre-authors a Rule-violating state any future executor would trust. |
| **D53** | Gate the 6 trial/demo MCP tools (`compose_demo`, `lossless_demo`, `anchor_demo`, `p5_state_demo`, `persist_stage`, `decision`) behind `HARLO_TRIAL_TOOLS=1`, OR a separate FastMCP instance the harness uses. Author demo scenes under `DATA_DIR/trial/`, not `stages/`. | `mcp_server.py:310-489`; live `DATA_DIR/stages/` already polluted with `anchor_demo/`, `lossless_demo/`, etc. | Every Claude Desktop client currently sees verifier surface in its tool list; demo `.usda` sit beside real cognitive state — exactly what a HealthKit privacy audit probes. |
| **D54** | `content_hash` must hash (`sha256(message)[:16]`) or be renamed `content_prefix`. Today it stores the first 16 chars of the raw message. | `usd_lite/persistence/__init__.py:118`; live `runtime.usda` shows `content_hash = "wave1 trial prob"` | Poisons every downstream "this field is content-free" assumption — the class of mistake Rule 9 exists to prevent. |
| **D55** | Double-clicking `Harlo.app` must give feedback (open a window / notify / print to a log the user can find) and must NOT permanently suppress the launchd onboarding offer on a silent first run. | `macos/launcher.py:65-93`; first-run marker logic | The v0.1.0 post-release "no visible feedback" symptom + a permanent marker that disables Rule-1 onboarding forever after one silent Finder launch. |

---

## TIER 1 — Decide what Harlo IS (architecture spine — needs architect input)

| ID | Decision | Fork |
|----|----------|------|
| **D56 — IMPLEMENTED (A), 2026-06-10** | **Dual-engine resolution.** `src/` (v9: the USD twin, predictor, schemas) is the real engine but is **never packaged** (maturin `python-source="python"`; reached only via a `sys.path` hack that works solely from a source checkout — `mcp_server.py:81-86`). `python/harlo` (v8 stack) is what ships. **Fork:** (A) promote `src/` into a real `harlo.engine` namespace and package it; (B) formally retire v9 from the shipped path and own that the bundle is the v8 stack. This is THE central architecture decision — everything downstream (USD-in-bundle, predictor, "cognitive twin" claim) depends on it. |
| **D57** | **Composition engines: 3 → 1.** `usd_lite/composer.py` is fully dead (only test + `__init__` import it) → **delete**. `composition/resolver.py` is legacy-live via the v8 daemon → keep only if D56 keeps the v8 daemon. Native `pxr` `subLayerPaths` is the real, load-bearing one (proven by the v0.1.2 trial). Consolidate to native pxr as the single composition story. |
| **D58** | **Encoder triplication.** `sentence_transformers` (dev/test only), `onnx_encoder` (aspirational — its only consumers `Observer`/`PromotionPipeline` are never instantiated outside tests), Rust lexical (the real, shipped path). **Decision:** either wire ONNX-BGE for real or **cut `onnxruntime`+`transformers` from runtime deps** and mark the semantic path dev-only. Right now they're mandatory pip deps for an unwired path — and a silent HuggingFace phone-home (`onnx_encoder.py:30,57`) in a "no cloud" product. |
| **D59** | **`harlo` console-script identity.** The installed `harlo` script is the **MCP stdio server** (`pyproject.toml:25`), but README/docs advertise `harlo doctor`/`intake`/`audit` as if it were the CLI. Decide: `harlo` = MCP server (rename CLI to `harlo-cli`), or `harlo` = CLI with an `--mcp` subcommand. Align docs to the choice. |

---

## TIER 2 — macOS 27 + Apple HealthKit (the explicit ask)

The bridge is **well-architected at the ADR level** (ADR-0001 is genuinely good) and the Swift
is clean, but it is **broken at every seam** and rests on a strategic bet. Decisions:

| ID | Decision | Evidence |
|----|----------|----------|
| **D60 — keystone** | **Route `biometric_force_red`/DEPLETED into a persistent store the coach + MCP read.** Today the `AllostasisTracker` is a **process-local in-memory deque** that dies with the single-connection daemon; `force_red` is computed then discarded and **never reaches the Basal Ganglia** — Rule 9 "High = DEPLETED" and Rule 28 are dead end-to-end. Without this, the entire HealthKit feature produces nothing the user can perceive. Land a small modulation-state row (twin.db) or state file, written by `biometric_ingest`, read by coach/status. | `router.py:972-1023`, `allostatic.py:84-85`, `basal_ganglia.py:66-73` (only writers of `biometric_force_red` are tests) |
| **D61** | **Fix the wire protocol.** Swift sends 4-byte big-endian length-prefixed frames; Python daemon reads newline-delimited JSON → **100% of samples dropped.** Pick length-prefixed framing on **both** sides (Swift is already correct; fix the Python `handle_client` recv loop). | `DaemonWriter.swift:52-56` vs `daemon/main.py:18-34` |
| **D62** | **Fix the path split-brain + sandbox.** Sandboxed bridge writes socket/anchor to its **container**, but the daemon listens at `~/Library/Application Support/Harlo/twind.sock`; the container path also **exceeds the 104-byte `sun_path` limit** and is silently truncated. Use the **App Group container** for both socket and anchor, add `com.apple.security.application-groups` to **Harlo.app**'s (currently empty) entitlements, and verify the socket path length. | `HarloHealthBridge.entitlements:24-25,52-55`, `DaemonWriter.swift:33-45`, `AnchorStore.swift:10-13`, `Harlo.app/Contents/Entitlements.plist` (empty) |
| **D63** | **Graceful fallback when `isHealthDataAvailable()` is false.** Today: `exit(1)` + `KeepAlive{Crashed:true}` = **infinite ~10s relaunch loop on every current Mac**. Idle/sleep instead of exiting into a crash loop. | `main.swift:19-22,41-44`, `com.harlo.healthbridge.plist:34-40` |
| **D64** | **Add `com.apple.developer.healthkit.background-delivery` entitlement.** `enableBackgroundDelivery` is called without it; error is logged-and-swallowed. | `Bridge.swift:32-36`, `HarloHealthBridge.entitlements:14-17` |
| **D65** | **Implement ADR-0001 constraint 1: per-data-type opt-in, default OFF.** The bridge requests **all 9 types unconditionally**; no toggle exists anywhere. Add a config block (read by the bridge) + a settings surface. | `main.swift:25-37`, `config/default_profile.yaml` (no biometric block) |
| **D66 — manifest** | **macOS-27 manifest readiness.** Add `PrivacyInfo.xcprivacy` (absent repo-wide — required for App Store and increasingly for notarization-era trust). HealthKit usage strings currently sit on Harlo.app's Info.plist but the entitlement is on the **bridge** — move the strings to where the entitlement lives. Drop the bogus `NSUserNotificationUsageDescription` (not a real key). Decide `LSMinimumSystemVersion` (13.0 today). | `Harlo.app/Info.plist:52-67`, `*.xcprivacy` (none) |
| **D67 — STRATEGIC** | **Is HealthKit-on-Mac viable for this product, or is the iPhone sidecar now required?** HealthKit-on-Mac needs the user's Health data **on the Mac**. The code bets on macOS-27 Health sync that does not exist on any current Mac (hence D63's crash loop). ADR-0001 "deferred" the iPhone-sidecar streaming. **This decision gates whether the entire bridge is shippable** — resolve it before investing in D60–D66. If macOS 27 does not sync Health to Mac, the sidecar moves from "deferred" to "required." |

> **D67 RESOLVED (2026-06-10, empirical).** Probed on the target machine itself (Darwin 27.0.0):
> `HKHealthStore.isHealthDataAvailable()` → **false**; no Health.app; no local Health store.
> The API surface exists (HealthKit links; `enableBackgroundDelivery` is `macos(13.0)+` in the
> local SDK) but the **data layer is absent on macOS 27**. Verdict: the Mac-native bet fails
> today → **the iPhone sidecar moves from "deferred" to "required"** for real biometric signal
> (needs its own ADR — it was explicitly rejected-deferred in ADR-0001 and reopening is an
> architect call). Consequences taken: D60–D63 implemented anyway (they are signal-source-
> agnostic — a sidecar pushes the same JSON through the same socket/barrier/tracker pipeline),
> and the bridge stays in-tree as a **dormant** Mac-native path: D63's clean-exit means it
> sleeps harmlessly until some future macOS ships Health-on-Mac, at which point it lights up
> with zero code change. D68 (build/sign/CI for the bridge) stays gated until the sidecar ADR.
| **D68** | **Bring HealthBridge into the build/sign/CI pipeline** (Phase 5B): add to `setup_py2app.py` DATA_FILES (plist), add the xcodegen+xcodebuild+sign job to `macos-build.yml`, ship in the DMG, fix bundle-ID drift (`com.harlo.healthbridge` vs app's `com.josephibrahim.harlo`). Do this **after** D67 says "go." |

---

## TIER 3 — Rule 1 (0-watt idle) keystone is broken on macOS

| ID | Decision | Evidence |
|----|----------|----------|
| **D69** | **Implement launchd socket activation.** Activation is **systemd-only** (`LISTEN_FDS`/`fromfd(3)`); launchd never sets that, so the activated daemon falls into the dev fallback, **`os.unlink`s launchd's own socket node**, rebinds privately, and strands the waking client. Use `launch_activate_socket()` (the macOS API). This is the core mechanism behind the headline Rule-1 claim. | `daemon/main.py:70-95` |
| **D70** | **launchd plists: literal `~` never expands.** `SockPathName`/`StandardOutPath` use `~` → the socket can never bind where clients look. Installer rewrites only `ProgramArguments[0]`. Extend `macos_install_daemon.py` to absolute-path the socket + log paths at install. | `com.harlo.daemon.plist:39,46,48`; `macos_install_daemon.py:32-33` |
| **D71** | **Make Rule-1 installable from the shipped app.** Bundled installer looks for plists at a dev-tree path absent from `Resources/`; `FileNotFoundError` before any `launchctl`. Bundle the plists + add a bundle-relative fallback. | `macos_install_daemon.py:101-105`, `setup_py2app.py:68-74` |
| **D72** | **Daemon: accept-loop, not single-accept; don't close all sessions on idle.** One connection per activation rate-limits HealthKit ingest to ~1 batch/5s (with `ThrottleInterval=5`) and drops bursts; `graceful_shutdown` force-closes **all** active sessions on every 30s idle exit, so sessions can't outlive one activation window. | `daemon/main.py:84-97`, `lifecycle.py:108-118` |
| **D73** | **DMN teardown (Rule 19/S6) is dead code** — `abort()` has no callers, the 30s budget is never enforced, synthesis is a placeholder, the daemon kills the synthesis thread at ~0s, and the Rule-30 temp path is `/dev/shm` (**nonexistent on macOS**). Either wire it or mark it explicitly unimplemented. | `dmn_teardown.py:56-103`, `config.py:70,82-84` |

---

## TIER 4 — Hygiene (deps, versions, CI, dev env, at-rest)

| ID | Decision |
|----|----------|
| **D74** | **Canonical dev env = `.venv312`.** `.venv314` `import harlo` is broken (stale `.so`), yet the Makefile defaults to it. Fix Makefile default + document one venv story; four docs currently disagree. |
| **D75** | **Prune phantom runtime deps.** Cut `maturin` (build tool), `onnxruntime`, `transformers`, `xgboost`, `scikit-learn`, `joblib` from `[project].dependencies` (unimported by the shipped package; gated by D58); **add `pyyaml`** (soft-imported, currently missing). |
| **D76** | **Tighten the USD pin** to the validated band `usd-core>=26.5,<27` before the first USD-27 wheel silently becomes the resolved substrate. |
| **D77** | **Version coherence.** Make `harlo.__version__` the single runtime source; CLI `--version`, MCP instructions string, coach context header, and daemon payloads still report `v8.0/8.0.0`; `INSTALL.md` says `3.3.1`; CHANGELOG has zero v0.1.x entries. |
| **D78** | **Stamp `CFBundleVersion`** at build time (monotonic from CI/git) — frozen at `1` across the whole release line; every future updater (Sparkle), LaunchServices, and crash triage keys on it. |
| **D79** | **`wave1_harness.py` → `harness/`**, derive `HARLO_BIN` from `sys.executable`/env (hardcodes `/Users/rustybeard/...` in a public repo), and add a small CI job so the flagship USD-trial claim is regression-guarded. |
| **D80** | **At-rest perms.** `DATA_DIR` → 0700, `twin.db`/audit/export → 0600 at creation; chmod the dev-mode socket after bind. Document the at-rest stance (FileVault-reliant today; SQLCipher/Keychain-wrapped key as roadmap) in an ADR. |
| **D81** | **`src/engine_config.py` vs `daemon/config.py` path split-brain** — `engine_config` defaults `STAGE_DIR`/`MODEL_PATH` to the **repo tree**, so installed runs write state into the source checkout. Make `daemon/config.py` the single path authority. |

---

## Recommended sequencing

1. **TIER 0** (D50–D55) — small, safe, stops active lies. Ship as v0.1.4.
2. **D67** (HealthKit-on-Mac viability) — **decide before** spending on D60–D66; it gates the bridge.
3. **D56** (dual-engine fork) — unblocks D57/D58 and the "USD twin" marketing precision.
4. **D60** (biometric→coach keystone) + **D61/D62/D63** — the seams that make HealthKit *do something*.
5. **TIER 3** (Rule 1) — the 0W-idle headline; meaningful effort, do as a focused sprint.
6. **TIER 4** — fold into each PR opportunistically; D74 (dev env) first so contributors aren't blocked.

## Device-evidence addendum (2026-06-10) — D82/D83

Architect connected hardware during the D67 follow-up; relevance reviewed under
delegated CTO authority:

- **D82 — iPhone (USB-connected, not data-enumerable).** The phone is the real home of
  the Health data the Mac lacks (D67). USB data access is currently blocked by missing
  trust pairing + tooling (no Xcode `devicectl`; CommandLineTools only) — so the sidecar's
  v1 transport is **LAN/Bonjour token-paired push**, with **USB via usbmuxd as the
  preferred v2** once pairing is set up (zero-radio, privacy-maximal). Full decision:
  `docs/adr/0002-iphone-sidecar.md`.
- **D83 — Apple Watch Ultra (v1) on unsupported watchOS.** No impact on the chosen
  architecture: Watch→iPhone Health sync continues on old watchOS. It DOES rule out any
  watch-app dependency (real-time HR streaming needs a current-SDK watch target) — which
  ADR-0001's trend-based analysis already rejected. Hardware constraint and product
  analysis agree; recorded in ADR-0002 as a binding "no watch app" scope line.

**D56 executed as fork (A)** the same day: `src/` → packaged `harlo.engine`
(git-mv with history), all imports rewritten, `sys.path` hacks deleted,
`engine_config` paths re-rooted to DATA_DIR (closing most of D81), compliance greps
repointed. Full-suite failure set byte-identical to the pre-move baseline; engine boots
`stage_type=real_usd`, `predictor=yes` from the packaged module; predictor joblib
unpickle verified post-move.

## Risk register
- **Highest:** D50 (plaintext "encrypted" export) — privacy exposure shipping today.
- **Credibility:** D67 unresolved means D60–D68 could be effort spent on a non-viable platform bet.
- **Audit triggers:** D53 (demo tools + demo scenes in user data dir), D66 (no privacy manifest),
  D64 (background-delivery entitlement) — the three a HealthKit App Review hits first.
