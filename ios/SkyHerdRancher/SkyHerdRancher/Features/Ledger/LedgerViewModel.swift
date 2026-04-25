import Foundation
import Observation

@Observable
@MainActor
final class LedgerViewModel {
    var entries: [AttestEntry] = []
    var searchText: String = ""
    var verifyResult: VerifyResult? = nil
    var isVerifying: Bool = false
    var lastSeq: Int = 0
    var isLoadingMore: Bool = false

    var filteredEntries: [AttestEntry] {
        guard !searchText.isEmpty else { return entries }
        return entries.filter {
            $0.eventHash.hasPrefix(searchText) ||
            $0.source.localizedCaseInsensitiveContains(searchText)
        }
    }

    // MARK: - Event handlers

    func handleInitial(_ newEntries: [AttestEntry]) {
        entries = newEntries
        lastSeq = newEntries.map { $0.seq }.max() ?? 0
    }

    func handle(_ entry: AttestEntry) {
        // Avoid duplicates — check by seq
        guard !entries.contains(where: { $0.seq == entry.seq }) else { return }
        entries.insert(entry, at: 0)
        if entry.seq > lastSeq { lastSeq = entry.seq }
    }

    func appendMore(_ newEntries: [AttestEntry]) {
        let existing = Set(entries.map { $0.seq })
        let fresh = newEntries.filter { !existing.contains($0.seq) }
        entries.append(contentsOf: fresh)
        lastSeq = entries.map { $0.seq }.max() ?? lastSeq
    }
}
