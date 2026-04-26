import XCTest
@testable import SkyHerdRancher

final class ModelsTests: XCTestCase {

    private let decoder = JSONDecoder()

    // MARK: - Fixture loader

    private func fixture(_ name: String) throws -> Data {
        let bundle = Bundle(for: type(of: self))
        // Look in bundle first (for compiled tests), fall back to file system
        if let url = bundle.url(forResource: name.replacingOccurrences(of: ".json", with: ""),
                                withExtension: "json") {
            return try Data(contentsOf: url)
        }
        // File-system fallback for xcodebuild test runs
        let dir = URL(fileURLWithPath: #file)
            .deletingLastPathComponent()
            .appendingPathComponent("Fixtures")
        let url = dir.appendingPathComponent(name)
        return try Data(contentsOf: url)
    }

    // MARK: - WorldSnapshot

    func testWorldSnapshotDecode() throws {
        let data = try fixture("world_snapshot.json")
        let snapshot = try decoder.decode(WorldSnapshot.self, from: data)
        XCTAssertEqual(snapshot.cows.count, 12)
        XCTAssertFalse(snapshot.paddocks.isEmpty)
        XCTAssertEqual(snapshot.paddocks.count, 4)
        XCTAssertEqual(snapshot.waterTanks.count, 2)
        XCTAssertEqual(snapshot.predators.count, 1)
        XCTAssertFalse(snapshot.isNight)
        XCTAssertEqual(snapshot.weather.conditions, "clear")
        XCTAssertEqual(snapshot.weather.tempF, 72.5, accuracy: 0.01)
    }

    func testCowFields() throws {
        let data = try fixture("world_snapshot.json")
        let snapshot = try decoder.decode(WorldSnapshot.self, from: data)
        let cow = snapshot.cows[0]
        XCTAssertEqual(cow.id, "cow_001")
        XCTAssertEqual(cow.tag, "A001")
        XCTAssertEqual(cow.pos.count, 2)
        XCTAssertEqual(cow.pos[0], 0.12, accuracy: 0.001)
        XCTAssertEqual(cow.state, "grazing")
        XCTAssertEqual(cow.headingDeg, 45.0)
    }

    func testPaddockBounds() throws {
        let data = try fixture("world_snapshot.json")
        let snapshot = try decoder.decode(WorldSnapshot.self, from: data)
        let north = snapshot.paddocks.first { $0.id == "north" }!
        XCTAssertEqual(north.bounds, [0.0, 0.0, 0.5, 0.5])
        XCTAssertEqual(north.foragePct, 78.5, accuracy: 0.01)
    }

    func testDroneFields() throws {
        let data = try fixture("world_snapshot.json")
        let snapshot = try decoder.decode(WorldSnapshot.self, from: data)
        XCTAssertEqual(snapshot.drone.state, "patrol")
        XCTAssertEqual(snapshot.drone.batteryPct, 82.5)
        XCTAssertEqual(snapshot.drone.altM, 30.0)
    }

    // MARK: - CostTick

    func testCostTickDecode() throws {
        let data = try fixture("cost_tick.json")
        let tick = try decoder.decode(CostTick.self, from: data)
        XCTAssertEqual(tick.seq, 42)
        XCTAssertFalse(tick.allIdle)
        XCTAssertEqual(tick.agents.count, 6)
        XCTAssertEqual(tick.ratePerHrUsd, 0.0829, accuracy: 0.0001)
        XCTAssertEqual(tick.totalCumulativeUsd, 0.01034, accuracy: 0.0001)
    }

    func testAgentCostEntry() throws {
        let data = try fixture("cost_tick.json")
        let tick = try decoder.decode(CostTick.self, from: data)
        let active = tick.agents.first { $0.name == "FenceLineDispatcher" }!
        XCTAssertEqual(active.state, "active")
        XCTAssertEqual(active.costDeltaUsd, 0.000023, accuracy: 0.0000001)
        XCTAssertEqual(active.tokensIn, 1500)
        XCTAssertEqual(active.tokensOut, 420)
    }

    // MARK: - AttestEntry

    func testAttestEntryDecode() throws {
        let data = try fixture("attest_entry.json")
        let entry = try decoder.decode(AttestEntry.self, from: data)
        XCTAssertEqual(entry.seq, 17)
        XCTAssertEqual(entry.source, "FenceLineDispatcher")
        XCTAssertEqual(entry.kind, "fence.breach")
        XCTAssertNil(entry.memverId)
        XCTAssertEqual(entry.eventHash, "cafebabe0000000011111111222222223333333344444444555555556666666677")
        XCTAssertFalse(entry.payloadJson.isEmpty)
    }

    // MARK: - AgentLogEvent

    func testAgentLogEventDecode() throws {
        let data = try fixture("agent_log.json")
        let event = try decoder.decode(AgentLogEvent.self, from: data)
        XCTAssertEqual(event.agent, "FenceLineDispatcher")
        XCTAssertEqual(event.state, "active")
        XCTAssertNotNil(event.message)
        XCTAssertEqual(event.seq, 101)
        XCTAssertNil(event.tool)
    }

    // MARK: - Scenario events

    func testScenarioActiveEventDecode() throws {
        let json = """
        {"name":"coyote","pass_idx":0,"speed":15.0,"started_at":"2026-04-22T15:00:00Z"}
        """
        let event = try decoder.decode(ScenarioActiveEvent.self, from: Data(json.utf8))
        XCTAssertEqual(event.name, "coyote")
        XCTAssertEqual(event.passIdx, 0)
        XCTAssertEqual(event.speed, 15.0)
        XCTAssertEqual(event.startedAt, "2026-04-22T15:00:00Z")
    }

    func testScenarioEndedEventDecode() throws {
        let json = """
        {"name":"coyote","pass_idx":0,"outcome":"ok","started_at":"2026-04-22T15:00:00Z","ended_at":"2026-04-22T15:01:30Z"}
        """
        let event = try decoder.decode(ScenarioEndedEvent.self, from: Data(json.utf8))
        XCTAssertEqual(event.name, "coyote")
        XCTAssertEqual(event.outcome, "ok")
    }

    // MARK: - VetIntakeDraftedEvent

    func testVetIntakeDraftedDecode() throws {
        let json = """
        {"id":"A014_20260422T153200Z","cow_tag":"A014","severity":"escalate","path":"/tmp/intake.md","ts":1745200010.0}
        """
        let event = try decoder.decode(VetIntakeDraftedEvent.self, from: Data(json.utf8))
        XCTAssertEqual(event.id, "A014_20260422T153200Z")
        XCTAssertEqual(event.cowTag, "A014")
        XCTAssertEqual(event.severity, "escalate")
    }

    // MARK: - NeighborAlertEvent

    func testNeighborAlertDecode() throws {
        let json = """
        {"from_ranch":"ranch_a","to_ranch":"ranch_b","species":"coyote","shared_fence":"fence_east","confidence":0.91,"ts":1745200020.0,"attestation_hash":"deadbeef"}
        """
        let event = try decoder.decode(NeighborAlertEvent.self, from: Data(json.utf8))
        XCTAssertEqual(event.fromRanch, "ranch_a")
        XCTAssertEqual(event.species, "coyote")
        XCTAssertEqual(event.confidence, 0.91, accuracy: 0.001)
    }

    // MARK: - NeighborHandoffEvent

    func testNeighborHandoffDecode() throws {
        let json = """
        {"from_ranch":"ranch_a","to_ranch":"ranch_b","species":"coyote","shared_fence":"fence_east","response_mode":"intercept","tool_calls":["dispatch_drone","page_rancher"],"rancher_paged":true,"ts":1745200025.0}
        """
        let event = try decoder.decode(NeighborHandoffEvent.self, from: Data(json.utf8))
        XCTAssertEqual(event.responseMode, "intercept")
        XCTAssertEqual(event.toolCalls.count, 2)
        XCTAssertTrue(event.rancherPaged)
    }

    // MARK: - MemoryWrittenEvent

    func testMemoryWrittenDecode() throws {
        let json = """
        {"agent":"FenceLineDispatcher","memory_store_id":"store_001","memory_id":"mem_abc","memory_version_id":"ver_xyz","content_sha256":"sha256abc","path":"/fence/coyote_track"}
        """
        let event = try decoder.decode(MemoryWrittenEvent.self, from: Data(json.utf8))
        XCTAssertEqual(event.agent, "FenceLineDispatcher")
        XCTAssertEqual(event.path, "/fence/coyote_track")
    }
}
