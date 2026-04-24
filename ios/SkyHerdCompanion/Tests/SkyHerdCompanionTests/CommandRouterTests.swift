import XCTest
@testable import SkyHerdCompanion

/// Tests for CommandRouter: de-duplication, unknown commands, double-ack
/// prevention, and Phase 7.2 additions (V1 envelope + patrol-unsupported).
@MainActor
final class CommandRouterTests: XCTestCase {

    // MARK: - Helpers

    private func makeRouter() -> CommandRouter {
        CommandRouter()
    }

    private func decode(_ raw: String) throws -> DroneCommand {
        try JSONDecoder().decode(DroneCommand.self, from: Data(raw.utf8))
    }

    // MARK: - Unknown command

    func test_unknown_command_returns_error_ack() async {
        let router = makeRouter()
        let cmd = DroneCommand(cmd: "launch_missiles", args: [:], seq: 1)
        let ack = await router.dispatch(cmd)
        XCTAssertEqual(ack.ack, "launch_missiles")
        XCTAssertEqual(ack.result, .error)
        XCTAssertTrue(ack.message?.contains("E_UNKNOWN_CMD") == true, "Error code in message")
    }

    // MARK: - De-duplication

    func test_duplicate_seq_is_ignored() async {
        let router = makeRouter()
        let cmd = DroneCommand(cmd: "get_state", args: [:], seq: 7)

        let ack1 = await router.dispatch(cmd)
        let ack2 = await router.dispatch(cmd)   // same seq — duplicate

        XCTAssertEqual(ack1.result, .ok)
        XCTAssertEqual(ack2.result, .ok)
        XCTAssertEqual(ack2.message, "duplicate ignored")
    }

    func test_different_seqs_are_both_dispatched() async {
        let router = makeRouter()
        let cmd1 = DroneCommand(cmd: "get_state", args: [:], seq: 10)
        let cmd2 = DroneCommand(cmd: "get_state", args: [:], seq: 11)

        let ack1 = await router.dispatch(cmd1)
        let ack2 = await router.dispatch(cmd2)

        XCTAssertEqual(ack1.seq, 10)
        XCTAssertEqual(ack2.seq, 11)
        XCTAssertNotEqual(ack1.message, "duplicate ignored")
        XCTAssertNotEqual(ack2.message, "duplicate ignored")
    }

    // MARK: - get_state returns data

    func test_get_state_returns_data_dict() async {
        let router = makeRouter()
        let cmd = DroneCommand(cmd: "get_state", args: [:], seq: 99)
        let ack = await router.dispatch(cmd)
        XCTAssertEqual(ack.result, .ok)
        XCTAssertNotNil(ack.data, "get_state should include data dict")
        XCTAssertNotNil(ack.data?["battery_pct"])
        XCTAssertNotNil(ack.data?["mode"])
        XCTAssertNotNil(ack.data?["gps_valid"], "Phase 7.2: gps_valid surfaced in state payload")
    }

    // MARK: - Return-to-home

    func test_return_to_home_dispatches_ok() async {
        let router = makeRouter()
        let cmd = DroneCommand(cmd: "return_to_home", args: [:], seq: 20)
        let ack = await router.dispatch(cmd)
        XCTAssertEqual(ack.ack, "return_to_home")
        XCTAssertEqual(ack.seq, 20)
    }

    // MARK: - play_deterrent

    func test_play_deterrent_dispatches_ok() async {
        let router = makeRouter()
        let cmd = DroneCommand(
            cmd: "play_deterrent",
            args: ["tone_hz": AnyCodable(12000), "duration_s": AnyCodable(6.0)],
            seq: 30
        )
        let ack = await router.dispatch(cmd)
        XCTAssertEqual(ack.ack, "play_deterrent")
        XCTAssertEqual(ack.seq, 30)
    }

    // MARK: - ACK seq/name mirroring

    func test_ack_seq_matches_cmd_seq() async {
        let router = makeRouter()
        for seq in [1, 5, 100, 9999] {
            let cmd = DroneCommand(cmd: "get_state", args: [:], seq: seq)
            let ack = await router.dispatch(cmd)
            XCTAssertEqual(ack.seq, seq, "ACK seq must mirror command seq")
        }
    }

