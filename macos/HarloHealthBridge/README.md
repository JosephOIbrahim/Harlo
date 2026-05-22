# HarloHealthBridge

The Swift KeepAlive helper that owns the `com.apple.developer.healthkit`
entitlement and pushes biometric deltas to the Harlo daemon over a
Unix domain socket / XPC.

This is the ONLY KeepAlive process in Harlo (ADR-0001). It must be
small, event-wakened by HealthKit callbacks, and never poll.

## Building

Requires:

- Xcode 16+ (macOS 26 SDK)
- A signed Apple Developer ID with `com.apple.developer.healthkit`
  provisioning for the bundle ID `com.harlo.healthbridge`.

Without a Developer ID, this code compiles but cannot run with
HealthKit access — macOS rejects the entitlement at runtime.

```sh
swift build -c release
```

## Architecture

```
+-------------------+   HKObserverQuery    +------------------+
|   Apple Watch     | -------------------->|  HarloHealth-    |
|   (HR / HRV /     |                      |  Bridge.app      |
|   sleep / etc.)   |                      |  (KeepAlive)     |
+-------------------+                      +--------+---------+
                                                    |
                                                    | JSON over UDS
                                                    v
                                           +------------------+
                                           |   Harlo daemon   |
                                           |   (0W idle,      |
                                           |    socket-       |
                                           |    activated)    |
                                           +--------+---------+
                                                    |
                                                    | biometric_ingest
                                                    v
                                           +------------------+
                                           | biometric_barrier|
                                           |  → Modulation    |
                                           |    Layer only    |
                                           +------------------+
```

## Invariants

- Never write biometric data to Harlo's SQLite directly. Always go
  through the daemon's `biometric_ingest` route handler. The daemon
  is the only process that owns `twin.db`.
- Persist the HKAnchoredObjectQuery anchor at
  `~/Library/Application Support/Harlo/healthkit_anchor.bin`. On
  disconnect, delete it.
- Drop samples we cannot identify (no schema match) — the Python
  biometric_barrier will reject them anyway; better not to send.
- All log lines go through `os_log` with the `com.harlo.healthbridge`
  subsystem so users can filter them in Console.app.
