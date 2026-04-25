import SwiftUI

struct RootView: View {
    @Environment(AppState.self) private var appState

    var body: some View {
        TabView {
            LiveView()
                .tabItem {
                    Label("Live", systemImage: "play.circle.fill")
                }

            MapView()
                .tabItem {
                    Label("Map", systemImage: "map.fill")
                }

            AgentsView()
                .tabItem {
                    Label("Agents", systemImage: "cpu.fill")
                }

            AlertsView()
                .tabItem {
                    Label("Alerts", systemImage: "bell.badge.fill")
                }
                .badge(appState.alertsVM.unreadCount > 0 ? appState.alertsVM.unreadCount : 0)

            LedgerView()
                .tabItem {
                    Label("Ledger", systemImage: "lock.shield.fill")
                }
        }
        .tint(Color.skhSky)
    }
}
