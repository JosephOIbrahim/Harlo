// AnchorStore — persists HKQueryAnchor per type to
// ~/Library/Application Support/Harlo/healthkit_anchor.bin.

import Foundation
import HealthKit

final class AnchorStore {
    private let path: URL

    init() {
        // D62: anchor lives in the App Group container (the entitlements
        // comment always promised this) so the main app's "dignified
        // revocation" path (ADR-0001 constraint 5) can find and delete it.
        self.path = SharedPaths.anchorURL
        try? FileManager.default.createDirectory(at: path.deletingLastPathComponent(), withIntermediateDirectories: true)
    }

    func load(for identifier: String) -> HKQueryAnchor? {
        guard let dict = readDictionary() else { return nil }
        guard let data = dict[identifier] else { return nil }
        return try? NSKeyedUnarchiver.unarchivedObject(ofClass: HKQueryAnchor.self, from: data)
    }

    func save(_ anchor: HKQueryAnchor, for identifier: String) {
        var dict = readDictionary() ?? [:]
        guard let data = try? NSKeyedArchiver.archivedData(withRootObject: anchor, requiringSecureCoding: true) else {
            return
        }
        dict[identifier] = data
        write(dict: dict)
    }

    func clear() {
        try? FileManager.default.removeItem(at: path)
    }

    private func readDictionary() -> [String: Data]? {
        guard let data = try? Data(contentsOf: path) else { return nil }
        return (try? NSKeyedUnarchiver.unarchivedObject(ofClasses: [NSDictionary.self, NSString.self, NSData.self], from: data)) as? [String: Data]
    }

    private func write(dict: [String: Data]) {
        guard let data = try? NSKeyedArchiver.archivedData(withRootObject: dict, requiringSecureCoding: true) else {
            return
        }
        try? data.write(to: path)
    }
}
