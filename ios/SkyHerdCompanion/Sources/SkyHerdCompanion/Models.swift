import Foundation

// MARK: - Inbound command envelope (Python → app)

/// A command sent by the SkyHerd Engine Python backend over MQTT.
///
/// **Legacy wire format** (v0, still accepted for backward compat):
/// ```json
/// {"cmd": "takeoff", "args": {"alt_m": 5.0}, "seq": 42}
/// ```
///
/// **V1 wire format** (``MissionV1`` envelope — see
/// `docs/MAVIC_MISSION_SCHEMA.md`):
/// ```json
/// {
///   "version": 1,
///   "metadata": {"mission_id": "m001", "battery_floor_pct": 30.0, "wind_kt": 12.0},
///   "command":  {"cmd": "takeoff", "args": {"alt_m": 5.0}},
///   "seq": 42
/// }
/// ```
///
/// Both shapes decode to this single struct.  When a V1 envelope is present,
/// ``metadata`` is populated; legacy payloads leave it ``nil``.
public struct DroneCommand: Codable, Equatable {
    public let cmd: String
    public let args: [String: AnyCodable]
    public let seq: Int
    /// Optional mission metadata (V1 envelope). ``nil`` for legacy payloads.
    public let metadata: MissionMetadata?

    public init(
        cmd: String,
        args: [String: AnyCodable] = [:],
        seq: Int,
        metadata: MissionMetadata? = nil
    ) {
        self.cmd = cmd
        self.args = args
        self.seq = seq
        self.metadata = metadata
    }

    // MARK: Custom decoder — supports legacy + V1 envelopes

    private enum TopKeys: String, CodingKey {
        case cmd, args, seq              // legacy
        case version, metadata, command  // V1
    }

    private enum V1CommandKeys: String, CodingKey {
        case cmd, args
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: TopKeys.self)

        // Detect V1 envelope by presence of `version` key.
        if container.contains(.version) {
            // Validate version (strictly 1 for now; forward-compat ignores unknowns elsewhere).
            let version = try container.decode(Int.self, forKey: .version)
            guard version == 1 else {
                throw DecodingError.dataCorruptedError(
                    forKey: .version,
                    in: container,
                    debugDescription: "Unsupported mission envelope version: \(version)"
                )
            }
            self.metadata = try container.decodeIfPresent(MissionMetadata.self, forKey: .metadata)
            let inner = try container.nestedContainer(keyedBy: V1CommandKeys.self, forKey: .command)
            self.cmd = try inner.decode(String.self, forKey: .cmd)
            self.args = try inner.decodeIfPresent([String: AnyCodable].self, forKey: .args) ?? [:]
            self.seq = try container.decode(Int.self, forKey: .seq)
        } else {
            // Legacy: flat {cmd, args, seq}
            self.cmd = try container.decode(String.self, forKey: .cmd)
            self.args = try container.decodeIfPresent([String: AnyCodable].self, forKey: .args) ?? [:]
            self.seq = try container.decode(Int.self, forKey: .seq)
            self.metadata = nil
        }
    }

    public func encode(to encoder: Encoder) throws {
        // Re-encode in legacy flat form to minimise wire churn. V1 envelope
        // is inbound-only; the app never originates mission packets.
        var container = encoder.container(keyedBy: TopKeys.self)
        try container.encode(cmd, forKey: .cmd)
        try container.encode(args, forKey: .args)
        try container.encode(seq, forKey: .seq)
    }
}

// MARK: - MissionV1 metadata

/// Subset of ``docs/MAVIC_MISSION_SCHEMA.md`` → ``MissionMetadata`` that
/// influences app-side behaviour (safety guards + logging).  Unknown keys are
/// ignored for forward compatibility.
public struct MissionMetadata: Codable, Equatable {
    public let missionId: String?
    public let ranchId: String?
    public let scenario: String?
    public let windKt: Double?
    public let batteryFloorPct: Double?
    public let geofenceVersion: String?
    public let issuedBy: String?

    public init(
        missionId: String? = nil,
        ranchId: String? = nil,
        scenario: String? = nil,
        windKt: Double? = nil,
        batteryFloorPct: Double? = nil,
        geofenceVersion: String? = nil,
        issuedBy: String? = nil
    ) {
        self.missionId = missionId
        self.ranchId = ranchId
        self.scenario = scenario
        self.windKt = windKt
        self.batteryFloorPct = batteryFloorPct
        self.geofenceVersion = geofenceVersion
        self.issuedBy = issuedBy
    }

    enum CodingKeys: String, CodingKey {
        case missionId = "mission_id"
        case ranchId = "ranch_id"
        case scenario
        case windKt = "wind_kt"
        case batteryFloorPct = "battery_floor_pct"
        case geofenceVersion = "geofence_version"
        case issuedBy = "issued_by"
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
    /// GPS fix is strong enough for autonomous flight.
    ///
    /// Populated from ``DJIFlightControllerState.isGPSSignalStrong`` when the
    /// DJI SDK is available; defaults to ``true`` in stub mode so unit tests
    /// don't need to thread GPS state.  Takeoff must refuse when this is
    /// ``false`` to satisfy the H3 audit gate (see ``docs/H3_DJI_AUDIT.md``).
    public var gpsValid: Bool

    public init(
        armed: Bool = false,
        inAir: Bool = false,
        altitudeM: Double = 0.0,
        batteryPct: Double = 100.0,
        mode: String = "UNKNOWN",
        lat: Double = 0.0,
        lon: Double = 0.0,
        gpsValid: Bool = true
    ) {
        self.armed = armed
        self.inAir = inAir
        self.altitudeM = altitudeM
        self.batteryPct = batteryPct
        self.mode = mode
        self.lat = lat
        self.lon = lon
        self.gpsValid = gpsValid
    }

    enum CodingKeys: String, CodingKey {
        case armed
        case inAir = "in_air"
        case altitudeM = "altitude_m"
        case batteryPct = "battery_pct"
        case mode, lat, lon
        case gpsValid = "gps_valid"
    }
}

// MARK: - MQTT envelope types

/// Outbound state published on ``skyherd/drone/state/ios``.
public struct MQTTStatePayload: Codable {
    public let ts: Double
    public let state: DroneStateSnapshot

    public init(ts: Double = Date().timeIntervalSince1970, state: DroneStateSnapshot) {
        self.ts = ts
        self.state = state
    }
}

/// Outbound ACK published on ``skyherd/drone/ack/ios``.
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
    case gpsInvalid = "E_GPS_INVALID"
    case lostSignal = "E_LOST_SIGNAL"
    /// Command recognised but not yet wired to the DJI SDK (e.g. gotoLocation
    /// pending DJIWaypointV2Mission). Surfaced by patrol missions that cannot
    /// honour waypoints.
    case unsupported = "E_UNSUPPORTED"
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
