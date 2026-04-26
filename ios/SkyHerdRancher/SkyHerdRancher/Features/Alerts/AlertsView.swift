import SwiftUI

// MARK: - AlertsView

struct AlertsView: View {
    @Environment(AppState.self) private var appState

    var body: some View {
        @Bindable var vm = appState.alertsVM
        NavigationStack {
            ZStack(alignment: .bottom) {
                VStack(spacing: 0) {
                    // Connection badge + filter chips
                    VStack(spacing: SkyHerdSpacing.sm) {
                        HStack {
                            ConnectionBadge(state: appState.connectionState)
                            Spacer()
                        }
                        .padding(.horizontal, SkyHerdSpacing.md)

                        SeverityFilterBar(selected: $vm.severityFilter)
                    }
                    .padding(.vertical, SkyHerdSpacing.sm)
                    .background(Color.skhBg1)

                    Divider().background(Color.skhLine)

                    // Alert list
                    if appState.alertsVM.activeAlerts.isEmpty {
                        AlertsEmptyState()
                    } else {
                        List {
                            ForEach(appState.alertsVM.activeAlerts) { alert in
                                AlertRow(
                                    alert: alert,
                                    isAcked: appState.alertsVM.acknowledgedIds.contains(alert.id),
                                    onAck: { appState.alertsVM.acknowledge(alert.id) },
                                    onSnooze: { appState.alertsVM.snooze(alert.id) },
                                    onEscalate: { appState.alertsVM.escalate(alert.id) }
                                )
                                .contentShape(Rectangle())
                                .onTapGesture {
                                    appState.alertsVM.selectedAlertId = alert.id
                                }
                                .listRowBackground(
                                    appState.alertsVM.acknowledgedIds.contains(alert.id)
                                        ? Color.skhBg1.opacity(0.6)
                                        : Color.skhBg1
                                )
                                .listRowInsets(EdgeInsets(
                                    top: SkyHerdSpacing.xs,
                                    leading: SkyHerdSpacing.md,
                                    bottom: SkyHerdSpacing.xs,
                                    trailing: SkyHerdSpacing.md
                                ))
                                .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                                    Button {
                                        appState.alertsVM.acknowledge(alert.id)
                                    } label: {
                                        Label("Ack", systemImage: "checkmark.circle")
                                    }
                                    .tint(Color.skhOk)
                                }
                                .swipeActions(edge: .leading, allowsFullSwipe: false) {
                                    Button {
                                        appState.alertsVM.escalate(alert.id)
                                    } label: {
                                        Label("Escalate", systemImage: "phone.fill")
                                    }
                                    .tint(Color.skhDanger)
                                }
                            }
                        }
                        .listStyle(.plain)
                        .scrollContentBackground(.hidden)
                        .background(Color.skhBg0)
                    }
                }
                .background(Color.skhBg0)
                .navigationTitle("Alerts")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .navigationBarTrailing) {
                        Button {
                            appState.alertsVM.toastMessage = "Wes test page sent"
                        } label: {
                            Label("Test Wes", systemImage: "phone.arrow.up.right")
                                .font(SkyHerdTypography.caption)
                        }
                        .tint(Color.skhThermal)
                    }
                }

                // Toast
                if let msg = appState.alertsVM.toastMessage {
                    ToastView(message: msg)
                        .padding(.bottom, SkyHerdSpacing.lg)
                        .transition(.move(edge: .bottom).combined(with: .opacity))
                        .onAppear {
                            Task {
                                try? await Task.sleep(nanoseconds: 3_000_000_000)
                                appState.alertsVM.toastMessage = nil
                            }
                        }
                }
            }
            .animation(.easeInOut(duration: 0.3), value: appState.alertsVM.toastMessage)
            .sheet(item: Binding(
                get: {
                    appState.alertsVM.selectedAlertId.flatMap { id in
                        appState.alertsVM.alerts.first { $0.id == id }
                    }.map { SelectedAlertWrapper(alert: $0) }
                },
                set: { appState.alertsVM.selectedAlertId = $0?.alert.id }
            )) { wrapper in
                AlertDetailSheet(
                    alert: wrapper.alert,
                    onNavigateToLedger: nil
                )
                .presentationDetents([.medium, .large])
                .presentationDragIndicator(.visible)
            }
        }
    }
}

