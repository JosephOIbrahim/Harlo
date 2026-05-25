// DaemonWriter — pushes biometric samples to the Harlo daemon via
// the existing socket at ~/Library/Application Support/Harlo/twind.sock.
//
// Connecting to the socket wakes the launchd-activated daemon. The
// daemon validates each sample through biometric_barrier (Rule 9 +
// ADR-0001) and forwards to the Modulation Layer only. Biometric
// data never enters the trace store.

import Foundation
import OSLog

final class DaemonWriter {
    private let log = Logger(subsystem: "com.harlo.healthbridge", category: "writer")

    func push(samples: [[String: Any]]) {
        let payload: [String: Any] = [
            "command": "biometric_ingest",
            "args": ["samples": samples],
        ]
        guard let data = try? JSONSerialization.data(withJSONObject: payload) else {
            log.error("could not serialize \(samples.count) samples")
            return
        }
        do {
            try send(data: data)
            log.info("pushed \(samples.count) samples to daemon")
        } catch {
            log.error("daemon push failed: \(error.localizedDescription)")
        }
    }

    private func send(data: Data) throws {
        let socketPath = (FileManager.default
            .urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("Harlo/twind.sock")).path

        let fd = socket(AF_UNIX, SOCK_STREAM, 0)
        guard fd >= 0 else { throw BridgeError.socketCreate }
        defer { close(fd) }

        var addr = sockaddr_un()
        addr.sun_family = sa_family_t(AF_UNIX)
        _ = withUnsafeMutablePointer(to: &addr.sun_path.0) { ptr in
            socketPath.withCString { strncpy(ptr, $0, MemoryLayout.size(ofValue: addr.sun_path) - 1) }
        }
        let len = socklen_t(MemoryLayout<sockaddr_un>.size)
        let ok = withUnsafePointer(to: &addr) { p in
            p.withMemoryRebound(to: sockaddr.self, capacity: 1) { connect(fd, $0, len) }
        }
        guard ok == 0 else { throw BridgeError.socketConnect }

        // Length-prefixed frame: 4-byte big-endian length, then payload.
        var be = UInt32(data.count).bigEndian
        let head = Data(bytes: &be, count: 4)
        try writeAll(fd: fd, data: head)
        try writeAll(fd: fd, data: data)
    }

    private func writeAll(fd: Int32, data: Data) throws {
        try data.withUnsafeBytes { raw in
            var remaining = data.count
            var ptr = raw.baseAddress!
            while remaining > 0 {
                let w = write(fd, ptr, remaining)
                if w < 0 { throw BridgeError.socketWrite }
                remaining -= w
                ptr = ptr.advanced(by: w)
            }
        }
    }

    enum BridgeError: Error {
        case socketCreate
        case socketConnect
        case socketWrite
    }
}
