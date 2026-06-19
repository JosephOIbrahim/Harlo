// PairingStore — Keychain-backed pairing state.
//
// Stores ONLY the derived key (SHA256 of the normalized 6-word token)
// plus host + port. The raw words are never persisted: normalize,
// hash, discard. The derivation matches the Mac's
// python/harlo/cli/commands/pulse.py derive_key() exactly —
// lowercase, whitespace-split, single-space join, SHA256.
//
// kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly: background pushes
// must work after first unlock; the pairing never migrates to a new
// device (re-pair instead — ADR-0002 constraint 3).

import CryptoKit
import Foundation
import Security

struct Pairing {
    let keyData: Data
    let host: String
    let port: UInt16
}

enum PairingStore {

    enum PairingError: Error {
        case keychain(OSStatus)
        case encode
    }

    private static let service = "com.josephibrahim.harlo.pulse"
    private static let account = "pairing-v1"

    static func save(token: String, host: String, port: UInt16) throws {
        let normalized = token
            .lowercased()
            .split(whereSeparator: { $0.isWhitespace })
            .joined(separator: " ")
        let digest = SHA256.hash(data: Data(normalized.utf8))
        let keyHex = digest.map { String(format: "%02x", $0) }.joined()

        let blob: [String: Any] = ["key_hex": keyHex, "host": host, "port": Int(port)]
        guard let data = try? JSONSerialization.data(withJSONObject: blob) else {
            throw PairingError.encode
        }

        // Replace semantics: delete any existing item, then add.
        SecItemDelete(baseQuery() as CFDictionary)
        var attrs = baseQuery()
        attrs[kSecValueData as String] = data
        attrs[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        let status = SecItemAdd(attrs as CFDictionary, nil)
        guard status == errSecSuccess else {
            throw PairingError.keychain(status)
        }
    }

    static func load() -> Pairing? {
        var query = baseQuery()
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne
        var out: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &out) == errSecSuccess,
              let data = out as? Data,
              let obj = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any],
              let keyHex = obj["key_hex"] as? String,
              let host = obj["host"] as? String,
              let portInt = obj["port"] as? Int,
              let port = UInt16(exactly: portInt),
              let keyData = dataFromHex(keyHex)
        else {
            return nil
        }
        return Pairing(keyData: keyData, host: host, port: port)
    }

    /// Unpair deletes the Keychain item. The caller is responsible for
    /// the matching anchor wipe (HealthReader.clearAllAnchors) —
    /// ADR-0002 constraint 3: revocation is explicit and complete.
    static func unpair() {
        let status = SecItemDelete(baseQuery() as CFDictionary)
        // errSecItemNotFound is fine — unpair is idempotent.
        _ = status
    }

    private static func baseQuery() -> [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
    }

    private static func dataFromHex(_ hex: String) -> Data? {
        guard hex.count % 2 == 0 else { return nil }
        var data = Data(capacity: hex.count / 2)
        var index = hex.startIndex
        while index < hex.endIndex {
            let next = hex.index(index, offsetBy: 2)
            guard let byte = UInt8(hex[index..<next], radix: 16) else { return nil }
            data.append(byte)
            index = next
        }
        return data
    }
}
