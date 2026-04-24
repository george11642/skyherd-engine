package com.skyherd.companion

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Phase 7.2: Android parity with iOS SafetyGuardTests.
 *
 * Each assertion below has an exact twin in
 * `ios/SkyHerdCompanion/Tests/.../SafetyGuardTests.swift` — if one moves, the
 * other must move with it.
 */
class SafetyGuardsTest {

    // ---------- Geofence (ray-cast) ----------

    private fun makeSquareFence(): SafetyGuards {
        val guards = SafetyGuards()
        guards.loadPolygon(listOf(
            listOf(36.0, -106.0),  // SW
            listOf(37.0, -106.0),  // NW
            listOf(37.0, -105.0),  // NE
            listOf(36.0, -105.0),  // SE
        ))
        return guards
    }

    @Test fun `geofence point inside passes`() {
        val g = makeSquareFence()
        g.checkGeofence(36.5, -105.5)  // would throw on failure
    }

    @Test fun `geofence point outside throws`() {
        val g = makeSquareFence()
        assertThrows(SafetyGuards.SafetyViolation::class.java) {
            g.checkGeofence(38.0, -104.0)
        }
    }

    @Test fun `geofence load skips invalid pairs`() {
        val g = SafetyGuards()
        g.loadPolygon(listOf(
            listOf(36.0, -106.0),
            listOf(37.0),               // invalid: only 1 coord
            listOf(37.0, -105.0),
        ))
        assertEquals(2, g.polygon?.size)
    }

    @Test fun `ray cast corner case triangle`() {
        val g = SafetyGuards()
        val poly = listOf(0.0 to 0.0, 1.0 to 0.0, 0.0 to 1.0)
        assertTrue(g.isInside(0.1, 0.1, poly))
        assertFalse(g.isInside(2.0, 2.0, poly))
    }

    @Test fun `geofence ray-cast accepts concave-polygon-interior that bbox-only would also accept`() {
        val g = SafetyGuards()
        // An L-shape: bbox is 0..2 x 0..2 but the (1.5, 1.5) cell is OUTSIDE
        // the polygon.  Bounding-box would accept; ray-cast rejects.
        g.loadPolygon(listOf(
            listOf(0.0, 0.0), listOf(0.0, 2.0), listOf(1.0, 2.0),
            listOf(1.0, 1.0), listOf(2.0, 1.0), listOf(2.0, 0.0),
        ))
        // (1.5, 1.5) is in the concave notch — outside the polygon.
        assertThrows(SafetyGuards.SafetyViolation::class.java) {
            g.checkGeofence(1.5, 1.5)
        }
        // (0.5, 0.5) is inside the L.
        g.checkGeofence(0.5, 0.5)
    }

    // ---------- BatteryGuard ----------

    @Test fun `battery above floor passes`() {
        val g = SafetyGuards()
        g.batteryFloorPct = 30f
        g.checkTakeoff(50f, 30f)
        g.checkTakeoff(30.1f, 30f)
    }

    @Test fun `battery at floor throws`() {
        val g = SafetyGuards()
        g.batteryFloorPct = 30f
        assertThrows(SafetyGuards.SafetyViolation::class.java) {
            g.checkTakeoff(30f, 30f)
        }
    }

    @Test fun `battery below floor throws`() {
        val g = SafetyGuards()
        g.batteryFloorPct = 30f
        assertThrows(SafetyGuards.SafetyViolation::class.java) {
            g.checkTakeoff(10f, 30f)
        }
    }

    @Test fun `default battery floor is 30 percent — parity with iOS and Python`() {
        val g = SafetyGuards()
        assertEquals(30f, g.batteryFloorPct)
    }

    // ---------- WindGuard ----------

    @Test fun `wind below ceiling passes`() {
        val g = SafetyGuards()
        g.checkWind(0f)
        g.checkWind(20.9f)
    }

    @Test fun `wind at ceiling throws — parity with iOS`() {
        val g = SafetyGuards()
        // 21.0 exactly must throw (was permissive `>` before Phase 7.2).
        assertThrows(SafetyGuards.SafetyViolation::class.java) {
            g.checkWind(21.0f)
        }
    }

    @Test fun `wind above ceiling throws`() {
        val g = SafetyGuards()
        assertThrows(SafetyGuards.SafetyViolation::class.java) {
            g.checkWind(35f)
        }
    }

    // ---------- RTH threshold ----------

    @Test fun `shouldRth true at or below threshold`() {
        val g = SafetyGuards()
        assertTrue(g.shouldRth(25f))
        assertTrue(g.shouldRth(10f))
        assertFalse(g.shouldRth(25.1f))
    }

    // ---------- Altitude ceiling ----------

    @Test fun `altitude above max throws takeoff`() {
        val g = SafetyGuards()
        assertThrows(SafetyGuards.SafetyViolation::class.java) {
            g.checkTakeoff(100f, 120f)
        }
    }

    @Test fun `altitude at max passes takeoff`() {
        val g = SafetyGuards()
        g.checkTakeoff(100f, SafetyGuards.MAX_ALTITUDE_M)
    }
}
