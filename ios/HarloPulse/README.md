# HarloPulse

The iPhone companion app that is Harlo's biometric signal source
(ADR-0002). The phone is where Health data actually lives — D67 showed
HealthKit data does not exist on any Mac through macOS 27. HarloPulse
reads only the types you switch on, batches trends, and pushes them
over your home network to `harlo pulse listen` on the Mac, where raw
samples die in the Modulation Layer exactly as Rule 9 demands —
nothing biometric ever touches disk, only the derived verdict.

## Build

**Verified 2026-06-10:** the full app typechecks AND builds unsigned
(`xcodebuild … CODE_SIGNING_ALLOWED=NO`) against the iOS 26.5 SDK on
the dev Mac. What remains is signing + the device trust dialog —
Xcode-interactive by nature.

> macOS 27 gotcha: `brew install xcodegen` refuses (no bottle, and the
> formula rejects Xcode 26.5 as "too outdated"). A source-built binary
> is already installed at `/opt/homebrew/bin/xcodegen` (SPM build of
> v2.45.4). To rebuild it: `git clone --depth 1
> https://github.com/yonaskolb/XcodeGen && cd XcodeGen &&
> DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swift build
> -c release`.

```sh
cd ios/HarloPulse
xcodegen generate
open HarloPulse.xcodeproj
```

In Xcode:

1. Signing is `Automatic` under team `233JSS4X69` (set in project.yml).
   Xcode will mint the HealthKit + background-delivery provisioning
   for `com.josephibrahim.harlo.pulse` on first build.
2. Select your iPhone as the run destination and Run.
3. First install on-device: Settings → General → VPN & Device
   Management → trust the developer certificate.

The generated `HarloPulse.xcodeproj` is gitignored; regenerate any
time.

## Pair

On the Mac:

```sh
harlo pulse pair
```

This prints a 6-word pairing token, host candidates, and the port.
Only the token's hash is stored (0600); re-running `pair` revokes the
old token.

On the phone: enter the 6 words, the host (try the `.local` name
first, then the LAN IP), and the port. Tap **Pair**, then accept the
Local Network permission prompt when iOS shows it.

## Enable data

Every data type toggle is **OFF by default** (ADR-0001 constraint 1 /
D65). Turn on only what you want — each toggle triggers its own Health
consent sheet for exactly that type, nothing more.

## Receive

On the Mac:

```sh
harlo pulse listen
```

Then tap **Push Now** on the phone for the first test. The listen
session prints device, frames, accepted count, and the derived verdict
(depleted / force_red / biometric_load).

Background cadence expectations: HealthKit background delivery is
OS-scheduled — pushes can be hours late or coalesced, and in v1 they
only land while `harlo pulse listen` is up (it is a foreground CLI
that exits on idle; no daemon). That is fine: the product need is
trend, not stream (ADR-0002 constraint 1). v1.1 is expected to add a
launchd socket-activated listener.

## Unpair / revoke

- Phone: **Unpair** wipes the Keychain pairing and all HealthKit
  anchors (ADR-0002 constraint 3).
- Mac: `harlo pulse unpair` deletes the token hash, so the phone can
  no longer authenticate. `harlo pulse pair` again to rotate.

## Known v1 limits

- Bonjour discovery is deferred (the Mac side would need a new
  dependency) — manual host:port entry is the only working path. The
  phone's NWBrowser code is compiled but dormant for v2.
- The Mac listener is a foreground CLI; pushes land only while it
  runs.
- Trend cadence, not real-time: no persistent connections, no watch
  app (out of scope per ADR-0002).
- No nonce replay cache: an attacker on the same LAN who captures an
  auth frame can replay it within the 300 s freshness window.
  Accepted at the household-network boundary; v2 should add a nonce
  LRU or per-connection challenge.
