// PulseLink — TCP client pushing sample batches to the Mac's
// `harlo pulse listen` (ADR-0002 v1 transport).
//
// Wire contract (Section 0 of the HarloPulse spec; D61 framing,
// byte-identical to the Mac bridge's DaemonWriter): every frame is a
// 4-byte big-endian length + UTF-8 JSON. Sequence per batch:
//
//   connect -> auth frame -> auth ack -> sample frame -> result ack -> close
//
// No persistent connection (ADR-0002 constraint 1: trend, not stream).
// The completion callback firing with success==true is what lets
// HealthReader commit its HKQueryAnchor — a failed push leaves the
// anchor untouched so samples are re-fetched next cycle.

import CryptoKit
import Foundation
import Network
import OSLog
import Security

final class PulseLink {

    enum LinkError: Error {
        case encode
    }

    private let log = Logger(subsystem: "com.josephibrahim.harlo.pulse", category: "link")
    private let queue = DispatchQueue(label: "com.josephibrahim.harlo.pulse.link")
    private var browser: NWBrowser?

    private static let maxFrame = 1 << 20  // 1 MiB, mirrors MAX_FRAME in pulse.py

    private let iso: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f
    }()

    /// Push one batch. Connect -> auth -> samples -> close.
    /// completion(true, summary) is the anchor-commit signal.
    func push(samples: [[String: Any]], completion: @escaping (Bool, String) -> Void) {
        guard let pairing = PairingStore.load() else {
            completion(false, "not paired")
            return
        }
        guard let port = NWEndpoint.Port(rawValue: pairing.port) else {
            completion(false, "invalid port \(pairing.port)")
            return
        }
        let connection = NWConnection(host: NWEndpoint.Host(pairing.host), port: port, using: .tcp)

        // All callbacks land on `queue`, so `finished` needs no lock.
        var finished = false
        let finish: (Bool, String) -> Void = { [weak self] ok, message in
            if finished { return }
            finished = true
            connection.cancel()
            self?.log.info("push finished ok=\(ok): \(message)")
            completion(ok, message)
        }

        connection.stateUpdateHandler = { [weak self] state in
            switch state {
            case .ready:
                self?.runHandshake(connection, key: pairing.keyData, samples: samples, finish: finish)
            case .failed(let error):
                finish(false, "connection failed: \(error.localizedDescription)")
            case .waiting(let error):
                // .waiting can self-recover, but at trend cadence a
                // quick fail-and-retry-next-cycle beats hanging.
                finish(false, "connection waiting: \(error.localizedDescription)")
            default:
                break
            }
        }
        connection.start(queue: queue)
    }

    // MARK: - Handshake

    private func runHandshake(
        _ connection: NWConnection,
        key: Data,
        samples: [[String: Any]],
        finish: @escaping (Bool, String) -> Void
    ) {
        let ts = iso.string(from: Date())
        var nonceBytes = [UInt8](repeating: 0, count: 8)
        guard SecRandomCopyBytes(kSecRandomDefault, nonceBytes.count, &nonceBytes) == errSecSuccess else {
            finish(false, "nonce generation failed")
            return
        }
        let nonce = nonceBytes.map { String(format: "%02x", $0) }.joined()

        // msg = "harlo-pulse-v1|<ts>|<nonce>" — byte-identical to
        // auth_msg() in pulse.py.
        let msg = Data("harlo-pulse-v1|\(ts)|\(nonce)".utf8)
        let mac = HMAC<SHA256>.authenticationCode(for: msg, using: SymmetricKey(data: key))
        let macHex = mac.map { String(format: "%02x", $0) }.joined()

        let authFrame: [String: Any] = [
            "kind": "auth",
            "version": 1,
            // UIDevice.current.name would need UIKit (banned in this
            // target); the spec allows the constant fallback.
            "device": "iPhone",
            "ts": ts,
            "nonce": nonce,
            "mac": macHex,
        ]

        sendFrame(connection, obj: authFrame) { [weak self] error in
            if let error = error {
                finish(false, "auth send failed: \(error.localizedDescription)")
                return
            }
            self?.receiveFrame(connection) { [weak self] obj, errorMessage in
                guard let obj = obj else {
                    finish(false, errorMessage ?? "no auth ack")
                    return
                }
                guard (obj["status"] as? String) == "ok" else {
                    // Surfaces the Mac's rejection reason (bad token,
                    // computed clock skew) directly in the UI.
                    let message = (obj["message"] as? String) ?? "auth rejected"
                    finish(false, message)
                    return
                }
                self?.sendSamples(connection, samples: samples, finish: finish)
            }
        }
    }

    private func sendSamples(
        _ connection: NWConnection,
        samples: [[String: Any]],
        finish: @escaping (Bool, String) -> Void
    ) {
        // The EXACT existing DaemonWriter payload, unchanged
        // (ADR-0002 point 2 — zero new Mac ingest code).
        let payload: [String: Any] = [
            "command": "biometric_ingest",
            "args": ["samples": samples],
        ]
        sendFrame(connection, obj: payload) { [weak self] error in
            if let error = error {
                finish(false, "sample send failed: \(error.localizedDescription)")
                return
            }
            self?.receiveFrame(connection) { obj, errorMessage in
                guard let obj = obj else {
                    finish(false, errorMessage ?? "no ack")
                    return
                }
                let result = obj["result"] as? [String: Any]
                let accepted = (result?["accepted"] as? Int) ?? 0
                finish(true, "accepted \(accepted) of \(samples.count)")
            }
        }
    }

    // MARK: - Framing (D61: 4-byte big-endian length + JSON)

    private func sendFrame(
        _ connection: NWConnection,
        obj: [String: Any],
        completion: @escaping (Error?) -> Void
    ) {
        guard let data = try? JSONSerialization.data(withJSONObject: obj) else {
            completion(LinkError.encode)
            return
        }
        // Length prefix built exactly like DaemonWriter.swift.
        var be = UInt32(data.count).bigEndian
        var frame = Data(bytes: &be, count: 4)
        frame.append(data)
        connection.send(content: frame, completion: .contentProcessed { error in
            completion(error)
        })
    }

    private func receiveFrame(
        _ connection: NWConnection,
        completion: @escaping ([String: Any]?, String?) -> Void
    ) {
        connection.receive(minimumIncompleteLength: 4, maximumLength: 4) { head, _, _, error in
            guard let head = head, head.count == 4 else {
                completion(nil, error?.localizedDescription ?? "connection closed before frame header")
                return
            }
            // Byte-wise big-endian decode (Data slices are not
            // guaranteed aligned for load(as:)).
            var length: UInt32 = 0
            for b in head { length = (length << 8) | UInt32(b) }
            guard length > 0, length <= UInt32(Self.maxFrame) else {
                completion(nil, "bad frame length \(length)")
                return
            }
            connection.receive(minimumIncompleteLength: Int(length), maximumLength: Int(length)) { body, _, _, error in
                guard let body = body, body.count == Int(length),
                      let obj = (try? JSONSerialization.jsonObject(with: body)) as? [String: Any]
                else {
                    completion(nil, error?.localizedDescription ?? "bad frame body")
                    return
                }
                completion(obj, nil)
            }
        }
    }

    // MARK: - v2 (dormant)

    /// Bonjour discovery of the Mac listener. Compiled but UNREFERENCED
    /// by the UI: the Mac side does not advertise _harlo-pulse._tcp in
    /// v1 (zeroconf would be a new Python dep, disallowed — see the
    /// TODO in pulse.py). Manual host:port is the only working path
    /// until then. Non-blocking and fully separate from the manual
    /// path by construction.
    func discover(_ found: @escaping (NWEndpoint) -> Void) {
        let browser = NWBrowser(for: .bonjour(type: "_harlo-pulse._tcp", domain: nil), using: .tcp)
        browser.browseResultsChangedHandler = { results, _ in
            if let first = results.first {
                found(first.endpoint)
            }
        }
        self.browser = browser
        browser.start(queue: queue)
    }
}
