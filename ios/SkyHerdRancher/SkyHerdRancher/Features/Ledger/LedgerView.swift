import SwiftUI

// MARK: - LedgerView

struct LedgerView: View {
    @Environment(AppState.self) private var appState

    var body: some View {
        @Bindable var vm = appState.ledgerVM
        NavigationStack {
            ZStack(alignment: .bottom) {
                VStack(spacing: 0) {
                    // Stats row
                    LedgerStatsRow(
                        totalEntries: appState.ledgerVM.entries.count,
                        lastEntryTime: appState.ledgerVM.lastEntryTime,
                        chainStatus: appState.ledgerVM.chainIntegrityOk
                    )
                    .padding(.horizontal, SkyHerdSpacing.md)
                    .padding(.vertical, SkyHerdSpacing.sm)
                    .background(Color.skhBg1)

                    Divider().background(Color.skhLine)

                    if appState.ledgerVM.entries.isEmpty && appState.ledgerVM.isLoadingMore {
                        // Initial load skeleton
                        HStack {
                            Spacer()
                            ProgressView("Loading ledger…")
                                .tint(Color.skhText2)
                                .foregroundStyle(Color.skhText2)
                                .padding(.top, 60)
                            Spacer()
                        }
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                        .background(Color.skhBg0)
                    } else if appState.ledgerVM.filteredEntries.isEmpty {
                        // Empty state
                        VStack(spacing: SkyHerdSpacing.md) {
                            Spacer()
                            Image(systemName: "lock.shield")
                                .font(.system(size: 48))
                                .foregroundStyle(Color.skhText2)
                            Text("No ledger entries yet.")
                                .font(SkyHerdTypography.heading)
                                .foregroundStyle(Color.skhText2)
                            Text("Attestation events appear here as the sim runs.")
                                .font(SkyHerdTypography.caption)
                                .foregroundStyle(Color.skhText2)
                                .multilineTextAlignment(.center)
                            Spacer()
                        }
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                        .background(Color.skhBg0)
                    } else {

                    List {
                        ForEach(appState.ledgerVM.filteredEntries) { entry in
                            LedgerEntryRow(
                                entry: entry,
                                verifyResult: appState.ledgerVM.entryVerifyResults[entry.eventHash],
                                isVerifying: appState.ledgerVM.entryVerifyingHashes.contains(entry.eventHash)
                            )
                            .contentShape(Rectangle())
                            .onTapGesture {
                                appState.ledgerVM.selectedEntryHash = entry.eventHash
                            }
                            .listRowBackground(Color.skhBg1)
                            .listRowInsets(EdgeInsets(
                                top: SkyHerdSpacing.xs,
                                leading: SkyHerdSpacing.md,
                                bottom: SkyHerdSpacing.xs,
                                trailing: SkyHerdSpacing.md
                            ))
                            .onAppear {
                                // Lazy-load more when near end
                                if entry.seq == appState.ledgerVM.filteredEntries.last?.seq {
                                    loadMoreIfNeeded()
                                }
                            }
                        }

                        if appState.ledgerVM.isLoadingMore {
                            HStack {
                                Spacer()
                                ProgressView()
                                    .tint(Color.skhText2)
                                Spacer()
                            }
                            .listRowBackground(Color.clear)
                        }
                    }
                    .listStyle(.plain)
                    .scrollContentBackground(.hidden)
                    .background(Color.skhBg0)
                    .searchable(
                        text: $vm.searchText,
                        placement: .navigationBarDrawer(displayMode: .automatic),
                        prompt: "Hash prefix or agent name"
                    )
                    .refreshable {
                        await refreshLedger()
                    }
                    } // end else (has entries)
                }
                .background(Color.skhBg0)
                .navigationTitle("Ledger")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .navigationBarLeading) {
                        ConnectionBadge(state: appState.connectionState)
                    }
                    ToolbarItem(placement: .navigationBarTrailing) {
                        Button {
                            appState.ledgerVM.pairMemver(using: appState.apiClient)
                        } label: {
                            Label("Pair", systemImage: "link.badge.plus")
                                .font(SkyHerdTypography.caption)
                        }
                        .tint(Color.skhSky)
                        .disabled(appState.ledgerVM.isPairing)
                    }
                }

                // Toast
                if let msg = appState.ledgerVM.toastMessage {
                    ToastView(message: msg)
                        .padding(.bottom, SkyHerdSpacing.lg)
                        .transition(.move(edge: .bottom).combined(with: .opacity))
                        .onAppear {
                            Task {
                                try? await Task.sleep(nanoseconds: 3_000_000_000)
                                appState.ledgerVM.toastMessage = nil
                            }
                        }
                }
            }
            .animation(.easeInOut(duration: 0.3), value: appState.ledgerVM.toastMessage)
            // Pairing result sheet
            .sheet(item: Binding(
                get: { appState.ledgerVM.pairResult },
                set: { appState.ledgerVM.pairResult = $0 }
            )) { result in
                PairResultSheet(result: result)
                    .presentationDetents([.medium])
                    .presentationDragIndicator(.visible)
            }
            // Entry detail sheet
            .sheet(item: Binding(
                get: {
                    appState.ledgerVM.selectedEntryHash.flatMap { hash in
                        appState.ledgerVM.entries.first { $0.eventHash == hash }
                    }.map { LedgerEntryWrapper(entry: $0) }
                },
                set: { appState.ledgerVM.selectedEntryHash = $0?.entry.eventHash }
            )) { wrapper in
                LedgerEntryDetailSheet(
                    entry: wrapper.entry,
                    verifyResult: appState.ledgerVM.entryVerifyResults[wrapper.entry.eventHash],
                    isVerifying: appState.ledgerVM.entryVerifyingHashes.contains(wrapper.entry.eventHash),
                    onVerify: {
                        appState.ledgerVM.verifyEntry(wrapper.entry.eventHash, using: appState.apiClient)
                    },
                    onNavigateToHash: { prevHash in
                        appState.ledgerVM.selectedEntryHash = prevHash
                    },
                    cliCommand: appState.ledgerVM.verifyCliCommand(for: wrapper.entry.eventHash)
                )
                .presentationDetents([.medium, .large])
                .presentationDragIndicator(.visible)
            }
        }
    }

    private func loadMoreIfNeeded() {
        guard !appState.ledgerVM.isLoadingMore,
              appState.ledgerVM.hasMorePages else { return }
        appState.ledgerVM.isLoadingMore = true
        Task {
            let nextSeq = appState.ledgerVM.lastSeq + 1
            if let resp = try? await appState.apiClient.attestations(sinceSeq: nextSeq) {
                await MainActor.run {
                    appState.ledgerVM.appendMore(resp.entries)
                    appState.ledgerVM.isLoadingMore = false
                }
            } else {
                await MainActor.run {
                    appState.ledgerVM.isLoadingMore = false
                }
            }
        }
    }

    @MainActor
    private func refreshLedger() async {
        guard let resp = try? await appState.apiClient.attestations(sinceSeq: 0) else {
            appState.ledgerVM.toastMessage = "Failed to refresh ledger"
            return
        }
        appState.ledgerVM.handleInitial(resp.entries)
        appState.ledgerVM.hasMorePages = true
        // Also re-verify chain
        appState.ledgerVM.verifyChain(using: appState.apiClient)
    }
}

