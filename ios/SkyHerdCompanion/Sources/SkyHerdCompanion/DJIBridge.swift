import Foundation
import CoreLocation

// ---------------------------------------------------------------------------
// DJI SDK import guard
//
// DJISDK.xcframework is a commercial binary that must be downloaded from
// developer.dji.com and placed in ios/SkyHerdCompanion/Frameworks/ before
// building.  The compile-time symbol DJI_SDK_AVAILABLE is set in project.yml
// once the framework is added.  Without it, all DJI calls degrade gracefully
// to stub implementations that log warnings — this keeps unit tests and CI
// green without the framework present.
// ---------------------------------------------------------------------------

#if DJI_SDK_AVAILABLE
import DJISDK
#endif

// MARK: - DJIBridge

/// Single-instance bridge between SkyHerdCompanion and the DJI Mobile SDK V5.
///
/// All public methods are async and throw ``DJIBridgeError`` on failure.
/// When ``DJI_SDK_AVAILABLE`` is not defined (no framework present) every
/// method logs a warning and either returns a stub value or throws
/// ``DJIBridgeError.sdkUnavailable``.
@MainActor
public final class DJIBridge: NSObject {
    public static let shared = DJIBridge()

    // State observable by the UI layer
    public private(set) var isRegistered = false
    public private(set) var isConnected = false

    // Cached state snapshot updated from SDK callbacks
    public private(set) var currentState = DroneStateSnapshot()

    // Weak back-reference to AppState so status callbacks can surface in the UI.
    // Set via ``registerApp(appState:)``.  Intentionally weak so the singleton
    // DJIBridge never keeps AppState alive beyond its SwiftUI lifecycle.
    private weak var appState: AppState?

    // Sequence counter for internal logging
    private var seqCounter = 0

    private override init() {
        super.init()
    }

    // MARK: - Registration

    /// Call once at app launch (from ``App.init``) with the shared ``AppState``.
    ///
    /// Reads ``Config.djiApiKey`` and invokes ``DJISDKManager.registerApp``.
    /// If the key is empty, ``AppState.lastError`` is set to a user-visible
    /// string and registration is skipped (no silent failure).
    public func registerApp(appState: AppState) {
        self.appState = appState
        let key = Config.djiApiKey
        guard !key.isEmpty else {
            AppLogger.dji.error("DJI API key is empty — registration aborted")
            appState.lastError =
                "DJI API key missing — set DJI_API_KEY in Config.xcconfig or the DJIAppKey " +
                "entry in Info.plist. Registration has been skipped; drone commands will be rejected."
            notifyStatus("No API key")
            return
        }

#if DJI_SDK_AVAILABLE
        DJISDKManager.registerApp(with: self)
        AppLogger.dji.info("DJI SDK registration initiated")
        notifyStatus("Registering…")
#else
        AppLogger.dji.warning("DJI SDK not available (framework not embedded) — stub mode")
        isRegistered = true
        notifyStatus("Stub (no SDK)")
#endif
    }

    // MARK: - Takeoff

    /// Arm and take off to the default altitude (5 m for dev testing; agents send alt_m in args).
    /// - Parameter altM: Target altitude in metres AGL.  Clamped to ``Config.maxAltitudeM``.
    ///
    /// Precondition (H3-01 audit gate): ``currentState.gpsValid`` must be ``true``.
    /// When the DJI SDK is unavailable (stub mode), this defaults to ``true`` so
    /// unit tests don't need to thread GPS state.
    public func takeoff(altM: Double = 5.0) async throws {
        let clampedAlt = min(altM, Config.maxAltitudeM)
        AppLogger.dji.info("takeoff requested: altM=\(clampedAlt, privacy: .public)")

        // GPS fix is a hard precondition for autonomous flight.  Stub mode
        // defaults gpsValid=true so tests pass without mocking SDK telemetry.
        guard currentState.gpsValid else {
            AppLogger.dji.warning("takeoff refused: GPS fix invalid")
            throw DJIBridgeError.gpsInvalid("GPS fix required before takeoff")
        }

#if DJI_SDK_AVAILABLE
        guard isRegistered, isConnected else {
            throw DJIBridgeError.sdkUnavailable("DJI not ready — register and connect first")
        }
        guard let fc = DJISDKManager.product()?.flightController else {
            throw DJIBridgeError.sdkUnavailable("FlightController unavailable")
        }
        try await withCheckedThrowingContinuation { (cont: CheckedContinuation<Void, Error>) in
            fc.startTakeoff { error in
                if let error {
                    cont.resume(throwing: DJIBridgeError.djiError(error.localizedDescription))
                } else {
                    cont.resume()
                }
            }
        }
        currentState.armed = true
        currentState.inAir = true
        currentState.altitudeM = clampedAlt
        currentState.mode = "GUIDED"
#else
        // Stub: log and update state only
        AppLogger.dji.warning("DJI SDK stub: takeoff() — no SDK embedded")
        currentState.armed = true
        currentState.inAir = true
        currentState.altitudeM = clampedAlt
        currentState.mode = "GUIDED"
#endif
        pushDroneStateToApp()
        AppLogger.dji.info("takeoff ok — alt=\(clampedAlt, privacy: .public) m")
    }

