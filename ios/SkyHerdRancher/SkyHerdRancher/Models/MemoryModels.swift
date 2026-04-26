import Foundation

struct MemoryResponse: Codable {
    let agent: String
    let memoryStoreId: String?
    let entries: [MemoryEntry]
    let prefixes: [String]?
    let ts: Double

    enum CodingKeys: String, CodingKey {
        case agent, entries, prefixes, ts
        case memoryStoreId = "memory_store_id"
    }
}

struct MemoryEntry: Codable, Identifiable {
    var id: String { memoryId }
    let memoryId: String
    let memoryVersionId: String
    let memoryStoreId: String
    let path: String
    let contentSha256: String
    let contentSizeBytes: Int?
    let createdAt: String
    let operation: String?

    enum CodingKeys: String, CodingKey {
        case path, operation
        case memoryId = "memory_id"
        case memoryVersionId = "memory_version_id"
        case memoryStoreId = "memory_store_id"
        case contentSha256 = "content_sha256"
        case contentSizeBytes = "content_size_bytes"
        case createdAt = "created_at"
    }
}

struct MemoryWrittenEvent: Codable {
    let agent: String
    let memoryStoreId: String
    let memoryId: String
    let memoryVersionId: String
    let contentSha256: String
    let path: String

    enum CodingKeys: String, CodingKey {
        case agent, path
        case memoryStoreId = "memory_store_id"
        case memoryId = "memory_id"
        case memoryVersionId = "memory_version_id"
        case contentSha256 = "content_sha256"
    }
}
