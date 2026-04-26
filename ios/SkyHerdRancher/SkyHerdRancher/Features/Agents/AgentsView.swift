import SwiftUI
import Charts

// MARK: - AgentsView

struct AgentsView: View {
    @Environment(AppState.self) private var appState

    private let agentOrder = [
        "FenceLineDispatcher",
        "HerdHealthWatcher",
        "PredatorPatternLearner",
        "GrazingOptimizer",
        "CalvingWatch"
    ]

    var body: some View {
        @Bindable var vm = appState.agentsVM
        NavigationStack {
            ZStack(alignment: .bottom) {
                List {
                    // Header badge
                    Section {
                        HStack {
                            Spacer()
                            ConnectionBadge(state: appState.connectionState)
                            Spacer()
                        }
                        .listRowBackground(Color.clear)
                        .listRowSeparator(.hidden)
                    }

                    // Agent cards
                    Section {
                        ForEach(agentOrder, id: \.self) { name in
                            AgentCardRow(
                                name: name,
                                status: appState.agentsVM.agentStatuses[name],
                                lastLog: appState.agentsVM.lastLogs[name],
                                cacheHits: appState.agentsVM.cacheHitSamples(for: name),
                                cacheRate: appState.agentsVM.agentCacheHitRates[name] ?? 0,
                                tokenDisplay: appState.agentsVM.formattedTokens(for: name)
                            )
                            .contentShape(Rectangle())
                            .onTapGesture {
                                appState.agentsVM.selectedAgent = name
                            }
                            .listRowBackground(Color.skhBg1)
                            .listRowInsets(EdgeInsets(
                                top: SkyHerdSpacing.xs,
                                leading: SkyHerdSpacing.md,
                                bottom: SkyHerdSpacing.xs,
                                trailing: SkyHerdSpacing.md
                            ))
                        }
                    }

                    // Mesh overview footer
                    Section {
                        MeshOverviewFooter(
                            totalDecisions: appState.agentsVM.totalDecisionsToday,
                            avgCacheRate: appState.agentsVM.averageCacheHitRate,
                            p50ms: appState.agentsVM.p50LatencyMs,
                            p95ms: appState.agentsVM.p95LatencyMs
                        )
                        .listRowBackground(Color.skhBg1)
                    } header: {
                        Text("MESH OVERVIEW")
                            .font(SkyHerdTypography.caption2)
                            .foregroundStyle(Color.skhText2)
                            .tracking(1.2)
                    }
                }
                .listStyle(.insetGrouped)
                .scrollContentBackground(.hidden)
                .background(Color.skhBg0)
                .refreshable {
                    await refreshAgents()
                }
                .navigationTitle("Agents")
                .navigationBarTitleDisplayMode(.inline)

                // Toast
                if let msg = appState.agentsVM.toastMessage {
                    ToastView(message: msg)
                        .padding(.bottom, SkyHerdSpacing.lg)
                        .transition(.move(edge: .bottom).combined(with: .opacity))
                        .onAppear {
                            Task {
                                try? await Task.sleep(nanoseconds: 3_000_000_000)
                                appState.agentsVM.toastMessage = nil
                            }
                        }
                }
            }
            .animation(.easeInOut(duration: 0.3), value: appState.agentsVM.toastMessage)
            .sheet(item: Binding(
                get: { appState.agentsVM.selectedAgent.map { SelectedAgent(name: $0) } },
                set: { appState.agentsVM.selectedAgent = $0?.name }
            )) { selected in
                AgentDetailSheet(
                    name: selected.name,
                    status: appState.agentsVM.agentStatuses[selected.name],
                    logs: appState.agentsVM.agentLogs[selected.name] ?? []
                )
                .presentationDetents([.medium, .large])
                .presentationDragIndicator(.visible)
            }
        }
    }

