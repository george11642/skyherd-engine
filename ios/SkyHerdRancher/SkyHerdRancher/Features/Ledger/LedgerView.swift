import SwiftUI

struct LedgerView: View {
    @Environment(AppState.self) private var appState

    var body: some View {
        NavigationStack {
            VStack(spacing: SkyHerdSpacing.md) {
                Text("Ledger — coming soon")
                    .font(SkyHerdTypography.heading)
                    .foregroundStyle(Color.skhText0)
                Text("Connection: \(appState.connectionState.description)")
                    .font(SkyHerdTypography.caption)
                    .foregroundStyle(Color.skhText2)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(Color.skhBg0)
            .navigationTitle("Ledger")
            .navigationBarTitleDisplayMode(.inline)
        }
    }
}