    // MARK: - Goto location

    /// Fly to a geographic position at the specified altitude.
    ///
    /// **NOT YET IMPLEMENTED** — the DJI SDK V5 exposes point-to-point flight only
    /// through ``DJIWaypointV2Mission``, which is a substantial wiring effort
    /// beyond the Phase 7.2 scope.  Calling this method always throws
    /// ``DJIBridgeError.unsupported`` so patrol missions fail loudly rather than
    /// silently triggering RTH (as the prior ``fc.startGoHome`` implementation
    /// did — see Phase 7.2 audit, Audit 1 #3).
    public func gotoLocation(
        _ lat: CLLocationDegrees,
        _ lon: CLLocationDegrees,
        _ alt: Double
    ) async throws {
        let clampedAlt = min(alt, Config.maxAltitudeM)
        AppLogger.dji.warning(
            "gotoLocation(\(lat),\(lon),\(clampedAlt)) is not implemented — " +
            "throwing unsupported (prev impl silently triggered RTH)"
        )
        throw DJIBridgeError.unsupported(
            "gotoLocation requires DJIWaypointV2Mission — not yet implemented. " +
            "Use return_to_home or wait for Phase 8+ waypoint support."
        )
    }

    // MARK: - Return to home

    /// Command return-to-launch.
    public func returnToHome() async throws {
        AppLogger.dji.info("returnToHome requested")

#if DJI_SDK_AVAILABLE
        guard isRegistered, isConnected else {
            throw DJIBridgeError.sdkUnavailable("DJI not ready")
        }
        guard let fc = DJISDKManager.product()?.flightController else {
            throw DJIBridgeError.sdkUnavailable("FlightController unavailable")
        }
        try await withCheckedThrowingContinuation { (cont: CheckedContinuation<Void, Error>) in
            fc.startGoHome { error in
                if let error {
                    cont.resume(throwing: DJIBridgeError.djiError(error.localizedDescription))
                } else {
                    cont.resume()
                }
            }
        }
        currentState.inAir = false
        currentState.armed = false
        currentState.mode = "LAND"
#else
        AppLogger.dji.warning("DJI SDK stub: returnToHome()")
        currentState.inAir = false
        currentState.armed = false
        currentState.mode = "LAND"
#endif
        pushDroneStateToApp()
        AppLogger.dji.info("returnToHome ok")
    }

    // MARK: - Play tone

    /// Play a deterrent tone.
    ///
    /// - Note: The Mavic Air 2 has **no onboard speaker**.  This method logs
    ///   the request; routing to a paired Bluetooth speaker via
    ///   ``AVAudioSession`` is a Phase 8+ enhancement.
    ///
    /// - Parameters:
    ///   - hz: Frequency in Hz (e.g. 12 000 for ultrasonic deterrent).
    ///   - ms: Duration in milliseconds.
    public func playTone(hz: Int, ms: Int) {
        AppLogger.dji.warning(
            "playTone(hz:\(hz), ms:\(ms)) — Mavic Air 2 has no onboard speaker; " +
            "log only.  Deferred: Bluetooth speaker accessory via AVAudioSession (Phase 8+)."
        )
    }