    @MainActor
    private func refreshAgents() async {
        guard let resp = try? await appState.apiClient.agents() else {
            appState.agentsVM.toastMessage = "Failed to refresh agents"
            return
        }
        appState.agentsVM.handleInitial(resp.agents)
    }
}

// MARK: - Identifiable wrapper for sheet binding

private struct SelectedAgent: Identifiable {
    let name: String
    var id: String { name }
}

// MARK: - AgentCardRow

private struct AgentCardRow: View {
    let name: String
    let status: AgentStatus?
    let lastLog: AgentLogEvent?
    let cacheHits: [Bool]
    let cacheRate: Double
    let tokenDisplay: String

    var body: some View {
        VStack(alignment: .leading, spacing: SkyHerdSpacing.sm) {
            // Top row: icon + name + status pill
            HStack(spacing: SkyHerdSpacing.sm) {
                Image(systemName: agentIcon(name))
                    .foregroundStyle(agentAccentColor(name))
                    .font(.system(size: 18, weight: .medium))
                    .frame(width: 28)

                Text(agentDisplayName(name))
                    .font(SkyHerdTypography.heading)
                    .foregroundStyle(Color.skhText0)

                Spacer()

                StatusPill(state: status?.state ?? "idle")
            }

            // Last decision summary
            if let msg = lastLog?.message ?? lastLog?.line {
                Text(msg)
                    .font(SkyHerdTypography.caption)
                    .foregroundStyle(Color.skhText1)
                    .lineLimit(2)
            } else {
                Text("No recent decisions")
                    .font(SkyHerdTypography.caption)
                    .foregroundStyle(Color.skhText2)
            }

            // Bottom row: sparkline + cache rate + tokens
            HStack(spacing: SkyHerdSpacing.md) {
                if !cacheHits.isEmpty {
                    CacheSparkline(samples: cacheHits)
                        .frame(width: 60, height: 20)
                }

                Text(String(format: "%.0f%% cache", cacheRate * 100))
                    .font(SkyHerdTypography.caption2)
                    .foregroundStyle(Color.skhText2)

                Spacer()

                HStack(spacing: 3) {
                    Image(systemName: "bolt.fill")
                        .font(.system(size: 9))
                        .foregroundStyle(Color.skhThermal)
                    Text(tokenDisplay)
                        .font(SkyHerdTypography.caption2)
                        .foregroundStyle(Color.skhText2)
                }
            }
        }
        .padding(.vertical, SkyHerdSpacing.sm)
    }
}

// MARK: - StatusPill

private struct StatusPill: View {
    let state: String

    var body: some View {
        Text(state.uppercased())
            .font(SkyHerdTypography.caption2)
            .tracking(0.8)
            .foregroundStyle(pillColor)
            .padding(.horizontal, 8)
            .padding(.vertical, 3)
            .background(pillColor.opacity(0.15), in: Capsule())
            .overlay(Capsule().strokeBorder(pillColor.opacity(0.3), lineWidth: 1))
    }

    private var pillColor: Color {
        switch state {
        case "active", "running": return .skhOk
        case "cooldown":          return .skhWarn
        case "error":             return .skhDanger
        default:                  return .skhText2
        }
    }
}

// MARK: - CacheSparkline (Swift Charts mini-chart)

private struct CacheSparkline: View {
    let samples: [Bool]

    var body: some View {
        Chart {
            ForEach(Array(samples.enumerated()), id: \.offset) { idx, hit in
                BarMark(
                    x: .value("Tick", idx),
                    y: .value("Hit", hit ? 1.0 : 0.3)
                )
                .foregroundStyle(hit ? Color.skhOk.opacity(0.8) : Color.skhDanger.opacity(0.5))
                .cornerRadius(2)
            }
        }
        .chartXAxis(.hidden)
        .chartYAxis(.hidden)
        .chartYScale(domain: 0...1.2)
    }
}

// MARK: - MeshOverviewFooter

