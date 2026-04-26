import Foundation

enum SkyHerdEvent {
    case worldSnapshot(WorldSnapshot)
    case costTick(CostTick)
    case attestAppend(AttestEntry)
    case agentLog(AgentLogEvent)
    case vetIntakeDrafted(VetIntakeDraftedEvent)
    case scenarioActive(ScenarioActiveEvent)
    case scenarioEnded(ScenarioEndedEvent)
    case memoryWritten(MemoryWrittenEvent)
    case memoryRead(MemoryWrittenEvent)
    case neighborAlert(NeighborAlertEvent)
    case neighborHandoff(NeighborHandoffEvent)
    case unknown(type: String, data: String)
}

// MARK: - SSE Frame parsing

/// An intermediate SSE frame before decoding into a typed SkyHerdEvent.
struct SSEFrame {
    var eventType: String = "message"
    var data: String = ""
}

// MARK: - Decoding

extension SkyHerdEvent {
    static func decode(frame: SSEFrame, decoder: JSONDecoder) -> SkyHerdEvent? {
        let raw = frame.data
        guard !raw.isEmpty else { return nil }
        let data = Data(raw.utf8)

        switch frame.eventType {
        case "world.snapshot":
            return (try? decoder.decode(WorldSnapshot.self, from: data)).map { .worldSnapshot($0) }
        case "cost.tick":
            return (try? decoder.decode(CostTick.self, from: data)).map { .costTick($0) }
        case "attest.append":
            return (try? decoder.decode(AttestEntry.self, from: data)).map { .attestAppend($0) }
        case "agent.log":
            return (try? decoder.decode(AgentLogEvent.self, from: data)).map { .agentLog($0) }
        case "vet_intake.drafted":
            return (try? decoder.decode(VetIntakeDraftedEvent.self, from: data)).map { .vetIntakeDrafted($0) }
        case "scenario.active":
            return (try? decoder.decode(ScenarioActiveEvent.self, from: data)).map { .scenarioActive($0) }
        case "scenario.ended":
            return (try? decoder.decode(ScenarioEndedEvent.self, from: data)).map { .scenarioEnded($0) }
        case "memory.written":
            return (try? decoder.decode(MemoryWrittenEvent.self, from: data)).map { .memoryWritten($0) }
        case "memory.read":
            return (try? decoder.decode(MemoryWrittenEvent.self, from: data)).map { .memoryRead($0) }
        case "neighbor.alert":
            return (try? decoder.decode(NeighborAlertEvent.self, from: data)).map { .neighborAlert($0) }
        case "neighbor.handoff":
            return (try? decoder.decode(NeighborHandoffEvent.self, from: data)).map { .neighborHandoff($0) }
        default:
            return .unknown(type: frame.eventType, data: raw)
        }
    }
}
