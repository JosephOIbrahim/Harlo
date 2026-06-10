// PulseIntents — App Intents surface for HarloPulse (WWDC26 adoption,
// phase P0; see docs/frontier/app-intents-adoption-plan.md).
//
// Patterns from "Explore advanced App Intents features" applied here:
//   - IntentDialog(full:supporting:) — voice-first vs glance responses
//   - $param.requestValue(...) — in-flight clarification (toggle intent)
//   - Enhanced DisplayRepresentation — title/subtitle/image on entities
//   - ShowsSnippetView — SwiftUI status snippet in Siri/Spotlight results
//   - IntentDonationManager — donate manual syncs so Siri learns cadence
//
// Deliberately NOT here (privacy gates — see the adoption plan):
//   - No CSSearchableIndex indexing (nothing biometric enters the
//     system index), no IntentValueQuery over Harlo memories.
//
// Note on assistant schemas: the session examples use
// @AppIntent(schema: .audio.*) domains. Apple ships no
// coaching/biometrics assistant schema, so these are plain AppIntents —
// which still get Siri, Shortcuts, Spotlight, and onscreen awareness.

import AppIntents
import SwiftUI

// MARK: - Status entity (DisplayRepresentation pattern)

struct PulseStatusEntity: AppEntity {
    static var typeDisplayRepresentation: TypeDisplayRepresentation =
        TypeDisplayRepresentation(name: "HarloPulse Status")
    static var defaultQuery = PulseStatusQuery()

    var id: String = "status"
    var paired: Bool
    var enabledTypes: Int
    var lastPush: Date?
    var lastResult: String

    var displayRepresentation: DisplayRepresentation {
        DisplayRepresentation(
            title: "HarloPulse",
            subtitle: paired
                ? "\(enabledTypes) data types on · last push \(lastPush.map { $0.formatted(date: .abbreviated, time: .shortened) } ?? "never")"
                : "Not paired",
            image: .init(systemName: paired ? "waveform.path.ecg" : "wave.3.right.circle")
        )
    }

    @MainActor
    static func current() -> PulseStatusEntity {
        let model = PulseModel.shared
        return PulseStatusEntity(
            paired: model.paired,
            enabledTypes: model.enabledTypeCount,
            lastPush: model.lastPush,
            lastResult: model.lastResult
        )
    }
}

struct PulseStatusQuery: EntityQuery {
    func entities(for identifiers: [String]) async throws -> [PulseStatusEntity] {
        identifiers.contains("status") ? [await PulseStatusEntity.current()] : []
    }
    func suggestedEntities() async throws -> [PulseStatusEntity] {
        [await PulseStatusEntity.current()]
    }
}

// MARK: - Data-type enum for the toggle intent

enum PulseTypeOption: String, AppEnum {
    case heartRate = "heart_rate"
    case heartRateVariabilitySDNN = "heart_rate_variability_sdnn"
    case restingHeartRate = "resting_heart_rate"
    case respiratoryRate = "respiratory_rate"
    case activeEnergyBurned = "active_energy_burned"
    case stepCount = "step_count"
    case sleepAnalysis = "sleep_analysis"
    case oxygenSaturation = "oxygen_saturation"
    case bodyTemperature = "body_temperature"

    static var typeDisplayRepresentation: TypeDisplayRepresentation =
        TypeDisplayRepresentation(name: "Data Type")

    static var caseDisplayRepresentations: [PulseTypeOption: DisplayRepresentation] = [
        .heartRate: "Heart Rate",
        .heartRateVariabilitySDNN: "HRV (SDNN)",
        .restingHeartRate: "Resting Heart Rate",
        .respiratoryRate: "Respiratory Rate",
        .activeEnergyBurned: "Active Energy",
        .stepCount: "Steps",
        .sleepAnalysis: "Sleep",
        .oxygenSaturation: "Blood Oxygen",
        .bodyTemperature: "Body Temperature",
    ]

    var pulseType: PulseType { PulseType(rawValue: rawValue)! }
}

// MARK: - Sync Now (dialog + donation patterns)

struct SyncPulseIntent: AppIntent {
    static var title: LocalizedStringResource = "Sync Harlo Pulse"
    static var description = IntentDescription(
        "Fetches new health deltas for every enabled data type and pushes them to Harlo on your Mac."
    )