private struct MeshOverviewFooter: View {
    let totalDecisions: Int
    let avgCacheRate: Double
    let p50ms: Double
    let p95ms: Double

    var body: some View {
        HStack(spacing: 0) {
            StatCell(label: "Decisions", value: "\(totalDecisions)")
            Divider().frame(height: 32)
            StatCell(label: "Cache Hit", value: String(format: "%.0f%%", avgCacheRate * 100))
            Divider().frame(height: 32)
            StatCell(label: "p50", value: p50ms > 0 ? String(format: "%.0fms", p50ms) : "—")
            Divider().frame(height: 32)
            StatCell(label: "p95", value: p95ms > 0 ? String(format: "%.0fms", p95ms) : "—")
        }
        .padding(.vertical, SkyHerdSpacing.sm)
    }
}

private struct StatCell: View {
    let label: String
    let value: String

    var body: some View {
        VStack(spacing: 2) {
            Text(value)
                .font(SkyHerdTypography.heading)
                .foregroundStyle(Color.skhText0)
            Text(label)
                .font(SkyHerdTypography.caption2)
                .foregroundStyle(Color.skhText2)
        }
        .frame(maxWidth: .infinity)
    }
}

// MARK: - AgentDetailSheet

private struct AgentDetailSheet: View {
    let name: String
    let status: AgentStatus?
    let logs: [AgentLogEvent]

    var body: some View {
        NavigationStack {
            ZStack {
                Color.skhBg0.ignoresSafeArea()
                VStack(spacing: 0) {
                    // Agent header
                    HStack(spacing: SkyHerdSpacing.md) {
                        Image(systemName: agentIcon(name))
                            .foregroundStyle(agentAccentColor(name))
                            .font(.system(size: 28, weight: .medium))

                        VStack(alignment: .leading, spacing: 2) {
                            Text(agentDisplayName(name))
                                .font(SkyHerdTypography.heading)
                                .foregroundStyle(Color.skhText0)
                            if let sid = status?.sessionId {
                                Text(sid)
                                    .font(SkyHerdTypography.mono)
                                    .foregroundStyle(Color.skhText2)
                            }
                        }

                        Spacer()

                        StatusPill(state: status?.state ?? "idle")
                    }
                    .padding(SkyHerdSpacing.md)
                    .background(Color.skhBg1)

                    // Token/cost row
                    if let s = status {
                        HStack(spacing: SkyHerdSpacing.lg) {
                            LabeledValue(label: "Tokens In",
                                        value: formatK(s.cumulativeTokensIn))
                            LabeledValue(label: "Tokens Out",
                                        value: formatK(s.cumulativeTokensOut))
                            LabeledValue(label: "Cost",
                                        value: String(format: "$%.4f", s.cumulativeCostUsd))
                        }
                        .padding(SkyHerdSpacing.md)
                        .background(Color.skhBg2)
                    }

                    Divider().background(Color.skhLine)

                    // Log events
                    if logs.isEmpty {
                        Spacer()
                        Text("No recent events for this agent.")
                            .font(SkyHerdTypography.caption)
                            .foregroundStyle(Color.skhText2)
                        Spacer()
                    } else {
                        List {
                            ForEach(Array(logs.enumerated()), id: \.offset) { _, event in
                                AgentLogRow(event: event)
                                    .listRowBackground(Color.skhBg1)
                                    .listRowInsets(EdgeInsets(
                                        top: SkyHerdSpacing.xs,
                                        leading: SkyHerdSpacing.md,
                                        bottom: SkyHerdSpacing.xs,
                                        trailing: SkyHerdSpacing.md
                                    ))
                            }
                        }
                        .listStyle(.plain)
                        .scrollContentBackground(.hidden)
                        .background(Color.skhBg0)
                    }
                }
            }
            .navigationTitle(agentDisplayName(name))
            .navigationBarTitleDisplayMode(.inline)
        }
    }