// MARK: - Wrappers for sheet bindings

private struct LedgerEntryWrapper: Identifiable {
    let entry: AttestEntry
    var id: String { entry.eventHash }
}

// MARK: - LedgerStatsRow

private struct LedgerStatsRow: View {
    let totalEntries: Int
    let lastEntryTime: String?
    let chainStatus: Bool?

    var body: some View {
        HStack(spacing: 0) {
            VStack(spacing: 2) {
                Text("\(totalEntries)")
                    .font(SkyHerdTypography.heading)
                    .foregroundStyle(Color.skhText0)
                Text("Entries")
                    .font(SkyHerdTypography.caption2)
                    .foregroundStyle(Color.skhText2)
            }
            .frame(maxWidth: .infinity)

            Divider().frame(height: 32)

            VStack(spacing: 2) {
                Text(lastEntryTime ?? "—")
                    .font(SkyHerdTypography.heading)
                    .foregroundStyle(Color.skhText0)
                Text("Last Entry")
                    .font(SkyHerdTypography.caption2)
                    .foregroundStyle(Color.skhText2)
            }
            .frame(maxWidth: .infinity)

            Divider().frame(height: 32)

            VStack(spacing: 2) {
                HStack(spacing: 4) {
                    if let ok = chainStatus {
                        Image(systemName: ok ? "checkmark.shield.fill" : "exclamationmark.shield.fill")
                            .foregroundStyle(ok ? Color.skhOk : Color.skhDanger)
                            .font(.system(size: 14))
                        Text(ok ? "Verified" : "Broken")
                            .font(SkyHerdTypography.heading)
                            .foregroundStyle(ok ? Color.skhOk : Color.skhDanger)
                    } else {
                        Text("—")
                            .font(SkyHerdTypography.heading)
                            .foregroundStyle(Color.skhText2)
                    }
                }
                Text("Chain")
                    .font(SkyHerdTypography.caption2)
                    .foregroundStyle(Color.skhText2)
            }
            .frame(maxWidth: .infinity)
        }
    }
}

