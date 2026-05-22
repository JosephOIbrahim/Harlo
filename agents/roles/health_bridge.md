# Health Bridge role

Owns the HealthKit ingestion path, end to end: Swift XPC service →
biometric_barrier → AllostasisTracker.

## Surface

- `macos/HarloHealthBridge/` (Swift)
- `macos/launchd/com.harlo.healthbridge.plist`
- `config/biometric_sample_schema.json`
- `python/harlo/modulation/biometric_barrier.py`
- `python/harlo/modulation/allostatic.py` (biometric methods only)
- `python/harlo/daemon/router.py` (the `biometric_ingest` command)
- `python/harlo/motor/basal_ganglia.py` (composite RED check)
- `tests/test_biometric_barrier/`

## Mandate

- HealthKit signals enrich allostatic load via a SEPARATE ingestion
  path (Rule 9 + ADR-0001).
- HKObserverQuery lives in the Swift bridge. The Harlo daemon stays
  0W idle (Rule 1).
- Apply the freshness window (default 5 min) before any biometric
  sample can flip cognitive_state to RED.

## Hard prohibitions

- Biometric data NEVER enters the trace store, reflex cache,
  composition, elenchus, or bridge. Enforced by the compliance grep
  in CLAUDE.md.
- No KeepAlive on the Harlo daemon, ever. KeepAlive on the
  HealthBridge plist only.
- No timestamp fuzzing on biometric samples in the Modulation Layer
  (Rule 22 applies on the trace path, which biometrics never take).

## Outputs

- Swift code + Python code + tests + `agents/outputs/<task-id>/health-bridge.md`
  documenting the consent flow, freshness behavior, and revocation.
