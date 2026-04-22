import XCTest
import CoreLocation
@testable import SkyHerdCompanion

final class SafetyGuardTests: XCTestCase {

    // MARK: - GeofenceChecker

    private func makeSquareFence() -> GeofenceChecker {
        // A 1-degree-square polygon centred roughly on northern New Mexico
        let fence = GeofenceChecker()
        fence.load(coordinates: [
            [36.0, -106.0],  // SW
            [37.0, -106.0],  // NW
            [37.0, -105.0],  // NE
            [36.0, -105.0],  // SE
        ])
        return fence
    }

    func test_geofence_point_inside_passes() throws {
        let fence = makeSquareFence()
        let inside = CLLocationCoordinate2D(latitude: 36.5, longitude: -105.5)
        XCTAssertNoThrow(try fence.checkPoints([inside]))
    }

    func test_geofence_point_outside_throws() {
        let fence = makeSquareFence()
        let outside = CLLocationCoordinate2D(latitude: 38.0, longitude: -104.0)
        XCTAssertThrowsError(try fence.checkPoints([outside])) { error in
            guard case SafetyGuardError.geofenceReject = error else {
                XCTFail("Expected geofenceReject, got \(error)")
                return
            }
        }
    }

    func test_geofence_multiple_points_one_outside_throws() {
        let fence = makeSquareFence()
        let inside = CLLocationCoordinate2D(latitude: 36.5, longitude: -105.5)
        let outside = CLLocationCoordinate2D(latitude: 39.0, longitude: -107.0)
        XCTAssertThrowsError(try fence.checkPoints([inside, outside]))
    }

    func test_geofence_no_polygon_permits_all() throws {
        let fence = GeofenceChecker()   // no polygon loaded
        let anyPoint = CLLocationCoordinate2D(latitude: 0, longitude: 0)
        XCTAssertNoThrow(try fence.checkPoints([anyPoint]))
    }

    func test_geofence_load_from_pairs() {
        let fence = GeofenceChecker()
        fence.load(coordinates: [[36.0, -106.0], [37.0, -106.0], [37.0, -105.0], [36.0, -105.0]])
        XCTAssertEqual(fence.polygon?.count, 4)
    }

    func test_geofence_load_skips_invalid_pairs() {
        let fence = GeofenceChecker()
        fence.load(coordinates: [[36.0, -106.0], [37.0], [37.0, -105.0]])  // middle pair has 1 coord
        XCTAssertEqual(fence.polygon?.count, 2)
    }

    func test_ray_cast_corner_case_triangle() {
        // A right triangle: (0,0), (1,0), (0,1)
        let fence = GeofenceChecker()
        let poly: [CLLocationCoordinate2D] = [
            .init(latitude: 0, longitude: 0),
            .init(latitude: 1, longitude: 0),
            .init(latitude: 0, longitude: 1),
        ]
        XCTAssertTrue(fence.isInside(
            point: .init(latitude: 0.1, longitude: 0.1),
            polygon: poly
        ))
        XCTAssertFalse(fence.isInside(
            point: .init(latitude: 2, longitude: 2),
            polygon: poly
        ))
    }

    // MARK: - BatteryGuard

    func test_battery_above_floor_passes() throws {
        let guard_ = BatteryGuard(floorPct: 25.0)
        XCTAssertNoThrow(try guard_.checkTakeoff(pct: 50.0))
        XCTAssertNoThrow(try guard_.checkTakeoff(pct: 25.1))
    }

    func test_battery_at_floor_throws() {
        let guard_ = BatteryGuard(floorPct: 25.0)
        XCTAssertThrowsError(try guard_.checkTakeoff(pct: 25.0)) { error in
            guard case SafetyGuardError.batteryLow(let pct) = error else {
                XCTFail("Expected batteryLow")
                return
            }
            XCTAssertEqual(pct, 25.0, accuracy: 0.001)
        }
    }

    func test_battery_below_floor_throws() {
        let guard_ = BatteryGuard(floorPct: 25.0)
        XCTAssertThrowsError(try guard_.checkTakeoff(pct: 10.0)) { error in
            guard case SafetyGuardError.batteryLow = error else {
                XCTFail("Expected batteryLow")
                return
            }
        }
    }

    func test_battery_100_pct_passes() throws {
        let guard_ = BatteryGuard()
        XCTAssertNoThrow(try guard_.checkTakeoff(pct: 100.0))
    }

    // MARK: - WindGuard

    func test_wind_below_ceiling_passes() throws {
        let guard_ = WindGuard(ceilingKt: 21.0)
        XCTAssertNoThrow(try guard_.check(speedKt: 0.0))
        XCTAssertNoThrow(try guard_.check(speedKt: 20.9))
    }

    func test_wind_at_ceiling_throws() {
        let guard_ = WindGuard(ceilingKt: 21.0)
        XCTAssertThrowsError(try guard_.check(speedKt: 21.0)) { error in
            guard case SafetyGuardError.windCeiling(let kt) = error else {
                XCTFail("Expected windCeiling")
                return
            }
            XCTAssertEqual(kt, 21.0, accuracy: 0.001)
        }
    }

    func test_wind_above_ceiling_throws() {
        let guard_ = WindGuard(ceilingKt: 21.0)
        XCTAssertThrowsError(try guard_.check(speedKt: 35.0))
    }

    // MARK: - AltitudeClamp

    func test_altitude_below_max_unchanged() {
        let clamp = AltitudeClamp(maxM: 60.0)
        XCTAssertEqual(clamp.clamp(30.0), 30.0, accuracy: 0.001)
        XCTAssertEqual(clamp.clamp(59.9), 59.9, accuracy: 0.001)
    }

    func test_altitude_exactly_at_max_unchanged() {
        let clamp = AltitudeClamp(maxM: 60.0)
        XCTAssertEqual(clamp.clamp(60.0), 60.0, accuracy: 0.001)
    }

    func test_altitude_above_max_clamped() {
        let clamp = AltitudeClamp(maxM: 60.0)
        XCTAssertEqual(clamp.clamp(120.0), 60.0, accuracy: 0.001)
        XCTAssertEqual(clamp.clamp(61.0), 60.0, accuracy: 0.001)
    }

    func test_altitude_zero_passes() {
        let clamp = AltitudeClamp(maxM: 60.0)
        XCTAssertEqual(clamp.clamp(0.0), 0.0, accuracy: 0.001)
    }
}
