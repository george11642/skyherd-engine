import Foundation
import Observation

@Observable
@MainActor
final class AgentsViewModel {
    var agentStatuses: [String: AgentStatus] = [:]   // keyed by name
    var costHistory: [String: [Double]] = [:]          // agent → last 20 cost deltas
    var lastLogs: [String: AgentLogEvent] = [:]        // agent → most recent log
    var selectedAgent: String? = nil                   // for detail sheet

    private let maxCostHistory = 20

    // MARK: - Event handlers (Wave C will implement card UI)

    func handleInitial(_ statuses: [AgentStatus]) {
        for status in statuses {
            agentStatuses[status.name] = status
        }
    }

    func handle(_ tick: CostTick) {
        for entry in tick.agents {
            // Update cost history
            var history = costHistory[entry.name] ?? []
            history.append(entry.costDeltaUsd)
            if history.count > maxCostHistory { history.removeFirst() }
            costHistory[entry.name] = history

            // Build a synthetic AgentStatus from the cost entry
            let current = agentStatuses[entry.name]
            agentStatuses[entry.name] = AgentStatus(
                name: entry.name,
                sessionId: current?.sessionId ?? "sess_mock_\(entry.name.lowercased())",
                state: entry.state,
                lastWake: current?.lastWake,
                cumulativeTokensIn: entry.tokensIn,
                cumulativeTokensOut: entry.tokensOut,
                cumulativeCostUsd: entry.cumulativeCostUsd
            )
        }
    }

    func handle(_ event: AgentLogEvent) {
        lastLogs[event.agent] = event
    }

    func handle(_ event: MemoryWrittenEvent) {
        // Memory events indicate agent activity — no state change needed at Wave A
    }
}
