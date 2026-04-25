import SwiftUI

struct RootView: View {
    @Environment(AppState.self) private var appState

    /// Initial tab selection from launch argument -SkyHerdInitialTab N (0-4).
    /// Used for automated screenshot capture. Not shown to users.
    @State private var selectedTab: Int = {
        let args = ProcessInfo.processInfo.arguments
        if let idx = args.firstIndex(of: "-SkyHerdInitialTab"),
           idx + 1 < args.count,
           let tab = Int(args[idx + 1]) {
            return tab
        }
        return 0
    }()

    var body: some View {
        TabView(selection: $selectedTab) {
            LiveView()
                .tabItem {
                    Label("Live", systemImage: "play.circle.fill")
                }
                .tag(0)

            MapView()
                .tabItem {
                    Label("Map", systemImage: "map.fill")
                }
                .tag(1)

            AgentsView()
                .tabItem {
                    Label("Agents", systemImage: "cpu.fill")
                }
                .tag(2)

            AlertsView()
                .tabItem {
                    Label("Alerts", systemImage: "bell.badge.fill")
                }
                .badge(appState.alertsVM.unreadCount > 0 ? appState.alertsVM.unreadCount : 0)
                .tag(3)

            LedgerView()
                .tabItem {
                    Label("Ledger", systemImage: "lock.shield.fill")
                }
                .tag(4)
        }
        .tint(Color.skhSky)
    }
}
