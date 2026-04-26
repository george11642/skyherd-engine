import Foundation

struct AgentsResponse: Codable {
    let agents: [AgentStatus]
    let ts: Double
}

struct AgentStatus: Codable {
    let name: String
    let sessionId: String     // "sess_mock_*" or real sess_* id
    let state: String         // "active" | "idle"
    let lastWake: Double?
    let cumulativeTokensIn: Int
    let cumulativeTokensOut: Int
    let cumulativeCostUsd: Double

    enum CodingKeys: String, CodingKey {
        case name, state
        case sessionId = "session_id"
        case lastWake = "last_wake"
        case cumulativeTokensIn = "cumulative_tokens_in"
        case cumulativeTokensOut = "cumulative_tokens_out"
        case cumulativeCostUsd = "cumulative_cost_usd"
    }
}

struct CostTick: Codable {
    let ts: Double
    let seq: Int
    let agents: [AgentCostEntry]
    let allIdle: Bool
    let ratePerHrUsd: Double
    let totalCumulativeUsd: Double

    enum CodingKeys: String, CodingKey {
        case ts, seq, agents
        case allIdle = "all_idle"
        case ratePerHrUsd = "rate_per_hr_usd"
        case totalCumulativeUsd = "total_cumulative_usd"
    }
}

struct AgentCostEntry: Codable {
    let name: String
    let state: String         // "active" | "idle"
    let costDeltaUsd: Double
    let cumulativeCostUsd: Double
    let tokensIn: Int
    let tokensOut: Int

    enum CodingKeys: String, CodingKey {
        case name, state
        case costDeltaUsd = "cost_delta_usd"
        case cumulativeCostUsd = "cumulative_cost_usd"
        case tokensIn = "tokens_in"
        case tokensOut = "tokens_out"
    }
}

struct AgentLogEvent: Codable {
    let ts: Double
    let agent: String
    let state: String?
    let message: String?
    let level: String?
    let tool: String?
    let line: String?
    let seq: Int?
}
