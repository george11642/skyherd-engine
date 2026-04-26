import Foundation
import Observation

@Observable
@MainActor
final class LedgerViewModel {
    // MARK: - State
    var entries: [AttestEntry] = []
    var searchText: String = ""
    var chainVerifyResult: VerifyResult? = nil
    var isVerifyingChain: Bool = false
    var lastSeq: Int = 0
    var isLoadingMore: Bool = false
    var hasMorePages: Bool = true
    var toastMessage: String? = nil

    // Per-entry verify state: hash → result
    var entryVerifyResults: [String: VerifyResult] = [:]
    var entryVerifyingHashes: Set<String> = []

    // Pairing sheet
    var isPairing: Bool = false
    var pairResult: AttestPairResponse? = nil

    // Detail sheet
    var selectedEntryHash: String? = nil

    var filteredEntries: [AttestEntry] {
        guard !searchText.isEmpty else { return entries }
        return entries.filter {
            $0.eventHash.hasPrefix(searchText) ||
            $0.source.localizedCaseInsensitiveContains(searchText) ||
            $0.kind.localizedCaseInsensitiveContains(searchText)
        }
    }

    var chainIntegrityOk: Bool? {
        chainVerifyResult.map { $0.valid }
    }

    var lastEntryTime: String? {
        guard let latest = entries.first else { return nil }
        return relativeTimeStatic(latest.tsIso)
    }

    // MARK: - Event handlers

    func handleInitial(_ newEntries: [AttestEntry]) {
        entries = newEntries
        lastSeq = newEntries.map { $0.seq }.max() ?? 0
    }

    func handle(_ entry: AttestEntry) {
        guard !entries.contains(where: { $0.seq == entry.seq }) else { return }
        entries.insert(entry, at: 0)
        if entry.seq > lastSeq { lastSeq = entry.seq }
    }

    func appendMore(_ newEntries: [AttestEntry]) {
        let existing = Set(entries.map { $0.seq })
        let fresh = newEntries.filter { !existing.contains($0.seq) }
        entries.append(contentsOf: fresh)
        lastSeq = entries.map { $0.seq }.max() ?? lastSeq
        if fresh.isEmpty { hasMorePages = false }
    }

    // MARK: - Verify a single entry

    func verifyEntry(_ hash: String, using client: APIClient) {
        guard !entryVerifyingHashes.contains(hash) else { return }
        entryVerifyingHashes.insert(hash)
        Task {
            do {
                // Use the by-hash endpoint to get chain depth as a verify proxy
                let resp = try await client.attestByHash(hash)
                let result = VerifyResult(valid: !resp.chain.isEmpty, total: resp.chain.count, reason: nil)
                entryVerifyResults[hash] = result
            } catch {
                entryVerifyResults[hash] = VerifyResult(valid: false, total: 0, reason: error.localizedDescription)
            }
            entryVerifyingHashes.remove(hash)
        }
    }

    // MARK: - Verify full chain

    func verifyChain(using client: APIClient) {
        guard !isVerifyingChain else { return }
        isVerifyingChain = true
        Task {
            do {
                let result = try await client.verifyAttestation()
                chainVerifyResult = result
            } catch {
                toastMessage = "Chain verify failed: \(error.localizedDescription)"
            }
            isVerifyingChain = false
        }
    }

    // MARK: - Pair memver

    func pairMemver(using client: APIClient) {
        guard !isPairing else { return }
        isPairing = true
        Task {
            do {
                // Pair with default ID "device-\(UIDevice)" — simplified for demo
                let result = try await client.attestPair("ios-companion")
                pairResult = result
            } catch {
                toastMessage = "Pairing failed: \(error.localizedDescription)"
            }
            isPairing = false
        }
    }

    // MARK: - Clipboard helper

    func verifyCliCommand(for hash: String) -> String {
        "skyherd-verify \(hash)"
    }
}

// MARK: - ISO timestamp to relative string (static, no Date() call dependency)

private func relativeTimeStatic(_ isoString: String) -> String {
    let fmt = ISO8601DateFormatter()
    fmt.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
    guard let date = fmt.date(from: isoString) ?? ISO8601DateFormatter().date(from: isoString) else {
        return isoString
    }
    let delta = Date().timeIntervalSince(date)
    if delta < 60    { return "\(max(0, Int(delta)))s ago" }
    if delta < 3600  { return "\(Int(delta / 60))m ago" }
    if delta < 86400 { return "\(Int(delta / 3600))h ago" }
    return "\(Int(delta / 86400))d ago"
}
