import Foundation

// MARK: - Inbound command envelope (Python → app)

/// A command sent by the SkyHerd Engine Python backend over WebSocket.
///
/// JSON wire format:
/// ```json
/// {"cmd": "takeoff", "args": {"alt_m": 5.0}, "seq": 42}
/// ```
public struct DroneCommand: Codable, Equatable {
    public let cmd: String
    public let args: [String: AnyCodable]
    public let seq: Int

    public init(cmd: String, args: [String: AnyCodable] = [:], seq: Int) {
        self.cmd = cmd
        self.args = args
        self.seq = seq
    }
}

// MARK: - Outbound ACK envelope (app → Python)

/// Acknowledgement sent back to the backend after executing (or rejecting) a command.
///
/// Success:
/// ```json
/// {"ack": "takeoff", "result": "ok", "seq": 42}
/// ```
/// Error:
/// ```json
/// {"ack": "takeoff", "result": "error", "message": "E_BATTERY_LOW", "seq": 42}
/// ```
public struct DroneAck: Codable, Equatable {
    public let ack: String
    public let result: AckResult
    public let seq: Int
    public let message: String?
    public let data: [String: AnyCodable]?

    public init(
        ack: String,
        result: AckResult,
        seq: Int,
        message: String? = nil,
        data: [String: AnyCodable]? = nil
    ) {
        self.ack = ack
        self.result = result
        self.seq = seq
        self.message = message
        self.data = data
    }

    public enum AckResult: String, Codable {
        case ok
        case error
    }
}

// MARK: - Drone state snapshot

/// A point-in-time snapshot of the drone's state, returned in response to ``get_state``.
public struct DroneStateSnapshot: Codable, Equatable {
    public var armed: Bool
    public var inAir: Bool
    public var altitudeM: Double
    public var batteryPct: Double
    public var mode: String
    public var lat: Double
    public var lon: Double

    public init(
        armed: Bool = false,
        inAir: Bool = false,
        altitudeM: Double = 0.0,
        batteryPct: Double = 100.0,
        mode: String = "UNKNOWN",
        lat: Double = 0.0,
        lon: Double = 0.0
    ) {
        self.armed = armed
        self.inAir = inAir
        self.altitudeM = altitudeM
        self.batteryPct = batteryPct
        self.mode = mode
        self.lat = lat
        self.lon = lon
    }

    enum CodingKeys: String, CodingKey {
        case armed
        case inAir = "in_air"
        case altitudeM = "altitude_m"
        case batteryPct = "battery_pct"
        case mode, lat, lon
    }
}

// MARK: - MQTT envelope types

/// Outbound state published on ``skyherd/drone/state/*``.
public struct MQTTStatePayload: Codable {
    public let ts: Double
    public let state: DroneStateSnapshot

    public init(ts: Double = Date().timeIntervalSince1970, state: DroneStateSnapshot) {
        self.ts = ts
        self.state = state
    }
}

/// Outbound ACK published on ``skyherd/drone/ack/*``.
public struct MQTTAckPayload: Codable {
    public let ts: Double
    public let ack: DroneAck

    public init(ts: Double = Date().timeIntervalSince1970, ack: DroneAck) {
        self.ts = ts
        self.ack = ack
    }
}

// MARK: - Error codes (canonical — see docs/HARDWARE_MAVIC_PROTOCOL.md)

public enum DroneErrorCode: String {
    case djiNotReady = "E_DJI_NOT_READY"
    case geofenceReject = "E_GEOFENCE_REJECT"
    case batteryLow = "E_BATTERY_LOW"
    case windCeiling = "E_WIND_CEILING"
    case timeout = "E_TIMEOUT"
    case unknownCmd = "E_UNKNOWN_CMD"
}

// MARK: - AnyCodable helper

/// Wraps arbitrary JSON-compatible values so ``DroneCommand.args`` can be typed.
public struct AnyCodable: Codable, Equatable {
    public let value: Any

    public init(_ value: Any) {
        self.value = value
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let int = try? container.decode(Int.self) {
            value = int
        } else if let double = try? container.decode(Double.self) {
            value = double
        } else if let bool = try? container.decode(Bool.self) {
            value = bool
        } else if let string = try? container.decode(String.self) {
            value = string
        } else if let array = try? container.decode([AnyCodable].self) {
            value = array.map(\.value)
        } else if let dict = try? container.decode([String: AnyCodable].self) {
            value = dict.mapValues(\.value)
        } else {
            value = NSNull()
        }
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch value {
        case let int as Int:    try container.encode(int)
        case let double as Double: try container.encode(double)
        case let bool as Bool:  try container.encode(bool)
        case let string as String: try container.encode(string)
        case let array as [Any]:
            try container.encode(array.map { AnyCodable($0) })
        case let dict as [String: Any]:
            try container.encode(dict.mapValues { AnyCodable($0) })
        default:
            try container.encodeNil()
        }
    }

    public static func == (lhs: AnyCodable, rhs: AnyCodable) -> Bool {
        // Equality by re-encoding to JSON (sufficient for test assertions)
        guard
            let lData = try? JSONEncoder().encode(lhs),
            let rData = try? JSONEncoder().encode(rhs)
        else { return false }
        return lData == rData
    }
}
