import Foundation

struct ScenarioActiveEvent: Codable {
    let name: String          // "coyote"|"sick_cow"|"water_drop"|"calving"|"storm"|
                              // "wildfire"|"rustling"|"cross_ranch_coyote"
    let passIdx: Int
    let speed: Double
    let startedAt: String     // ISO 8601

    enum CodingKeys: String, CodingKey {
        case name, speed
        case passIdx = "pass_idx"
        case startedAt = "started_at"
    }
}

struct ScenarioEndedEvent: Codable {
    let name: String
    let passIdx: Int
    let outcome: String       // "ok" | "cancelled" | error string
    let startedAt: String
    let endedAt: String

    enum CodingKeys: String, CodingKey {
        case name, outcome
        case passIdx = "pass_idx"
        case startedAt = "started_at"
        case endedAt = "ended_at"
    }
}

struct ScenariosResponse: Codable {
    let scenarios: [String]
}

struct StatusResponse: Codable {
    let activeScenario: String?
    let speed: Double
    let mock: Bool

    enum CodingKeys: String, CodingKey {
        case speed, mock
        case activeScenario = "active_scenario"
    }
}

struct HealthResponse: Codable {
    let status: String
    let ts: String
}

struct SpeedResponse: Codable {
    let speed: Double
}

struct SkipResponse: Codable {
    let skipped: String?
}
