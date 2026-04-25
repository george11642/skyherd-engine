import Foundation
import Observation

// MARK: - Alert severity

enum AlertSeverity: String, CaseIterable {
    case critical, high, medium, low

    var label: String { rawValue.capitalized }

    var color: String {
        switch self {
        case .critical: return "danger"
        case .high:     return "thermal"
        case .medium:   return "warn"
        case .low:      return "sky"
        }
    }
}

extension SkyHerdAlert {
    var severity: AlertSeverity {
        switch self {
        case .vetIntake(let e):
            return e.severity == "escalate" ? .critical : .high
        case .neighborAlert(let e):
            return e.confidence >= 0.8 ? .high : .medium
        case .neighborHandoff(let e):
            return e.rancherPaged ? .high : .medium
        }
    }

    var title: String {
        switch self {
        case .vetIntake(let e):
            return "Sick cow — \(e.cowTag)"
        case .neighborAlert(let e):
            return "\(e.species.capitalized) near \(e.sharedFence)"
        case .neighborHandoff(let e):
            return "Handoff: \(e.species.capitalized) from \(e.fromRanch)"
        }
    }

    var sourceAgent: String {
        switch self {
        case .vetIntake:       return "HerdHealthWatcher"
        case .neighborAlert:   return "FenceLineDispatcher"
        case .neighborHandoff: return "FenceLineDispatcher"
        }
    }

    var contextLine: String {
        switch self {
        case .vetIntake(let e):
            return "Tag \(e.cowTag) · severity \(e.severity)"
        case .neighborAlert(let e):
            return "\(e.fromRanch) → \(e.toRanch) · \(Int(e.confidence * 100))% confidence"
        case .neighborHandoff(let e):
            return "\(e.fromRanch) → \(e.toRanch) · \(e.responseMode)"
        }
    }

    var attestHash: String? {
        switch self {
        case .neighborAlert(let e): return e.attestationHash
        default: return nil
        }
    }
}

// MARK: - Snooze state

struct AlertSnooze {
    let until: Date
}

@Observable
@MainActor
final class AlertsViewModel {
    // MARK: - State
    var alerts: [SkyHerdAlert] = []
    var acknowledgedIds: Set<String> = []
    var snoozedAlerts: [String: AlertSnooze] = [:]
    var severityFilter: AlertSeverity? = nil       // nil = show all
    var selectedAlertId: String? = nil             // for detail sheet
    var toastMessage: String? = nil

    var unreadCount: Int {
        activeAlerts.filter { !acknowledgedIds.contains($0.id) }.count
    }

    var activeAlerts: [SkyHerdAlert] {
        let now = Date()
        return alerts.filter { alert in
            // Filter out snoozed
            if let snooze = snoozedAlerts[alert.id], snooze.until > now {
                return false
            }
            // Apply severity filter
            if let filter = severityFilter, alert.severity != filter {
                return false
            }
            return true
        }
    }

    // MARK: - Event handlers

    func handle(_ event: VetIntakeDraftedEvent) {
        let alert = SkyHerdAlert.vetIntake(event)
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

    // MARK: - Actions

    func acknowledge(_ id: String) {
        acknowledgedIds.insert(id)
    }

    func snooze(_ id: String, hours: Double = 1.0) {
        snoozedAlerts[id] = AlertSnooze(until: Date().addingTimeInterval(hours * 3600))
    }

    func escalate(_ id: String) {
        // In production this would POST to /api/rancher/page
        // For demo: mark acknowledged + show toast
        acknowledgedIds.insert(id)
        toastMessage = "Wes paged — expect a call shortly"
    }
}
