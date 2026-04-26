import XCTest
@testable import SkyHerdRancher

@MainActor
final class MapViewModelTests: XCTestCase {

    // MARK: - Entity ingestion

    func testHandleWorldSnapshotStoresSnapshot() {
        let vm = MapViewModel()
        XCTAssertNil(vm.snapshot)
        let snapshot = makeSnapshot()
        vm.handle(snapshot)
        XCTAssertNotNil(vm.snapshot)
        XCTAssertEqual(vm.snapshot?.cows.count, 2)
    }

    func testHandleWorldSnapshotUpdatesSnapshot() {
        let vm = MapViewModel()
        vm.handle(makeSnapshot(cowCount: 2))
        vm.handle(makeSnapshot(cowCount: 5))
        XCTAssertEqual(vm.snapshot?.cows.count, 5)
    }

    // MARK: - Layer visibility flags

    func testDefaultLayerVisibility() {
        let vm = MapViewModel()
        XCTAssertTrue(vm.showPaddocks)
        XCTAssertTrue(vm.showFences)
        XCTAssertTrue(vm.showCows)
        XCTAssertTrue(vm.showDrone)
        XCTAssertTrue(vm.showPredators)
        XCTAssertTrue(vm.showTanks)
    }

    func testToggleCowLayer() {
        let vm = MapViewModel()
        vm.showCows = false
        XCTAssertFalse(vm.showCows)
        vm.showCows = true
        XCTAssertTrue(vm.showCows)
    }

    // MARK: - Breach events

    func testBreachEventAddedToBreachPins() {
        let vm = MapViewModel()
        let alert = makeNeighborAlert()
        vm.handle(alert)
        XCTAssertEqual(vm.breachPins.count, 1)
    }

    func testMultipleBreachesAccumulate() {
        let vm = MapViewModel()
        vm.handle(makeNeighborAlert(fence: "fence_a"))
        vm.handle(makeNeighborAlert(fence: "fence_b"))
        XCTAssertEqual(vm.breachPins.count, 2)
    }

    func testScenarioEndedClearsBreachPins() {
        let vm = MapViewModel()
        vm.handle(makeNeighborAlert())
        XCTAssertEqual(vm.breachPins.count, 1)
        let ended = ScenarioEndedEvent(
            name: "coyote", passIdx: 0, outcome: "ok",
            startedAt: "2026-04-22T15:00:00Z", endedAt: "2026-04-22T15:01:00Z"
        )
        vm.handle(ended)
        XCTAssertEqual(vm.breachPins.count, 0)
    }

    // MARK: - Scenario active / ended

    func testScenarioActiveSetsName() {
        let vm = MapViewModel()
        let event = ScenarioActiveEvent(name: "storm", passIdx: 0, speed: 15, startedAt: "2026-04-22T15:00:00Z")
        vm.handle(event)
        XCTAssertEqual(vm.activeScenario, "storm")
    }

    func testScenarioEndedClearsName() {
        let vm = MapViewModel()
        vm.handle(ScenarioActiveEvent(name: "storm", passIdx: 0, speed: 15, startedAt: "2026-04-22T15:00:00Z"))
        vm.handle(ScenarioEndedEvent(name: "storm", passIdx: 0, outcome: "ok",
                                     startedAt: "2026-04-22T15:00:00Z", endedAt: "2026-04-22T15:01:00Z"))
        XCTAssertNil(vm.activeScenario)
    }

    // MARK: - Periodic refresh cancellation

    func testOnDisappearCancelsRefresh() {
        // Verify onDisappear doesn't crash and cancels cleanly
        let vm = MapViewModel()
        vm.onAppear()
        vm.onDisappear()
        // If the refresh task was cancelled, onDisappear should leave refreshTask nil
        // We test indirectly by ensuring no crash and the snapshot remains nil
        XCTAssertNil(vm.snapshot) // no API client, so no data fetched
    }

