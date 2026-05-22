// Bridge — installs HKObserverQuery per type, fetches deltas via
// HKAnchoredObjectQuery, and pushes JSON to the Harlo daemon via UDS.
//
// Anchor persistence: ~/Library/Application Support/Harlo/healthkit_anchor.bin
// (one anchor per type, dictionary-keyed by identifier).

import Foundation
import HealthKit
import OSLog

final class Bridge {
    static let shared = Bridge()

    private let log = Logger(subsystem: "com.harlo.healthbridge", category: "bridge")
    private let anchorStore = AnchorStore()
    private let writer = DaemonWriter()

    func installObservers(types: Set<HKObjectType>, store: HKHealthStore) {
        for type in types {
            guard let sampleType = type as? HKSampleType else { continue }
            let observer = HKObserverQuery(sampleType: sampleType, predicate: nil) { [weak self] _, completion, error in
                if let error = error {
                    self?.log.error("observer error for \(sampleType.identifier): \(error.localizedDescription)")
                    completion()
                    return
                }
                self?.fetchDelta(for: sampleType, store: store) {
                    completion()
                }
            }
            store.execute(observer)
            store.enableBackgroundDelivery(for: sampleType, frequency: .immediate) { ok, err in
                if let err = err {
                    self.log.error("bg delivery err \(sampleType.identifier): \(err.localizedDescription)")
                }
                self.log.info("bg delivery for \(sampleType.identifier): \(ok)")
            }
        }
    }

    private func fetchDelta(for sampleType: HKSampleType, store: HKHealthStore, done: @escaping () -> Void) {
        let anchor = anchorStore.load(for: sampleType.identifier)
        let q = HKAnchoredObjectQuery(
            type: sampleType,
            predicate: nil,
            anchor: anchor,
            limit: HKObjectQueryNoLimit
        ) { [weak self] _, newSamples, _, newAnchor, error in
            guard let self = self else { done(); return }
            if let error = error {
                self.log.error("delta fetch err: \(error.localizedDescription)")
                done()
                return
            }
            if let newAnchor = newAnchor {
                self.anchorStore.save(newAnchor, for: sampleType.identifier)
            }
            let payloads = (newSamples ?? []).compactMap { sample -> [String: Any]? in
                BiometricEncoder.encode(sample: sample)
            }
            if !payloads.isEmpty {
                self.writer.push(samples: payloads)
            }
            done()
        }
        store.execute(q)
    }
}
