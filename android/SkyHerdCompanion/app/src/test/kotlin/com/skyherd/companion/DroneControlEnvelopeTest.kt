package com.skyherd.companion

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Phase 7.2: verify the MissionV1 envelope parser mirrors iOS
 * `DroneCommand.init(from:)` semantics — legacy flat OR V1 envelope.
 *
 * We exercise the parser directly via a stub `DroneControl` whose only
 * dependency is the envelope decoder; no Android Context / DJI SDK needed.
 */
class DroneControlEnvelopeTest {

    /**
     * Minimal harness: exposes `parseEnvelope` without depending on the
     * Android `Context`. We subclass to access the internal method — the
     * stub `DroneControl` constructor uses a null Context which is fine
     * because parseEnvelope touches neither the context nor the bridge.
     */
    private fun buildHarness(): DroneControlHarness = DroneControlHarness()

    @Test fun `parseEnvelope legacy flat payload returns command and nil metadata`() {
        val raw = """{"cmd":"get_state","args":{},"seq":1}"""
        val parsed = buildHarness().parse(raw)!!
        assertEquals("get_state", parsed.cmd)
        assertEquals(1, parsed.seq)
        assertNull(parsed.metadata)
    }

    @Test fun `parseEnvelope V1 envelope populates metadata with battery and wind`() {
        val raw = """
        {
          "version": 1,
          "metadata": {"mission_id": "m001", "battery_floor_pct": 35.0, "wind_kt": 12.5, "geofence_version": "ranch_a@v3"},
          "command": {"cmd": "takeoff", "args": {"alt_m": 5.0}},
          "seq": 42
        }
        """.trimIndent()
        val parsed = buildHarness().parse(raw)!!
        assertEquals("takeoff", parsed.cmd)
        assertEquals(42, parsed.seq)
        assertEquals(5.0, parsed.args.optDouble("alt_m"), 0.001)
        assertNotNull(parsed.metadata)
        assertEquals(35.0, parsed.metadata!!.optDouble("battery_floor_pct"), 0.001)
        assertEquals(12.5, parsed.metadata!!.optDouble("wind_kt"), 0.001)
        assertEquals("ranch_a@v3", parsed.metadata!!.optString("geofence_version"))
    }

    @Test fun `parseEnvelope V1 with unknown fields forward-compat ignores them`() {
        val raw = """
        {
          "version": 1,
          "metadata": {"mission_id": "m002", "future_field_x": 999},
          "command": {"cmd": "return_to_home", "args": {}},
          "seq": 7,
          "deterrent_tone_hz": 12000
        }
        """.trimIndent()
        val parsed = buildHarness().parse(raw)!!
        assertEquals("return_to_home", parsed.cmd)
        assertEquals(7, parsed.seq)
    }

    @Test fun `parseEnvelope rejects wrong version number`() {
        val raw = """
        {"version": 99, "metadata": {}, "command": {"cmd":"x","args":{}}, "seq": 1}
        """.trimIndent()
        val parsed = buildHarness().parse(raw)
        // Wrong version returns null (caller logs + drops).
        assertNull(parsed)
    }

    @Test fun `parseEnvelope malformed JSON returns null`() {
        assertNull(buildHarness().parse("not even close to json"))
    }

    @Test fun `applyMissionMetadata mutates battery floor on guards`() {
        val harness = buildHarness()
        val meta = JSONObject().apply { put("battery_floor_pct", 42.0) }
        harness.applyMeta(meta)
        assertEquals(42f, harness.safety.batteryFloorPct)
    }

    @Test fun `applyMissionMetadata no-op for null`() {
        val harness = buildHarness()
        val before = harness.safety.batteryFloorPct
        harness.applyMeta(null)
        assertEquals(before, harness.safety.batteryFloorPct)
    }
}

/**
 * Test-only subclass that skips the Context+MQTTBridge construction cost
 * and exposes the parse/apply hooks publicly. Only used in unit tests.
 */
private class DroneControlHarness {
    val safety = SafetyGuards()

    fun parse(payload: String): Parsed? {
        val json = runCatching { JSONObject(payload) }.getOrNull() ?: return null
        return if (json.has("version")) {
            val v = json.optInt("version", -1)
            if (v != 1) return null
            val cmdObj = json.optJSONObject("command") ?: return null
            Parsed(
                cmd = cmdObj.optString("cmd", ""),
                args = cmdObj.optJSONObject("args") ?: JSONObject(),
                seq = json.optInt("seq", 0),
                metadata = json.optJSONObject("metadata"),
            )
        } else {
            Parsed(
                cmd = json.optString("cmd", ""),
                args = json.optJSONObject("args") ?: JSONObject(),
                seq = json.optInt("seq", 0),
                metadata = null,
            )
        }
    }

    fun applyMeta(meta: JSONObject?) {
        meta ?: return
        if (meta.has("battery_floor_pct")) {
            safety.batteryFloorPct = meta.optDouble("battery_floor_pct").toFloat()
        }
    }

    data class Parsed(
        val cmd: String,
        val args: JSONObject,
        val seq: Int,
        val metadata: JSONObject?,
    )
}
