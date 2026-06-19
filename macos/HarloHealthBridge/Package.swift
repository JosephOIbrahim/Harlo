// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "HarloHealthBridge",
    platforms: [.macOS(.v13)],
    products: [
        .executable(name: "HarloHealthBridge", targets: ["HarloHealthBridge"]),
    ],
    targets: [
        .executableTarget(
            name: "HarloHealthBridge",
            path: "Sources/HarloHealthBridge",
            exclude: ["HarloHealthBridge.entitlements"]
        ),
    ]
)
