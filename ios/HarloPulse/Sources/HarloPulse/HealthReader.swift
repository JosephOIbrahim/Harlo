// HealthReader — HealthKit observation + delta fetch for enabled types.
//
// Mirrors macos/HarloHealthBridge/Sources/.../Bridge.swift (observer +
// anchored-query shape, handler-based) with two deliberate inversions:
//
//   1. D65: authorization is requested per type, at the moment its
//      toggle turns ON — never the full set up front (the Mac bridge's
//      request-everything mistake, inverted).
//   2. Anchor commit happens ONLY in the push-success callback. A
//      failed or unpaired push leaves the anchor untouched, so the
//      same samples are re-fetched next cycle (no data loss). The
//      tradeoff: a crash between send and commit re-delivers the same
//      samples — duplicates are possible. AllostasisTracker treats
//      samples as a rolling window, so duplicates only skew load
//      slightly; acceptable at trend cadence (ADR-0002 constraint 1).
//
// Anchors persist in UserDefaults under "pulse.anchor.<hk identifier>"
// via NSKeyedArchiver secure coding. Toggle-off stops the query,
// disables background delivery, and deletes the anchor. Unpair wipes
// all anchors (ADR-0002 constraint 3).

import Foundation
import HealthKit
import OSLog

final class HealthReader {

    private let log = Logger(subsystem: "com.josephibrahim.harlo.pulse", category: "health")
    private let store = HKHealthStore()
    private var activeQueries: [String: HKObserverQuery] = [:]

    /// Injected by PulseModel: sends encoded samples to the Mac via
    /// PulseLink. The Bool in the callback (push success) is the
    /// anchor-commit signal.
    var push: (([[String: Any]], @escaping (Bool, String) -> Void) -> Void)?

    // MARK: - Enable / disable (driven by the per-type toggles)

    func enable(_ type: PulseType) {
        guard HKHealthStore.isHealthDataAvailable() else {
            log.error("HealthKit not available on this device")
            return
        }
        // D65: ask for ONLY this type. Re-requesting an already-granted
        // type is a no-op (no sheet), so this is safe on every launch.
        store.requestAuthorization(toShare: nil, read: [type.objectType]) { [weak self] ok, err in
            guard let self = self else { return }
            if let err = err {
                self.log.error("auth error for \(type.rawValue): \(err.localizedDescription)")
                return
            }
            guard ok else {
                self.log.notice("authorization not granted for \(type.rawValue)")
                return
            }
            self.installObserver(for: type)
        }
    }

    func disable(_ type: PulseType) {
        if let query = activeQueries.removeValue(forKey: type.rawValue) {
            store.stop(query)
        }
        store.disableBackgroundDelivery(for: type.sampleType) { ok, err in
            if let err = err {
                self.log.error("disable bg delivery err \(type.rawValue): \(err.localizedDescription)")
            }
            self.log.info("bg delivery disabled for \(type.rawValue): \(ok)")
        }
        deleteAnchor(for: type)
    }

    /// Push Now: fetch deltas for every enabled type.
    func fetchAndPushAll() {
        for type in PulseType.allCases where isEnabled(type) {
            fetchDelta(for: type) {}
        }
    }

    /// Unpair support — ADR-0002 constraint 3: revocation wipes the
    /// phone-side anchor state too.
    func clearAllAnchors() {
        for type in PulseType.allCases {
            deleteAnchor(for: type)
        }
    }

    private func isEnabled(_ type: PulseType) -> Bool {
        UserDefaults.standard.bool(forKey: type.storageKey)
    }

    // MARK: - Observation (Bridge.swift shape)

    private func installObserver(for type: PulseType) {
        let sampleType = type.sampleType
        let observer = HKObserverQuery(sampleType: sampleType, predicate: nil) { [weak self] _, completion, error in
            guard let self = self else {
                completion()
                return
            }
            if let error = error {
                self.log.error("observer error for \(sampleType.identifier): \(error.localizedDescription)")
                completion()
                return
            }
            // completion() runs in every path — HealthKit penalizes
            // observers that drop it.
            self.fetchDelta(for: type) {
                completion()
            }
        }
        store.execute(observer)
        activeQueries[type.rawValue] = observer
        // OS coalesces .immediate; trend cadence per ADR-0002
        // constraint 1. Requires the background-delivery entitlement
        // (D64).
        store.enableBackgroundDelivery(for: sampleType, frequency: .immediate) { ok, err in
            if let err = err {
                self.log.error("bg delivery err \(sampleType.identifier): \(err.localizedDescription)")
            }
            self.log.info("bg delivery for \(sampleType.identifier): \(ok)")
        }
    }

    func fetchDelta(for type: PulseType, done: @escaping () -> Void) {
        let sampleType = type.sampleType
        let anchor = loadAnchor(for: type)
        let query = HKAnchoredObjectQuery(
            type: sampleType,
            predicate: nil,
            anchor: anchor,
            limit: HKObjectQueryNoLimit
        ) { [weak self] _, newSamples, _, newAnchor, error in
            guard let self = self else {
                done()
                return
            }
            if let error = error {
                self.log.error("delta fetch err \(sampleType.identifier): \(error.localizedDescription)")
                done()
                return
            }
            let payloads = (newSamples ?? []).compactMap { sample -> [String: Any]? in
                SampleEncoder.encode(sample: sample)
            }
            guard !payloads.isEmpty else {
                // Nothing to push — safe to advance the anchor so an
                // empty delta is not re-walked forever.
                if let newAnchor = newAnchor {
                    self.saveAnchor(newAnchor, for: type)
                }
                done()
                return
            }
            guard let push = self.push else {
                self.log.error("no push pipeline wired; anchor not advanced")
                done()
                return
            }
            push(payloads) { ok, message in
                // Anchor commits ONLY on push success (see header).
                if ok, let newAnchor = newAnchor {
                    self.saveAnchor(newAnchor, for: type)
                } else if !ok {
                    self.log.notice("push failed (\(message)); anchor not advanced for \(type.rawValue)")
                }
                done()
            }
        }
        store.execute(query)
    }

    // MARK: - Anchor persistence

    private func anchorKey(for type: PulseType) -> String {
        "pulse.anchor.\(type.sampleType.identifier)"
    }

    private func loadAnchor(for type: PulseType) -> HKQueryAnchor? {
        guard let data = UserDefaults.standard.data(forKey: anchorKey(for: type)) else {
            return nil
        }
        return try? NSKeyedUnarchiver.unarchivedObject(ofClass: HKQueryAnchor.self, from: data)
    }

    private func saveAnchor(_ anchor: HKQueryAnchor, for type: PulseType) {
        guard let data = try? NSKeyedArchiver.archivedData(withRootObject: anchor, requiringSecureCoding: true) else {
            log.error("could not archive anchor for \(type.rawValue)")
            return
        }
        UserDefaults.standard.set(data, forKey: anchorKey(for: type))
    }

    private func deleteAnchor(for type: PulseType) {
        UserDefaults.standard.removeObject(forKey: anchorKey(for: type))
    }
}
