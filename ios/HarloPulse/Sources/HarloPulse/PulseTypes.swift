// PulseTypes — the 9 biometric types Harlo ingests. Single source of
// truth for the UI toggles, HealthKit authorization, and SampleEncoder
// so the type table is never triplicated.
//
// Raw values are EXACTLY the schema enum strings in
// config/biometric_sample_schema.json — the same set the Mac bridge
// reads (macos/HarloHealthBridge/Sources/.../main.swift).

import Foundation
import HealthKit

enum PulseType: String, CaseIterable, Identifiable {
    case heartRate = "heart_rate"
    case heartRateVariabilitySDNN = "heart_rate_variability_sdnn"
    case restingHeartRate = "resting_heart_rate"
    case respiratoryRate = "respiratory_rate"
    case activeEnergyBurned = "active_energy_burned"
    case stepCount = "step_count"
    case sleepAnalysis = "sleep_analysis"
    case oxygenSaturation = "oxygen_saturation"
    case bodyTemperature = "body_temperature"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .heartRate: return "Heart Rate"
        case .heartRateVariabilitySDNN: return "HRV (SDNN)"
        case .restingHeartRate: return "Resting Heart Rate"
        case .respiratoryRate: return "Respiratory Rate"
        case .activeEnergyBurned: return "Active Energy"
        case .stepCount: return "Steps"
        case .sleepAnalysis: return "Sleep"
        case .oxygenSaturation: return "Blood Oxygen"
        case .bodyTemperature: return "Body Temperature"
        }
    }

    /// @AppStorage key for the per-type toggle. DEFAULT IS OFF —
    /// ADR-0001 constraint 1 / D65: per-type opt-in, enforced in the
    /// UI layer.
    var storageKey: String { "pulse.enabled.\(rawValue)" }

    var sampleType: HKSampleType {
        switch self {
        case .heartRate:
            return HKSampleType.quantityType(forIdentifier: .heartRate)!
        case .heartRateVariabilitySDNN:
            return HKSampleType.quantityType(forIdentifier: .heartRateVariabilitySDNN)!
        case .restingHeartRate:
            return HKSampleType.quantityType(forIdentifier: .restingHeartRate)!
        case .respiratoryRate:
            return HKSampleType.quantityType(forIdentifier: .respiratoryRate)!
        case .activeEnergyBurned:
            return HKSampleType.quantityType(forIdentifier: .activeEnergyBurned)!
        case .stepCount:
            return HKSampleType.quantityType(forIdentifier: .stepCount)!
        case .sleepAnalysis:
            return HKSampleType.categoryType(forIdentifier: .sleepAnalysis)!
        case .oxygenSaturation:
            return HKSampleType.quantityType(forIdentifier: .oxygenSaturation)!
        case .bodyTemperature:
            return HKSampleType.quantityType(forIdentifier: .bodyTemperature)!
        }
    }

    var objectType: HKObjectType { sampleType }
}
