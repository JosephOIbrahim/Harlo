// SharedPaths — single source of truth for bridge↔daemon paths (D62).
//
// The bridge is sandboxed (HarloHealthBridge.entitlements). Inside the
// sandbox, .applicationSupportDirectory resolves to the bridge's
// CONTAINER (~/Library/Containers/…), where no daemon socket exists —
// the previous hardcoded paths could never reach the daemon, and the
// container-relative socket path also exceeded sockaddr_un's 104-byte
// sun_path limit (silent strncpy truncation).
//
// Resolution order:
//   1. App Group container (233JSS4X69.com.harlo.shared) — works under
//      the sandbox; Harlo.app carries the matching entitlement so the
//      daemon can bind/read the same paths.
//   2. Legacy ~/Library/Application Support/Harlo — unsandboxed dev
//      runs (swift run from a terminal), where containerURL may still
//      resolve, so the sandbox check comes first.

import Foundation

enum SharedPaths {
    static let appGroupID = "233JSS4X69.com.harlo.shared"

    /// True when running inside an App Sandbox container.
    static var isSandboxed: Bool {
        ProcessInfo.processInfo.environment["APP_SANDBOX_CONTAINER_ID"] != nil
    }

    /// Root directory shared with the Harlo daemon.
    static var sharedRoot: URL {
        if let group = FileManager.default.containerURL(
            forSecurityApplicationGroupIdentifier: appGroupID
        ) {
            // Under the sandbox the group container is the ONLY shared
            // surface; unsandboxed we still prefer it when available so
            // both processes converge on one path.
            return group
        }
        // Unsandboxed fallback: the legacy data dir.
        return FileManager.default
            .urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("Harlo")
    }

    /// The daemon's Unix-domain socket.
    static var socketURL: URL {
        sharedRoot.appendingPathComponent("twind.sock")
    }

    /// Persisted HealthKit anchor dictionary.
    static var anchorURL: URL {
        sharedRoot.appendingPathComponent("healthkit_anchor.bin")
    }

    /// sockaddr_un.sun_path holds 104 usable bytes on Darwin. A path
    /// that exceeds it gets silently truncated by strncpy and connects
    /// to the wrong (nonexistent) node — fail loudly instead.
    static func validateSocketPathLength(_ path: String) -> Bool {
        path.utf8.count < 104
    }
}
