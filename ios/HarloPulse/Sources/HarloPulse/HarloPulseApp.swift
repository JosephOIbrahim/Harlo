// HarloPulseApp — SwiftUI entry point + the single screen.
//
// Three sections: Pairing (6 words + host + port, pair/unpair),
// Data Types (9 per-type toggles, DEFAULT OFF — ADR-0001 constraint 1
// / D65, enforced here in the UI layer), Status (last push, last
// result, Push Now).
//
// One coordinator (PulseModel) owns HealthReader + PulseLink and wires
// the push pipeline so anchor commits ride on push success.

import AppIntents
import SwiftUI

@main
struct HarloPulseApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}

// MARK: - Coordinator

/// Singleton: App Intents run outside the view hierarchy and must share
/// the ONE HealthReader (a second instance would double-register
/// HKObserverQuery callbacks). Views observe the same object.
final class PulseModel: ObservableObject {
    static let shared = PulseModel()

    @Published var lastPush: Date?
    @Published var lastResult: String = "—"
    @Published var paired: Bool

    let reader = HealthReader()
    private let link = PulseLink()

    // Persisted mirrors so App Intents (and the status snippet) can
    // report the last outcome even on a cold background launch.
    private static let lastPushKey = "pulse.status.lastPush"
    private static let lastResultKey = "pulse.status.lastResult"

    private init() {
        paired = PairingStore.load() != nil
        lastPush = UserDefaults.standard.object(forKey: Self.lastPushKey) as? Date
        lastResult = UserDefaults.standard.string(forKey: Self.lastResultKey) ?? "—"

        reader.push = { [weak self] samples, done in
            guard let self = self else {
                done(false, "model gone")
                return
            }
            self.link.push(samples: samples) { ok, message in
                DispatchQueue.main.async {
                    if ok {
                        self.lastPush = Date()
                        UserDefaults.standard.set(self.lastPush, forKey: Self.lastPushKey)
                    }
                    self.lastResult = message
                    UserDefaults.standard.set(message, forKey: Self.lastResultKey)
                }
                // This callback is the anchor-commit signal inside
                // HealthReader.
                done(ok, message)
            }
        }

        // Re-arm observers for types toggled ON in a previous launch.
        // Auth is already granted for them, so no sheet appears.
        for type in PulseType.allCases
        where UserDefaults.standard.bool(forKey: type.storageKey) {
            reader.enable(type)
        }
    }

    var enabledTypeCount: Int {
        PulseType.allCases.filter {
            UserDefaults.standard.bool(forKey: $0.storageKey)
        }.count
    }

    /// Awaitable sync for App Intents: triggers a delta fetch+push for
    /// every enabled type and resolves when all per-type cycles call
    /// back (push success or failure both count as completion).
    func syncNow() async -> (typesSynced: Int, lastResult: String) {
        let enabled = PulseType.allCases.filter {
            UserDefaults.standard.bool(forKey: $0.storageKey)
        }
        guard paired, !enabled.isEmpty else {
            return (0, paired ? "no data types enabled" : "not paired")
        }
        let pushBefore = UserDefaults.standard.object(forKey: Self.lastPushKey) as? Date
        await withCheckedContinuation { (cont: CheckedContinuation<Void, Never>) in
            let group = DispatchGroup()
            for type in enabled {
                group.enter()
                reader.fetchDelta(for: type) { group.leave() }
            }
            group.notify(queue: .main) { cont.resume() }
        }
        // Stale-result guard (PR #13 review): empty-delta cycles never
        // write lastResult, so without this check Siri could speak
        // yesterday's ack as if it were this run's.
        let pushAfter = UserDefaults.standard.object(forKey: Self.lastPushKey) as? Date
        if pushBefore == pushAfter {
            return (enabled.count, "no new samples since last push")
        }
        let result = UserDefaults.standard.string(forKey: Self.lastResultKey) ?? "—"
        return (enabled.count, result)
    }

    func setEnabled(_ type: PulseType, _ on: Bool) {
        if on {
            reader.enable(type)
        } else {
            reader.disable(type)
        }
    }

