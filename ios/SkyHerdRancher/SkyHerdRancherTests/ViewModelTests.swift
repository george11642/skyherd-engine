import XCTest
@testable import SkyHerdRancher

// MARK: - LiveViewModel Tests

@MainActor
final class LiveViewModelTests: XCTestCase {

    func testHandleScenarioActive() {
        let vm = LiveViewModel()
        let event = ScenarioActiveEvent(name: "coyote", passIdx: 0, speed: 15.0, startedAt: "2026-04-22T15:00:00Z")
        vm.handle(event)
        XCTAssertEqual(vm.activeScenario, "coyote")
        XCTAssertEqual(vm.speed, 15.0, accuracy: 0.001)
    }

    func testHandleScenarioEnded() {
        let vm = LiveViewModel()
        let active = ScenarioActiveEvent(name: "storm", passIdx: 1, speed: 20.0, startedAt: "2026-04-22T15:00:00Z")
        vm.handle(active)
        XCTAssertEqual(vm.activeScenario, "storm")

        let ended = ScenarioEndedEvent(name: "storm", passIdx: 1, outcome: "ok",
                                       startedAt: "2026-04-22T15:00:00Z", endedAt: "2026-04-22T15:01:00Z")
        vm.handle(ended)
        XCTAssertNil(vm.activeScenario)
    }

    func testHandleAgentLog() {
        let vm = LiveViewModel()
        let log = AgentLogEvent(ts: 1.0, agent: "FenceLineDispatcher", state: "active",
                                message: "Breach detected", level: "info", tool: nil, line: nil, seq: 1)
        vm.handle(log)
        XCTAssertEqual(vm.recentEvents.count, 1)
        XCTAssertEqual(vm.recentEvents[0].agent, "FenceLineDispatcher")
    }

    func testAgentLogCapAt50() {
        let vm = LiveViewModel()
        for i in 0..<60 {
            let log = AgentLogEvent(ts: Double(i), agent: "Agent", state: nil,
                                    message: "msg \(i)", level: nil, tool: nil, line: nil, seq: i)
            vm.handle(log)
        }
        XCTAssertEqual(vm.recentEvents.count, 50)
    }

    func testAgentLogNewestFirst() {
        let vm = LiveViewModel()
        let log1 = AgentLogEvent(ts: 1.0, agent: "A", state: nil, message: "first",
                                  level: nil, tool: nil, line: nil, seq: 1)
        let log2 = AgentLogEvent(ts: 2.0, agent: "B", state: nil, message: "second",
                                  level: nil, tool: nil, line: nil, seq: 2)
        vm.handle(log1)
        vm.handle(log2)
        XCTAssertEqual(vm.recentEvents[0].agent, "B")  // newest at index 0
        XCTAssertEqual(vm.recentEvents[1].agent, "A")
    }

    func testCostTickUpdatesRate() {
        let vm = LiveViewModel()
        let agents: [AgentCostEntry] = []
        let tick = CostTick(ts: 1.0, seq: 1, agents: agents, allIdle: true,
                            ratePerHrUsd: 0.042, totalCumulativeUsd: 0.001)
        vm.handle(tick)
        XCTAssertEqual(vm.costRate, 0.042, accuracy: 0.0001)
        XCTAssertTrue(vm.allIdle)
    }
}

// MARK: - LedgerViewModel Tests

@MainActor
final class LedgerViewModelTests: XCTestCase {

    private func makeEntry(seq: Int, hash: String, source: String) -> AttestEntry {
        AttestEntry(seq: seq, tsIso: "2026-04-22T15:00:00Z", source: source,
                    kind: "sensor.reading", payloadJson: "{}", prevHash: "0000",
                    eventHash: hash, signature: "sig", pubkey: "pub", memverId: nil)
    }

    func testSearchFilteringByHashPrefix() {
        let vm = LedgerViewModel()
        vm.entries = [
            makeEntry(seq: 1, hash: "cafebabe0000", source: "AgentA"),
            makeEntry(seq: 2, hash: "deadbeef0000", source: "AgentB"),
            makeEntry(seq: 3, hash: "cafebabe1111", source: "AgentC"),
        ]
        vm.searchText = "cafebabe"
        let filtered = vm.filteredEntries
        XCTAssertEqual(filtered.count, 2)
        XCTAssertTrue(filtered.allSatisfy { $0.eventHash.hasPrefix("cafebabe") })
    }

    func testSearchFilteringBySource() {
        let vm = LedgerViewModel()
        vm.entries = [
            makeEntry(seq: 1, hash: "aaa", source: "FenceLineDispatcher"),
            makeEntry(seq: 2, hash: "bbb", source: "HerdHealthWatcher"),
        ]
        vm.searchText = "fence"
        let filtered = vm.filteredEntries
        XCTAssertEqual(filtered.count, 1)
        XCTAssertEqual(filtered[0].source, "FenceLineDispatcher")
    }

    func testEmptySearchReturnsAll() {
        let vm = LedgerViewModel()
        vm.entries = [
            makeEntry(seq: 1, hash: "aaa", source: "A"),
            makeEntry(seq: 2, hash: "bbb", source: "B"),
        ]
        vm.searchText = ""
        XCTAssertEqual(vm.filteredEntries.count, 2)
    }

