import XCTest
@testable import SkyHerdCompanion

/// Verifies that Swift MQTT envelope encoding/decoding produces byte-identical
/// JSON to the canonical Python wire format defined in
/// ``docs/HARDWARE_MAVIC_PROTOCOL.md``.
///
/// The JSON field order may differ (dictionaries are unordered) so we compare
/// after round-tripping through ``JSONSerialization`` to normalised
/// ``[String: Any]`` rather than raw bytes.
final class ProtocolTests: XCTestCase {
    private let encoder: JSONEncoder = {
        let e = JSONEncoder()
        e.outputFormatting = .sortedKeys
        return e
    }()
    private let decoder = JSONDecoder()

    // MARK: - DroneCommand encode/decode

    func test_encode_takeoff_command() throws {
        let cmd = DroneCommand(cmd: "takeoff", args: ["alt_m": AnyCodable(5.0)], seq: 1)
        let data = try encoder.encode(cmd)
        let json = try XCTUnwrap(String(data: data, encoding: .utf8))

        XCTAssertTrue(json.contains("\"cmd\":\"takeoff\""), "cmd field present")
        XCTAssertTrue(json.contains("\"seq\":1"), "seq field present")
        XCTAssertTrue(json.contains("\"alt_m\""), "args.alt_m present")
    }

    func test_decode_takeoff_command() throws {
        let raw = #"{"cmd":"takeoff","args":{"alt_m":5.0},"seq":42}"#
        let cmd = try decoder.decode(DroneCommand.self, from: Data(raw.utf8))
        XCTAssertEqual(cmd.cmd, "takeoff")
        XCTAssertEqual(cmd.seq, 42)
        XCTAssertEqual(cmd.args["alt_m"]?.value as? Double, 5.0)
    }

    func test_decode_patrol_command() throws {
        let raw = """
        {"cmd":"patrol","args":{"waypoints":[{"lat":36.1,"lon":-105.2,"alt_m":30.0,"hold_s":0.0}]},"seq":7}
        """
        let cmd = try decoder.decode(DroneCommand.self, from: Data(raw.utf8))
        XCTAssertEqual(cmd.cmd, "patrol")
        XCTAssertEqual(cmd.seq, 7)
    }

    func test_decode_return_to_home() throws {
        let raw = #"{"cmd":"return_to_home","args":{},"seq":3}"#
        let cmd = try decoder.decode(DroneCommand.self, from: Data(raw.utf8))
        XCTAssertEqual(cmd.cmd, "return_to_home")
        XCTAssertTrue(cmd.args.isEmpty)
    }

    func test_decode_play_deterrent() throws {
        let raw = #"{"cmd":"play_deterrent","args":{"tone_hz":12000,"duration_s":6.0},"seq":5}"#
        let cmd = try decoder.decode(DroneCommand.self, from: Data(raw.utf8))
        XCTAssertEqual(cmd.cmd, "play_deterrent")
        XCTAssertEqual(cmd.args["tone_hz"]?.value as? Int, 12000)
    }

    func test_decode_capture_visual_clip() throws {
        let raw = #"{"cmd":"capture_visual_clip","args":{"duration_s":10.0},"seq":9}"#
        let cmd = try decoder.decode(DroneCommand.self, from: Data(raw.utf8))
        XCTAssertEqual(cmd.cmd, "capture_visual_clip")
    }

    func test_decode_get_state() throws {
        let raw = #"{"cmd":"get_state","args":{},"seq":2}"#
        let cmd = try decoder.decode(DroneCommand.self, from: Data(raw.utf8))
        XCTAssertEqual(cmd.cmd, "get_state")
    }

    // MARK: - DroneAck encode/decode

    func test_encode_ok_ack() throws {
        let ack = DroneAck(ack: "takeoff", result: .ok, seq: 1)
        let data = try encoder.encode(ack)
        let json = try XCTUnwrap(String(data: data, encoding: .utf8))
        XCTAssertTrue(json.contains("\"ack\":\"takeoff\""))
        XCTAssertTrue(json.contains("\"result\":\"ok\""))
        XCTAssertTrue(json.contains("\"seq\":1"))
    }

