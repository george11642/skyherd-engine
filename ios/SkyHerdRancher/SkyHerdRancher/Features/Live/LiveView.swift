import SwiftUI

struct LiveView: View {
    @Environment(AppState.self) private var appState
    @State private var sliderPosition: Double = LiveViewModel.speedToSlider(15.0)
    @State private var showBanner: Bool = false
    @State private var bannerScenario: String = ""
    @State private var bannerHideTask: Task<Void, Never>? = nil
    @State private var isAtBottom: Bool = true

    private var vm: LiveViewModel { appState.liveVM }

    var body: some View {
        NavigationStack {
            ZStack(alignment: .top) {
                Color.skhBg0.ignoresSafeArea()

                VStack(spacing: 0) {
                    // Top bar: connection badge + cost rate
                    topBar

                    // Narration banner (overlay, slide from top)
                    NarrationBanner(scenarioName: bannerScenario, isVisible: showBanner)
                        .padding(.top, SkyHerdSpacing.sm)

                    // Scenario pills
                    scenarioPicker
                        .padding(.top, SkyHerdSpacing.sm)

                    // Playback controls
                    playbackControls
                        .padding(.top, SkyHerdSpacing.sm)

                    // Divider
                    Divider()
                        .overlay(Color.skhLine)
                        .padding(.top, SkyHerdSpacing.sm)

                    // Event feed
                    eventFeed
                }
            }
            .navigationTitle("Live")
            .navigationBarTitleDisplayMode(.inline)
        }
        .task {
            await vm.loadScenarios()
        }
        .onChange(of: vm.activeScenario) { _, newVal in
            if let name = newVal {
                bannerScenario = name
                bannerHideTask?.cancel()
                withAnimation { showBanner = true }
                bannerHideTask = Task {
                    try? await Task.sleep(nanoseconds: 6_000_000_000)
                    withAnimation { showBanner = false }
                }
            } else {
                bannerHideTask?.cancel()
                withAnimation { showBanner = false }
            }
        }
        .onChange(of: vm.speed) { _, newVal in
            let t = LiveViewModel.speedToSlider(newVal)
            if abs(t - sliderPosition) > 0.001 {
                sliderPosition = t
            }
        }
        .overlay(alignment: .bottom) {
            if let msg = vm.toastMessage {
                toastView(msg)
                    .transition(.move(edge: .bottom).combined(with: .opacity))
                    .padding(.bottom, SkyHerdSpacing.lg)
            }
        }
        .animation(.easeInOut(duration: 0.25), value: vm.toastMessage)
    }

    // MARK: - Top bar

    private var topBar: some View {
        HStack {
            ConnectionBadge(state: appState.connectionState)
            Spacer()
            HStack(spacing: SkyHerdSpacing.xs) {
                Circle()
                    .fill(vm.allIdle ? Color.skhOk : Color.skhWarn)
                    .frame(width: 7, height: 7)
                Text(costLabel)
                    .font(SkyHerdTypography.caption)
                    .foregroundStyle(vm.allIdle ? Color.skhOk : Color.skhWarn)
            }
            .padding(.horizontal, SkyHerdSpacing.sm)
            .padding(.vertical, 4)
            .background((vm.allIdle ? Color.skhOk : Color.skhWarn).opacity(0.12), in: Capsule())
        }
        .padding(.horizontal, SkyHerdSpacing.md)
        .padding(.top, SkyHerdSpacing.sm)
    }

    private var costLabel: String {
        if vm.costRate < 0.001 { return "$0.00/hr" }
        return String(format: "$%.3f/hr", vm.costRate)
    }

    // MARK: - Scenario picker

