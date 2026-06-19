# ADR-0002: iPhone sidecar is the biometric signal source

- **Status**: Accepted (delegated CTO authority, 2026-06-10; architect
  pre-approved the decision class — ratification note welcome)
- **Date**: 2026-06-10
- **Supersedes in part**: ADR-0001's "iPhone-sidecar streaming —
  Deferred" alternative
- **Touches**: Rule 1 (0W idle), Rule 9 (biometrics in Modulation
  Layer only), D60–D67 (CTO review 2026-06-09)

## Context

ADR-0001 bet on HealthKit-on-Mac: a sandboxed Swift helper
(HarloHealthBridge) reading Health data locally. **D67 falsified the
bet empirically on the target machine** (Darwin 27.0.0 / macOS 27):
`HKHealthStore.isHealthDataAvailable()` returns **false**, there is no
Health.app and no local Health store. The HealthKit API links on macOS
(SDK marks `enableBackgroundDelivery` as `macos(13.0)+`) but the data
layer does not exist on any Mac through macOS 27. Health data lives on
the iPhone (synced from the Watch).

Hardware facts recorded at decision time (architect's desk):

- **iPhone**: present, USB-connected — but not enumerable as a USB
  data device from this Mac session (no visible trust pairing; no
  Xcode `devicectl`; CommandLineTools only). USB data access requires
  pairing trust plus tooling that is not currently set up.
- **Apple Watch Ultra (v1)**: the architect's sensor source, no longer
  supported by current watchOS. **This does not impair the design**:
  Watch→iPhone Health sync continues on the old watchOS. What it does
  rule out is any dependency on a *watch app* (real-time HR streaming
  via HKWorkoutSession requires one, and would require a current
  watchOS SDK target). ADR-0001 already concluded real-time streaming
  is unnecessary — trend-based DEPLETED detection over minutes is the
  product need. The hardware constraint and the product analysis
  agree.

## Decision

Build **HarloPulse** — a minimal iOS companion app that is the sole
biometric signal source for Harlo:

1. **HealthKit on the phone, where the data actually is.** HarloPulse
   holds the HealthKit read entitlement (standard on iOS, unlike the
   Mac's restricted story), reads the same 9 types as the Mac bridge
   (mirroring `config/biometric_sample_schema.json`), per-type opt-in
   default OFF (ADR-0001 constraint 1 / D65 applies to the iOS UI).
2. **The Mac-side contract is already built and stays unchanged.**
   HarloPulse emits the exact existing wire format: JSON matching
   `biometric_sample_schema.json`, 4-byte big-endian length-prefixed
   frames (the daemon speaks this since D61), validated by
   `biometric_barrier` (Rule 9), tracked by `AllostasisTracker`,
   persisted as derived-verdict-only via the D60 `modulation_state`
   store, surfaced in coach/status. **Zero new Mac ingest code.**
3. **Transport v1: local network, token-paired.** Bonjour discovery +
   a pairing token displayed by `harlo pulse pair` (HMAC pattern
   reused from the OOB consent token design), pushing to a Mac
   listener that hands frames to the existing daemon socket path.
   LAN-only, no cloud relay — the "your memory, your device" posture
   holds at the household-network boundary. This is the first
   sanctioned network listener in Harlo; it exists because of this
   ADR (per the HealthBridge entitlements note that any TCP requires
   an ADR).
4. **Transport v2 (preferred when available): USB via usbmuxd.**
   Zero-radio, privacy-maximal, and matches the architect's plugged-in
   workflow. Direction inverts (Mac initiates to the phone's listening
   port over the cable), which suits trend-cadence pulls. Deferred to
   v2 because it depends on device trust pairing + tooling that is
   not currently in place (empirical check above) — v1 must not be
   blockable by a cable.
5. **Watch app: explicitly out of scope** (hardware constraint +
   trend-based product need, above).
6. **HarloHealthBridge stays in-tree, dormant.** D63's clean-exit
   means it sleeps at zero cost. If a future macOS ships Health-on-
   Mac, the Mac-native path lights up with no code change and this
   ADR's sidecar becomes the redundant source. D68 (bridge build/CI)
   stays gated until then or until this ADR ships HarloPulse.

## Constraints (binding)

1. Cadence is **trend, not stream**: batched pushes on HealthKit
   background delivery / app-refresh cadence. No persistent
   connections; the Mac listener hands off and exits (Rule 1 spirit).
2. Raw samples die in the Modulation Layer exactly as today — the
   sidecar changes the SOURCE, never the Rule 9 containment.
3. Pairing is explicit and revocable: unpair deletes the token and
   the phone-side anchor state (mirrors ADR-0001's dignified
   revocation).
4. Freshness window semantics unchanged (stale samples cannot drive
   RED; D60's 30-min verdict staleness on top).

## Alternatives considered

- **Encrypted-iPhone-backup parsing on the Mac** (Health data is in
  encrypted local backups): rejected — Apple-unsupported schema,
  fragile, and it would land the user's complete raw Health history
  on the Mac, which Rule 9's containment philosophy exists to avoid.
- **Watch app for real-time HR**: rejected (out of scope above).
- **Wait for Health-on-Mac**: rejected as the primary plan — D67 shows
  it does not exist through macOS 27; waiting leaves the entire
  biometric layer dead indefinitely. The dormant bridge preserves the
  option at zero cost.

## Consequences

- A second app target (iOS) enters the repo (`ios/HarloPulse/`,
  future PR): Xcode project, HealthKit entitlement (standard iOS
  provisioning under team 233JSS4X69), TestFlight or dev-signed
  personal install.
- The Mac gains a small paired-listener component (`harlo pulse`
  CLI + launchd socket-activated listener) — designed in the
  HarloPulse PR, reusing D61 framing end-to-end.
- ADR-0001's Mac-bridge constraints (per-type opt-in, freshness,
  anchor isolation) transfer to HarloPulse verbatim.
