import SwiftUI

/// Main developer-testing UI.
///
/// Shows live DJI registration state, WebSocket server state, MQTT state,
/// last received command, and manual arm / takeoff / RTH buttons for bench testing.
struct ContentView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        NavigationStack {
            List {
                statusSection
                lastCommandSection
                droneStateSection
                if appState.lastError != nil {
                    errorSection
                }
                devButtonsSection
            }
            .navigationTitle("SkyHerd Companion")
            .navigationBarTitleDisplayMode(.inline)
        }
    }

    // MARK: - Sections

    private var statusSection: some View {
        Section("Connection Status") {
            labeledRow("DJI SDK", value: appState.djiStatus,
                       color: statusColor(appState.djiStatus, good: "Registered"))
            labeledRow("WebSocket", value: appState.wsStatus,
                       color: statusColor(appState.wsStatus, good: "Listening"))
            labeledRow("MQTT", value: appState.mqttStatus,
                       color: statusColor(appState.mqttStatus, good: "Connected"))
        }
    }

    private var lastCommandSection: some View {
        Section("Last Command") {
            if appState.lastCmdId == "--" {
                Text("None received yet")
                    .foregroundStyle(.secondary)
            } else {
                labeledRow("Command", value: appState.lastCmdId)
                if let ts = appState.lastCmdTs {
                    labeledRow("At", value: ts.formatted(date: .omitted, time: .standard))
                }
            }
        }
    }

    private var droneStateSection: some View {
        Section("Drone State") {
            let s = appState.droneState
            labeledRow("Armed", value: s.armed ? "Yes" : "No",
                       color: s.armed ? .orange : .primary)
            labeledRow("In Air", value: s.inAir ? "Yes" : "No",
                       color: s.inAir ? .blue : .primary)
            labeledRow("Altitude", value: String(format: "%.1f m", s.altitudeM))
            labeledRow("Battery", value: String(format: "%.0f%%", s.batteryPct),
                       color: s.batteryPct < 25 ? .red : .primary)
            labeledRow("Mode", value: s.mode)
            labeledRow("Position",
                       value: String(format: "%.5f, %.5f", s.lat, s.lon))
        }
    }

    private var errorSection: some View {
        Section("Last Error") {
            Text(appState.lastError ?? "")
                .foregroundStyle(.red)
                .font(.caption)
        }
    }

    private var devButtonsSection: some View {
        Section("Dev Controls (bench testing)") {
            Button("Manual Takeoff (5 m)") {
                Task { await devTakeoff() }
            }
            .tint(.blue)

            Button("Return to Home") {
                Task { await devRTH() }
            }
            .tint(.orange)

            Button("Arm (DJI motors)") {
                Task { await devArm() }
            }
            .tint(.green)
        }
    }

    // MARK: - Dev actions (bypass WebSocket, call DJIBridge directly)

    private func devTakeoff() async {
        do {
            try await DJIBridge.shared.takeoff()
        } catch {
            await MainActor.run { appState.lastError = error.localizedDescription }
        }
    }

    private func devRTH() async {
        do {
            try await DJIBridge.shared.returnToHome()
        } catch {
            await MainActor.run { appState.lastError = error.localizedDescription }
        }
    }

    private func devArm() async {
        // DJI SDK V5 does not expose a standalone arm command — motors start on takeoff.
        // This button is a no-op placeholder that documents the limitation.
        await MainActor.run {
            appState.lastError =
                "DJI SDK V5 does not expose a standalone arm command; use Takeoff instead."
        }
    }

    // MARK: - Helpers

    private func labeledRow(_ label: String, value: String, color: Color = .primary) -> some View {
        HStack {
            Text(label).foregroundStyle(.secondary)
            Spacer()
            Text(value).foregroundStyle(color).multilineTextAlignment(.trailing)
        }
    }

    private func statusColor(_ value: String, good: String) -> Color {
        if value.contains(good) { return .green }
        if value.lowercased().contains("error") || value.lowercased().contains("fail") {
            return .red
        }
        return .orange
    }
}

#Preview {
    ContentView()
        .environmentObject(AppState())
}
