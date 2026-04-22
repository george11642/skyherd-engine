package com.skyherd.companion

/**
 * Android-side safety guards mirroring ``src/skyherd/drone/safety.py``.
 *
 * These are intentional mirrors — if a command slips past the Python layer
 * (e.g. direct MQTT injection), the Android side still refuses to actuate
 * an unsafe command.
 *
 * Guards:
 *  - [checkTakeoff]    — battery and altitude limits.
 *  - [checkWind]       — wind ceiling (caller supplies wind speed from
 *                        weather telemetry).
 *  - [checkGeofence]   — bounding box check against configured ranch bounds.
 *
 * All guards raise [SafetyViolation] on failure so [DroneControl] can
 * respond with an error ACK without crashing.
 */
class SafetyGuards {

    class SafetyViolation(message: String) : Exception(message)

    companion object {
        // Match Python safety.py constants
        const val BATTERY_MIN_TAKEOFF_PCT = 30f
        const val BATTERY_RTH_THRESHOLD_PCT = 25f
        const val WIND_CEILING_MAVIC_KT = 21f
        const val MAX_ALTITUDE_M = 60f
    }

    // Geofence: loose NM ranch bounding box (degrees).
    // Real deployment: load from ranch config pushed over MQTT on connect.
    var geofenceMinLat = 32.0
    var geofenceMaxLat = 37.0
    var geofenceMinLon = -109.0
    var geofenceMaxLon = -103.0

    // Wind ceiling (configurable by caller; default Mavic Air 2 spec)
    var windCeilingKt = WIND_CEILING_MAVIC_KT

    // ------------------------------------------------------------------
    // Guard methods
    // ------------------------------------------------------------------

    /**
     * Validate takeoff preconditions.
     *
     * @param batteryPct  Current battery percentage (0–100).
     * @param altM        Requested takeoff altitude in metres.
     * @throws SafetyViolation if any condition is not met.
     */
    fun checkTakeoff(batteryPct: Float, altM: Float) {
        if (batteryPct < BATTERY_MIN_TAKEOFF_PCT) {
            throw SafetyViolation(
                "Battery at ${batteryPct.toInt()}% — minimum for takeoff is " +
                        "${BATTERY_MIN_TAKEOFF_PCT.toInt()}%. Swap battery before launching."
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
     * @param windSpeedKt  Wind speed in knots (from weather sensor or MQTT payload).
     * @throws SafetyViolation if wind exceeds [windCeilingKt].
     */
    fun checkWind(windSpeedKt: Float) {
        if (windSpeedKt > windCeilingKt) {
            throw SafetyViolation(
                "Wind at ${windSpeedKt}kt exceeds platform ceiling ${windCeilingKt}kt. " +
                        "Takeoff vetoed until wind subsides."
            )
        }
    }

    /**
     * Validate a waypoint against the configured ranch geofence bounding box.
     *
     * @param lat  Waypoint latitude.
     * @param lon  Waypoint longitude.
     * @throws SafetyViolation if the point is outside the configured bounding box.
     */
    fun checkGeofence(lat: Double, lon: Double) {
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
     * Check in-flight battery; return true if RTH should be triggered.
     */
    fun shouldRth(batteryPct: Float): Boolean = batteryPct <= BATTERY_RTH_THRESHOLD_PCT
}
