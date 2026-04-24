package com.skyherd.companion

/**
 * Android-side safety guards mirroring ``src/skyherd/drone/safety.py``
 * and the iOS ``SafetyGuards.swift``.
 *
 * These are intentional mirrors — if a command slips past the Python layer
 * (e.g. direct MQTT injection), the Android side still refuses to actuate
 * an unsafe command.
 *
 * Parity contract (Phase 7.2):
 *  - Battery floor: **30 %** (reject at or below).  Configurable via
 *    [batteryFloorPct] for per-mission overrides from `MissionMetadata`.
 *  - Wind ceiling: **21 kt** (reject at or above).  Matches iOS `>=`
 *    semantics exactly — edge behaviour must agree across platforms.
 *  - Geofence: **ray-cast** polygon containment. Matches iOS algorithm
 *    for waypoints the bounding-box test would accept but the polygon
 *    would reject.
 *
 * Guards:
 *  - [checkTakeoff]    — battery (<= floor ⇒ reject) and altitude.
 *  - [checkWind]       — wind ceiling (>= ceiling ⇒ reject).
 *  - [checkGeofence]   — polygon ray-cast.  Falls back to permit-all when
 *                        no polygon is loaded (matches iOS).
 *
 * All guards raise [SafetyViolation] on failure so [DroneControl] can
 * respond with an error ACK without crashing.
 */
class SafetyGuards {

    class SafetyViolation(message: String) : Exception(message)

    companion object {
        // Match Python safety.py + iOS Config constants
        const val BATTERY_MIN_TAKEOFF_PCT = 30f
        const val BATTERY_RTH_THRESHOLD_PCT = 25f
        /**
         * Mavic Air 2 wind ceiling in knots. Reject condition is strictly
         * `speedKt >= WIND_CEILING_MAVIC_KT` — matches iOS `WindGuard.check`.
         */
        const val WIND_CEILING_MAVIC_KT = 21f
        const val MAX_ALTITUDE_M = 60f
    }

    /** Active geofence polygon (lat/lon vertex pairs).  `null` = permit all. */
    var polygon: List<Pair<Double, Double>>? = null

    // Legacy bounding-box fields retained for back-compat with callers that
    // set them directly; [checkGeofence] now uses [polygon] when loaded.
    var geofenceMinLat = 32.0
    var geofenceMaxLat = 37.0
    var geofenceMinLon = -109.0
    var geofenceMaxLon = -103.0

    /** Battery floor percent; may be overridden per-mission from metadata. */
    var batteryFloorPct: Float = BATTERY_MIN_TAKEOFF_PCT

    /** Wind ceiling (configurable by caller; default Mavic Air 2 spec). */
    var windCeilingKt: Float = WIND_CEILING_MAVIC_KT

    // ------------------------------------------------------------------
    // Geofence polygon loading
    // ------------------------------------------------------------------

    /**
     * Load (or replace) the active geofence polygon from `[[lat, lon], ...]`
     * pairs. Pairs of length != 2 are silently dropped (matches iOS).
     */
    fun loadPolygon(coordinates: List<List<Double>>) {
        polygon = coordinates
            .filter { it.size == 2 }
            .map { it[0] to it[1] }
    }

    // ------------------------------------------------------------------
    // Guard methods
    // ------------------------------------------------------------------

    /**
     * Validate takeoff preconditions.
     *
     * Reject condition is `batteryPct <= batteryFloorPct` — "at or below the
     * floor = unsafe", matching iOS/Python. A battery sitting exactly on the
     * floor has no spin-up margin.
     *
     * @param batteryPct  Current battery percentage (0–100).
     * @param altM        Requested takeoff altitude in metres.
     * @throws SafetyViolation if any condition is not met.
     */
    fun checkTakeoff(batteryPct: Float, altM: Float) {
        if (batteryPct <= batteryFloorPct) {
            throw SafetyViolation(
                "Battery at ${batteryPct.toInt()}% is at or below the floor of " +
                        "${batteryFloorPct.toInt()}%. Swap battery before launching."
            )
        }
        if (altM > MAX_ALTITUDE_M) {
            throw SafetyViolation(
                "Requested altitude ${altM}m exceeds hard ceiling ${MAX_ALTITUDE_M}m."
            )
        }
    }

    /**
     * Validate wind speed before takeoff.
     *
     * Reject condition is `windSpeedKt >= windCeilingKt` — "at or above the
     * ceiling = unsafe", matching iOS exactly.
     *
     * @param windSpeedKt  Wind speed in knots.
     * @throws SafetyViolation if wind meets or exceeds [windCeilingKt].
     */
    fun checkWind(windSpeedKt: Float) {
        if (windSpeedKt >= windCeilingKt) {
            throw SafetyViolation(
                "Wind at ${windSpeedKt}kt meets or exceeds platform ceiling " +
                        "${windCeilingKt}kt. Takeoff vetoed until wind subsides."
            )
        }
    }

    /**
     * Validate a waypoint against the configured ranch geofence.
     *
     * Uses polygon ray-casting when [polygon] is loaded (matches iOS
     * `GeofenceChecker.isInside`); otherwise falls back to the legacy
     * bounding-box test.  When no polygon AND the bounding-box defaults are
     * left in place the legacy test still permits most of New Mexico, so
     * callers should load a real polygon for production use.
     *
     * @param lat  Waypoint latitude.
     * @param lon  Waypoint longitude.
     * @throws SafetyViolation if the point is outside the configured fence.
     */
    fun checkGeofence(lat: Double, lon: Double) {
        polygon?.let { poly ->
            if (poly.size >= 3 && !isInside(lat, lon, poly)) {
                throw SafetyViolation(
                    "Waypoint ($lat, $lon) is outside the ranch geofence polygon."
                )
            }
            if (poly.size >= 3) return  // polygon check passed
        }
        // Legacy bounding-box fallback (permit-mostly for dev).
        if (lat < geofenceMinLat || lat > geofenceMaxLat ||
            lon < geofenceMinLon || lon > geofenceMaxLon
        ) {
            throw SafetyViolation(
                "Waypoint ($lat, $lon) is outside the ranch geofence " +
                        "[$geofenceMinLat–$geofenceMaxLat, $geofenceMinLon–$geofenceMaxLon]."
            )
        }
    }

    /**
     * Ray-casting point-in-polygon. Mirror of iOS `GeofenceChecker.isInside`
     * — treats polygon vertices as (lat, lon) pairs with the ray travelling
     * in the +lon direction from the test point.
     */
    fun isInside(lat: Double, lon: Double, poly: List<Pair<Double, Double>>): Boolean {
        val n = poly.size
        if (n < 3) return false
        var inside = false
        var j = n - 1
        for (i in 0 until n) {
            val yi = poly[i].first; val xi = poly[i].second
            val yj = poly[j].first; val xj = poly[j].second
            val intersect = ((yi > lat) != (yj > lat)) &&
                    (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi)
            if (intersect) inside = !inside
            j = i
        }
        return inside
    }

    /**
     * Check in-flight battery; return true if RTH should be triggered.
     */
    fun shouldRth(batteryPct: Float): Boolean = batteryPct <= BATTERY_RTH_THRESHOLD_PCT
}