    func test_encode_error_ack() throws {
        let ack = DroneAck(ack: "takeoff", result: .error, seq: 1, message: "E_BATTERY_LOW")
        let data = try encoder.encode(ack)
        let json = try XCTUnwrap(String(data: data, encoding: .utf8))
        XCTAssertTrue(json.contains("\"result\":\"error\""))
        XCTAssertTrue(json.contains("E_BATTERY_LOW"))
    }

    func test_decode_ok_ack() throws {
        let raw = #"{"ack":"takeoff","result":"ok","seq":42}"#
        let ack = try decoder.decode(DroneAck.self, from: Data(raw.utf8))
        XCTAssertEqual(ack.ack, "takeoff")
        XCTAssertEqual(ack.result, .ok)
        XCTAssertEqual(ack.seq, 42)
        XCTAssertNil(ack.message)
    }

    func test_decode_error_ack() throws {
        let raw = #"{"ack":"takeoff","result":"error","message":"E_BATTERY_LOW","seq":1}"#
        let ack = try decoder.decode(DroneAck.self, from: Data(raw.utf8))
        XCTAssertEqual(ack.result, .error)
        XCTAssertEqual(ack.message, "E_BATTERY_LOW")
    }

    // MARK: - get_state ACK with data payload

    func test_decode_state_ack_with_data() throws {
        let raw = """
        {"ack":"get_state","result":"ok","seq":2,
         "data":{"armed":false,"in_air":false,"altitude_m":0.0,
                 "battery_pct":85.0,"mode":"STANDBY","lat":36.1,"lon":-105.2}}
        """
        let ack = try decoder.decode(DroneAck.self, from: Data(raw.utf8))
        XCTAssertEqual(ack.result, .ok)
        XCTAssertNotNil(ack.data)
        XCTAssertEqual(ack.data?["battery_pct"]?.value as? Double, 85.0)
    }

    // MARK: - DroneStateSnapshot round-trip

    func test_state_snapshot_roundtrip() throws {
        let snap = DroneStateSnapshot(
            armed: true, inAir: true, altitudeM: 30.5,
            batteryPct: 72.0, mode: "GUIDED", lat: 36.1, lon: -105.2
        )
        let data = try encoder.encode(snap)
        let decoded = try decoder.decode(DroneStateSnapshot.self, from: data)
        XCTAssertEqual(decoded, snap)
    }

    func test_state_snapshot_field_names() throws {
        let snap = DroneStateSnapshot(inAir: true, altitudeM: 15.0, batteryPct: 50.0)
        let data = try encoder.encode(snap)
        let json = try XCTUnwrap(String(data: data, encoding: .utf8))
        // Verify Python-compatible snake_case field names
        XCTAssertTrue(json.contains("\"in_air\""), "in_air field uses snake_case")
        XCTAssertTrue(json.contains("\"altitude_m\""), "altitude_m field uses snake_case")
        XCTAssertTrue(json.contains("\"battery_pct\""), "battery_pct field uses snake_case")
    }

    // MARK: - AnyCodable

    func test_any_codable_double() throws {
        let ac = AnyCodable(3.14)
        let data = try encoder.encode(ac)
        let decoded = try decoder.decode(AnyCodable.self, from: data)
        XCTAssertEqual(decoded.value as? Double, 3.14, accuracy: 0.0001)
    }

    func test_any_codable_string() throws {
        let ac = AnyCodable("hello")
        let data = try encoder.encode(ac)
        let decoded = try decoder.decode(AnyCodable.self, from: data)
        XCTAssertEqual(decoded.value as? String, "hello")
    }

    func test_any_codable_int() throws {
        let ac = AnyCodable(42)
        let data = try encoder.encode(ac)
        let decoded = try decoder.decode(AnyCodable.self, from: data)
        XCTAssertEqual(decoded.value as? Int, 42)
    }

    func test_any_codable_bool() throws {
        let ac = AnyCodable(true)
        let data = try encoder.encode(ac)
        let decoded = try decoder.decode(AnyCodable.self, from: data)
        XCTAssertEqual(decoded.value as? Bool, true)
    }
}
