# ADR-0001: Opt-in HealthKit signals enrich allostatic load

- **Status**: Accepted (constitutional amendment to Rule 9)
- **Date**: 2026-05-22
- **Touches**: Rule 9 (ALLOSTATIC LOAD), Rule 1 (0W idle),
  Rule 8 (JSON Barrier), Rule 22 (timestamp fuzzing),
  Rule 27 (DEPLETED downgrade), Rule 28 (RED kills motor)

## Context

Rule 9 originally read: *"Token velocity + prompt frequency.
**Software only**."* The "software only" clause deliberately kept
biometric sensors out of the cognitive loop — both as a privacy
posture and to avoid the engineering cost of long-running observers
contradicting Rule 1's 0W idle.

For Harlo to be a useful macOS 26.5 application that supports the
user as an extension of their body, the Modulation Layer needs a
signal source richer than "tokens per minute". Apple HealthKit is
the canonical macOS surface; opt-in HR / HRV / sleep / activity from
an Apple Watch turns a software-only fatigue heuristic into a
grounded one without inventing proprietary sensors.

## Decision

Rule 9 is amended to:

> ALLOSTATIC LOAD: Token velocity + prompt frequency, plus OPTIONAL
> opt-in biometric signals via the biometric_barrier per ADR-0001.
> Biometric signals default OFF per data type and never enter the
> trace / reflex pipelines — they live in the Modulation Layer only.
> Samples older than the configured freshness window (default 5 min)
> cannot drive cognitive_state="RED". High = DEPLETED = refuse to
> wake System 2.

## Constraints (binding, not aspirational)

1. **Off by default, per data type.** No data flows until the user
   grants HealthKit permission *and* toggles the data type on in
   Harlo's settings.
2. **Separate ingestion path.** `python/harlo/modulation/biometric_barrier.py`
   validates against `config/biometric_sample_schema.json`. Biometric
   data **never** crosses into `bridge/`, `elenchus/`, the trace
   store, or the reflex cache. A compliance grep enforces this.
3. **Process isolation.** HealthKit observers live in
   `macos/HarloHealthBridge` — a separate Swift app + XPC service
   with `KeepAlive=true`. The Harlo daemon stays 0W idle and is
   woken via socket activation only when the bridge has a delta
   batch.
4. **Freshness window.** Default 5 minutes. Samples older than the
   window can update DEPLETED state but cannot transition cognitive
   state to RED — Apple Watch → Mac latency is 5–20+ minutes, so a
   stale HR spike must not inhibit motor.
5. **Dignified revocation.** Disabling biometrics via Harlo settings
   `launchctl unload`s the bridge and deletes the persisted
   HealthKit anchor. No silent re-enable.
6. **Anchors untouched.** Biometric signals never modify anchor
   gains (Rule 7, Rule 10). SAFETY/CONSENT/KNOWLEDGE/CONSTITUTIONAL
   remain structural 1.0.

## Alternatives considered

- **Keep "software only".** Rejected: leaves a real signal source
  untapped, and "opt-in with a hard barrier" is a more honest answer
  than "categorically refuse hardware."
- **Integrate HealthKit into the Harlo daemon directly.** Rejected:
  long-running HKObserverQuery would violate Rule 1. Separate
  process is the minimal concession.
- **Push biometrics through the core Blood-Brain Barrier.** Rejected:
  conflates per-user mood/fact memory with sensor telemetry. They
  have different lifetimes, different retention, different consent.
- **iPhone-sidecar streaming over local network for real-time HR.**
  Deferred. Doubles surface area (a second app to maintain) for a
  capability the allostatic load doesn't actually need —
  trend-based DEPLETED detection over minutes is what's useful.

## Consequences

- Compliance grep added to CLAUDE.md:
  `grep -rn "biometric" python/harlo/elenchus/ python/harlo/bridge/`
  MUST return 0.
- A second launchd unit (`com.harlo.healthbridge.plist`) ships with
  the app. It is the only KeepAlive process; the Harlo daemon plist
  stays socket-activated.
- The macOS UX must include a HealthKit consent screen with
  per-data-type toggles and an honest latency disclaimer.
- A new prerequisite step (acquiring an Apple Developer ID with
  HealthKit entitlement provisioning) gates the bridge from shipping
  in signed builds. Until then, the bridge is Swift + Python code
  with no signed entitlement.