    private var scenarioPicker: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: SkyHerdSpacing.sm) {
                if vm.isLoadingScenarios {
                    ProgressView()
                        .tint(Color.skhText2)
                        .scaleEffect(0.8)
                        .padding(.horizontal, SkyHerdSpacing.md)
                } else {
                    let names = vm.scenarios.isEmpty ? defaultScenarios : vm.scenarios
                    ForEach(names, id: \.self) { name in
                        ScenarioPill(
                            name: name,
                            isActive: vm.activeScenario == name
                        ) {
                            Task { await vm.skipToNextScenario() }
                        }
                    }
                }
            }
            .padding(.horizontal, SkyHerdSpacing.md)
        }
    }

    private let defaultScenarios = [
        "coyote", "sick_cow", "water_drop", "calving",
        "storm", "wildfire", "rustling", "cross_ranch_coyote"
    ]

    // MARK: - Playback controls

    private var playbackControls: some View {
        HStack(spacing: SkyHerdSpacing.md) {
            // Play / Pause
            Button {
                vm.togglePlayback()
            } label: {
                Image(systemName: vm.isPaused ? "play.fill" : "pause.fill")
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(Color.skhSky)
                    .frame(width: 36, height: 36)
                    .background(Color.skhSky.opacity(0.15), in: Circle())
            }
            .accessibilityLabel(vm.isPaused ? "Resume feed" : "Pause feed")

            // Speed label
            Text(speedLabel)
                .font(SkyHerdTypography.mono)
                .foregroundStyle(Color.skhText1)
                .frame(width: 52, alignment: .trailing)

            // Logarithmic speed slider
            Slider(value: $sliderPosition, in: 0...1) { editing in
                if !editing {
                    let newSpeed = LiveViewModel.sliderToSpeed(sliderPosition)
                    vm.setSpeed(newSpeed)
                }
            }
            .tint(Color.skhSky)

            Text("100×")
                .font(SkyHerdTypography.caption2)
                .foregroundStyle(Color.skhText2)
        }
        .padding(.horizontal, SkyHerdSpacing.md)
    }

    private var speedLabel: String {
        let s = vm.speed
        if s < 2 { return "1×" }
        return String(format: "%.0f×", s)
    }

    // MARK: - Event feed

    private var eventFeed: some View {
        Group {
            if vm.recentEvents.isEmpty && !vm.isPaused {
                emptyState
            } else {
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(spacing: 0) {
                            // Anchor at top for auto-scroll (newest first)
                            Color.clear
                                .frame(height: 1)
                                .id("top")

                            let eventsToShow = vm.isPaused
                                ? vm.recentEvents
                                : vm.recentEvents
                            ForEach(eventsToShow.indices, id: \.self) { idx in
                                EventRow(event: eventsToShow[idx])
                                    .transition(.asymmetric(
                                        insertion: .move(edge: .top).combined(with: .opacity),
                                        removal: .opacity
                                    ))
                                if idx < eventsToShow.count - 1 {
                                    Divider()
                                        .overlay(Color.skhLine.opacity(0.5))
                                        .padding(.leading, SkyHerdSpacing.md)
                                }
                            }
                        }
                        .animation(.easeOut(duration: 0.18), value: vm.recentEvents.count)
                    }
                    .onChange(of: vm.recentEvents.count) { _, _ in
                        if !vm.isPaused {
                            withAnimation {
                                proxy.scrollTo("top", anchor: .top)
                            }
                        }
                    }
                }
            }
        }
    }

    private var emptyState: some View {
        VStack(spacing: SkyHerdSpacing.md) {
            Spacer()
            Image(systemName: "hare.fill")
                .font(.system(size: 48))
                .foregroundStyle(Color.skhText2)
            Text("Waiting for live events…")
                .font(SkyHerdTypography.heading)
                .foregroundStyle(Color.skhText2)
            Text("Start the backend with `make dashboard`")
                .font(SkyHerdTypography.caption)
                .foregroundStyle(Color.skhText2)
            Spacer()
        }
        .frame(maxWidth: .infinity)
    }

    // MARK: - Toast

    private func toastView(_ message: String) -> some View {
        Text(message)
            .font(SkyHerdTypography.caption)
            .foregroundStyle(Color.skhText0)
            .padding(.horizontal, SkyHerdSpacing.md)
            .padding(.vertical, SkyHerdSpacing.sm)
            .background(Color.skhBg2, in: Capsule())
            .overlay(Capsule().strokeBorder(Color.skhLine, lineWidth: 1))
            .shadow(color: .black.opacity(0.3), radius: 8, y: 4)
    }
}

// MARK: - ScenarioPill

