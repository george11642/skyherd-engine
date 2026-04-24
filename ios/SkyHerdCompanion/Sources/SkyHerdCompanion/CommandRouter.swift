import Foundation
import CoreLocation

/// Routes incoming ``DroneCommand`` messages (from MQTT) to the appropriate
/// ``DJIBridge`` method and produces a ``DroneAck``.
///
/// Safety guards are applied before any DJI SDK call.  De-duplication by
/// sequence number prevents double-acks on network retries.
///
/// **MissionV1 envelope support** (Phase 7.2): when a command arrives inside a
/// V1 envelope (``DroneCommand.metadata != nil``), per-call safety guards are
/// instantiated from ``MissionMetadata.battery_floor_pct`` / ``wind_kt`` /
/// ``geofence_version``. Legacy flat payloads continue to use the router's
/// default guards.
@MainActor
public final class CommandRouter {
    private let bridge: DJIBridge
    private let geofence: GeofenceChecker
    private let battery: BatteryGuard
    private let wind: WindGuard
    private let altClamp: AltitudeClamp

    /// Weak reference to AppState (set via ``setAppState`` after construction)
    /// so the router can surface `last_error` and command history in the UI.
    private weak var appState: AppState?

    /// Sequence numbers already processed (de-dup window).  The set provides
    /// O(1) membership test; the deque tracks insertion order so we can evict
    /// the oldest entry when the window overflows (Phase 7.2 Audit 1 #7 —
    /// prior impl used `seenSeqs.min()!` which evicted the numerically smallest
    /// seq rather than the oldest, breaking ordering semantics).
    private var seenSeqs: Set<Int> = []
    private var seqOrder: [Int] = []
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

    /// Attach the observable AppState; optional but recommended so dispatch
    /// results flash in the UI.
    public func setAppState(_ appState: AppState) {
        self.appState = appState
    }

    // MARK: - Dispatch

    /// Dispatch a decoded ``DroneCommand`` and return the appropriate ``DroneAck``.
    public func dispatch(_ cmd: DroneCommand) async -> DroneAck {
        AppLogger.router.info("Dispatching cmd=\(cmd.cmd) seq=\(cmd.seq) hasMeta=\(cmd.metadata != nil)")
        appState?.recordCommand(id: "\(cmd.cmd)#\(cmd.seq)")

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
            appState?.lastError = err.localizedDescription
            return ack(cmd, result: .error, message: err.localizedDescription)
        } catch let err as DJIBridgeError {
            AppLogger.router.error("DJI error for cmd=\(cmd.cmd): \(err.localizedDescription)")
            appState?.lastError = err.localizedDescription
            return ack(cmd, result: .error, message: err.localizedDescription)
        } catch {
            AppLogger.router.error("Unexpected error for cmd=\(cmd.cmd): \(error)")
            appState?.lastError = error.localizedDescription
            return ack(cmd, result: .error, message: error.localizedDescription)
        }
    }

    // MARK: - Command routing

    private func route(_ cmd: DroneCommand) async throws -> [String: AnyCodable]? {
        // Build per-call guards. For V1 envelopes, metadata overrides take
        // precedence; legacy payloads fall through to the router's defaults.
        let effectiveBattery: BatteryGuard = {
            if let pct = cmd.metadata?.batteryFloorPct { return BatteryGuard(floorPct: pct) }
            return self.battery
        }()

        // Wind from metadata is a pre-flight observation (not a ceiling
        // override); the ceiling stays at ``Config.windCeilingKt``.
        let observedWindKt: Double? = cmd.metadata?.windKt

        if let gfv = cmd.metadata?.geofenceVersion {
            AppLogger.router.info("Mission geofence_version=\(gfv, privacy: .public)")
            // Geofence polygons are loaded out-of-band via MQTT /geofence topic;
            // the version string is logged for attestation audit trails.
        }

        switch cmd.cmd {

        case "takeoff":
            let altM = cmd.args["alt_m"]?.value as? Double ?? 5.0
            let clamped = altClamp.clamp(altM)
            let snapshot = await bridge.state()
            try effectiveBattery.checkTakeoff(pct: snapshot.batteryPct)
            if let kt = observedWindKt {
                try wind.check(speedKt: kt)
            }
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
            // Pre-flight wind check from metadata (optional)
            if let kt = observedWindKt {
                try wind.check(speedKt: kt)
            }
            // Execute each waypoint — gotoLocation currently throws .unsupported
            // (see DJIBridge.swift, DJIWaypointV2Mission not wired). The throw
            // surfaces as an E_UNSUPPORTED ack rather than a silent RTH.
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
                "gps_valid":   AnyCodable(s.gpsValid),
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

    /// Record a seq as seen. When the window exceeds ``seenSeqsMaxSize``, the
    /// **oldest** (by insertion order) entry is evicted — not the smallest.
    /// This preserves correct ordering semantics when a gateway retries
    /// out-of-order seqs (e.g. seq=500 followed by seq=1 after a reset).
    private func recordSeq(_ seq: Int) {
        seenSeqs.insert(seq)
        seqOrder.append(seq)
        while seqOrder.count > seenSeqsMaxSize {
            let oldest = seqOrder.removeFirst()
            seenSeqs.remove(oldest)
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