    func perform() async throws -> some IntentResult & ProvidesDialog {
        let model = PulseModel.shared
        guard model.paired else {
            return .result(dialog: IntentDialog(
                full: "HarloPulse isn't paired with your Mac yet. Open the app to pair.",
                supporting: "Not paired"
            ))
        }
        let outcome = await model.syncNow()
        guard outcome.typesSynced > 0 else {
            return .result(dialog: IntentDialog(
                full: "No data types are switched on, so there was nothing to sync.",
                supporting: "Nothing enabled"
            ))
        }

        // Donation: manual syncs teach Siri the user's cadence so it can
        // suggest syncing at habitual moments. The intent carries NO
        // payload — donating it leaks nothing biometric.
        let donation = SyncPulseIntent()
        Task { try? await IntentDonationManager.shared.donate(intent: donation) }

        return .result(dialog: IntentDialog(
            full: "Synced \(outcome.typesSynced) data type\(outcome.typesSynced == 1 ? "" : "s") to Harlo. Mac said: \(outcome.lastResult).",
            supporting: "Synced"
        ))
    }
}

// MARK: - Status (snippet-view pattern)

struct PulseStatusIntent: AppIntent {
    static var title: LocalizedStringResource = "Harlo Pulse Status"
    static var description = IntentDescription(
        "Shows pairing state, enabled data types, and the last push to your Mac."
    )

    func perform() async throws
        -> some IntentResult & ProvidesDialog & ShowsSnippetView & ReturnsValue<PulseStatusEntity>
    {
        let status = await PulseStatusEntity.current()
        let dialog = IntentDialog(
            full: status.paired
                ? "HarloPulse is paired. \(status.enabledTypes) data types are on; last push \(status.lastPush.map { $0.formatted(.relative(presentation: .named)) } ?? "never")."
                : "HarloPulse isn't paired with your Mac yet.",
            supporting: status.paired ? "Paired" : "Not paired"
        )
        return .result(
            value: status,
            dialog: dialog,
            view: PulseStatusSnippetView(status: status)
        )
    }
}

struct PulseStatusSnippetView: View {
    let status: PulseStatusEntity

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Image(systemName: status.paired ? "waveform.path.ecg" : "wave.3.right.circle")
                    .foregroundStyle(status.paired ? .green : .orange)
                Text("HarloPulse")
                    .font(.headline)
                Spacer()
                Text(status.paired ? "Paired" : "Not paired")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
            Divider()
            LabeledContent("Data types on", value: "\(status.enabledTypes) of \(PulseType.allCases.count)")
            LabeledContent(
                "Last push",
                value: status.lastPush.map { $0.formatted(date: .abbreviated, time: .shortened) } ?? "never"
            )
            LabeledContent("Last result", value: status.lastResult)
        }
        .padding()
    }
}

// MARK: - Toggle a data type (requestValue clarification pattern)

struct TogglePulseTypeIntent: AppIntent, ForegroundContinuableIntent {
    static var title: LocalizedStringResource = "Turn Harlo Pulse Data On or Off"
    static var description = IntentDescription(
        "Switches one health data type on or off. Turning a type on for the first time opens the app for the Health permission sheet."
    )

    @Parameter(title: "Data Type")
    var dataType: PulseTypeOption?

    @Parameter(title: "Enabled", default: true)
    var enabled: Bool

    func perform() async throws -> some IntentResult & ProvidesDialog {
        // Clarification pattern: ask in-flight instead of failing when
        // the user said "turn on Harlo data" without naming a type.
        let resolved: PulseTypeOption
        if let dataType {
            resolved = dataType
        } else {
            resolved = try await $dataType.requestValue(
                "Which data type should I \(enabled ? "turn on" : "turn off")?"
            )
        }
        let type = resolved.pulseType
        let alreadyOn = UserDefaults.standard.bool(forKey: type.storageKey)

        if enabled && !alreadyOn {
            // First-time enable needs the HealthKit consent sheet, which
            // requires the foreground app — be honest about it rather
            // than silently flipping a toggle whose auth never happened.
            throw needsToContinueInForegroundError(
                IntentDialog("Turning on \(type.displayName) needs the Health permission sheet."),
                continuation: {
                    UserDefaults.standard.set(true, forKey: type.storageKey)
                    PulseModel.shared.setEnabled(type, true)
                }
            )
        }

        UserDefaults.standard.set(enabled, forKey: type.storageKey)
        PulseModel.shared.setEnabled(type, enabled)
        return .result(dialog: IntentDialog(
            full: "\(type.displayName) is now \(enabled ? "on" : "off").",
            supporting: enabled ? "On" : "Off"
        ))
    }
}

// MARK: - Shortcuts vocabulary

struct PulseShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: SyncPulseIntent(),
            phrases: [
                "Sync \(.applicationName)",
                "Push my health data with \(.applicationName)",
            ],
            shortTitle: "Sync",
            systemImageName: "arrow.triangle.2.circlepath"
        )
        AppShortcut(
            intent: PulseStatusIntent(),
            phrases: [
                "\(.applicationName) status",
                "Is \(.applicationName) paired",
            ],
            shortTitle: "Status",
            systemImageName: "waveform.path.ecg"
        )
    }
}