    // MARK: - State

    /// Return a fresh ``DroneStateSnapshot``.
    public func state() async -> DroneStateSnapshot {
#if DJI_SDK_AVAILABLE
        if let fc = DJISDKManager.product()?.flightController,
           let fcState = fc.state
        {
            currentState.altitudeM = Double(fcState.altitude)
            currentState.mode = fcState.flightMode.rawValue.description
            if let loc = fcState.aircraftLocation {
                currentState.lat = loc.coordinate.latitude
                currentState.lon = loc.coordinate.longitude
            }
            // H3-01 audit: surface GPS fix strength so takeoff can refuse
            // when no 3D fix is present (Mavic Air 2 GPS level reports 0–5;
            // level >= 3 corresponds to isGPSSignalStrong in DJI SDK V5).
            currentState.gpsValid = fcState.isGPSSignalStrong
        }
        if let battery = DJISDKManager.product()?.battery {
            currentState.batteryPct = Double(battery.chargeRemainingInPercent)
        }
        pushDroneStateToApp()
#endif
        return currentState
    }

    // MARK: - Internal helpers

    /// Post a status message to both the system logger **and** the bound
    /// ``AppState.djiStatus`` (surfaced in the UI). Prior implementations
    /// logged only, so the UI stuck on "Not registered" forever.
    private func notifyStatus(_ message: String) {
        AppLogger.dji.info("DJI status: \(message, privacy: .public)")
        if let appState = appState {
            appState.djiStatus = message
        }
    }

    /// Mirror the cached ``currentState`` into ``AppState.droneState`` so the UI
    /// refreshes after every bridge transition.
    private func pushDroneStateToApp() {
        appState?.droneState = currentState
    }
}

// MARK: - DJISDKManagerDelegate

#if DJI_SDK_AVAILABLE
extension DJIBridge: DJISDKManagerDelegate {
    public nonisolated func appRegisteredWithError(_ error: Error?) {
        Task { @MainActor in
            if let error {
                AppLogger.dji.error("DJI registration failed: \(error.localizedDescription)")
                self.isRegistered = false
                self.notifyStatus("Registration failed")
            } else {
                AppLogger.dji.info("DJI SDK registered successfully")
                self.isRegistered = true
                self.notifyStatus("Registered")
                DJISDKManager.startConnectionToProduct()
            }
        }
    }

    public nonisolated func productConnected(_ product: DJIBaseProduct?) {
        Task { @MainActor in
            AppLogger.dji.info("DJI product connected: \(product?.model ?? "unknown")")
            self.isConnected = product != nil
            self.currentState.mode = "STANDBY"
            self.notifyStatus(product != nil ? "Connected" : "Disconnected")
            self.pushDroneStateToApp()
        }
    }

    public nonisolated func productDisconnected() {
        Task { @MainActor in
            AppLogger.dji.warning("DJI product disconnected")
            self.isConnected = false
            self.currentState.mode = "UNKNOWN"
            self.notifyStatus("Disconnected")
            self.pushDroneStateToApp()
        }
    }

    public nonisolated func didUpdateDatabaseDownloadProgress(_ progress: Progress) {
        // Not used.
    }
}
#endif

// MARK: - Error type

public enum DJIBridgeError: Error, LocalizedError {
    case sdkUnavailable(String)
    case djiError(String)
    case timeout(String)
    case gpsInvalid(String)
    case lostSignal(String)
    case unsupported(String)

    public var errorDescription: String? {
        switch self {
        case .sdkUnavailable(let msg): return "DJI SDK unavailable: \(msg)"
        case .djiError(let msg):       return "DJI error: \(msg)"
        case .timeout(let msg):        return "Timeout: \(msg)"
        case .gpsInvalid(let msg):     return "\(DroneErrorCode.gpsInvalid.rawValue): \(msg)"
        case .lostSignal(let msg):     return "\(DroneErrorCode.lostSignal.rawValue): \(msg)"
        case .unsupported(let msg):    return "\(DroneErrorCode.unsupported.rawValue): \(msg)"
        }
    }
}
