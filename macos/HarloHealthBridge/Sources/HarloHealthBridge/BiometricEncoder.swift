// BiometricEncoder — converts an HKSample into a JSON payload
// matching config/biometric_sample_schema.json. Returns nil for
// types Harlo does not handle.

import Foundation
import HealthKit

enum BiometricEncoder {

    static func encode(sample: HKSample) -> [String: Any]? {
        let iso = ISO8601DateFormatter()
        iso.formatOptions = [.withInternetDateTime, .withFractionalSeconds]

        guard let q = sample as? HKQuantitySample else {
            // Category samples (sleep) handled below.
            if let c = sample as? HKCategorySample, c.sampleType.identifier == HKCategoryTypeIdentifier.sleepAnalysis.rawValue {
                return [
                    "type": "sleep_analysis",
                    "value": Double(c.value),
                    "unit": "category",
                    "sampled_at": iso.string(from: c.startDate),
                    "source": ["device": deviceName(for: sample)],
                ]
            }
            return nil
        }

        let type: String
        let unit: HKUnit
        switch q.quantityType.identifier {
        case HKQuantityTypeIdentifier.heartRate.rawValue:
            type = "heart_rate"; unit = HKUnit(from: "count/min")
        case HKQuantityTypeIdentifier.heartRateVariabilitySDNN.rawValue:
            type = "heart_rate_variability_sdnn"; unit = HKUnit.secondUnit(with: .milli)
        case HKQuantityTypeIdentifier.restingHeartRate.rawValue:
            type = "resting_heart_rate"; unit = HKUnit(from: "count/min")
        case HKQuantityTypeIdentifier.respiratoryRate.rawValue:
            type = "respiratory_rate"; unit = HKUnit(from: "count/min")
        case HKQuantityTypeIdentifier.activeEnergyBurned.rawValue:
            type = "active_energy_burned"; unit = HKUnit.kilocalorie()
        case HKQuantityTypeIdentifier.stepCount.rawValue:
            type = "step_count"; unit = HKUnit.count()
        case HKQuantityTypeIdentifier.oxygenSaturation.rawValue:
            type = "oxygen_saturation"; unit = HKUnit.percent()
        case HKQuantityTypeIdentifier.bodyTemperature.rawValue:
            type = "body_temperature"; unit = HKUnit.degreeCelsius()
        default:
            return nil
        }

        let value = q.quantity.doubleValue(for: unit)
        return [
            "type": type,
            "value": value,
            "unit": unit.unitString,
            "sampled_at": iso.string(from: q.startDate),
            "source": ["device": deviceName(for: q), "bundle_id": q.sourceRevision.source.bundleIdentifier],
        ]
    }

    private static func deviceName(for sample: HKSample) -> String {
        sample.device?.name ?? sample.sourceRevision.source.name
    }
}
