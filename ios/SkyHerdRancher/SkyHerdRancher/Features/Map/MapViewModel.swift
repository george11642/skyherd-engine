import Foundation
import Observation

@Observable
@MainActor
final class MapViewModel {

    // MARK: - State

    var snapshot: WorldSnapshot? = nil
    var activeScenario: String? = nil
    var breachPins: [NeighborAlertEvent] = []

    // Layer visibility toggles
    var showPaddocks: Bool = true
    var showFences: Bool = true
    var showCows: Bool = true
    var showDrone: Bool = true
    var showPredators: Bool = true
    var showTanks: Bool = true

    // Periodic refresh
    private var apiClient: APIClient?
    private var refreshTask: Task<Void, Never>?

    // MARK: - Init

    init(apiClient: APIClient? = nil) {
        self.apiClient = apiClient
    }

    // MARK: - Lifecycle

    func onAppear() {
        startPeriodicRefresh()
    }

    func onDisappear() {
        refreshTask?.cancel()
        refreshTask = nil
    }

    private func startPeriodicRefresh() {
        refreshTask?.cancel()
        refreshTask = Task {
            while !Task.isCancelled {
                await fetchSnapshot()
                try? await Task.sleep(nanoseconds: 1_000_000_000) // 1s
            }
        }
    }

    private func fetchSnapshot() async {
        guard let apiClient else { return }
        if let s = try? await apiClient.snapshot() {
            snapshot = s
        }
    }

    // MARK: - Event handlers (called by AppState.route)

    func handle(_ s: WorldSnapshot) {
        snapshot = s
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

// MARK: - SelectedEntity union

enum SelectedEntity: Identifiable {
    case cow(Cow)
    case drone(Drone)
    case predator(Predator)
    case tank(WaterTank)

    var id: String {
        switch self {
        case .cow(let c):      return "cow-\(c.id)"
        case .drone:           return "drone"
        case .predator(let p): return "predator-\(p.id)"
        case .tank(let t):     return "tank-\(t.id)"
        }
    }

    var title: String {
        switch self {
        case .cow(let c):      return "Cow \(c.tag ?? c.id)"
        case .drone:           return "Drone"
        case .predator(let p): return "Predator \(p.id)"
        case .tank(let t):     return "Tank \(t.id)"
        }
    }

    var statusLines: [String] {
        switch self {
        case .cow(let c):
            var lines = [String]()
            if let state = c.state { lines.append("State: \(state)") }
            if let bcs = c.bcs { lines.append(String(format: "BCS: %.1f / 9", bcs)) }
            lines.append(String(format: "Pos: (%.2f, %.2f)", c.pos.first ?? 0, c.pos.last ?? 0))
            return lines
        case .drone(let d):
            var lines = [String]()
            if let state = d.state { lines.append("State: \(state)") }
            if let bat = d.batteryPct { lines.append(String(format: "Battery: %.0f%%", bat)) }
            if let alt = d.altM { lines.append(String(format: "Alt: %.1f m", alt)) }
            return lines
        case .predator(let p):
            var lines = [String]()
            if let sp = p.species { lines.append("Species: \(sp)") }
            if let tl = p.threatLevel { lines.append("Threat: \(tl)") }
            lines.append(String(format: "Pos: (%.2f, %.2f)", p.pos.first ?? 0, p.pos.last ?? 0))
            return lines
        case .tank(let t):
            return [
                String(format: "Level: %.0f%%", t.levelPct * 100),
                String(format: "Pos: (%.2f, %.2f)", t.pos.first ?? 0, t.pos.last ?? 0),
            ]
        }
    }
}
