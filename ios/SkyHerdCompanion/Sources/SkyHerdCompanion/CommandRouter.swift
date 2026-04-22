import Foundation
import CoreLocation

/// Routes incoming ``DroneCommand`` messages from the WebSocket transport
/// to the appropriate ``DJIBridge`` method and produces a ``DroneAck``.
///
/// Safety guards are applied before any DJI SDK call.  De-duplication by
/// sequence number prevents double-acks on network retries.
@MainActor
public final class CommandRouter {
    private let bridge: DJIBridge
    private let geofence: GeofenceChecker
    private let battery: BatteryGuard
    private let wind: WindGuard
    private let altClamp: AltitudeClamp

    /// Sequence numbers of commands already processed (de-dup window).
    private var seenSeqs: Set<Int> = []
    private let seenSeqsMaxSize = 256

    public init(
        bridge: DJIBridge = .shared,
        geofence: GeofenceChecker = .init(),
        battery: BatteryGuard = .init(),
        wind: WindGuard = .init(),
        altClamp: AltitudeClamp = .init()
    ) {
        self.bridge = bridge
        self.geofence = geofence
        self.battery = battery
        self.wind = wind
        self.altClamp = altClamp
    }

    // MARK: - Dispatch

    /// Dispatch a decoded ``DroneCommand`` and return the appropriate ``DroneAck``.
    public func dispatch(_ cmd: DroneCommand) async -> DroneAck {
        AppLogger.router.info("Dispatching cmd=\(cmd.cmd) seq=\(cmd.seq)")

        // De-duplication: ignore commands we've already ACKed
        if seenSeqs.contains(cmd.seq) {
            AppLogger.router.warning("Duplicate seq=\(cmd.seq) for cmd=\(cmd.cmd) — ignoring")
            return ack(cmd, result: .ok, message: "duplicate ignored")
        }
        recordSeq(cmd.seq)

        do {
            let data = try await route(cmd)
            return ack(cmd, result: .ok, data: data)
        } catch let err as SafetyGuardError {
            AppLogger.router.warning("Safety guard blocked cmd=\(cmd.cmd): \(err.localizedDescription)")
            return ack(cmd, result: .error, message: err.localizedDescription)
        } catch let err as DJIBridgeError {
            AppLogger.router.error("DJI error for cmd=\(cmd.cmd): \(err.localizedDescription)")
            return ack(cmd, result: .error, message: err.localizedDescription)
        } catch {
            AppLogger.router.error("Unexpected error for cmd=\(cmd.cmd): \(error)")
            return ack(cmd, result: .error, message: error.localizedDescription)
        }
    }

    // MARK: - Command routing

    private func route(_ cmd: DroneCommand) async throws -> [String: AnyCodable]? {
        switch cmd.cmd {

        case "takeoff":
            let altM = cmd.args["alt_m"]?.value as? Double ?? 5.0
            let clamped = altClamp.clamp(altM)
            // Battery check
            let snapshot = await bridge.state()
            try battery.checkTakeoff(pct: snapshot.batteryPct)
            try await bridge.takeoff(altM: clamped)
            return nil

        case "patrol":
            guard let rawWps = cmd.args["waypoints"]?.value as? [[String: Any]] else {
                throw RoutingError.badArgs("patrol requires 'waypoints' array")
            }
            let points = try rawWps.map { wp -> CLLocationCoordinate2D in
                guard let lat = wp["lat"] as? Double, let lon = wp["lon"] as? Double else {
                    throw RoutingError.badArgs("each waypoint needs lat/lon")
                }
                return CLLocationCoordinate2D(latitude: lat, longitude: lon)
            }
            try geofence.checkPoints(points)
            // Execute each waypoint in sequence
            for (wp, coord) in zip(rawWps, points) {
                let alt = (wp["alt_m"] as? Double) ?? 30.0
                try await bridge.gotoLocation(coord.latitude, coord.longitude, alt)
            }
            return nil

        case "return_to_home":
            try await bridge.returnToHome()
            return nil

        case "play_deterrent":
            let hz = cmd.args["tone_hz"]?.value as? Int ?? 12000
            let durS = cmd.args["duration_s"]?.value as? Double ?? 6.0
            bridge.playTone(hz: hz, ms: Int(durS * 1000))
            return nil

        case "capture_visual_clip":
            let durS = cmd.args["duration_s"]?.value as? Double ?? 10.0
            let url = try await bridge.captureVisualClip(seconds: Int(durS))
            return ["path": AnyCodable(url.path)]

        case "get_state":
            let s = await bridge.state()
            return [
                "armed":       AnyCodable(s.armed),
                "in_air":      AnyCodable(s.inAir),
                "altitude_m":  AnyCodable(s.altitudeM),
                "battery_pct": AnyCodable(s.batteryPct),
                "mode":        AnyCodable(s.mode),
                "lat":         AnyCodable(s.lat),
                "lon":         AnyCodable(s.lon),
            ]

        default:
            throw RoutingError.unknownCommand(cmd.cmd)
        }
    }

    // MARK: - Helpers

    private func ack(
        _ cmd: DroneCommand,
        result: DroneAck.AckResult,
        message: String? = nil,
        data: [String: AnyCodable]? = nil
    ) -> DroneAck {
        DroneAck(ack: cmd.cmd, result: result, seq: cmd.seq, message: message, data: data)
    }

    private func recordSeq(_ seq: Int) {
        seenSeqs.insert(seq)
        // Evict oldest when window overflows
        if seenSeqs.count > seenSeqsMaxSize {
            seenSeqs.remove(seenSeqs.min()!)
        }
    }
}

// MARK: - RoutingError

enum RoutingError: Error, LocalizedError {
    case unknownCommand(String)
    case badArgs(String)
    case timeout(String)

    var errorDescription: String? {
        switch self {
        case .unknownCommand(let cmd):
            return "\(DroneErrorCode.unknownCmd.rawValue): \(cmd)"
        case .badArgs(let msg):
            return "Bad arguments: \(msg)"
        case .timeout(let msg):
            return "\(DroneErrorCode.timeout.rawValue): \(msg)"
        }
    }
}