// MARK: - Wrapper for sheet binding

private struct SelectedAlertWrapper: Identifiable {
    let alert: SkyHerdAlert
    var id: String { alert.id }
}

// MARK: - SeverityFilterBar

private struct SeverityFilterBar: View {
    @Binding var selected: AlertSeverity?

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: SkyHerdSpacing.sm) {
                FilterChip(label: "All", isSelected: selected == nil) {
                    selected = nil
                }
                ForEach(AlertSeverity.allCases, id: \.rawValue) { sev in
                    FilterChip(
                        label: sev.label,
                        isSelected: selected == sev,
                        accentColor: severityColor(sev)
                    ) {
                        selected = (selected == sev) ? nil : sev
                    }
                }
            }
            .padding(.horizontal, SkyHerdSpacing.md)
        }
    }
}

private struct FilterChip: View {
    let label: String
    let isSelected: Bool
    var accentColor: Color = .skhText1
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(label)
                .font(SkyHerdTypography.caption)
                .foregroundStyle(isSelected ? accentColor : Color.skhText2)
                .padding(.horizontal, 12)
                .padding(.vertical, 5)
                .background(
                    isSelected ? accentColor.opacity(0.15) : Color.skhBg2,
                    in: Capsule()
                )
                .overlay(
                    Capsule().strokeBorder(
                        isSelected ? accentColor.opacity(0.4) : Color.skhLine,
                        lineWidth: 1
                    )
                )
        }
        .buttonStyle(.plain)
    }
}

// MARK: - AlertRow

private struct AlertRow: View {
    let alert: SkyHerdAlert
    let isAcked: Bool
    let onAck: () -> Void
    let onSnooze: () -> Void
    let onEscalate: () -> Void

    var body: some View {
        HStack(alignment: .top, spacing: SkyHerdSpacing.sm) {
            // Urgency badge
            UrgencyBadge(severity: alert.severity)

            // Content
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(alert.title)
                        .font(SkyHerdTypography.body)
                        .foregroundStyle(isAcked ? Color.skhText2 : Color.skhText0)
                        .lineLimit(2)
                    Spacer()
                }
                HStack(spacing: 4) {
                    Image(systemName: agentIcon(alert.sourceAgent))
                        .font(.system(size: 10))
                        .foregroundStyle(agentAccentColor(alert.sourceAgent))
                    Text(agentDisplayName(alert.sourceAgent))
                        .font(SkyHerdTypography.caption2)
                        .foregroundStyle(Color.skhText2)
                    Text("·")
                        .foregroundStyle(Color.skhText2)
                    Text(relativeTime(alert.ts))
                        .font(SkyHerdTypography.caption2)
                        .foregroundStyle(Color.skhText2)
                }
                Text(alert.contextLine)
                    .font(SkyHerdTypography.caption)
                    .foregroundStyle(Color.skhText1)
                    .lineLimit(1)
            }

            // Action icons
            VStack(spacing: SkyHerdSpacing.sm) {
                Button(action: onAck) {
                    Image(systemName: isAcked ? "checkmark.circle.fill" : "checkmark.circle")
                        .foregroundStyle(isAcked ? Color.skhOk : Color.skhText2)
                        .font(.system(size: 20))
                }
                .buttonStyle(.plain)
                .accessibilityLabel(isAcked ? "Acknowledged" : "Acknowledge alert")

                Button(action: onSnooze) {
                    Image(systemName: "clock.badge.xmark")
                        .foregroundStyle(Color.skhText2)
                        .font(.system(size: 18))
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Snooze alert")

                Button(action: onEscalate) {
                    Image(systemName: "phone.fill")
                        .foregroundStyle(Color.skhDanger)
                        .font(.system(size: 18))
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Escalate to Wes")
            }
        }
        .padding(.vertical, SkyHerdSpacing.sm)
        .opacity(isAcked ? 0.65 : 1.0)
    }
}

// MARK: - UrgencyBadge (DesignSystem)

struct UrgencyBadge: View {
    let severity: AlertSeverity

    var body: some View {
        VStack {
            RoundedRectangle(cornerRadius: 3)
                .fill(severityColor(severity))
                .frame(width: 4, height: 40)
        }
        .accessibilityLabel("\(severity.label) severity")
        .accessibilityHidden(false)
    }
}

