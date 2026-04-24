import XCTest
import CoreLocation
@testable import SkyHerdCompanion

/// Phase 7.2: DJIBridge behavioural tests.
///
/// All tests run in stub mode (DJI_SDK_AVAILABLE is off on CI). The assertions
/// exercise the bridge's OWN logic — gating, state mutation, and the Phase 7.2
/// `gotoLocation` unsupported-throw fix — without touching the real DJI SDK.
@MainActor
final class DJIBridgeTests: XCTestCase {

    // MARK: - Fixtures

    private var bridge: DJIBridge { DJIBridge.shared }

    override func setUp() async throws {
        // The bridge is a singleton; reset the mutable state slots we touch
        // to avoid order-dependent test leakage.
        await resetBridgeForTest()
    }

    private func resetBridgeForTest() async {
        // Mutate through a takeoff cycle then RTH so inAir/armed are false,
        // then force-set gpsValid back to the default true via the reset
        // trick of calling returnToHome on a stubbed bridge.
        // (No direct setter is exposed; the bridge's private state is
        // effectively reset by the stub RTH path.)
        _ = try? await bridge.returnToHome()
    }

    // MARK: - gotoLocation (Phase 7.2: must throw, must NOT silently RTH)

    func test_goto_throws_unsupported_instead_of_silent_rth() async {
        do {
            try await bridge.gotoLocation(36.5, -105.5, 30.0)
            XCTFail("gotoLocation must throw — prior impl silently invoked RTH")
        } catch let err as DJIBridgeError {
            if case .unsupported(let msg) = err {
                XCTAssertTrue(msg.contains("DJIWaypointV2Mission"),
                    "Message should explain why: \(msg)")
            } else {
                XCTFail("Expected .unsupported, got \(err)")
            }
        } catch {
            XCTFail("Unexpected error type: \(error)")
        }
    }

    func test_goto_error_carries_E_UNSUPPORTED_code() async {
        do {
            try await bridge.gotoLocation(36.5, -105.5, 30.0)
        } catch {
            let description = (error as? DJIBridgeError)?.errorDescription ?? ""
            XCTAssertTrue(description.contains("E_UNSUPPORTED"),
                "errorDescription must carry the canonical code: \(description)")
        }
    }

    // MARK: - Takeoff (stub mode)

    func test_stub_takeoff_succeeds_with_valid_gps() async throws {
        // After resetBridgeForTest, currentState.gpsValid defaults to true
        // (DroneStateSnapshot default init).  Stub takeoff should succeed.
        try await bridge.takeoff(altM: 5.0)
        let state = await bridge.state()
        XCTAssertEqual(state.altitudeM, 5.0, accuracy: 0.01)
        XCTAssertTrue(state.inAir)
        XCTAssertTrue(state.armed)
        // Cleanup.
        _ = try? await bridge.returnToHome()
    }

    func test_stub_takeoff_clamps_altitude_to_max() async throws {
        try await bridge.takeoff(altM: 10_000.0)
        let state = await bridge.state()
        XCTAssertEqual(state.altitudeM, Config.maxAltitudeM, accuracy: 0.01,
            "Takeoff altitude must be clamped to Config.maxAltitudeM")
        _ = try? await bridge.returnToHome()
    }

    // MARK: - registerApp with missing API key surfaces user-visible error

    func test_register_app_without_key_sets_lastError_on_appState() async {
        // Save/restore DJI_API_KEY env to avoid polluting other tests.
        let originalKey = ProcessInfo.processInfo.environment["DJI_API_KEY"]
        setenv("DJI_API_KEY", "", 1)
        defer {
            if let originalKey {
                setenv("DJI_API_KEY", originalKey, 1)
            } else {
                unsetenv("DJI_API_KEY")
            }
        }
        let appState = AppState()
        bridge.registerApp(appState: appState)
        // In stub mode, an empty key produces `lastError` and still flips
        // isRegistered=false (registration is aborted, no silent success).
        XCTAssertNotNil(appState.lastError,
            "Empty DJI_API_KEY must set user-visible lastError")
        XCTAssertTrue(appState.lastError?.contains("DJI API key missing") == true,
            "lastError should name the missing key: \(appState.lastError ?? "nil")")
    }

    // MARK: - notifyStatus reaches AppState (Audit 1 #5)

    func test_register_app_status_propagates_to_appState() async {
        let appState = AppState()
        setenv("DJI_API_KEY", "test-key-abc", 1)
        defer { unsetenv("DJI_API_KEY") }
        bridge.registerApp(appState: appState)
        // In stub mode the bridge immediately notifies "Stub (no SDK)".
        XCTAssertTrue(appState.djiStatus.contains("Stub") || appState.djiStatus.contains("Registering"),
            "djiStatus must update from default 'Not registered'; got: \(appState.djiStatus)")
    }

    // MARK: - Play tone is no-op but doesn't throw

    func test_play_tone_does_not_throw() {
        // Not async, not throws — just make sure the method is reachable.
        bridge.playTone(hz: 12000, ms: 6000)
    }
}
