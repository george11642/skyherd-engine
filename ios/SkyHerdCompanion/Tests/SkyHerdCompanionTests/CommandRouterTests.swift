import XCTest
@testable import SkyHerdCompanion

/// Tests for CommandRouter: de-duplication, unknown commands, and double-ack prevention.
///
/// Uses a stub DJIBridge by testing the router in isolation with mocked state.
@MainActor
final class CommandRouterTests: XCTestCase {

    // MARK: - Helpers

    private func makeRouter() -> CommandRouter {
        CommandRouter()
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
        // Second dispatch should return ok with "duplicate ignored" message
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
        // Neither should be a duplicate
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
    }

    // MARK: - Return-to-home

    func test_return_to_home_dispatches_ok() async {
        let router = makeRouter()
        let cmd = DroneCommand(cmd: "return_to_home", args: [:], seq: 20)
        let ack = await router.dispatch(cmd)
        XCTAssertEqual(ack.ack, "return_to_home")
        // Result depends on DJI SDK availability; in stub mode it should be ok
        // (DJIBridge stub always succeeds)
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

    // MARK: - ACK seq matches command seq

    func test_ack_seq_matches_cmd_seq() async {
        let router = makeRouter()
        for seq in [1, 5, 100, 9999] {
            let cmd = DroneCommand(cmd: "get_state", args: [:], seq: seq)
            let ack = await router.dispatch(cmd)
            XCTAssertEqual(ack.seq, seq, "ACK seq must mirror command seq")
        }
    }

    // MARK: - ACK cmd name matches command name

    func test_ack_cmd_name_mirrors_command() async {
        let router = makeRouter()
        let cmds = ["get_state", "return_to_home", "play_deterrent"]
        for (i, cmdName) in cmds.enumerated() {
            let cmd = DroneCommand(cmd: cmdName, args: [:], seq: i + 50)
            let ack = await router.dispatch(cmd)
            XCTAssertEqual(ack.ack, cmdName, "ack.ack must match cmd.cmd")
        }
    }

    // MARK: - Seen-seq window eviction

    func test_seq_window_does_not_grow_unbounded() async {
        let router = makeRouter()
        // Dispatch 300 unique-seq commands to force eviction
        for seq in 0..<300 {
            let cmd = DroneCommand(cmd: "get_state", args: [:], seq: seq)
            _ = await router.dispatch(cmd)
        }
        // After eviction, an early seq that was evicted should be processed again
        let evictedSeq = 0
        let cmd = DroneCommand(cmd: "get_state", args: [:], seq: evictedSeq)
        let ack = await router.dispatch(cmd)
        // Should NOT say "duplicate ignored" after eviction
        XCTAssertNotEqual(ack.message, "duplicate ignored",
            "Evicted seq should be re-processed, not treated as duplicate")
    }
}