    func pair(token: String, host: String, portText: String) {
        guard let port = UInt16(portText) else {
            lastResult = "invalid port"
            return
        }
        do {
            try PairingStore.save(token: token, host: host, port: port)
            paired = true
            lastResult = "paired with \(host):\(port)"
        } catch {
            lastResult = "pairing failed: \(error)"
        }
    }

    func unpair() {
        PairingStore.unpair()
        // ADR-0002 constraint 3: unpair wipes anchor state too.
        reader.clearAllAnchors()
        paired = false
        lastResult = "unpaired"
    }

    func pushNow() {
        reader.fetchAndPushAll()
    }
}

// MARK: - UI

struct ContentView: View {
    @ObservedObject private var model = PulseModel.shared
    @State private var tokenWords = ""
    @State private var host = ""
    @State private var portText = "48653"

    var body: some View {
        NavigationStack {
            List {
                pairingSection
                dataTypesSection
                statusSection
            }
            .navigationTitle("HarloPulse")
            // Onscreen awareness (code-along pattern 10a): the status
            // singleton is the app's one primary entity — annotating it
            // lets Siri resolve "sync this" / "is this paired" against
            // what's on screen. Identifier only; no content leaves the
            // app (adoption-plan privacy gate holds).
            .userActivity("com.josephibrahim.harlo.pulse.status") { activity in
                activity.title = "HarloPulse Status"
                if #available(iOS 18.2, *) {
                    activity.appEntityIdentifier = EntityIdentifier(
                        for: PulseStatusEntity.self, identifier: "status"
                    )
                }
            }
        }
    }

    private var pairingSection: some View {
        Section("Pairing") {
            if model.paired {
                LabeledContent("State", value: "Paired")
                Button("Unpair", role: .destructive) {
                    model.unpair()
                }
            } else {
                TextField("6 pairing words", text: $tokenWords)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                // Field lesson 2026-06-10: the old placeholder showed a
                // plausible-looking example hostname and a user typed it
                // verbatim -> NWError -65554 NoSuchRecord at the resolver.
                // Point at the authoritative source instead; the IP it
                // prints needs no DNS at all.
                TextField("Host — the IP shown by `harlo pulse pair`", text: $host)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                TextField("Port", text: $portText)
                    .keyboardType(.numberPad)
                Button("Pair") {
                    model.pair(token: tokenWords, host: host, portText: portText)
                    // Discard the raw words from UI state — only the
                    // derived key persists (in the Keychain).
                    tokenWords = ""
                }
                .disabled(tokenWords.isEmpty || host.isEmpty)
            }
        }
    }

    private var dataTypesSection: some View {
        Section {
            ForEach(PulseType.allCases) { type in
                TypeToggleRow(type: type) { changed, on in
                    model.setEnabled(changed, on)
                }
            }
        } header: {
            Text("Data Types")
        } footer: {
            Text("Every type is off until you turn it on. Each toggle asks for its own Health permission.")
        }
    }

    private var statusSection: some View {
        Section("Status") {
            LabeledContent(
                "Last push",
                value: model.lastPush.map { $0.formatted(date: .abbreviated, time: .shortened) } ?? "never"
            )
            LabeledContent("Last result", value: model.lastResult)
            Button("Push Now") {
                model.pushNow()
            }
            .disabled(!model.paired)
        }
    }
}

/// One toggle row with its own @AppStorage binding. DEFAULT IS OFF
/// (wrappedValue: false) — ADR-0001 constraint 1 / D65: per-type
/// opt-in, enforced in the UI layer.
struct TypeToggleRow: View {
    let type: PulseType
    let onToggle: (PulseType, Bool) -> Void

    @AppStorage private var enabled: Bool

    init(type: PulseType, onToggle: @escaping (PulseType, Bool) -> Void) {
        self.type = type
        self.onToggle = onToggle
        _enabled = AppStorage(wrappedValue: false, type.storageKey)
    }

    var body: some View {
        Toggle(type.displayName, isOn: $enabled)
            .onChange(of: enabled) { _, newValue in
                onToggle(type, newValue)
            }
    }
}
