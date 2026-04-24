import Foundation

/// Watchdog that fires `returnToHome()` when the MQTT link to the ranch broker
/// stays down for longer than a grace period *while the drone is in-air*.
///
/// This mirrors the Android implementation
/// (``android/.../DroneControl.kt``'s `startLostSignalWatchdog`) and restores
/// feature parity identified in the Phase 7.2 audit.
///
/// ## Operation
///
/// - Polls every ``pollInterval`` seconds.
/// - If MQTT is disconnected **and** the drone is in-air, start a grace timer.
/// - After ``graceInterval`` seconds continuously disconnected, invoke
///   ``rthAction``.
/// - Any successful MQTT reconnect resets the grace timer.
/// - When the drone is on the ground (`inAir == false`), the watchdog idles.
///
/// ## Design rationale
///
/// The DJI SDK already has its own RC-signal-lost RTH (handled firmware-side).
/// This watchdog covers the separate failure mode where the **companion-to-
/// broker** link drops but the RC link stays up — e.g. the laptop moves out
/// of WiFi range mid-mission. In that case the drone keeps flying with the
/// last accepted waypoint and no-one can cancel it; the watchdog closes that
/// gap.
@MainActor
public final class LostSignalWatchdog {

    /// Poll interval in seconds.
    public let pollInterval: TimeInterval
    /// How long the MQTT link must stay down (in-air) before RTH is fired.
    public let graceInterval: TimeInterval

    /// Probe for the current MQTT connection status. Injected so unit tests
    /// can simulate connected / disconnected states.
    private let mqttConnected: @MainActor () -> Bool

    /// Snapshot provider for the drone's current state. Used to check `inAir`.
    private let currentStateProvider: @MainActor () -> DroneStateSnapshot

    /// Closure that commands RTH. Injected for testability.
    private let rthAction: @MainActor () async throws -> Void

    /// The running watchdog task (nil when stopped).
    private var task: Task<Void, Never>?

    /// Monotonic timestamp of the first disconnect observation in the current
    /// in-air window. Reset on reconnect or on RTH fire.
    private var firstDisconnectAt: Date?

    /// Whether auto-RTH-on-lost-signal is currently enabled. Allows the user
    /// to opt out from Settings → Diagnostic without restarting the app.
    public var autoRthEnabled: Bool = true

    /// Count of RTH invocations fired by the watchdog so far (diagnostics).
    public private(set) var rthFireCount: Int = 0

    /// Weak back-reference to AppState so status updates surface in the UI.
    private weak var appState: AppState?

    public init(
        pollInterval: TimeInterval = 5.0,
        graceInterval: TimeInterval = 30.0,
        mqttConnected: @escaping @MainActor () -> Bool,
        currentStateProvider: @escaping @MainActor () -> DroneStateSnapshot,
        rthAction: @escaping @MainActor () async throws -> Void
    ) {
        self.pollInterval = pollInterval
        self.graceInterval = graceInterval
        self.mqttConnected = mqttConnected
        self.currentStateProvider = currentStateProvider
        self.rthAction = rthAction
    }

    // MARK: - Lifecycle

    /// Begin polling. Idempotent: calling ``start`` twice cancels the previous
    /// task and replaces it.
    public func start(appState: AppState? = nil) {
        self.appState = appState
        task?.cancel()
        task = Task { @MainActor in
            await self.runLoop()
        }
        appState?.watchdogStatus = "Running"
        AppLogger.safety.info("LostSignalWatchdog started (poll=\(self.pollInterval)s, grace=\(self.graceInterval)s)")
    }

    /// Stop polling. Safe to call multiple times.
    public func stop() {
        task?.cancel()
        task = nil
        firstDisconnectAt = nil
        appState?.watchdogStatus = "Stopped"
        AppLogger.safety.info("LostSignalWatchdog stopped")
    }

    // MARK: - Loop

    private func runLoop() async {
        while !Task.isCancelled {
            await tick()
            // Sleep; if cancelled, exit cleanly.
            do {
                try await Task.sleep(nanoseconds: UInt64(pollInterval * 1_000_000_000))
            } catch {
                return
            }
        }
    }

    /// Single watchdog tick. Exposed `internal` so tests can drive it
    /// deterministically without waiting for real time.
    func tick() async {
        guard autoRthEnabled else {
            firstDisconnectAt = nil
            return
        }
        let connected = mqttConnected()
        let state = currentStateProvider()
        let inAir = state.inAir

        if connected {
            // Healthy link — clear any pending grace timer.
            if firstDisconnectAt != nil {
                appState?.watchdogStatus = "OK (reconnected)"
                AppLogger.safety.info("Watchdog: MQTT reconnected — grace timer cleared")
            }
            firstDisconnectAt = nil
            return
        }

        // Disconnected. Only act when airborne.
        guard inAir else {
            firstDisconnectAt = nil
            appState?.watchdogStatus = "Idle (on-ground, MQTT down)"
            return
        }

        let now = Date()
        if let firstSeen = firstDisconnectAt {
            let elapsed = now.timeIntervalSince(firstSeen)
            if elapsed >= graceInterval {
                // Grace exceeded — fire RTH.
                AppLogger.safety.error("Watchdog: MQTT down \(elapsed)s (>= \(self.graceInterval)s) while in-air — firing RTH")
                appState?.watchdogStatus = "RTH fired (MQTT lost)"
                rthFireCount += 1
                do {
                    try await rthAction()
                    AppLogger.safety.info("Watchdog RTH initiated")
                } catch {
                    AppLogger.safety.error("Watchdog RTH failed: \(error.localizedDescription)")
                    appState?.lastError = "Lost-signal RTH failed: \(error.localizedDescription)"
                }
                // Reset so we don't keep re-firing every tick.
                firstDisconnectAt = nil
            } else {
                appState?.watchdogStatus = "MQTT down \(Int(elapsed))s / \(Int(graceInterval))s"
            }
        } else {
            firstDisconnectAt = now
            appState?.watchdogStatus = "MQTT down — grace started"
            AppLogger.safety.warning("Watchdog: MQTT disconnected while in-air — grace timer started")
        }
    }
}
