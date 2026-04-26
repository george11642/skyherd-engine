import SwiftUI

// MARK: - SkyHerd typography tokens
// Uses SF Pro Rounded for friendly ranch tone

enum SkyHerdTypography {
    static let title:   Font = .system(.largeTitle, design: .rounded).bold()
    static let heading: Font = .system(.headline, design: .rounded)
    static let body:    Font = .system(.body, design: .rounded)
    static let caption: Font = .system(.caption, design: .rounded)
    static let caption2: Font = .system(.caption2, design: .rounded)

    // Monospace: hashes, session IDs, JSON payloads
    static let mono:    Font = .system(.caption, design: .monospaced)
    static let monoSm:  Font = .system(.caption2, design: .monospaced)
}
