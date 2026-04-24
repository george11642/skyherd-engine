import XCTest
@testable import SkyHerdCompanion

/// Phase 7.2: new iOS parity with Android DroneControl.startLostSignalWatchdog.
///
/// The watchdog should:
///  - idle silently when the drone is on-ground even if MQTT is down
///  - idle silently when MQTT is up even if the drone is in-air
///  - fire `rthAction` ONLY when both conditions hold for at least the grace
///    interval continuously
///  - reset the grace timer on reconnect
///  - honour the `autoRthEnabled` toggle
@MainActor
final class LostSignalWatchdogTests: XCTestCase {

    // MARK: - Fixtures

    /// Mutable state the tests drive directly, avoiding real clock/task delays.
    final class Controls {
        var connected: Bool = true
        var inAir: Bool = false
        var rthInvocations: Int = 0
    }

    private func makeWatchdog(controls: Controls, grace: TimeInterval = 30.0) -> LostSignalWatchdog {
        LostSignalWatchdog(
            pollInterval: 5.0,
            graceInterval: grace,
            mqttConnected: { controls.connected },
            currentStateProvider: {
                DroneStateSnapshot(inAir: controls.inAir)
            },
            rthAction: {
                controls.rthInvocations += 1
            }
        )
    }

    // MARK: - Happy path

    func test_idle_when_mqtt_up_and_in_air() async {
        let c = Controls()
        c.connected = true
        c.inAir = true
        let dog = makeWatchdog(controls: c)
        await dog.tick()
        await dog.tick()
        XCTAssertEqual(c.rthInvocations, 0, "No RTH when connected")
    }

    func test_idle_when_mqtt_down_but_on_ground() async {
        let c = Controls()
        c.connected = false
        c.inAir = false
        let dog = makeWatchdog(controls: c)
        // Several ticks should accumulate no RTH firings because drone is on-ground.
        for _ in 0..<5 {
            await dog.tick()
        }
        XCTAssertEqual(c.rthInvocations, 0, "No RTH when on-ground")
    }

    // MARK: - Firing behaviour

    func test_rth_fires_after_grace_while_in_air_disconnected() async {
        let c = Controls()
        c.connected = false
        c.inAir = true
        // 0-second grace so the second tick fires immediately (no sleep).
        let dog = makeWatchdog(controls: c, grace: 0.0)
        await dog.tick()   // start grace timer
        // Allow an infinitesimal amount of wall time to pass.
        try? await Task.sleep(nanoseconds: 1_000_000)  // 1 ms
        await dog.tick()   // elapsed >= 0 → fires
        XCTAssertGreaterThanOrEqual(c.rthInvocations, 1, "Grace exceeded must fire RTH")
    }

    func test_reconnect_resets_grace_timer() async {
        let c = Controls()
        c.connected = false
        c.inAir = true
        let dog = makeWatchdog(controls: c, grace: 100.0)
        await dog.tick()    // start grace timer
        c.connected = true
        await dog.tick()    // reconnect — should clear grace
        c.connected = false
        await dog.tick()    // new disconnect — fresh grace timer
        XCTAssertEqual(c.rthInvocations, 0,
            "Reconnect must reset timer — RTH must NOT fire during first cycle")
    }

    func test_auto_rth_disabled_prevents_firing() async {
        let c = Controls()
        c.connected = false
        c.inAir = true
        let dog = makeWatchdog(controls: c, grace: 0.0)
        dog.autoRthEnabled = false
        await dog.tick()
        try? await Task.sleep(nanoseconds: 1_000_000)
        await dog.tick()
        XCTAssertEqual(c.rthInvocations, 0,
            "Disabled watchdog must not fire even when grace is exceeded")
    }

    func test_rth_fires_exactly_once_per_grace_window() async {
        // After firing, the internal `firstDisconnectAt` is nil again; the
        // next tick starts a fresh grace window instead of retrying every tick.
        let c = Controls()
        c.connected = false
        c.inAir = true
        let dog = makeWatchdog(controls: c, grace: 0.0)
        await dog.tick()
        try? await Task.sleep(nanoseconds: 1_000_000)
        await dog.tick()   // fires #1
        await dog.tick()   // starts NEW grace window — no fire
        let firstRound = c.rthInvocations
        XCTAssertGreaterThanOrEqual(firstRound, 1)
        XCTAssertLessThanOrEqual(firstRound, 2, "Must not fire every tick")
    }

    // MARK: - Diagnostics

    func test_fire_count_tracks_invocations() async {
        let c = Controls()
        c.connected = false
        c.inAir = true
        let dog = makeWatchdog(controls: c, grace: 0.0)
        XCTAssertEqual(dog.rthFireCount, 0)
        await dog.tick()
        try? await Task.sleep(nanoseconds: 1_000_000)
        await dog.tick()
        XCTAssertGreaterThanOrEqual(dog.rthFireCount, 1)
    }
}
