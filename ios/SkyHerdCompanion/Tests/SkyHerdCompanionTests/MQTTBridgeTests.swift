import XCTest
@testable import SkyHerdCompanion

/// Phase 7.2: MQTTBridge decode + dispatch pipeline tests.
///
/// The full CocoaMQTT transport is not exercised in unit tests (it needs a
/// live broker). Instead we drive the bridge through its `_decodeAndDispatch`
/// test hook which exercises:
///   - JSON → DroneCommand decode (both legacy and V1 envelopes)
///   - Routing through the registered CommandRouter
///   - ACK production for unknown / malformed payloads
@MainActor
final class MQTTBridgeTests: XCTestCase {

    private var bridge: MQTTBridge { MQTTBridge.shared }

    override func setUp() async throws {
        // Bind a fresh router + AppState to the singleton. In production this
        // happens in App.init via MQTTBridge.shared.start(...).
        let router = CommandRouter()
        let appState = AppState()
        router.setAppState(appState)
        bridge.start(router: router, appState: appState)
    }

    // MARK: - Decode paths

    func test_decode_legacy_envelope_and_dispatch() async {
        let raw = #"{"cmd":"get_state","args":{},"seq":1}"#
        let ack = await bridge._decodeAndDispatch(payload: Data(raw.utf8))
        XCTAssertNotNil(ack)
        XCTAssertEqual(ack?.ack, "get_state")
        XCTAssertEqual(ack?.result, .ok)
        XCTAssertEqual(ack?.seq, 1)
    }

    func test_decode_v1_envelope_and_dispatch() async {
        let raw = """
        {
          "version": 1,
          "metadata": {"mission_id": "m001", "battery_floor_pct": 30.0, "wind_kt": 8.0},
          "command": {"cmd": "get_state", "args": {}},
          "seq": 7
        }
        """
        let ack = await bridge._decodeAndDispatch(payload: Data(raw.utf8))
        XCTAssertNotNil(ack)
        XCTAssertEqual(ack?.ack, "get_state")
        XCTAssertEqual(ack?.seq, 7)
    }

    func test_malformed_json_returns_nil() async {
        let raw = "not even JSON"
        let ack = await bridge._decodeAndDispatch(payload: Data(raw.utf8))
        XCTAssertNil(ack, "Malformed payload should not produce an ACK")
    }

    func test_missing_cmd_field_returns_nil() async {
        // `cmd` is required by DroneCommand; decoder should throw.
        let raw = #"{"seq":99}"#
        let ack = await bridge._decodeAndDispatch(payload: Data(raw.utf8))
        XCTAssertNil(ack, "Missing required cmd key should fail decode and return nil")
    }

    // MARK: - Unknown command surfaces error ACK through the pipeline

    func test_unknown_command_surfaces_error_ack() async {
        let raw = #"{"cmd":"launch_missiles","args":{},"seq":5}"#
        let ack = await bridge._decodeAndDispatch(payload: Data(raw.utf8))
        XCTAssertEqual(ack?.result, .error)
        XCTAssertTrue(ack?.message?.contains("E_UNKNOWN_CMD") == true)
    }

    // MARK: - Connection state default

    func test_isConnected_default_false_without_broker() {
        // Without an actual broker the bridge should report disconnected.
        XCTAssertFalse(bridge.isConnected,
            "Fresh bridge with no broker must start disconnected")
    }
}
