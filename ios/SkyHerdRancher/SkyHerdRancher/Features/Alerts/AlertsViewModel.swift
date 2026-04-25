import Foundation
import Observation

@Observable
@MainActor
final class AlertsViewModel {
    var alerts: [SkyHerdAlert] = []
    var acknowledgedIds: Set<String> = []

    var unreadCount: Int {
        alerts.filter { !acknowledgedIds.contains($0.id) }.count
    }

    // MARK: - Event handlers

    func handle(_ event: VetIntakeDraftedEvent) {
        let alert = SkyHerdAlert.vetIntake(event)
        // Avoid duplicate inserts
        guard !alerts.contains(where: { $0.id == alert.id }) else { return }
        alerts.insert(alert, at: 0)
    }

    func handle(_ event: NeighborAlertEvent) {
        let alert = SkyHerdAlert.neighborAlert(event)
        guard !alerts.contains(where: { $0.id == alert.id }) else { return }
        alerts.insert(alert, at: 0)
    }

    func handle(_ event: NeighborHandoffEvent) {
        let alert = SkyHerdAlert.neighborHandoff(event)
        guard !alerts.contains(where: { $0.id == alert.id }) else { return }
        alerts.insert(alert, at: 0)
    }

    func acknowledge(_ id: String) {
        acknowledgedIds.insert(id)
    }
}
