import SwiftUI

// MARK: - CowShape
// Filled circle — Wave B will scale by canvas cell size

struct CowShape: Shape {
    func path(in rect: CGRect) -> Path {
        Path(ellipseIn: rect)
    }
}

// MARK: - DroneShape
// Equilateral triangle pointing up (heading applied by caller via .rotationEffect)

struct DroneShape: Shape {
    func path(in rect: CGRect) -> Path {
        var path = Path()
        let cx = rect.midX
        path.move(to: CGPoint(x: cx, y: rect.minY))
        path.addLine(to: CGPoint(x: rect.maxX, y: rect.maxY))
        path.addLine(to: CGPoint(x: rect.minX, y: rect.maxY))
        path.closeSubpath()
        return path
    }
}

// MARK: - PredatorShape
// X mark (two crossing lines)

struct PredatorShape: Shape {
    func path(in rect: CGRect) -> Path {
        var path = Path()
        path.move(to: CGPoint(x: rect.minX, y: rect.minY))
        path.addLine(to: CGPoint(x: rect.maxX, y: rect.maxY))
        path.move(to: CGPoint(x: rect.maxX, y: rect.minY))
        path.addLine(to: CGPoint(x: rect.minX, y: rect.maxY))
        return path
    }
}

// MARK: - Health ring overlay (thin stroke circle, color by state)

struct HealthRingShape: Shape {
    func path(in rect: CGRect) -> Path {
        Path(ellipseIn: rect.insetBy(dx: 1, dy: 1))
    }
}

// MARK: - Cow color by state helper

extension Color {
    static func cowColor(for state: String?) -> Color {
        switch state {
        case "sick":           return .skhCowSick
        case "calving", "labor": return .skhCowCalving
        case "grazing", "resting", "walking":
            return .skhCowHealthy
        default:
            return .skhCowWatch
        }
    }
}