    func test_ack_cmd_name_mirrors_command() async {
        let router = makeRouter()
        let cmds = ["get_state", "return_to_home", "play_deterrent"]
        for (i, cmdName) in cmds.enumerated() {
            let cmd = DroneCommand(cmd: cmdName, args: [:], seq: i + 50)
            let ack = await router.dispatch(cmd)
            XCTAssertEqual(ack.ack, cmdName, "ack.ack must match cmd.cmd")
        }
    }

    // MARK: - Seen-seq window eviction (insertion-order; Phase 7.2 fix)

    func test_seq_window_does_not_grow_unbounded() async {
        let router = makeRouter()
        for seq in 0..<300 {
            let cmd = DroneCommand(cmd: "get_state", args: [:], seq: seq)
            _ = await router.dispatch(cmd)
        }
        // The oldest inserted seq (0) should have been evicted → accepting it
        // again must NOT be flagged as duplicate.
        let cmd = DroneCommand(cmd: "get_state", args: [:], seq: 0)
        let ack = await router.dispatch(cmd)
        XCTAssertNotEqual(ack.message, "duplicate ignored",
            "Evicted seq should be re-processed, not treated as duplicate")
    }

    /// Phase 7.2 audit: the old impl evicted via `seenSeqs.min()!` which
    /// would remove seq=1 before seq=500 even if 500 arrived first. The
    /// fix uses insertion order, so a high seq inserted early is evicted
    /// before a low seq inserted late.
    func test_seq_window_evicts_by_insertion_order_not_by_value() async {
        let router = makeRouter()

        // Insert seq=500 first (oldest), then fill with 0..<255
        _ = await router.dispatch(DroneCommand(cmd: "get_state", args: [:], seq: 500))
        for seq in 0..<255 {
            _ = await router.dispatch(DroneCommand(cmd: "get_state", args: [:], seq: seq))
        }
        // Window size = 256; 500 + 255 = 256 total, all should be present.
        let dupOf500 = await router.dispatch(
            DroneCommand(cmd: "get_state", args: [:], seq: 500)
        )
        XCTAssertEqual(dupOf500.message, "duplicate ignored",
            "500 should still be in the window (256 total entries)")

        // Now push one more seq — this evicts the OLDEST (which is 500).
        _ = await router.dispatch(DroneCommand(cmd: "get_state", args: [:], seq: 999))

        // 500 should now be gone (insertion-order eviction).
        let reAccept = await router.dispatch(
            DroneCommand(cmd: "get_state", args: [:], seq: 500)
        )
        XCTAssertNotEqual(reAccept.message, "duplicate ignored",
            "500 was the oldest entry; insertion-order eviction must drop it first")

        // And seq=0 (the value-wise smallest) should STILL be in the window.
        let dupOf0 = await router.dispatch(
            DroneCommand(cmd: "get_state", args: [:], seq: 0)
        )
        XCTAssertEqual(dupOf0.message, "duplicate ignored",
            "Low-value seq 0 must survive; old impl's .min() would have evicted it wrongly")
    }

    // MARK: - Patrol (Phase 7.2: unsupported path)

    func test_patrol_command_surfaces_unsupported() async {
        let router = makeRouter()
        let waypoint: [String: Any] = ["lat": 36.5, "lon": -105.5, "alt_m": 30.0]
        let cmd = DroneCommand(
            cmd: "patrol",
            args: ["waypoints": AnyCodable([waypoint])],
            seq: 60
        )
        let ack = await router.dispatch(cmd)
        XCTAssertEqual(ack.result, .error)
        XCTAssertTrue(
            ack.message?.contains("E_UNSUPPORTED") == true,
            "patrol should surface unsupported (was silently RTH before Phase 7.2); got: \(ack.message ?? "nil")"
        )
    }

    // MARK: - capture_visual_clip removed (Phase 7.2: deferred)

    func test_capture_visual_clip_is_unknown_command() async {
        let router = makeRouter()
        let cmd = DroneCommand(
            cmd: "capture_visual_clip",
            args: ["duration_s": AnyCodable(5.0)],
            seq: 70
        )
        let ack = await router.dispatch(cmd)
        XCTAssertEqual(ack.result, .error)
        // Removed from router; falls through to "unknown" branch.
        XCTAssertTrue(ack.message?.contains("E_UNKNOWN_CMD") == true)
    }

    // MARK: - MissionV1 envelope decoding

