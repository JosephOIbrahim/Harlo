// DaemonWriter — pushes biometric samples to the Harlo daemon via the
// HarloXPCRelay Mach service (ADR-0001 Phase 5B).
//
// The sandboxed bridge cannot reach the daemon's UNIX socket directly, and the
// App Group container can't host it (the non-sandboxed daemon is blocked from
// binding there). So we hand the samples to HarloXPCRelay — a launchd Mach
// service — over XPC, and the (non-sandboxed) relay forwards them to twind.sock.
// Reaching the relay requires the mach-lookup temporary-exception entitlement.

import Foundation
import OSLog

@objc protocol HarloXPCProtocol {
    func ingest(_ payload: Data, withReply reply: @escaping (Bool, String) -> Void)
}

final class DaemonWriter {
    private let log = Logger(subsystem: "com.harlo.healthbridge", category: "writer")
    private static let machServiceName = "233JSS4X69.com.harlo.xpc"

    func push(samples: [[String: Any]]) {
        let payload: [String: Any] = [
            "command": "biometric_ingest",
            "args": ["samples": samples],
        ]
        guard let data = try? JSONSerialization.data(withJSONObject: payload) else {
            log.error("could not serialize \(samples.count) samples")
            return
        }

        let conn = NSXPCConnection(machServiceName: DaemonWriter.machServiceName, options: [])
        conn.remoteObjectInterface = NSXPCInterface(with: HarloXPCProtocol.self)
        conn.resume()

        let proxy = conn.remoteObjectProxyWithErrorHandler { [weak self] error in
            self?.log.error("xpc relay error: \(error.localizedDescription)")
            conn.invalidate()
        } as? HarloXPCProtocol

        proxy?.ingest(data) { [weak self] ok, resp in
            self?.log.info("daemon ingest ok=\(ok) resp=\(resp, privacy: .public)")
            conn.invalidate()
        }
    }
}
