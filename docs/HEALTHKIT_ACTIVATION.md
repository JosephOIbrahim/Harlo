# HealthKit / Apple Watch Activation — runbook

Status as of 2026-06-19. Resume point for connecting a real Apple Watch.

## Where we are

- **Stage 1 (GO):** macOS 27 / SDK 26.5 vends `HealthKit.framework`; the bridge
  builds clean (`swift build --package-path macos/HarloHealthBridge -c release`).
  Fixed a Swift exclusivity bug in `DaemonWriter.swift` (staged).
- **Stage 3a (VERIFIED):** the entire Mac-side pipeline passes on this machine —
  `biometric_ingest` → `biometric_barrier` → `AllostasisTracker` →
  `force_red`/DEPLETED → Basal Ganglia motor inhibition, plus the Swift↔Python
  wire contract (32 tests green).
- **Paused at Stage 2** for Apple provisioning (operator-only).

## What the entitlements actually require

`Sources/HarloHealthBridge/HarloHealthBridge.entitlements` declares:
- `com.apple.developer.healthkit` = true (+ empty `.access` array = standard
  sample types, no clinical records)
- `com.apple.security.app-sandbox` = true
- `com.apple.security.application-groups` = `["233JSS4X69.com.harlo.shared"]`

So the App ID needs **both HealthKit and App Groups** capabilities, and the App
Group `233JSS4X69.com.harlo.shared` must be registered.

## Provisioning (operator — Team 233JSS4X69)

PREREQUISITE (checked 2026-06-19): this Mac currently has **0 codesigning
identities** and **no provisioning profiles** — it is not signing-ready yet.
Before any profile exists you must: (1) sign Xcode into the Apple ID tied to
Team 233JSS4X69 (Xcode → Settings → Accounts → +) — this installs the
"Apple Development" cert into the keychain; (2) confirm that team has an ACTIVE
PAID Developer Program membership — HealthKit is a restricted entitlement and a
free Personal Team cannot provision it.

EASIEST PATH — Xcode automatic signing (recommended for personal use): once
signed in with a paid membership, building with automatic signing +
`xcodebuild -allowProvisioningUpdates` makes Xcode auto-create the App ID,
enable HealthKit + the App Group, register this Mac, and create + install the
profile. No portal clicks, no hand-managed files. The profile lands at
`~/Library/Developer/Xcode/UserData/Provisioning Profiles/`.

MANUAL PATH (developer.apple.com) — only if you prefer doing it by hand. Two
variants by goal:

- **Path A — Development signing (recommended to use it on YOUR Mac).** Apple
  Development cert + a Development provisioning profile + your Mac registered as a
  dev device. No notarization. Fastest to live data. (project.yml is set for
  Developer ID; for a local dev build I'll override the signing config.)
- **Path B — Developer ID (only to distribute to others).** Developer ID
  Application cert + a Developer ID profile authorizing the entitlements +
  notarization. NOTE: confirm in the portal that HealthKit is permitted for
  direct (non-App-Store) distribution — that policy is the open question.

Portal steps (both paths):
1. Identifiers → App ID `com.harlo.healthbridge` (explicit, not wildcard) →
   enable **HealthKit** + **App Groups**.
2. Identifiers → App Groups → register `233JSS4X69.com.harlo.shared` (match the
   entitlement string exactly) and associate it with the App ID.
3. (Path A) Devices → register this Mac's provisioning UDID.
4. Profiles → create a **Development** (A) or **Developer ID** (B) profile for the
   App ID + your cert → download the `.provisionprofile`.
5. Hand the profile to the build (or drop it in place) → I build + sign + install.

Local sanity gate: `bash scripts/check_signing_readiness.sh` (already checks the
entitlements parse, HealthKit declared, Team ID).

## ⚠️ Known build-time gap to fix before it runs sandboxed

With App Sandbox ON, the bridge cannot reach paths outside its container, but:
- `AnchorStore.swift` writes the anchor to `~/Library/Application Support/Harlo/`
  (outside the sandbox) — the entitlements intend the **App Group container**
  `~/Library/Group Containers/233JSS4X69.com.harlo.shared/`.
- `DaemonWriter.swift` connects to `~/Library/Application Support/Harlo/twind.sock`
  — also outside the sandbox container.

Fix at Stage 2 (build time): point the anchor + the daemon socket at the shared
App Group container (and have the daemon bind/own its socket there), or the
sandboxed bridge will be denied access to the daemon. Tracked here so it isn't
forgotten.

## Resume (when the profile is ready — I drive)

1. `brew install xcodegen` → `xcodegen generate`.
2. Fix the sandbox/App-Group paths (above).
3. `xcodebuild` the `.app` with the profile embedded → sign → install via
   `python scripts/macos_install_daemon.py install --healthbridge` → load launchd.
4. Operator: approve the HealthKit permission dialog; confirm Watch→iPhone→Mac
   Health sync; trigger a sample (workout / elevated HR).
5. `log stream --predicate 'subsystem == "com.harlo.healthbridge"'` + `harlo
   doctor` → confirm real HR/HRV → DEPLETED/RED.
