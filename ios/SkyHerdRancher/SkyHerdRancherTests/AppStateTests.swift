import XCTest
@testable import SkyHerdRancher

@MainActor
final class AppStateTests: XCTestCase {

    func testAppStateInitialization() {
        let appState = AppState()
        XCTAssertNotNil(appState.apiClient)
        XCTAssertNotNil(appState.liveVM)
        XCTAssertNotNil(appState.mapVM)
        XCTAssertNotNil(appState.agentsVM)
        XCTAssertNotNil(appState.alertsVM)
        XCTAssertNotNil(appState.ledgerVM)
    }

    func testInitialConnectionStateIsDisconnected() {
        let appState = AppState()
        XCTAssertEqual(appState.connectionState, .disconnected)
    }

    func testInitialViewModelState() {
        let appState = AppState()
        XCTAssertNil(appState.liveVM.activeScenario)
        XCTAssertEqual(appState.liveVM.speed, 15.0, accuracy: 0.001)
        XCTAssertFalse(appState.liveVM.isPaused)
        XCTAssertTrue(appState.liveVM.recentEvents.isEmpty)

        XCTAssertNil(appState.mapVM.snapshot)
        XCTAssertNil(appState.mapVM.activeScenario)
        XCTAssertTrue(appState.mapVM.breachPins.isEmpty)

        XCTAssertTrue(appState.agentsVM.agentStatuses.isEmpty)
        XCTAssertTrue(appState.alertsVM.alerts.isEmpty)
        XCTAssertEqual(appState.alertsVM.unreadCount, 0)
        XCTAssertTrue(appState.ledgerVM.entries.isEmpty)
    }

    func testLedgerVMFilteredEntriesEmpty() {
        let appState = AppState()
        appState.ledgerVM.searchText = "cafebabe"
        XCTAssertTrue(appState.ledgerVM.filteredEntries.isEmpty)
    }

    func testConfigurationDefaultURL() {
        let url = Configuration.defaultBaseURL
        XCTAssertEqual(url.scheme, "http")
        XCTAssertEqual(url.host, "localhost")
        XCTAssertEqual(url.port, 8000)
    }
}