    private func formatK(_ n: Int) -> String {
        if n >= 1_000_000 { return String(format: "%.1fM", Double(n) / 1_000_000) }
        if n >= 1_000    { return String(format: "%.1fK", Double(n) / 1_000) }
        return "\(n)"
    }
}

private struct LabeledValue: View {
    let label: String
    let value: String

    var body: some View {
        VStack(spacing: 2) {
            Text(value)
                .font(SkyHerdTypography.body)
                .foregroundStyle(Color.skhText0)
            Text(label)
                .font(SkyHerdTypography.caption2)
                .foregroundStyle(Color.skhText2)
        }
    }
}

private struct AgentLogRow: View {
    let event: AgentLogEvent

    var body: some View {
        HStack(alignment: .top, spacing: SkyHerdSpacing.sm) {
            levelDot
                .padding(.top, 4)

            VStack(alignment: .leading, spacing: 2) {
                if let msg = event.message ?? event.line {
                    Text(msg)
                        .font(SkyHerdTypography.caption)
                        .foregroundStyle(Color.skhText1)
                }
                if let tool = event.tool {
                    Text("tool: \(tool)")
                        .font(SkyHerdTypography.mono)
                        .foregroundStyle(Color.skhThermal)
                }
                Text(relativeTime(event.ts))
                    .font(SkyHerdTypography.caption2)
                    .foregroundStyle(Color.skhText2)
            }
        }
        .padding(.vertical, 4)
    }

    private var levelDot: some View {
        Circle()
            .fill(levelColor)
            .frame(width: 6, height: 6)
    }

    private var levelColor: Color {
        switch event.level {
        case "error":   return .skhDanger
        case "warn":    return .skhWarn
        case "info":    return .skhOk
        default:        return .skhText2
        }
    }

    private func relativeTime(_ ts: Double) -> String {
        let delta = Date().timeIntervalSince1970 - ts
        if delta < 60    { return "\(Int(delta))s ago" }
        if delta < 3600  { return "\(Int(delta / 60))m ago" }
        return "\(Int(delta / 3600))h ago"
    }
}

// MARK: - ToastView (shared helper — also used by Alerts/Ledger)

struct ToastView: View {
    let message: String

    var body: some View {
        Text(message)
            .font(SkyHerdTypography.caption)
            .foregroundStyle(Color.skhText0)
            .padding(.horizontal, SkyHerdSpacing.md)
            .padding(.vertical, SkyHerdSpacing.sm)
            .background(Color.skhBg2, in: Capsule())
            .overlay(Capsule().strokeBorder(Color.skhLine, lineWidth: 1))
            .shadow(color: .black.opacity(0.4), radius: 8, y: 4)
    }
}

// MARK: - Agent metadata helpers (shared with Alerts/Ledger)

func agentIcon(_ name: String) -> String {
    switch name {
    case "FenceLineDispatcher":   return "shield.lefthalf.filled"
    case "HerdHealthWatcher":     return "cross.case"
    case "PredatorPatternLearner":return "eye.trianglebadge.exclamationmark"
    case "GrazingOptimizer":      return "leaf.circle"
    case "CalvingWatch":          return "heart.text.square"
    default:                      return "cpu"
    }
}

func agentAccentColor(_ name: String) -> Color {
    switch name {
    case "FenceLineDispatcher":   return .skhDanger
    case "HerdHealthWatcher":     return .skhOk
    case "PredatorPatternLearner":return .skhThermal
    case "GrazingOptimizer":      return .skhSage
    case "CalvingWatch":          return .skhSky
    default:                      return .skhText1
    }
}

func agentDisplayName(_ name: String) -> String {
    switch name {
    case "FenceLineDispatcher":   return "FenceLine"
    case "HerdHealthWatcher":     return "Herd Health"
    case "PredatorPatternLearner":return "Predator"
    case "GrazingOptimizer":      return "Grazing"
    case "CalvingWatch":          return "Calving"
    default:                      return name
    }
}
