// HarloHealthBridge — KeepAlive helper owning the HealthKit entitlement.
//
// ADR-0001: this is the ONLY KeepAlive process in the Harlo stack.
// Wakes on HKObserverQuery callbacks, fetches deltas via
// HKAnchoredObjectQuery, pushes them as JSON to the Harlo daemon via
// a Unix domain socket. The daemon's biometric_ingest route validates
// against config/biometric_sample_schema.json and forwards to the
// Modulation Layer only — biometric data never enters the trace
// store.

import Foundation
import HealthKit
import OSLog

let log = Logger(subsystem: "com.harlo.healthbridge", category: "lifecycle")

let healthStore = HKHealthStore()

guard HKHealthStore.isHealthDataAvailable() else {
    // D63 + D67: as of macOS 27, isHealthDataAvailable() is false on
    // every Mac (verified empirically — the API links but the data
    // layer is absent; Health data lives on iPhone/Watch). exit(0) is
    // a SUCCESSFUL exit: the launchd KeepAlive dict only relaunches on
    // crash, so a clean exit is dormancy, not a 10s relaunch loop.
    // If a future macOS ships Health-on-Mac, this branch stops firing
    // and the bridge lights up unchanged. Until then the real signal
    // path is the iPhone sidecar (D67 — separate ADR).
    log.notice("HealthKit data not available on this Mac (expected through macOS 27). Bridge going dormant — exiting cleanly.")
    exit(0)
}

// Types Harlo can ingest. Mirrors config/biometric_sample_schema.json.
let readTypes: Set<HKObjectType> = [
    HKObjectType.quantityType(forIdentifier: .heartRate)!,
    HKObjectType.quantityType(forIdentifier: .heartRateVariabilitySDNN)!,
    HKObjectType.quantityType(forIdentifier: .restingHeartRate)!,
    HKObjectType.quantityType(forIdentifier: .respiratoryRate)!,
    HKObjectType.quantityType(forIdentifier: .activeEnergyBurned)!,
    HKObjectType.quantityType(forIdentifier: .stepCount)!,
    HKObjectType.categoryType(forIdentifier: .sleepAnalysis)!,
    HKObjectType.quantityType(forIdentifier: .oxygenSaturation)!,
    HKObjectType.quantityType(forIdentifier: .bodyTemperature)!,
]

healthStore.requestAuthorization(toShare: nil, read: readTypes) { ok, err in
    if let err = err {
        log.error("HealthKit auth error: \(err.localizedDescription)")
    }
    guard ok else {
        // D63: denial is a user decision, not a crash — exit cleanly so
        // KeepAlive{Crashed:true} does not relaunch-loop the consent
        // sheet. Re-enabling from Harlo settings restarts the bridge.
        log.notice("HealthKit authorization not granted; exiting cleanly.")
        exit(0)
    }
    log.info("HealthKit authorization granted; installing observers.")
    Bridge.shared.installObservers(types: readTypes, store: healthStore)
}

// Keep the run loop alive — HKObserverQuery callbacks fire on it.
// The daemon socket connection is event-driven; we never poll.
RunLoop.main.run()
