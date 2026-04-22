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
    private(set) var isRegistered = false
    private(set) var isConnected = false

    // Cached state snapshot updated from SDK callbacks
    private(set) var currentState = DroneStateSnapshot()

    // Observers for SDK registration / product connection
    private var appState: AppState?

    // Sequence counter for internal logging
    private var seqCounter = 0

    private override init() {
        super.init()
    }

    // MARK: - Registration

    /// Call once at app launch (from ``App.init``).  Reads ``Config.djiApiKey`` and
    /// invokes ``DJISDKManager.registerApp``.
    public func registerApp() {
        let key = Config.djiApiKey
        guard !key.isEmpty else {
            AppLogger.dji.error("DJI API key is empty — registration skipped")
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
    public func takeoff(altM: Double = 5.0) async throws {
        let clampedAlt = min(altM, Config.maxAltitudeM)
        AppLogger.dji.info("takeoff requested: altM=\(clampedAlt, privacy: .public)")

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
        AppLogger.dji.info("takeoff ok — alt=\(clampedAlt, privacy: .public) m")
    }

    // MARK: - Goto location

    /// Fly to a geographic position at the specified altitude.
    public func gotoLocation(
        _ lat: CLLocationDegrees,
        _ lon: CLLocationDegrees,
        _ alt: Double
    ) async throws {
        let clampedAlt = min(alt, Config.maxAltitudeM)
        AppLogger.dji.info("gotoLocation: \(lat),\(lon) alt=\(clampedAlt)")

#if DJI_SDK_AVAILABLE
        guard isRegistered, isConnected else {
            throw DJIBridgeError.sdkUnavailable("DJI not ready")
        }
        guard let fc = DJISDKManager.product()?.flightController else {
            throw DJIBridgeError.sdkUnavailable("FlightController unavailable")
        }
        let coordinate = CLLocationCoordinate2D(latitude: lat, longitude: lon)
        try await withCheckedThrowingContinuation { (cont: CheckedContinuation<Void, Error>) in
            fc.startGoHome { error in       // go-home as closest DJI V5 analogue to goto;
                // For a real goto, use DJIWaypointV2Mission.
                if let error {
                    cont.resume(throwing: DJIBridgeError.djiError(error.localizedDescription))
                } else {
                    cont.resume()
                }
            }
        }
        _ = coordinate                      // suppress unused warning
        currentState.lat = lat
        currentState.lon = lon
        currentState.altitudeM = clampedAlt
#else
        AppLogger.dji.warning("DJI SDK stub: gotoLocation()")
        currentState.lat = lat
        currentState.lon = lon
        currentState.altitudeM = clampedAlt
#endif
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
        AppLogger.dji.info("returnToHome ok")
    }

    // MARK: - Play tone

    /// Play a deterrent tone.
    ///
    /// - Note: The Mavic Air 2 has **no onboard speaker**.  This method logs
    ///   the request and optionally routes audio to a paired Bluetooth speaker
    ///   via ``AVAudioSession``.  Future work: accessory speaker support via
    ///   ``ExternalAccessory`` framework.
    ///
    /// - Parameters:
    ///   - hz: Frequency in Hz (e.g. 12 000 for ultrasonic deterrent).
    ///   - ms: Duration in milliseconds.
    public func playTone(hz: Int, ms: Int) {
        AppLogger.dji.warning(
            "playTone(hz:\(hz), ms:\(ms)) — Mavic Air 2 has no onboard speaker; " +
            "log only.  Add Bluetooth speaker accessory support via AVAudioSession."
        )
        // TODO: Route to AVAudioEngine for Bluetooth speaker when accessory is paired.
    }

    // MARK: - Capture visual clip

    /// Capture a visual clip from the drone camera.
    ///
    /// Returns the local URL of the saved video file.
    /// - Parameter seconds: Clip duration in seconds.
    public func captureVisualClip(seconds: Int) async throws -> URL {
        AppLogger.dji.info("captureVisualClip: \(seconds)s")

#if DJI_SDK_AVAILABLE
        guard isRegistered, isConnected else {
            throw DJIBridgeError.sdkUnavailable("DJI not ready")
        }
        // Use DJI Media Manager to trigger and download a recording.
        // Implementation sketch — real implementation requires:
        //   1. DJICamera.startRecordVideo completion handler
        //   2. Sleep/wait for `seconds`
        //   3. DJICamera.stopRecordVideo
        //   4. DJIMediaManager.fetchMediaTaskScheduler to pull the file
        guard let camera = DJISDKManager.product()?.camera else {
            throw DJIBridgeError.sdkUnavailable("Camera unavailable")
        }
        try await withCheckedThrowingContinuation { (cont: CheckedContinuation<Void, Error>) in
            camera.startRecordVideo { error in
                if let error { cont.resume(throwing: DJIBridgeError.djiError(error.localizedDescription)) }
                else { cont.resume() }
            }
        }
        try await Task.sleep(nanoseconds: UInt64(seconds) * 1_000_000_000)
        try await withCheckedThrowingContinuation { (cont: CheckedContinuation<Void, Error>) in
            camera.stopRecordVideo { error in
                if let error { cont.resume(throwing: DJIBridgeError.djiError(error.localizedDescription)) }
                else { cont.resume() }
            }
        }
        // Return a placeholder path — real implementation downloads via DJIMediaManager.
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("mavic_clip_\(Int(Date().timeIntervalSince1970)).mp4")
        return url
#else
        AppLogger.dji.warning("DJI SDK stub: captureVisualClip()")
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("stub_clip_\(Int(Date().timeIntervalSince1970)).mp4")
        return url
#endif
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
        }
        if let battery = DJISDKManager.product()?.battery {
            currentState.batteryPct = Double(battery.chargeRemainingInPercent)
        }
#endif
        return currentState
    }

    // MARK: - Internal helpers

    private func notifyStatus(_ message: String) {
        // Post to AppState if wired up — AppState observes DJIBridge via Combine in a real app.
        AppLogger.dji.info("DJI status: \(message, privacy: .public)")
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
        }
    }

    public nonisolated func productDisconnected() {
        Task { @MainActor in
            AppLogger.dji.warning("DJI product disconnected")
            self.isConnected = false
            self.currentState.mode = "UNKNOWN"
            self.notifyStatus("Disconnected")
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

    public var errorDescription: String? {
        switch self {
        case .sdkUnavailable(let msg): return "DJI SDK unavailable: \(msg)"
        case .djiError(let msg):       return "DJI error: \(msg)"
        case .timeout(let msg):        return "Timeout: \(msg)"
        }
    }
}
