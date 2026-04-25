import XCTest
@testable import SkyHerdRancher

final class SSEClientTests: XCTestCase {

    private let decoder = JSONDecoder()

    // MARK: - SSEFrame parsing helpers (testing pure parsing logic)

    /// Simulate the SSE line parser on a sequence of lines, return accumulated frames.
    private func parseLines(_ lines: [String]) -> [SSEFrame] {
        var frames: [SSEFrame] = []
        var current = SSEFrame()

        for line in lines {
            if line.hasPrefix("event:") {
                current.eventType = String(line.dropFirst(6)).trimmingCharacters(in: .whitespaces)
            } else if line.hasPrefix("data:") {
                let chunk = String(line.dropFirst(5)).trimmingCharacters(in: .whitespaces)
                if current.data.isEmpty {
                    current.data = chunk
                } else {
                    current.data += "\n" + chunk
                }
            } else if line.hasPrefix(":") {
                // comment / keepalive — ignore
            } else if line.isEmpty {
                if !current.data.isEmpty {
                    frames.append(current)
                }
                current = SSEFrame()
            }
        }

        return frames
    }

    // MARK: - Basic frame parsing

    func testBasicEventFrame() {
        let lines = [
            "event: world.snapshot",
            "data: {\"ts\":1.0,\"sim_time_s\":10.0,\"clock_iso\":\"2026-04-22T00:00:00Z\",\"is_night\":false,\"weather\":{\"conditions\":\"clear\",\"temp_f\":70.0,\"wind_kt\":5.0,\"humidity_pct\":40.0},\"cows\":[],\"predators\":[],\"drone\":{},\"paddocks\":[],\"water_tanks\":[]}",
            ""
        ]
        let frames = parseLines(lines)
        XCTAssertEqual(frames.count, 1)
        XCTAssertEqual(frames[0].eventType, "world.snapshot")
        XCTAssertFalse(frames[0].data.isEmpty)
    }

    func testMultipleFrames() {
        let lines = [
            "event: agent.log",
            "data: {\"ts\":1.0,\"agent\":\"FenceLineDispatcher\"}",
            "",
            "event: cost.tick",
            "data: {\"ts\":2.0,\"seq\":1,\"agents\":[],\"all_idle\":true,\"rate_per_hr_usd\":0.0,\"total_cumulative_usd\":0.0}",
            ""
        ]
        let frames = parseLines(lines)
        XCTAssertEqual(frames.count, 2)
        XCTAssertEqual(frames[0].eventType, "agent.log")
        XCTAssertEqual(frames[1].eventType, "cost.tick")
    }

    func testKeepAliveCommentsIgnored() {
        let lines = [
            ": keep-alive",
            "event: agent.log",
            "data: {\"ts\":1.0,\"agent\":\"HerdHealthWatcher\"}",
            "",
            ": heartbeat",
            ""
        ]
        let frames = parseLines(lines)
        XCTAssertEqual(frames.count, 1)
        XCTAssertEqual(frames[0].eventType, "agent.log")
    }

    func testMalformedFrameWithNoData() {
        let lines = [
            "event: world.snapshot",
            // no data line
            ""
        ]
        let frames = parseLines(lines)
        XCTAssertEqual(frames.count, 0, "Frame with no data should be dropped")
    }

    func testDefaultEventType() {
        let lines = [
            "data: {\"ts\":1.0,\"agent\":\"CalvingWatch\"}",
            ""
        ]
        let frames = parseLines(lines)
        XCTAssertEqual(frames.count, 1)
        XCTAssertEqual(frames[0].eventType, "message")
    }

    func testMultilineData() {
        let lines = [
            "event: agent.log",
            "data: {\"ts\":1.0,",
            "data: \"agent\":\"GrazingOptimizer\"}",
            ""
        ]
        let frames = parseLines(lines)
        XCTAssertEqual(frames.count, 1)
        XCTAssertTrue(frames[0].data.contains("GrazingOptimizer"))
    }

    // MARK: - SkyHerdEvent decode from frames

    func testDecodeAgentLogFromFrame() {
        let frame = SSEFrame(eventType: "agent.log", data: "{\"ts\":1.0,\"agent\":\"FenceLineDispatcher\",\"state\":\"active\",\"message\":\"Breach detected\"}")
        let event = SkyHerdEvent.decode(frame: frame, decoder: decoder)
        guard case .agentLog(let log) = event else {
            XCTFail("Expected agentLog, got \(String(describing: event))")
            return
        }
        XCTAssertEqual(log.agent, "FenceLineDispatcher")
        XCTAssertEqual(log.state, "active")
    }

    func testDecodeScenarioActive() {
        let frame = SSEFrame(
            eventType: "scenario.active",
            data: "{\"name\":\"coyote\",\"pass_idx\":0,\"speed\":15.0,\"started_at\":\"2026-04-22T15:00:00Z\"}"
        )
        let event = SkyHerdEvent.decode(frame: frame, decoder: decoder)
        guard case .scenarioActive(let s) = event else {
            XCTFail("Expected scenarioActive")
            return
        }
        XCTAssertEqual(s.name, "coyote")
        XCTAssertEqual(s.speed, 15.0)
    }

    func testUnknownEventType() {
        let frame = SSEFrame(eventType: "some.future.event", data: "{\"foo\":\"bar\"}")
        let event = SkyHerdEvent.decode(frame: frame, decoder: decoder)
        guard case .unknown(let type, _) = event else {
            XCTFail("Expected unknown event")
            return
        }
        XCTAssertEqual(type, "some.future.event")
    }

    func testMalformedJSONReturnsNil() {
        let frame = SSEFrame(eventType: "agent.log", data: "not valid json{{{")
        let event = SkyHerdEvent.decode(frame: frame, decoder: decoder)
        // Decode returns nil for malformed JSON matching a known event type
        XCTAssertNil(event)
    }

    func testEmptyDataReturnsNil() {
        let frame = SSEFrame(eventType: "agent.log", data: "")
        let event = SkyHerdEvent.decode(frame: frame, decoder: decoder)
        XCTAssertNil(event)
    }

    // MARK: - Backoff delay calculation

    func testBackoffDelaySequence() {
        // 1s, 2s, 4s, 8s, 16s, 30s (cap) — excluding jitter
        let expected = [1.0, 2.0, 4.0, 8.0, 16.0, 30.0]
        for (i, expectedBase) in expected.enumerated() {
            let attempt = i + 1
            // Run 20 times to check jitter bounds
            for _ in 0..<20 {
                let delay = SSEClient.backoffDelay(attempt: attempt)
                XCTAssertGreaterThanOrEqual(delay, expectedBase,
                    "Delay for attempt \(attempt) should be >= \(expectedBase)")
                XCTAssertLessThan(delay, expectedBase + 0.5,
                    "Delay for attempt \(attempt) should be < \(expectedBase + 0.5) (jitter max 0.5)")
            }
        }
    }

    func testBackoffCapAt30s() {
        // Attempts beyond the table should stay capped at 30s + jitter
        for attempt in [7, 10, 20, 100] {
            let delay = SSEClient.backoffDelay(attempt: attempt)
            XCTAssertGreaterThanOrEqual(delay, 30.0)
            XCTAssertLessThan(delay, 30.5)
        }
    }

    func testBackoffFirstAttemptIsOneSec() {
        let delay = SSEClient.backoffDelay(attempt: 1)
        XCTAssertGreaterThanOrEqual(delay, 1.0)
        XCTAssertLessThan(delay, 1.5)
    }
}
