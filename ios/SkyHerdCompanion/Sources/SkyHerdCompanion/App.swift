import SwiftUI

@main
struct SkyHerdCompanionApp: App {
    @StateObject private var appState = AppState()

    init() {
        // Register with DJI SDK as early as possible in the app lifecycle.
        // The actual registration callback is handled inside DJIBridge.
        DJIBridge.shared.registerApp()
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appState)
        }
    }
}
