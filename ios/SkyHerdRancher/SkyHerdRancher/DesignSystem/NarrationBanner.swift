import SwiftUI

/// Animated narration banner that slides in from top when a scenario becomes active.
/// Displayed on the Live tab; shared component in DesignSystem for Wave C reuse.
struct NarrationBanner: View {
    let scenarioName: String
    let isVisible: Bool

    var body: some View {
        HStack(spacing: SkyHerdSpacing.sm) {
            Image(systemName: scenarioIcon(for: scenarioName))
                .foregroundStyle(Color.skhWarn)
                .font(.system(size: 18, weight: .semibold))

            VStack(alignment: .leading, spacing: 2) {
                Text("SCENARIO ACTIVE")
                    .font(SkyHerdTypography.caption2)
                    .foregroundStyle(Color.skhText2)
                    .tracking(1.2)
                Text(scenarioDisplayName(for: scenarioName))
                    .font(SkyHerdTypography.heading)
                    .foregroundStyle(Color.skhText0)
            }

            Spacer()
        }
        .padding(.horizontal, SkyHerdSpacing.md)
        .padding(.vertical, SkyHerdSpacing.sm)
        .background(
            RoundedRectangle(cornerRadius: 10)
                .fill(Color.skhBg2)
                .overlay(
                    RoundedRectangle(cornerRadius: 10)
                        .strokeBorder(Color.skhWarn.opacity(0.35), lineWidth: 1)
                )
        )
        .padding(.horizontal, SkyHerdSpacing.md)
        .offset(y: isVisible ? 0 : -80)
        .opacity(isVisible ? 1 : 0)
        .animation(.spring(response: 0.4, dampingFraction: 0.7), value: isVisible)
    }

    private func scenarioIcon(for name: String) -> String {
        switch name {
        case "coyote", "cross_ranch_coyote": return "pawprint.fill"
        case "sick_cow":                     return "heart.fill"
        case "water_drop":                   return "drop.fill"
        case "calving":                      return "heart.fill"
        case "storm":                        return "cloud.bolt.fill"
        case "wildfire":                     return "flame.fill"
        case "rustling":                     return "exclamationmark.triangle.fill"
        default:                             return "bolt.fill"
        }
    }

    private func scenarioDisplayName(for name: String) -> String {
        switch name {
        case "coyote":             return "Coyote at Fence"
        case "sick_cow":           return "Sick Cow"
        case "water_drop":         return "Water Tank Drop"
        case "calving":            return "Calving"
        case "storm":              return "Storm Incoming"
        case "wildfire":           return "Wildfire Alert"
        case "rustling":           return "Rustling Detected"
        case "cross_ranch_coyote": return "Cross-Ranch Coyote"
        default:                   return name.replacingOccurrences(of: "_", with: " ").capitalized
        }
    }
}