    func testHandleNewEntry() {
        let vm = LedgerViewModel()
        let entry = makeEntry(seq: 5, hash: "newentry", source: "CalvingWatch")
        vm.handle(entry)
        XCTAssertEqual(vm.entries.count, 1)
        XCTAssertEqual(vm.lastSeq, 5)
    }

    func testHandleDuplicateEntryNotAdded() {
        let vm = LedgerViewModel()
        let entry = makeEntry(seq: 5, hash: "newentry", source: "CalvingWatch")
        vm.handle(entry)
        vm.handle(entry)  // duplicate
        XCTAssertEqual(vm.entries.count, 1)
    }

    func testHandleInitial() {
        let vm = LedgerViewModel()
        let entries = [
            makeEntry(seq: 1, hash: "aaa", source: "A"),
            makeEntry(seq: 3, hash: "bbb", source: "B"),
        ]
        vm.handleInitial(entries)
        XCTAssertEqual(vm.entries.count, 2)
        XCTAssertEqual(vm.lastSeq, 3)
    }

    func testAppendMore() {
        let vm = LedgerViewModel()
        vm.handleInitial([makeEntry(seq: 1, hash: "aaa", source: "A")])
        vm.appendMore([
            makeEntry(seq: 2, hash: "bbb", source: "B"),
            makeEntry(seq: 1, hash: "aaa", source: "A"),  // duplicate — should not be added
        ])
        XCTAssertEqual(vm.entries.count, 2)
        XCTAssertEqual(vm.lastSeq, 2)
    }
}

// MARK: - AlertsViewModel Tests

@MainActor
final class AlertsViewModelTests: XCTestCase {

    func testHandleVetIntake() {
        let vm = AlertsViewModel()
        let event = VetIntakeDraftedEvent(id: "A014_test", cowTag: "A014",
                                          severity: "escalate", path: "/tmp/t.md", ts: 1.0)
        vm.handle(event)
        XCTAssertEqual(vm.alerts.count, 1)
        XCTAssertEqual(vm.unreadCount, 1)
    }

    func testAcknowledgeReducesUnread() {
        let vm = AlertsViewModel()
        let event = VetIntakeDraftedEvent(id: "A014_test", cowTag: "A014",
                                          severity: "escalate", path: "/tmp/t.md", ts: 1.0)
        vm.handle(event)
        XCTAssertEqual(vm.unreadCount, 1)
        vm.acknowledge(vm.alerts[0].id)
        XCTAssertEqual(vm.unreadCount, 0)
    }

    func testNoDuplicateAlerts() {
        let vm = AlertsViewModel()
        let event = VetIntakeDraftedEvent(id: "A014_test", cowTag: "A014",
                                          severity: "escalate", path: "/tmp/t.md", ts: 1.0)
        vm.handle(event)
        vm.handle(event)
        XCTAssertEqual(vm.alerts.count, 1)
    }
}

// MARK: - AgentsViewModel Tests

@MainActor
final class AgentsViewModelTests: XCTestCase {

    func testHandleInitialAgents() {
        let vm = AgentsViewModel()
        let statuses = [
            AgentStatus(name: "FenceLineDispatcher", sessionId: "sess_mock_1",
                        state: "idle", lastWake: nil,
                        cumulativeTokensIn: 100, cumulativeTokensOut: 50, cumulativeCostUsd: 0.001)
        ]
        vm.handleInitial(statuses)
        XCTAssertEqual(vm.agentStatuses["FenceLineDispatcher"]?.state, "idle")
    }

    func testCostTickUpdatesCostHistory() throws {
        let vm = AgentsViewModel()
        let entry = AgentCostEntry(name: "HerdHealthWatcher", state: "active",
                                   costDeltaUsd: 0.00005, cumulativeCostUsd: 0.001,
                                   tokensIn: 100, tokensOut: 30)
        let tick = CostTick(ts: 1.0, seq: 1, agents: [entry], allIdle: false,
                            ratePerHrUsd: 0.01, totalCumulativeUsd: 0.001)
        vm.handle(tick)
        XCTAssertEqual(vm.costHistory["HerdHealthWatcher"]?.count, 1)
        let delta = try XCTUnwrap(vm.costHistory["HerdHealthWatcher"]?.first)
        XCTAssertEqual(delta, 0.00005, accuracy: 0.000001)
    }

    func testCostHistoryCapAt20() {
        let vm = AgentsViewModel()
        for i in 0..<25 {
            let entry = AgentCostEntry(name: "GrazingOptimizer", state: "active",
                                       costDeltaUsd: Double(i) * 0.00001, cumulativeCostUsd: 0.001,
                                       tokensIn: 100, tokensOut: 30)
            let tick = CostTick(ts: Double(i), seq: i, agents: [entry], allIdle: false,
                                ratePerHrUsd: 0.01, totalCumulativeUsd: 0.001)
            vm.handle(tick)
        }
        XCTAssertLessThanOrEqual(vm.costHistory["GrazingOptimizer"]?.count ?? 0, 20)
    }
}
