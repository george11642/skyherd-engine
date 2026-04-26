import Foundation

struct VetIntakeDraftedEvent: Codable {
    let id: String            // e.g. "A014_20260422T153200Z"
    let cowTag: String
    let severity: String      // "escalate"
    let path: String
    let ts: Double

    enum CodingKeys: String, CodingKey {
        case id, severity, path, ts
        case cowTag = "cow_tag"
    }
}

struct NeighborAlertEvent: Codable {
    let fromRanch: String
    let toRanch: String
    let species: String
    let sharedFence: String
    let confidence: Double
    let ts: Double
    let attestationHash: String

    enum CodingKeys: String, CodingKey {
        case species, confidence, ts
        case fromRanch = "from_ranch"
        case toRanch = "to_ranch"
        case sharedFence = "shared_fence"
        case attestationHash = "attestation_hash"
    }
}

struct NeighborHandoffEvent: Codable {
    let fromRanch: String
    let toRanch: String
    let species: String
    let sharedFence: String
    let responseMode: String
    let toolCalls: [String]
    let rancherPaged: Bool
    let ts: Double

    enum CodingKeys: String, CodingKey {
        case species, ts
        case fromRanch = "from_ranch"
        case toRanch = "to_ranch"
        case sharedFence = "shared_fence"
        case responseMode = "response_mode"
        case toolCalls = "tool_calls"
        case rancherPaged = "rancher_paged"
    }
}

struct NeighborsResponse: Codable {
    let entries: [NeighborEntry]
    let ts: Double
}

struct NeighborEntry: Codable {
    let direction: String     // "inbound" | "outbound"
    let fromRanch: String
    let toRanch: String
    let species: String
    let sharedFence: String
    let confidence: Double
    let ts: Double
    let attestationHash: String

    enum CodingKeys: String, CodingKey {
        case direction, species, confidence, ts
        case fromRanch = "from_ranch"
        case toRanch = "to_ranch"
        case sharedFence = "shared_fence"
        case attestationHash = "attestation_hash"
    }
}

// Union type for the Alerts tab
enum SkyHerdAlert: Identifiable {
    case vetIntake(VetIntakeDraftedEvent)
    case neighborAlert(NeighborAlertEvent)
    case neighborHandoff(NeighborHandoffEvent)

    var id: String {
        switch self {
        case .vetIntake(let e):       return "vi-\(e.id)"
        case .neighborAlert(let e):   return "na-\(e.fromRanch)-\(e.toRanch)-\(e.ts)"
        case .neighborHandoff(let e): return "nh-\(e.fromRanch)-\(e.toRanch)-\(e.ts)"
        }
    }

    var ts: Double {
        switch self {
        case .vetIntake(let e):       return e.ts
        case .neighborAlert(let e):   return e.ts
        case .neighborHandoff(let e): return e.ts
        }
    }
}
