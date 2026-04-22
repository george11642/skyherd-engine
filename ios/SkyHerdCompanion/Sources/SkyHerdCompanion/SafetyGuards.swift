import Foundation
import CoreLocation

// MARK: - SafetyGuardError

public enum SafetyGuardError: Error, LocalizedError {
    case geofenceReject(String)
    case batteryLow(Double)
    case windCeiling(Double)
    case altitudeClamped(Double)

    public var errorDescription: String? {
        switch self {
        case .geofenceReject(let msg): return "\(DroneErrorCode.geofenceReject.rawValue): \(msg)"
        case .batteryLow(let pct):
            return "\(DroneErrorCode.batteryLow.rawValue): battery \(Int(pct))% below floor \(Int(Config.batteryFloorPct))%"
        case .windCeiling(let kt):
            return "\(DroneErrorCode.windCeiling.rawValue): wind \(String(format: "%.1f", kt)) kt exceeds ceiling \(Config.windCeilingKt) kt"
        case .altitudeClamped(let alt):
            return "Altitude clamped to \(alt) m (max \(Config.maxAltitudeM) m)"
        }
    }
}

// MARK: - GeofenceChecker

/// Validates that a set of geographic points lies within the configured ranch polygon.
/// The polygon is loaded from MQTT on connect; defaults to `nil` (all pass) until loaded.
public final class GeofenceChecker {
    /// Geofence polygon vertices in order.  `nil` means no fence loaded yet — all pass.
    public private(set) var polygon: [CLLocationCoordinate2D]?

    public init(polygon: [CLLocationCoordinate2D]? = nil) {
        self.polygon = polygon
    }

    /// Load (or replace) the geofence polygon from a flat array of [lat, lon] pairs.
    /// - Parameter coordinates: Array of `[lat, lon]` pairs, e.g. `[[36.1, -105.2], ...]`.
    public func load(coordinates: [[Double]]) {
        polygon = coordinates.compactMap { pair in
            guard pair.count == 2 else { return nil }
            return CLLocationCoordinate2D(latitude: pair[0], longitude: pair[1])
        }
        AppLogger.safety.info("Geofence loaded: \(self.polygon?.count ?? 0) vertices")
    }

    /// Check that every point is inside the polygon.  Throws if any is outside.
    public func checkPoints(_ points: [CLLocationCoordinate2D]) throws {
        guard let poly = polygon, poly.count >= 3 else {
            // No fence loaded — permit all
            AppLogger.safety.debug("Geofence: no polygon loaded, permitting all")
            return
        }
        for point in points {
            if !isInside(point: point, polygon: poly) {
                throw SafetyGuardError.geofenceReject(
                    "Point (\(point.latitude),\(point.longitude)) is outside geofence"
                )
            }
        }
    }

    // MARK: Ray-casting point-in-polygon

    /// Returns `true` if `point` is inside `polygon` using the ray-casting algorithm.
    public func isInside(point: CLLocationCoordinate2D, polygon: [CLLocationCoordinate2D]) -> Bool {
        let n = polygon.count
        guard n >= 3 else { return false }
        var inside = false
        var j = n - 1
        for i in 0..<n {
            let xi = polygon[i].longitude, yi = polygon[i].latitude
            let xj = polygon[j].longitude, yj = polygon[j].latitude
            let intersect = (yi > point.latitude) != (yj > point.latitude) &&
                (point.longitude < (xj - xi) * (point.latitude - yi) / (yj - yi) + xi)
            if intersect { inside = !inside }
            j = i
        }
        return inside
    }
}

// MARK: - BatteryGuard

/// Denies takeoff when battery is below ``Config.batteryFloorPct``.
public struct BatteryGuard {
    public let floorPct: Double

    public init(floorPct: Double = Config.batteryFloorPct) {
        self.floorPct = floorPct
    }

    /// Throws ``SafetyGuardError.batteryLow`` if `pct` is below the floor.
    public func checkTakeoff(pct: Double) throws {
        if pct < floorPct {
            AppLogger.safety.warning("Battery guard: \(pct)% < floor \(self.floorPct)%")
            throw SafetyGuardError.batteryLow(pct)
        }
    }
}

// MARK: - WindGuard

/// Denies takeoff when wind speed exceeds ``Config.windCeilingKt``.
public struct WindGuard {
    public let ceilingKt: Double

    public init(ceilingKt: Double = Config.windCeilingKt) {
        self.ceilingKt = ceilingKt
    }

    /// Throws ``SafetyGuardError.windCeiling`` if `speedKt` exceeds the ceiling.
    public func check(speedKt: Double) throws {
        if speedKt >= ceilingKt {
            AppLogger.safety.warning("Wind guard: \(speedKt) kt >= ceiling \(self.ceilingKt) kt")
            throw SafetyGuardError.windCeiling(speedKt)
        }
    }
}

// MARK: - AltitudeClamp

/// Clamps requested altitude to ``Config.maxAltitudeM``.
public struct AltitudeClamp {
    public let maxM: Double

    public init(maxM: Double = Config.maxAltitudeM) {
        self.maxM = maxM
    }

    /// Returns the clamped altitude.  Logs a warning if clamping occurred.
    public func clamp(_ alt: Double) -> Double {
        if alt > maxM {
            AppLogger.safety.warning("Altitude clamped: \(alt) → \(self.maxM) m")
            return maxM
        }
        return alt
    }
}
