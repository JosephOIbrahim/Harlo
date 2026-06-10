// HarloPulseApp — SwiftUI entry point + the single screen.
//
// Three sections: Pairing (6 words + host + port, pair/unpair),
// Data Types (9 per-type toggles, DEFAULT OFF — ADR-0001 constraint 1
// / D65, enforced here in the UI layer), Status (last push, last
// result, Push Now).
//
// One coordinator (PulseModel) owns HealthReader + PulseLink and wires
// the push pipeline so anchor commits ride on push success.

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

final class PulseModel: ObservableObject {
    @Published var lastPush: Date?
    @Published var lastResult: String = "—"
    @Published var paired: Bool

    let reader = HealthReader()
    private let link = PulseLink()

    init() {
        paired = PairingStore.load() != nil

        reader.push = { [weak self] samples, done in
            guard let self = self else {
                done(false, "model gone")
                return
            }
            self.link.push(samples: samples) { ok, message in
                DispatchQueue.main.async {
                    if ok { self.lastPush = Date() }
                    self.lastResult = message
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
    @StateObject private var model = PulseModel()
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
                TextField("Host (e.g. mac-studio.local)", text: $host)
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
