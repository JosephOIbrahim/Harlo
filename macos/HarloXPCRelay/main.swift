// HarloXPCRelay — sandbox-safe bridge between the sandboxed HarloHealthBridge and
// the (non-sandboxed) Harlo daemon. ADR-0001 Phase 5B.
//
// The sandboxed bridge cannot reach the daemon's UNIX socket, and the App Group
// container can't host it (macOS blocks the non-sandboxed daemon from binding
// there). But the bridge CAN reach a launchd Mach service (with a mach-lookup
// entitlement). This relay vends that Mach service and forwards framed
// `biometric_ingest` JSON to the daemon's twind.sock — which the relay, being
// non-sandboxed, can reach.
//
// Wire format to the daemon (daemon/framing.py): [4-byte big-endian length][UTF-8 JSON].

import Foundation

let kMachServiceName = "233JSS4X69.com.harlo.xpc"

@objc protocol HarloXPCProtocol {
    func ingest(_ payload: Data, withReply reply: @escaping (Bool, String) -> Void)
}

enum RelayError: Error { case socketCreate, socketConnect, socketWrite, socketRead }

func daemonSocketPath() -> String {
    // Non-sandboxed process: NSHomeDirectory() resolves to the real home.
    (NSHomeDirectory() as NSString)
        .appendingPathComponent("Library/Application Support/Harlo/twind.sock")
}

func writeAll(_ fd: Int32, _ data: Data) throws {
    try data.withUnsafeBytes { (raw: UnsafeRawBufferPointer) in
        guard var ptr = raw.baseAddress else { return }
        var remaining = data.count
        while remaining > 0 {
            let w = write(fd, ptr, remaining)
            if w <= 0 { throw RelayError.socketWrite }
            remaining -= w
            ptr = ptr.advanced(by: w)
        }
    }
}

func readN(_ fd: Int32, _ n: Int) throws -> Data {
    var buf = Data(count: n)
    var got = 0
    try buf.withUnsafeMutableBytes { (raw: UnsafeMutableRawBufferPointer) in
        guard let base = raw.baseAddress else { throw RelayError.socketRead }
        while got < n {
            let r = read(fd, base.advanced(by: got), n - got)
            if r <= 0 { throw RelayError.socketRead }
            got += r
        }
    }
    return buf
}

func sendToDaemon(_ payload: Data) throws -> String {
    let path = daemonSocketPath()
    let fd = socket(AF_UNIX, SOCK_STREAM, 0)
    guard fd >= 0 else { throw RelayError.socketCreate }
    defer { close(fd) }

    var addr = sockaddr_un()
    addr.sun_family = sa_family_t(AF_UNIX)
    let cap = MemoryLayout.size(ofValue: addr.sun_path) - 1
    _ = withUnsafeMutablePointer(to: &addr.sun_path.0) { p in
        path.withCString { strncpy(p, $0, cap) }
    }
    let len = socklen_t(MemoryLayout<sockaddr_un>.size)
    let ok = withUnsafePointer(to: &addr) { p in
        p.withMemoryRebound(to: sockaddr.self, capacity: 1) { connect(fd, $0, len) }
    }
    guard ok == 0 else { throw RelayError.socketConnect }

    var be = UInt32(payload.count).bigEndian
    let head = withUnsafeBytes(of: &be) { Data($0) }
    try writeAll(fd, head)
    try writeAll(fd, payload)

    let hdr = try readN(fd, 4)
    let n = (UInt32(hdr[0]) << 24) | (UInt32(hdr[1]) << 16) | (UInt32(hdr[2]) << 8) | UInt32(hdr[3])
    guard n > 0, n < 8_000_000 else { return "" }
    let body = try readN(fd, Int(n))
    return String(data: body, encoding: .utf8) ?? ""
}

final class Relay: NSObject, HarloXPCProtocol {
    func ingest(_ payload: Data, withReply reply: @escaping (Bool, String) -> Void) {
        do { reply(true, try sendToDaemon(payload)) }
        catch { reply(false, "relay error: \(error)") }
    }
}

final class Delegate: NSObject, NSXPCListenerDelegate {
    let relay = Relay()
    func listener(_ listener: NSXPCListener, shouldAcceptNewConnection conn: NSXPCConnection) -> Bool {
        conn.exportedInterface = NSXPCInterface(with: HarloXPCProtocol.self)
        conn.exportedObject = relay
        conn.resume()
        return true
    }
}

let delegate = Delegate()
let listener = NSXPCListener(machServiceName: kMachServiceName)
listener.delegate = delegate
listener.resume()
RunLoop.main.run()