// MARK: - Severity color helper

func severityColor(_ severity: AlertSeverity) -> Color {
    switch severity {
    case .critical: return .skhDanger
    case .high:     return .skhThermal
    case .medium:   return .skhWarn
    case .low:      return .skhSky
    }
}

// MARK: - AlertsEmptyState

private struct AlertsEmptyState: View {
    var body: some View {
        VStack(spacing: SkyHerdSpacing.md) {
            Spacer()
            Image(systemName: "checkmark.seal.fill")
                .font(.system(size: 48))
                .foregroundStyle(Color.skhOk.opacity(0.6))
            Text("All clear, partner.")
                .font(SkyHerdTypography.heading)
                .foregroundStyle(Color.skhText1)
            Text("No alerts right now. The ranch is quiet.")
                .font(SkyHerdTypography.caption)
                .foregroundStyle(Color.skhText2)
                .multilineTextAlignment(.center)
            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.skhBg0)
    }
}

// MARK: - AlertDetailSheet

struct AlertDetailSheet: View {
    let alert: SkyHerdAlert
    let onNavigateToLedger: ((String) -> Void)?

    var body: some View {
        NavigationStack {
            ZStack {
                Color.skhBg0.ignoresSafeArea()
                ScrollView {
                    VStack(alignment: .leading, spacing: SkyHerdSpacing.md) {
                        // Severity + title
                        HStack(spacing: SkyHerdSpacing.sm) {
                            UrgencyBadge(severity: alert.severity)
                            VStack(alignment: .leading, spacing: 4) {
                                Text(alert.title)
                                    .font(SkyHerdTypography.heading)
                                    .foregroundStyle(Color.skhText0)
                                HStack(spacing: 4) {
                                    Text(alert.severity.label.uppercased())
                                        .font(SkyHerdTypography.caption2)
                                        .tracking(0.8)
                                        .foregroundStyle(severityColor(alert.severity))
                                    Text("·")
                                        .foregroundStyle(Color.skhText2)
                                    Text(relativeTime(alert.ts))
                                        .font(SkyHerdTypography.caption2)
                                        .foregroundStyle(Color.skhText2)
                                }
                            }
                        }
                        .padding(SkyHerdSpacing.md)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Color.skhBg1, in: RoundedRectangle(cornerRadius: 10))

                        // Context
                        DetailSection(title: "Context") {
                            Text(alert.contextLine)
                                .font(SkyHerdTypography.body)
                                .foregroundStyle(Color.skhText1)
                        }

                        // Source agent
                        DetailSection(title: "Source Agent") {
                            HStack(spacing: SkyHerdSpacing.sm) {
                                Image(systemName: agentIcon(alert.sourceAgent))
                                    .foregroundStyle(agentAccentColor(alert.sourceAgent))
                                Text(alert.sourceAgent)
                                    .font(SkyHerdTypography.body)
                                    .foregroundStyle(Color.skhText0)
                            }
                        }

                        // Attestation hash
                        if let hash = alert.attestHash {
                            DetailSection(title: "Attestation") {
                                HStack {
                                    Text(String(hash.prefix(16)) + "…")
                                        .font(SkyHerdTypography.mono)
                                        .foregroundStyle(Color.skhSky)
                                    Spacer()
                                    Button {
                                        onNavigateToLedger?(hash)
                                    } label: {
                                        Label("View in Ledger", systemImage: "link")
                                            .font(SkyHerdTypography.caption)
                                    }
                                    .tint(Color.skhSky)
                                }
                            }
                        }
                    }
                    .padding(SkyHerdSpacing.md)
                }
            }
            .navigationTitle("Alert Detail")
            .navigationBarTitleDisplayMode(.inline)
        }
    }
}

private struct DetailSection<Content: View>: View {
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

// MARK: - Relative time helper (shared across feature files)

func relativeTime(_ ts: Double) -> String {
    let delta = Date().timeIntervalSince1970 - ts
    if delta < 60    { return "\(max(0, Int(delta)))s ago" }
    if delta < 3600  { return "\(Int(delta / 60))m ago" }
    if delta < 86400 { return "\(Int(delta / 3600))h ago" }
    return "\(Int(delta / 86400))d ago"
}
