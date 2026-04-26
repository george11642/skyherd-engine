import SwiftUI

@main
struct SkyHerdRancherApp: App {
    @State private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(appState)
                .onAppear { appState.start() }
                .onDisappear { appState.stop() }
        }
    }
}