// MARK: - LedgerEntryRow

private struct LedgerEntryRow: View {
    let entry: AttestEntry
    let verifyResult: VerifyResult?
    let isVerifying: Bool

    var body: some View {
        HStack(spacing: SkyHerdSpacing.sm) {
            // Hash chip
            Text(String(entry.eventHash.prefix(12)))
                .font(SkyHerdTypography.mono)
                .foregroundStyle(Color.skhSky)
                .padding(.horizontal, 6)
                .padding(.vertical, 3)
                .background(Color.skhSky.opacity(0.1), in: RoundedRectangle(cornerRadius: 4))

            // Agent + kind
            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 4) {
                    Image(systemName: agentIcon(entry.source))
                        .font(.system(size: 10))
                        .foregroundStyle(agentAccentColor(entry.source))
                    Text(agentDisplayName(entry.source))
                        .font(SkyHerdTypography.caption)
                        .foregroundStyle(Color.skhText1)
                }
                Text(entry.kind)
                    .font(SkyHerdTypography.caption2)
                    .foregroundStyle(Color.skhText2)
                    .lineLimit(1)
            }

            Spacer()

            // Verify badge + timestamp
            VStack(alignment: .trailing, spacing: 2) {
                if isVerifying {
                    ProgressView()
                        .scaleEffect(0.6)
                        .tint(Color.skhText2)
                } else if let result = verifyResult {
                    Image(systemName: result.valid ? "checkmark.circle.fill" : "exclamationmark.triangle.fill")
                        .foregroundStyle(result.valid ? Color.skhOk : Color.skhWarn)
                        .font(.system(size: 14))
                } else {
                    Image(systemName: "circle.dotted")
                        .foregroundStyle(Color.skhText2)
                        .font(.system(size: 12))
                }

                Text(isoToRelative(entry.tsIso))
                    .font(SkyHerdTypography.caption2)
                    .foregroundStyle(Color.skhText2)
            }
        }
        .padding(.vertical, SkyHerdSpacing.xs)
    }
}

// MARK: - LedgerEntryDetailSheet

private struct LedgerEntryDetailSheet: View {
    let entry: AttestEntry
    let verifyResult: VerifyResult?
    let isVerifying: Bool
    let onVerify: () -> Void
    let onNavigateToHash: (String) -> Void
    let cliCommand: String

    @State private var copied = false

