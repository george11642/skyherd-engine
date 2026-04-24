import SwiftUI

@main
struct SkyHerdCompanionApp: App {
    @StateObject private var appState = AppState()

    /// The command router — built once per app instance and shared with the
    /// MQTT bridge and the lost-signal watchdog.
    private let router: CommandRouter

    /// The lost-signal watchdog — fires RTH if MQTT stays disconnected > 30 s
    /// while the drone is in-air. Retained strongly here so the poll loop
    /// outlives the init scope.
    private let watchdog: LostSignalWatchdog

    init() {
        let router = CommandRouter()
        self.router = router
        self.watchdog = LostSignalWatchdog(
            mqttConnected: { MQTTBridge.shared.isConnected },
            currentStateProvider: { DJIBridge.shared.currentState },
            rthAction: { try await DJIBridge.shared.returnToHome() }
        )
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appState)
                .task {
                    // These must run on the main actor — hence .task, not init.
                    await MainActor.run {
                        DJIBridge.shared.registerApp(appState: appState)
                        router.setAppState(appState)

                        // Only start MQTT if a broker host is configured. In
                        // CI / unit-test builds the host may be empty and we
                        // don't want a connect loop spamming the log.
                        if !Config.mqttHost.isEmpty {
                            MQTTBridge.shared.start(router: router, appState: appState)
                        } else {
                            AppLogger.mqtt.warning("MAVIC_MQTT_HOST empty — MQTT bridge not started")
                        }

                        watchdog.start(appState: appState)
                    }
                }
        }
    }
}
