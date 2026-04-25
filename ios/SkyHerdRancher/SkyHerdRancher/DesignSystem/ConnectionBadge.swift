import SwiftUI

/// Pill badge showing SSE connection state.
/// Shared between Live and Map tabs.
/// Long-press opens a debug sheet showing backend URL and sim seed.
struct ConnectionBadge: View {
    let state: SSEConnectionState
    @State private var showDebug = false

    var body: some View {
        HStack(spacing: SkyHerdSpacing.xs) {
            Circle()
                .fill(dotColor)
                .frame(width: 7, height: 7)
            Text(label)
                .font(SkyHerdTypography.caption2)
                .foregroundStyle(dotColor)
        }
        .padding(.horizontal, SkyHerdSpacing.sm)
        .padding(.vertical, 4)
        .background(dotColor.opacity(0.12), in: Capsule())
        .overlay(Capsule().strokeBorder(dotColor.opacity(0.25), lineWidth: 1))
        .accessibilityLabel("Connection status: \(label)")
        .onLongPressGesture {
            showDebug = true
        }
        .sheet(isPresented: $showDebug) {
            ConnectionDebugSheet()
                .presentationDetents([.medium])
                .presentationDragIndicator(.visible)
        }
    }

    private var label: String {
        switch state {
        case .disconnected:           return "Offline"
        case .connecting:             return "Connecting…"
        case .connected:              return "Live"
        case .reconnecting(let n):
            let remaining = min(n * n, 30)
            return "Reconnecting in \(remaining)s"
        case .failed:                 return "Error"
        }
    }

    private var dotColor: Color {
        switch state {
        case .connected:              return .skhOk
        case .connecting:             return .skhWarn
        case .reconnecting:           return .skhWarn
        case .disconnected, .failed:  return .skhDanger
        }
    }
}

// MARK: - Connection Debug Sheet

/// Judge-facing sheet: shows backend URL, UserDefaults key, seed info.
/// Inject a custom backend URL by writing to UserDefaults key "skyherd.baseURL".
struct ConnectionDebugSheet: View {
    @Environment(\.dismiss) private var dismiss

    @State private var editedURL: String = UserDefaults.standard.string(forKey: "skyherd.baseURL")
        ?? Configuration.defaultBaseURL.absoluteString

    @State private var saved = false

    var body: some View {
        NavigationStack {
            ZStack {
                Color.skhBg0.ignoresSafeArea()
                VStack(alignment: .leading, spacing: SkyHerdSpacing.lg) {

                    // Backend URL
                    VStack(alignment: .leading, spacing: SkyHerdSpacing.sm) {
                        Text("BACKEND URL")
                            .font(SkyHerdTypography.caption2)
                            .foregroundStyle(Color.skhText2)
                            .tracking(1.2)

                        TextField("http://localhost:8000", text: $editedURL)
                            .font(SkyHerdTypography.mono)
                            .foregroundStyle(Color.skhText0)
                            .autocapitalization(.none)
                            .disableAutocorrection(true)
                            .keyboardType(.URL)
                            .padding(SkyHerdSpacing.sm)
                            .background(Color.skhBg2, in: RoundedRectangle(cornerRadius: 8))
                            .overlay(
                                RoundedRectangle(cornerRadius: 8)
                                    .strokeBorder(Color.skhLine, lineWidth: 1)
                            )

                        Text("UserDefaults key: skyherd.baseURL  ·  Restart app to apply")
                            .font(SkyHerdTypography.caption2)
                            .foregroundStyle(Color.skhText2)
                    }
                    .padding(SkyHerdSpacing.md)
                    .background(Color.skhBg1, in: RoundedRectangle(cornerRadius: 10))

                    // Sim seed info
                    VStack(alignment: .leading, spacing: SkyHerdSpacing.sm) {
                        Text("SIM CONFIG")
                            .font(SkyHerdTypography.caption2)
                            .foregroundStyle(Color.skhText2)
                            .tracking(1.2)

                        HStack {
                            Text("Seed")
                                .font(SkyHerdTypography.caption)
                                .foregroundStyle(Color.skhText2)
                            Spacer()
                            Text("42")
                                .font(SkyHerdTypography.mono)
                                .foregroundStyle(Color.skhText0)
                        }
                        Divider().overlay(Color.skhLine)
                        HStack {
                            Text("Active URL")
                                .font(SkyHerdTypography.caption)
                                .foregroundStyle(Color.skhText2)
                            Spacer()
                            Text(Configuration.defaultBaseURL.absoluteString)
                                .font(SkyHerdTypography.mono)
                                .foregroundStyle(Color.skhSky)
                                .lineLimit(1)
                                .minimumScaleFactor(0.7)
                        }
                    }
                    .padding(SkyHerdSpacing.md)
                    .background(Color.skhBg1, in: RoundedRectangle(cornerRadius: 10))

                    // Save button
                    Button {
                        UserDefaults.standard.set(editedURL, forKey: "skyherd.baseURL")
                        saved = true
                        Task {
                            try? await Task.sleep(nanoseconds: 1_500_000_000)
                            dismiss()
                        }
                    } label: {
                        HStack {
                            Spacer()
                            Label(saved ? "Saved — restart app" : "Save URL",
                                  systemImage: saved ? "checkmark.circle.fill" : "arrow.right.circle")
                                .font(SkyHerdTypography.body)
                                .foregroundStyle(saved ? Color.skhOk : Color.skhSky)
                            Spacer()
                        }
                        .padding(.vertical, SkyHerdSpacing.sm)
                        .background(
                            (saved ? Color.skhOk : Color.skhSky).opacity(0.12),
                            in: RoundedRectangle(cornerRadius: 10)
                        )
                    }
                    .buttonStyle(.plain)

                    Spacer()
                }
                .padding(SkyHerdSpacing.md)
            }
            .navigationTitle("Debug Info")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") { dismiss() }
                        .tint(Color.skhSky)
                }
            }
        }
    }
}