    // MARK: - Helpers

    private func makeSnapshot(cowCount: Int = 2) -> WorldSnapshot {
        let cows = (0..<cowCount).map { i in
            Cow(id: "cow_\(i)", tag: "T\(i)", pos: [0.5, 0.5], bcs: 6.0, state: "grazing", headingDeg: 0)
        }
        return WorldSnapshot(
            ts: 1.0,
            simTimeS: 100.0,
            clockIso: "2026-04-22T15:00:00Z",
            isNight: false,
            weather: Weather(conditions: "clear", tempF: 72.0, windKt: 5.0, humidityPct: 0.45),
            cows: cows,
            predators: [],
            drone: Drone(lat: 34.12, lon: -106.45, altM: 10.0, state: "idle", batteryPct: 0.9),
            paddocks: [],
            waterTanks: []
        )
    }

    private func makeNeighborAlert(fence: String = "fence_north") -> NeighborAlertEvent {
        NeighborAlertEvent(
            fromRanch: "ranch_b",
            toRanch: "ranch_a",
            species: "coyote",
            sharedFence: fence,
            confidence: 0.87,
            ts: 1.0,
            attestationHash: "deadbeef"
        )
    }
}

// MARK: - LiveViewModel speed slider tests (extending coverage)

@MainActor
final class LiveViewModelSpeedTests: XCTestCase {

    func testSliderToSpeedAt0IsOne() {
        let speed = LiveViewModel.sliderToSpeed(0.0)
        XCTAssertEqual(speed, 1.0, accuracy: 0.01)
    }

    func testSliderToSpeedAt1Is100() {
        let speed = LiveViewModel.sliderToSpeed(1.0)
        XCTAssertEqual(speed, 100.0, accuracy: 0.1)
    }

    func testSliderToSpeedAt0_5IsLogMid() {
        // At 0.5 slider, speed should be 10x (log midpoint of 1–100)
        let speed = LiveViewModel.sliderToSpeed(0.5)
        XCTAssertEqual(speed, 10.0, accuracy: 0.1)
    }

    func testSpeedToSliderRoundTrip() {
        // Verify round-trip: sliderToSpeed(speedToSlider(x)) ≈ x
        let speeds = [1.0, 5.0, 10.0, 50.0, 100.0]
        for s in speeds {
            let t = LiveViewModel.speedToSlider(s)
            let back = LiveViewModel.sliderToSpeed(t)
            XCTAssertEqual(back, s, accuracy: 0.01, "Round-trip failed for speed \(s)")
        }
    }

    func testSpeedToSliderClampsBelow1() {
        let t = LiveViewModel.speedToSlider(0.1)
        XCTAssertEqual(t, 0.0, accuracy: 0.001)
    }

    func testSpeedToSliderClampsAbove100() {
        let t = LiveViewModel.speedToSlider(200.0)
        XCTAssertEqual(t, 1.0, accuracy: 0.001)
    }

    func testSliderClampsNegative() {
        let speed = LiveViewModel.sliderToSpeed(-0.5)
        XCTAssertEqual(speed, 1.0, accuracy: 0.01)
    }

    func testSliderClampsAbove1() {
        let speed = LiveViewModel.sliderToSpeed(1.5)
        XCTAssertEqual(speed, 100.0, accuracy: 0.1)
    }

    // Play/pause state transitions
    func testTogglePlayback() {
        let vm = LiveViewModel()
        XCTAssertFalse(vm.isPaused)
        vm.togglePlayback()
        XCTAssertTrue(vm.isPaused)
        vm.togglePlayback()
        XCTAssertFalse(vm.isPaused)
    }

    // setSpeed updates local state immediately
    func testSetSpeedUpdatesLocalState() {
        let vm = LiveViewModel()
        vm.setSpeed(42.0)
        XCTAssertEqual(vm.speed, 42.0, accuracy: 0.01)
    }
}
