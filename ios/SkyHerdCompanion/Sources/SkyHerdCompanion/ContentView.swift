import SwiftUI

/// Main developer-testing UI.
///
/// Shows live DJI registration state, MQTT state, lost-signal watchdog state,
/// last received command, and manual takeoff / RTH buttons for bench testing.
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
            labeledRow("MQTT", value: appState.mqttStatus,
                       color: statusColor(appState.mqttStatus, good: "Connected"))
            labeledRow("Watchdog", value: appState.watchdogStatus,
                       color: statusColor(appState.watchdogStatus, good: "Running"))
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
                       color: s.batteryPct <= Config.batteryFloorPct ? .red : .primary)
            labeledRow("GPS Fix", value: s.gpsValid ? "Valid" : "Invalid",
                       color: s.gpsValid ? .primary : .red)
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
        // Arm button removed (Phase 7.2): DJI SDK V5 has no standalone arm —
        // motors spin up on startTakeoff. Showing a no-op button was misleading.
        Section("Dev Controls (bench testing)") {
            Button("Manual Takeoff (5 m)") {
                Task { await devTakeoff() }
            }
            .tint(.blue)

            Button("Return to Home") {
                Task { await devRTH() }
            }
            .tint(.orange)
        }
    }

    // MARK: - Dev actions (bypass MQTT, call DJIBridge directly)

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