    func test_decode_legacy_envelope() throws {
        let raw = #"{"cmd":"takeoff","args":{"alt_m":5.0},"seq":42}"#
        let cmd = try decode(raw)
        XCTAssertEqual(cmd.cmd, "takeoff")
        XCTAssertEqual(cmd.seq, 42)
        XCTAssertNil(cmd.metadata, "Legacy envelope has no metadata")
    }

    func test_decode_v1_envelope_populates_metadata() throws {
        let raw = """
        {
          "version": 1,
          "metadata": {
            "mission_id": "m001",
            "ranch_id": "ranch_a",
            "scenario": "coyote_fence",
            "wind_kt": 12.5,
            "battery_floor_pct": 35.0,
            "geofence_version": "ranch_a@v3",
            "issued_by": "FenceLineDispatcher"
          },
          "command": {"cmd": "takeoff", "args": {"alt_m": 5.0}},
          "seq": 42
        }
        """
        let cmd = try decode(raw)
        XCTAssertEqual(cmd.cmd, "takeoff")
        XCTAssertEqual(cmd.seq, 42)
        XCTAssertEqual(cmd.args["alt_m"]?.value as? Double, 5.0)
        XCTAssertEqual(cmd.metadata?.missionId, "m001")
        XCTAssertEqual(cmd.metadata?.batteryFloorPct, 35.0)
        XCTAssertEqual(cmd.metadata?.windKt, 12.5)
        XCTAssertEqual(cmd.metadata?.geofenceVersion, "ranch_a@v3")
        XCTAssertEqual(cmd.metadata?.issuedBy, "FenceLineDispatcher")
    }

    func test_decode_v1_envelope_with_unknown_keys_ignored() throws {
        // Forward-compat: extra top-level + metadata keys must not break parse.
        let raw = """
        {
          "version": 1,
          "metadata": {"mission_id": "m002", "future_field": 123},
          "command": {"cmd": "return_to_home", "args": {}},
          "seq": 7,
          "deterrent_tone_hz": 12000
        }
        """
        let cmd = try decode(raw)
        XCTAssertEqual(cmd.cmd, "return_to_home")
        XCTAssertEqual(cmd.seq, 7)
        XCTAssertEqual(cmd.metadata?.missionId, "m002")
    }

    func test_decode_v1_envelope_reject_wrong_version() {
        let raw = """
        {"version": 99, "metadata": {"mission_id": "x"},
         "command": {"cmd": "takeoff", "args": {}}, "seq": 1}
        """
        XCTAssertThrowsError(try decode(raw))
    }

    // MARK: - V1 metadata propagates to guards

    func test_v1_metadata_battery_floor_rejects_marginal_battery() async {
        // Using default (stub) DJIBridge — batteryPct defaults to 100 in snapshot.
        // To force the reject we set floor above the stub battery.
        let router = makeRouter()
        let cmd = DroneCommand(
            cmd: "takeoff",
            args: ["alt_m": AnyCodable(5.0)],
            seq: 80,
            metadata: MissionMetadata(batteryFloorPct: 110.0)  // impossibly high → should reject
        )
        let ack = await router.dispatch(cmd)
        XCTAssertEqual(ack.result, .error)
        XCTAssertTrue(
            ack.message?.contains("E_BATTERY_LOW") == true,
            "Per-call metadata floor must reject; got: \(ack.message ?? "nil")"
        )
    }

    func test_v1_metadata_wind_rejects_high_wind() async {
        let router = makeRouter()
        let cmd = DroneCommand(
            cmd: "takeoff",
            args: ["alt_m": AnyCodable(5.0)],
            seq: 81,
            metadata: MissionMetadata(windKt: 25.0)  // above 21 kt ceiling
        )
        let ack = await router.dispatch(cmd)
        XCTAssertEqual(ack.result, .error)
        XCTAssertTrue(
            ack.message?.contains("E_WIND_CEILING") == true,
            "Per-call metadata wind must reject; got: \(ack.message ?? "nil")"
        )
    }

    func test_v1_metadata_calm_wind_allows_takeoff() async {
        let router = makeRouter()
        let cmd = DroneCommand(
            cmd: "takeoff",
            args: ["alt_m": AnyCodable(5.0)],
            seq: 82,
            metadata: MissionMetadata(windKt: 8.0, batteryFloorPct: 30.0)
        )
        let ack = await router.dispatch(cmd)
        XCTAssertEqual(ack.result, .ok, "Calm wind + stub battery 100% should allow takeoff; got: \(ack.message ?? "nil")")
    }
}
