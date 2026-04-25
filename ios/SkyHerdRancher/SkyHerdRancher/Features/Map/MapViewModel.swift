import Foundation
import Observation

@Observable
@MainActor
final class MapViewModel {
    var snapshot: WorldSnapshot? = nil
    var activeScenario: String? = nil
    var breachPins: [NeighborAlertEvent] = []   // cleared on scenario.ended

    // MARK: - Event handlers (Wave B will implement Canvas drawing)

    func handle(_ snapshot: WorldSnapshot) {
        self.snapshot = snapshot
    }

    func handle(_ event: ScenarioActiveEvent) {
        activeScenario = event.name
    }

    func handle(_ event: ScenarioEndedEvent) {
        activeScenario = nil
        breachPins.removeAll()
    }

    func handle(_ event: NeighborAlertEvent) {
        breachPins.append(event)
    }
}