    var body: some View {
        NavigationStack {
            ZStack {
                Color.skhBg0.ignoresSafeArea()
                ScrollView {
                    VStack(alignment: .leading, spacing: SkyHerdSpacing.md) {

                        // Full hash (selectable)
                        LedgerDetailSection(title: "Event Hash") {
                            Text(entry.eventHash)
                                .font(SkyHerdTypography.mono)
                                .foregroundStyle(Color.skhSky)
                                .textSelection(.enabled)
                        }

                        // Agent + kind + time
                        LedgerDetailSection(title: "Source") {
                            HStack(spacing: SkyHerdSpacing.sm) {
                                Image(systemName: agentIcon(entry.source))
                                    .foregroundStyle(agentAccentColor(entry.source))
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(entry.source)
                                        .font(SkyHerdTypography.body)
                                        .foregroundStyle(Color.skhText0)
                                    Text(entry.kind)
                                        .font(SkyHerdTypography.caption)
                                        .foregroundStyle(Color.skhText2)
                                    Text(entry.tsIso)
                                        .font(SkyHerdTypography.caption2)
                                        .foregroundStyle(Color.skhText2)
                                }
                            }
                        }

                        // Previous hash link
                        if entry.prevHash != "0000" && !entry.prevHash.isEmpty {
                            LedgerDetailSection(title: "Previous Hash") {
                                Button {
                                    onNavigateToHash(entry.prevHash)
                                } label: {
                                    HStack {
                                        Text(String(entry.prevHash.prefix(16)) + "…")
                                            .font(SkyHerdTypography.mono)
                                            .foregroundStyle(Color.skhSky)
                                        Spacer()
                                        Image(systemName: "arrow.right.circle")
                                            .foregroundStyle(Color.skhSky)
                                    }
                                }
                                .buttonStyle(.plain)
                            }
                        }

                        // Payload JSON
                        LedgerDetailSection(title: "Payload") {
                            ScrollView(.horizontal, showsIndicators: false) {
                                Text(prettyJSON(entry.payloadJson))
                                    .font(SkyHerdTypography.monoSm)
                                    .foregroundStyle(Color.skhText1)
                                    .textSelection(.enabled)
                            }
                        }

                        // Verify section
                        LedgerDetailSection(title: "Verification") {
                            VStack(alignment: .leading, spacing: SkyHerdSpacing.sm) {
                                if isVerifying {
                                    HStack {
                                        ProgressView()
                                            .tint(Color.skhText2)
                                        Text("Verifying…")
                                            .font(SkyHerdTypography.caption)
                                            .foregroundStyle(Color.skhText2)
                                    }
                                } else if let result = verifyResult {
                                    HStack(spacing: SkyHerdSpacing.sm) {
                                        Image(systemName: result.valid
                                              ? "checkmark.shield.fill"
                                              : "exclamationmark.shield.fill")
                                            .foregroundStyle(result.valid ? Color.skhOk : Color.skhDanger)
                                        VStack(alignment: .leading, spacing: 2) {
                                            Text(result.valid ? "Chain verified" : "Verification failed")
                                                .font(SkyHerdTypography.body)
                                                .foregroundStyle(result.valid ? Color.skhOk : Color.skhDanger)
                                            Text("Chain depth: \(result.total)")
                                                .font(SkyHerdTypography.caption2)
                                                .foregroundStyle(Color.skhText2)
                                            if let reason = result.reason {
                                                Text(reason)
                                                    .font(SkyHerdTypography.caption2)
                                                    .foregroundStyle(Color.skhWarn)
                                            }
                                        }
                                    }
                                }

                                Button(action: onVerify) {
                                    Label("Verify Entry", systemImage: "shield.checkered")
                                        .font(SkyHerdTypography.caption)
                                        .padding(.horizontal, SkyHerdSpacing.md)
                                        .padding(.vertical, SkyHerdSpacing.sm)
                                        .frame(maxWidth: .infinity)
                                        .background(Color.skhBg2, in: RoundedRectangle(cornerRadius: 8))
                                        .overlay(
                                            RoundedRectangle(cornerRadius: 8)
                                                .strokeBorder(Color.skhLine, lineWidth: 1)
                                        )
                                }
                                .buttonStyle(.plain)
                                .disabled(isVerifying)
                            }
                        }

                        // CLI copy
                        LedgerDetailSection(title: "CLI Verify") {
                            HStack {
                                Text(cliCommand)
                                    .font(SkyHerdTypography.mono)
                                    .foregroundStyle(Color.skhText1)
                                    .textSelection(.enabled)
                                Spacer()
                                Button {
                                    UIPasteboard.general.string = cliCommand
                                    copied = true
                                    Task {
                                        try? await Task.sleep(nanoseconds: 2_000_000_000)
                                        copied = false
                                    }
                                } label: {
                                    Label(
                                        copied ? "Copied" : "Copy",
                                        systemImage: copied ? "checkmark" : "doc.on.doc"
                                    )
                                    .font(SkyHerdTypography.caption)
                                    .foregroundStyle(copied ? Color.skhOk : Color.skhSky)
                                }
                                .buttonStyle(.plain)
                            }
                        }

                        // Memver ID if present
                        if let memverId = entry.memverId {
                            LedgerDetailSection(title: "Memver ID") {
                                Text(memverId)
                                    .font(SkyHerdTypography.mono)
                                    .foregroundStyle(Color.skhDust)
                                    .textSelection(.enabled)
                            }
                        }
                    }
                    .padding(SkyHerdSpacing.md)
                }
            }
            .navigationTitle("Entry #\(entry.seq)")
            .navigationBarTitleDisplayMode(.inline)
        }
    }
}

