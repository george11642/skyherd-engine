import os

/// Centralised `os.Logger` channels.  Each subsystem maps to a logical component.
enum AppLogger {
    private static let subsystem = Bundle.main.bundleIdentifier ?? "com.skyherd.companion"

    /// DJI SDK registration and aircraft events.
    static let dji = Logger(subsystem: subsystem, category: "DJI")

    /// MQTT bridge — primary command transport + telemetry bus.
    static let mqtt = Logger(subsystem: subsystem, category: "MQTT")

    /// Command routing and dispatch.
    static let router = Logger(subsystem: subsystem, category: "Router")

    /// Safety guards (geofence, battery, wind).
    static let safety = Logger(subsystem: subsystem, category: "Safety")

    /// App-level config loading.
    static let config = Logger(subsystem: subsystem, category: "Config")

    /// General / uncategorised.
    static let general = Logger(subsystem: subsystem, category: "General")
}
