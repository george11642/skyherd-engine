import Foundation
import Observation

@Observable
@MainActor
final class LiveViewModel {
    var activeScenario: String? = nil
    var speed: Double = 15.0
    var isPaused: Bool = false
    var recentEvents: [AgentLogEvent] = []   // capped at 50
    var costRate: Double = 0.0
    var allIdle: Bool = true

    private let maxEvents = 50

    // MARK: - Event handlers (Wave B will flesh these out)

    func handle(_ event: AgentLogEvent) {
        recentEvents.insert(event, at: 0)
        if recentEvents.count > maxEvents {
            recentEvents.removeLast()
        }
    }

    func handle(_ tick: CostTick) {
        costRate = tick.ratePerHrUsd
        allIdle = tick.allIdle
    }

    func handle(_ event: ScenarioActiveEvent) {
        activeScenario = event.name
        speed = event.speed
    }

    func handle(_ event: ScenarioEndedEvent) {
        activeScenario = nil
    }
}