private struct ScenarioPill: View {
    let name: String
    let isActive: Bool
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            HStack(spacing: 4) {
                Image(systemName: icon)
                    .font(.system(size: 11, weight: .semibold))
                Text(displayName)
                    .font(SkyHerdTypography.caption)
                    .lineLimit(1)
            }
            .foregroundStyle(isActive ? Color.skhWarn : Color.skhText1)
            .padding(.horizontal, SkyHerdSpacing.sm)
            .padding(.vertical, 6)
            .background(
                Capsule()
                    .fill(isActive ? Color.skhWarn.opacity(0.15) : Color.skhBg2)
                    .overlay(
                        Capsule().strokeBorder(
                            isActive ? Color.skhWarn.opacity(0.6) : Color.skhLine,
                            lineWidth: 1
                        )
                    )
            )
        }
        .buttonStyle(.plain)
    }

    private var displayName: String {
        switch name {
        case "coyote":             return "Coyote"
        case "sick_cow":           return "Sick Cow"
        case "water_drop":         return "Water Drop"
        case "calving":            return "Calving"
        case "storm":              return "Storm"
        case "wildfire":           return "Wildfire"
        case "rustling":           return "Rustling"
        case "cross_ranch_coyote": return "X-Ranch"
        default:                   return name.capitalized
        }
    }

    private var icon: String {
        switch name {
        case "coyote", "cross_ranch_coyote": return "pawprint.fill"
        case "sick_cow":                     return "heart.fill"
        case "water_drop":                   return "drop.fill"
        case "calving":                      return "heart.fill"
        case "storm":                        return "cloud.bolt.fill"
        case "wildfire":                     return "flame.fill"
        case "rustling":                     return "exclamationmark.triangle.fill"
        default:                             return "bolt.fill"
        }
    }
}

// MARK: - EventRow

private struct EventRow: View {
    let event: AgentLogEvent

    var body: some View {
        HStack(alignment: .top, spacing: SkyHerdSpacing.sm) {
            // Agent color chip
            Text(agentShortName)
                .font(SkyHerdTypography.caption2)
                .foregroundStyle(agentColor)
                .padding(.horizontal, 6)
                .padding(.vertical, 3)
                .background(agentColor.opacity(0.15), in: Capsule())
                .frame(minWidth: 60, alignment: .center)

            VStack(alignment: .leading, spacing: 2) {
                Text(messageText)
                    .font(SkyHerdTypography.caption)
                    .foregroundStyle(Color.skhText0)
                    .lineLimit(2)

                HStack(spacing: SkyHerdSpacing.xs) {
                    Text(relativeTime)
                        .font(SkyHerdTypography.caption2)
                        .foregroundStyle(Color.skhText2)
                    if let tool = event.tool {
                        Text("· \(tool)")
                            .font(SkyHerdTypography.caption2)
                            .foregroundStyle(Color.skhSky.opacity(0.8))
                    }
                }
            }

            Spacer(minLength: 0)
        }
        .padding(.horizontal, SkyHerdSpacing.md)
        .padding(.vertical, 10)
    }

    private var messageText: String {
        event.message ?? event.line ?? "(no message)"
    }

    private var agentShortName: String {
        let name = event.agent
        let shorts: [String: String] = [
            "FenceLineDispatcher": "Fence",
            "HerdHealthWatcher": "Health",
            "PredatorPatternLearner": "Predator",
            "GrazingOptimizer": "Graze",
            "CalvingWatch": "Calving",
            "CrossRanchCoordinator": "X-Ranch",
        ]
        return shorts[name] ?? String(name.prefix(6))
    }

    private var agentColor: Color {
        switch event.agent {
        case "FenceLineDispatcher":    return .skhDanger
        case "HerdHealthWatcher":      return .skhSage
        case "PredatorPatternLearner": return .skhThermal
        case "GrazingOptimizer":       return .skhOk
        case "CalvingWatch":           return .skhSky
        case "CrossRanchCoordinator":  return .skhDust
        default:                       return .skhText1
        }
    }

    private var relativeTime: String {
        let ts = event.ts
        let diff = Date().timeIntervalSince1970 - ts
        if diff < 5  { return "just now" }
        if diff < 60 { return "\(Int(diff))s ago" }
        let mins = Int(diff / 60)
        return "\(mins)m ago"
    }
}