private struct LedgerDetailSection<Content: View>: View {
    let title: String
    @ViewBuilder let content: () -> Content

    var body: some View {
        VStack(alignment: .leading, spacing: SkyHerdSpacing.sm) {
            Text(title.uppercased())
                .font(SkyHerdTypography.caption2)
                .foregroundStyle(Color.skhText2)
                .tracking(1.2)
            content()
        }
        .padding(SkyHerdSpacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.skhBg1, in: RoundedRectangle(cornerRadius: 10))
    }
}

// MARK: - PairResultSheet

private struct PairResultSheet: View {
    let result: AttestPairResponse

    var body: some View {
        NavigationStack {
            ZStack {
                Color.skhBg0.ignoresSafeArea()
                VStack(spacing: SkyHerdSpacing.lg) {
                    Image(systemName: "link.badge.plus")
                        .font(.system(size: 48))
                        .foregroundStyle(Color.skhSky)

                    Text("Device Paired")
                        .font(SkyHerdTypography.title)
                        .foregroundStyle(Color.skhText0)

                    VStack(alignment: .leading, spacing: SkyHerdSpacing.sm) {
                        HStack {
                            Text("Memver ID")
                                .font(SkyHerdTypography.caption2)
                                .foregroundStyle(Color.skhText2)
                            Spacer()
                            Text(result.memverId)
                                .font(SkyHerdTypography.mono)
                                .foregroundStyle(Color.skhDust)
                                .textSelection(.enabled)
                        }
                        HStack {
                            Text("Ledger Entry")
                                .font(SkyHerdTypography.caption2)
                                .foregroundStyle(Color.skhText2)
                            Spacer()
                            Text("#\(result.ledgerEntry.seq)")
                                .font(SkyHerdTypography.body)
                                .foregroundStyle(Color.skhText0)
                        }
                    }
                    .padding(SkyHerdSpacing.md)
                    .background(Color.skhBg1, in: RoundedRectangle(cornerRadius: 10))
                    .padding(.horizontal, SkyHerdSpacing.md)

                    Spacer()
                }
                .padding(SkyHerdSpacing.md)
            }
            .navigationTitle("Memver Pairing")
            .navigationBarTitleDisplayMode(.inline)
        }
    }
}

// MARK: - Helpers

private func prettyJSON(_ jsonString: String) -> String {
    guard let data = jsonString.data(using: .utf8),
          let obj = try? JSONSerialization.jsonObject(with: data),
          let pretty = try? JSONSerialization.data(withJSONObject: obj, options: .prettyPrinted),
          let str = String(data: pretty, encoding: .utf8) else {
        return jsonString
    }
    return str
}

private func isoToRelative(_ isoString: String) -> String {
    let fmt = ISO8601DateFormatter()
    fmt.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
    if let date = fmt.date(from: isoString) ?? ISO8601DateFormatter().date(from: isoString) {
        return relativeTime(date.timeIntervalSince1970)
    }
    return isoString
}

// MARK: - AttestPairResponse Identifiable conformance for sheet binding

extension AttestPairResponse: Identifiable {
    public var id: String { memverId }
}
