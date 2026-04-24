import Foundation

/// Central configuration loaded from Info.plist and UserDefaults,
/// with environment-variable fallbacks for CI / test builds.
enum Config {
    // MARK: - DJI

    /// DJI SDK API key.  Set the value in SupportingFiles/Info.plist under the
    /// key ``DJIAppKey``, or override via the environment variable ``DJI_API_KEY``
    /// (useful in unit tests and CI where Info.plist patching is impractical).
    static var djiApiKey: String {
        if let envKey = ProcessInfo.processInfo.environment["DJI_API_KEY"], !envKey.isEmpty {
            return envKey
        }
        if let plistKey = Bundle.main.object(forInfoDictionaryKey: "DJIAppKey") as? String,
           !plistKey.isEmpty
        {
            return plistKey
        }
        AppLogger.config.warning("DJIAppKey not set — DJI registration will fail")
        return ""
    }

    // NOTE: No WebSocket server exists — MQTT is the primary transport.
    // The app subscribes to skyherd/drone/cmd/# and publishes ACKs on
    // skyherd/drone/ack/ios. WebSocket references in prior builds were
    // aspirational and have been removed (see Phase 7.2 audit).

    // MARK: - MQTT (primary transport — same broker as the ranch sim)

    /// MQTT broker host.  Override with UserDefaults key "mqtt_host" or
    /// env var "MAVIC_MQTT_HOST".
    static var mqttHost: String {
        if let envVal = ProcessInfo.processInfo.environment["MAVIC_MQTT_HOST"], !envVal.isEmpty {
            return envVal
        }
        return UserDefaults.standard.string(forKey: "mqtt_host") ?? "localhost"
    }

    /// MQTT broker port.
    static var mqttPort: UInt16 {
        if let envVal = ProcessInfo.processInfo.environment["MAVIC_MQTT_PORT"],
           let port = UInt16(envVal)
        {
            return port
        }
        let saved = UserDefaults.standard.integer(forKey: "mqtt_port")
        return saved > 0 ? UInt16(saved) : 1883
    }

    /// MQTT topic prefix.  All SkyHerd topics are under this base.
    static var mqttTopicBase: String {
        UserDefaults.standard.string(forKey: "mqtt_topic_base") ?? "skyherd/drone"
    }

    // MARK: - Safety defaults

    /// Max altitude cap in metres (DJI hard limit 120 m; SkyHerd ops cap 60 m).
    static let maxAltitudeM: Double = 60.0

    /// Battery floor at or below which takeoff is denied (percent).
    /// Aligned to Android + Python `BATTERY_MIN_TAKEOFF_PCT = 30` for cross-
    /// platform parity. Override via env var `MAVIC_BATTERY_FLOOR_PCT` for
    /// test/dev scenarios (e.g. a 25% override when demoing on a depleted pack).
    static var batteryFloorPct: Double {
        if let envVal = ProcessInfo.processInfo.environment["MAVIC_BATTERY_FLOOR_PCT"],
           let pct = Double(envVal)
        {
            return pct
        }
        return 30.0
    }

    /// Wind ceiling above which takeoff is denied (knots).
    static let windCeilingKt: Double = 21.0
}
