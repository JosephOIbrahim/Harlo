# NEXT — Resume point after the HarloPulse loop landing (2026-06-10)

State captured at v0.1.6 on master, end of a two-day arc (June 9–10) that took
HarloPulse from scaffold to a field-verified push-on-arrival loop on real
hardware, adopted four WWDC26 sessions into the codebase, and merged PRs
#12–#15.

## Where we are

**The loop is live and autonomous.** Apple Watch → iPhone HealthKit
(background delivery) → HarloPulse delta push (HMAC, 48h window, chunked) →
Mac launchd socket (TCP 48653, 0W idle) → `pulse listen` → biometric barrier →
D60 modulation verdict → `coach`/`status` in Claude Desktop + Claude Code.
First organic biometrics flowed 2026-06-10 15:15 local; Desktop's coach
surfaces the modulation block.

**Landed this arc (v0.1.3 → v0.1.6):**
- PR #12 — HarloPulse scaffold (ADR-0002): pairing CLI, listener, iOS app
- PR #13 — App Intents P0: Sync/Status/Toggle intents, snippet view, shortcuts
- PR #14 — frontier docs: App Intents adoption plan (12-pattern matrix),
  FM provider review (+ live-verified `apple_fm_sdk` Python addendum),
  code-along addendum, HealthKit collaboration report
- PR #15 — code-along P1: OpenIntent + onscreen awareness (iOS 18.2+)
- Direct to master: device-deploy fixes, host-candidate fix (scutil Bonjour),
  1 MiB frame fix (48h lookback + 500-sample chunks), launchd socket
  activation for `pulse listen` + `com.harlo.pulse` plist + structural tests

**Verified:** signed device build on Xcode 27 toolchain, installed + launched
on the iPhone; lean-bundle suite 1,381 passed / 5 skipped; criterion
benchmarks landed in README (100k-trace search 0.844 ms median — Rule 3 holds
with 2.4× headroom).

## Toolchain facts (will bite again if forgotten)

- Xcode 27 beta lives at `/Applications/Xcode-beta.app`; `xcode-select` still
  points at CLT (no sudo policy) — prefix builds with
  `DEVELOPER_DIR=/Applications/Xcode-beta.app/Contents/Developer`.
- `xcodegen` is a source build at `/opt/homebrew/bin/xcodegen` (brew refused
  on macOS 27). Do NOT re-add an `info:` block to `project.yml` — it
  regenerates Info.plist and destroys the HealthKit usage strings.
- Device builds need `-allowProvisioningUpdates` AND
  `-allowProvisioningDeviceRegistration` the first time; after that, plain
  GUI-equivalent builds work.
- The lean venv (`.venv312`) excludes the ML stack by design:
  `test_provider`, `test_encoder/test_semantic`, `test_onnx`, one tactical
  test fail on ImportError (`anthropic`, `sentence_transformers`). Not
  regressions — the full bundle runs them.

## Next-session candidates, ranked

1. **v0.1.6 follow-through** — verify the GitHub release renders, badges
   resolve, mermaid loop diagram renders on github.com.
2. **Apple Developer secrets** (carried) — 8 secrets per
   `docs/APPLE_SECRETS_SETUP.md`; unblocks signed/notarized DMG on tag push.
3. **HarloGlance** (P1, adoption plan §5) — Mac menu-bar status app; py2app
   can't host App Intents, needs a small Swift host.
4. **HdAppleFM spike** — pure-Python Foundation Models delegate via
   `apple_fm_sdk` (feasibility proven live 2026-06-09); System 1/System 2
   mapping to `reasoningLevel`.
5. **Pulse plist installer wiring** — materialize `com.harlo.pulse.plist`
   via `scripts/macos_install_daemon.py` (rides Phase 5B / D68).
6. **CHANGELOG.md backfill** for the v0.1.x line (D77 leftover).
7. **Icon Composer pass** — HarloPulse app icon; Reality Composer Pro
   brain.usda render-the-mind demo (parked creative).
8. **WWDC follow-up reminder** — Monday June 15, 10:00 AM calendar slot
   already exists; agenda: assistant-schema gap, FM provider timeline.

## Known fragilities (carried, still true)

- macos-build `build` job is advisory on PRs (continue-on-error), strict on
  tag pushes. Without Apple secrets, tag pushes skip the signing chain.
- py2app needs the 3.12 venv (`make build-macos`); modulegraph breaks on 3.14.
- gh CLI OAuth on this machine cannot hold `workflow` scope — workflow-file
  edits need the browser or a fine-grained PAT.

## Pointers

- Loop design history: `docs/adr/0002-iphone-sidecar.md`
- WWDC26 analyses: `docs/frontier/`
- Signing runbook: `docs/SIGNING.md` · operator checklist: `docs/APPLE_SECRETS_SETUP.md`
- CTO review of the orchestrated sprint: `docs/CTO_REVIEW_2026-06-09.md`
