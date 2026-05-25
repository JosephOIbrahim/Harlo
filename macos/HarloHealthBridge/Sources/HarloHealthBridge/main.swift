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
    log.error("HealthKit not available on this host. Exiting.")
    exit(1)
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
        log.error("HealthKit authorization not granted; exiting.")
        exit(2)
    }
    log.info("HealthKit authorization granted; installing observers.")
    Bridge.shared.installObservers(types: readTypes, store: healthStore)
}

// Keep the run loop alive — HKObserverQuery callbacks fire on it.
// The daemon socket connection is event-driven; we never poll.
RunLoop.main.run()
