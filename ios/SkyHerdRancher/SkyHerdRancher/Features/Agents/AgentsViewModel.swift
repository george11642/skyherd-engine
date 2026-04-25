import Foundation
import Observation

@Observable
@MainActor
final class AgentsViewModel {
    // MARK: - State
    var agentStatuses: [String: AgentStatus] = [:]      // keyed by name
    var costHistory: [String: [Double]] = [:]            // agent → last 20 cost deltas
    var lastLogs: [String: AgentLogEvent] = [:]          // agent → most recent log
    var agentLogs: [String: [AgentLogEvent]] = [:]       // agent → last 50 log events
    var selectedAgent: String? = nil                     // for detail sheet
    var toastMessage: String? = nil                      // inline error toast

    // Latency tracking: store timestamps per agent to compute p50/p95
    var agentLatencies: [String: [Double]] = [:]         // agent → recent latency samples (ms)

    private let maxCostHistory = 20
    private let maxAgentLogs = 50
    private let maxLatencySamples = 100

    // MARK: - Computed mesh overview stats

    var totalDecisionsToday: Int {
        agentLogs.values.reduce(0) { $0 + $1.count }
    }

    var averageCacheHitRate: Double {
        // Use cost delta as proxy: zero-delta ticks = cache hit (no new tokens billed)
        let rates = agentCacheHitRates.values
        guard !rates.isEmpty else { return 0 }
        return rates.reduce(0, +) / Double(rates.count)
    }

    var agentCacheHitRates: [String: Double] {
        var result: [String: Double] = [:]
        for (name, history) in costHistory {
            guard !history.isEmpty else { continue }
            let hits = history.filter { $0 < 0.000001 }.count
            result[name] = Double(hits) / Double(history.count)
        }
        return result
    }

    var p50LatencyMs: Double {
        let all = agentLatencies.values.flatMap { $0 }.sorted()
        guard !all.isEmpty else { return 0 }
        return all[all.count / 2]
    }

    var p95LatencyMs: Double {
        let all = agentLatencies.values.flatMap { $0 }.sorted()
        guard !all.isEmpty else { return 0 }
        let idx = max(0, Int(Double(all.count) * 0.95) - 1)
        return all[idx]
    }

    // MARK: - Event handlers

    func handleInitial(_ statuses: [AgentStatus]) {
        for status in statuses {
            agentStatuses[status.name] = status
        }
    }

    func handle(_ tick: CostTick) {
        for entry in tick.agents {
            var history = costHistory[entry.name] ?? []
            history.append(entry.costDeltaUsd)
            if history.count > maxCostHistory { history.removeFirst() }
            costHistory[entry.name] = history

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

        var logs = agentLogs[event.agent] ?? []
        logs.insert(event, at: 0)
        if logs.count > maxAgentLogs { logs.removeLast() }
        agentLogs[event.agent] = logs

        // Track latency if available via seq-based ordering
        if let seq = event.seq, seq > 1 {
            // Approximate: use timestamp delta between consecutive events
            if let prev = agentLogs[event.agent]?.dropFirst().first {
                let deltaMs = (event.ts - prev.ts) * 1000
                if deltaMs > 0 && deltaMs < 60_000 {
                    var samples = agentLatencies[event.agent] ?? []
                    samples.append(deltaMs)
                    if samples.count > maxLatencySamples { samples.removeFirst() }
                    agentLatencies[event.agent] = samples
                }
            }
        }
    }

    func handle(_ event: MemoryWrittenEvent) {
        // Memory events indicate agent activity — no UI update needed
    }

    // MARK: - Cache hit sparkline data (last N ticks for a given agent)
    // Returns array of 0/1 booleans (true = hit) for sparkline rendering

    func cacheHitSamples(for agentName: String) -> [Bool] {
        (costHistory[agentName] ?? []).map { $0 < 0.000001 }
    }

    // MARK: - Token display helpers

    func formattedTokens(for agentName: String) -> String {
        guard let status = agentStatuses[agentName] else { return "—" }
        let total = status.cumulativeTokensIn + status.cumulativeTokensOut
        if total >= 1_000_000 { return String(format: "%.1fM", Double(total) / 1_000_000) }
        if total >= 1_000    { return String(format: "%.1fK", Double(total) / 1_000) }
        return "\(total)"
    }
}
