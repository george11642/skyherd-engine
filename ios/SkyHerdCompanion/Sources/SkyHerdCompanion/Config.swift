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

    // MARK: - WebSocket server (this app acts as server; Python backend connects to us)

    /// Port the app's WebSocket server binds on.
    /// Override with UserDefaults key "ws_port" or env var "SKYHERD_WS_PORT".
    static var wsPort: UInt16 {
        if let envVal = ProcessInfo.processInfo.environment["SKYHERD_WS_PORT"],
           let port = UInt16(envVal)
        {
            return port
        }
        let saved = UserDefaults.standard.integer(forKey: "ws_port")
        return saved > 0 ? UInt16(saved) : 8765
    }

    // MARK: - MQTT (optional telemetry bus — same broker as the ranch sim)

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

    /// Battery floor below which takeoff is denied (percent).
    static let batteryFloorPct: Double = 25.0

    /// Wind ceiling above which takeoff is denied (knots).
    static let windCeilingKt: Double = 21.0
}
