import Foundation

struct AttestResponse: Codable {
    let entries: [AttestEntry]
    let ts: Double
}

struct AttestEntry: Codable, Identifiable {
    var id: Int { seq }
    let seq: Int
    let tsIso: String
    let source: String
    let kind: String
    let payloadJson: String
    let prevHash: String
    let eventHash: String
    let signature: String
    let pubkey: String
    let memverId: String?

    enum CodingKeys: String, CodingKey {
        case seq, source, kind, signature, pubkey
        case tsIso = "ts_iso"
        case payloadJson = "payload_json"
        case prevHash = "prev_hash"
        case eventHash = "event_hash"
        case memverId = "memver_id"
    }
}

struct VerifyResult: Codable {
    let valid: Bool
    let total: Int
    let reason: String?
}

struct AttestByHashResponse: Codable {
    let target: String
    let chain: [AttestEntry]
    let ts: Double
}

struct AttestPairResponse: Codable {
    let memverId: String
    let ledgerEntry: AttestEntry
    let memver: MemverInfo
    let ts: Double

    enum CodingKeys: String, CodingKey {
        case memverId = "memver_id"
        case ledgerEntry = "ledger_entry"
        case memver, ts
    }
}

struct MemverInfo: Codable {
    let id: String
    let agent: String?
    let contentSha256: String?
    let path: String?

    enum CodingKeys: String, CodingKey {
        case id, agent, path
        case contentSha256 = "content_sha256"
    }
}
