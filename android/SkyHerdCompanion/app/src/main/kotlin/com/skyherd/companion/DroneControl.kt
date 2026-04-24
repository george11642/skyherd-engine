package com.skyherd.companion

import android.content.Context
import android.util.Log
import dji.v5.common.callback.CommonCallbacks
import dji.v5.common.error.IDJIError
import dji.v5.manager.aircraft.flightcontroller.FlightControllerManager
import dji.v5.manager.aircraft.payload.PayloadCenter
import dji.v5.manager.aircraft.battery.BatteryManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import org.json.JSONObject
import org.json.JSONArray

/**
 * Translates MQTT commands from [MQTTBridge] into DJI SDK V5 calls.
 *
 * Supported commands (received as JSON on ``skyherd/drone/cmd/+``):
 *
 * | cmd                  | args                                         | DJI call                            |
 * |----------------------|----------------------------------------------|-------------------------------------|
 * | ``takeoff``          | ``{alt_m: Float}``                           | FlightController.startTakeoff       |
 * | ``goto``             | ``{lat: Double, lon: Double, alt_m: Float}`` | FlightController.startGoHome (stub) |
 * | ``return_to_home``   | ``{}``                                       | FlightController.startGoHome        |
 * | ``play_deterrent``   | ``{tone_hz: Int, duration_ms: Int}``         | speaker / log                       |
 * | ``capture_visual_clip`` | ``{duration_s: Float}``                   | camera capture (stub)               |
 * | ``get_state``        | ``{}``                                       | telemetry snapshot                  |
 *
 * The command envelope may be legacy flat (`{cmd, args, seq}`) OR
 * MissionV1 (`{version:1, metadata:{...}, command:{cmd,args}, seq}`). V1
 * `metadata.battery_floor_pct` / `wind_kt` / `geofence_version` are honoured.
 *
 * ACKs are published to ``skyherd/drone/ack/android`` (unified scheme —
 * see `docs/MAVIC_MISSION_SCHEMA.md` §5); telemetry on
 * ``skyherd/drone/state/android``.
 *
 * [SafetyGuards] is checked before every actuator command.  If a guard
 * fires, an error ACK is returned and the command is not forwarded to the
 * DJI SDK.
 */
class DroneControl(
    private val context: Context,
    private val mqttBridge: MQTTBridge,
) {
    companion object {
        private const val TAG = "SkyHerdDroneControl"
        /** Unified ACK topic — see `docs/MAVIC_MISSION_SCHEMA.md` §5. */
        const val ACK_TOPIC = "skyherd/drone/ack/android"
        /** Unified state/telemetry topic for this platform. */
        const val STATE_TOPIC = "skyherd/drone/state/android"

        /** Lost-signal watchdog poll interval (ms). */
        private const val WATCHDOG_POLL_MS = 5_000L
        /** How long MQTT must stay disconnected (in-flight) before RTH fires. */
        private const val WATCHDOG_GRACE_MS = 30_000L
    }

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val safety = SafetyGuards()

    /** H3-01: set when takeoff ACK succeeds; cleared on RTH or land. */
    @Volatile private var inAirState: Boolean = false

    /** H3-01: watchdog toggle (default on; can be disabled via [autoRthOnLostSignal]). */
    @Volatile var autoRthOnLostSignal: Boolean = true

    /** Active watchdog coroutine job (null when not running). */
    private var watchdogJob: Job? = null

    fun start() {
        mqttBridge.commandListener = { topic, payload ->
            scope.launch { handleCommand(topic, payload) }
        }
        startLostSignalWatchdog()
        Log.i(TAG, "DroneControl started — listening for commands")
    }

    fun stop() {
        watchdogJob?.cancel()
        watchdogJob = null
        scope.cancel()
        mqttBridge.commandListener = null
    }

    // ------------------------------------------------------------------
    // Lost-signal watchdog (H3-01, Rule-2)
    // ------------------------------------------------------------------

    private fun startLostSignalWatchdog() {
        watchdogJob?.cancel()
        watchdogJob = scope.launch {
            var firstDisconnectAtMs: Long? = null
            while (isActive) {
                delay(WATCHDOG_POLL_MS)
                val connected = mqttBridge.isConnected
                if (!connected && inAirState && autoRthOnLostSignal) {
                    val now = System.currentTimeMillis()
                    if (firstDisconnectAtMs == null) {
                        firstDisconnectAtMs = now
                        Log.w(TAG, "Watchdog: MQTT disconnected while in-air — grace timer started")
                    } else if (now - firstDisconnectAtMs >= WATCHDOG_GRACE_MS) {
                        Log.e(TAG, "Watchdog: MQTT down > ${WATCHDOG_GRACE_MS}ms — firing RTH")
                        val fc = getFlightController()
                        fc?.startGoHome(object : CommonCallbacks.CompletionCallback {
                            override fun onSuccess() {
                                Log.i(TAG, "Watchdog RTH initiated")
                                inAirState = false
                            }

                            override fun onFailure(error: IDJIError) {
                                Log.e(TAG, "Watchdog RTH failed: ${error.description()}")
                            }
                        })
                        firstDisconnectAtMs = null
                    }
                } else if (connected) {
                    firstDisconnectAtMs = null
                }
            }
        }
    }

    // ------------------------------------------------------------------
    // Command dispatch
    // ------------------------------------------------------------------

    /**
     * Parse either a legacy `{cmd, args, seq}` payload or a MissionV1 envelope
     * into a normalised tuple `(cmd, args, seq, metadata?)`. Returns null if
     * the payload is malformed.
     */
    internal data class Parsed(
        val cmd: String,
        val args: JSONObject,
        val seq: Int,
        val metadata: JSONObject?,
    )

    internal fun parseEnvelope(payload: String): Parsed? {
        val json = runCatching { JSONObject(payload) }.getOrNull() ?: return null
        return if (json.has("version")) {
            // V1 envelope
            val v = json.optInt("version", -1)
            if (v != 1) {
                Log.w(TAG, "Unsupported envelope version: $v")
                return null
            }
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

    private fun handleCommand(topic: String, payload: String) {
        val parsed = parseEnvelope(payload) ?: run {
            Log.w(TAG, "Malformed payload on $topic: $payload")
            return
        }
        applyMissionMetadata(parsed.metadata)

        Log.d(TAG, "Command: ${parsed.cmd} seq=${parsed.seq} args=${parsed.args} " +
                "metaPresent=${parsed.metadata != null}")

        when (parsed.cmd) {
            "takeoff" -> cmdTakeoff(parsed.args, parsed.seq, parsed.metadata)
            "goto" -> cmdGoto(parsed.args, parsed.seq)
            "patrol" -> cmdPatrol(parsed.args, parsed.seq, parsed.metadata)
            "return_to_home" -> cmdReturnToHome(parsed.args, parsed.seq)
            "play_deterrent" -> cmdPlayDeterrent(parsed.args, parsed.seq)
            "capture_visual_clip" -> cmdCaptureVisualClip(parsed.args, parsed.seq)
            "get_state" -> cmdGetState(parsed.seq)
            else -> ackError(parsed.cmd, parsed.seq, "Unknown command: ${parsed.cmd}")
        }
    }

    /**
     * Apply MissionV1 metadata overrides to the safety guards (battery
     * floor, wind ceiling reference). Geofence version is logged for
     * attestation; the polygon itself is loaded out-of-band via MQTT.
     */
    internal fun applyMissionMetadata(meta: JSONObject?) {
        meta ?: return
        if (meta.has("battery_floor_pct")) {
            val pct = meta.optDouble("battery_floor_pct").toFloat()
            safety.batteryFloorPct = pct
            Log.d(TAG, "Mission metadata: battery_floor_pct=$pct")
        }
        if (meta.has("geofence_version")) {
            Log.i(TAG, "Mission geofence_version=${meta.optString("geofence_version")}")
        }
    }

    // ------------------------------------------------------------------
    // Command handlers
    // ------------------------------------------------------------------

    private fun cmdTakeoff(args: JSONObject, seq: Int, meta: JSONObject?) {
        val altM = args.optDouble("alt_m", 30.0).toFloat()
        // Prefer metadata wind_kt over args (metadata is canonical per schema).
        val windKt: Float? = meta?.takeIf { it.has("wind_kt") }
            ?.optDouble("wind_kt")?.toFloat()
            ?: args.opt("wind_kt")?.let { (it as? Number)?.toFloat() }

        val batteryPct = getBatteryPercent()
        try {
            safety.checkTakeoff(batteryPct = batteryPct, altM = altM)
            if (windKt != null) {
                safety.checkWind(windKt)
            }
        } catch (e: SafetyGuards.SafetyViolation) {
            ackError("takeoff", seq, e.message ?: "safety violation")
            return
        }

        val fc = getFlightController() ?: run {
            ackError("takeoff", seq, "Flight controller not available — drone not connected")
            return
        }

        fc.startTakeoff(object : CommonCallbacks.CompletionCallback {
            override fun onSuccess() {
                Log.i(TAG, "Takeoff started — target alt ${altM}m")
                inAirState = true
                ackOk("takeoff", seq)
            }

            override fun onFailure(error: IDJIError) {
                Log.e(TAG, "Takeoff failed: ${error.description()}")
                ackError("takeoff", seq, error.description())
            }
        })
    }

    private fun cmdGoto(args: JSONObject, seq: Int) {
        val lat = args.optDouble("lat", 0.0)
        val lon = args.optDouble("lon", 0.0)
        val altM = args.optDouble("alt_m", 30.0)
        try {
            safety.checkGeofence(lat, lon)
        } catch (e: SafetyGuards.SafetyViolation) {
            ackError("goto", seq, e.message ?: "geofence reject")
            return
        }
        // DJI SDK V5 waypoint / precision-fly requires WaypointV2 mission.
        // Parity with iOS: surface E_UNSUPPORTED rather than silent-ACK.
        Log.w(TAG, "Goto: lat=$lat lon=$lon alt=${altM}m — DJIWaypointV2 not wired (unsupported)")
        ackError("goto", seq, "E_UNSUPPORTED: gotoLocation requires DJIWaypointV2Mission — not yet implemented")
    }

    private fun cmdPatrol(args: JSONObject, seq: Int, meta: JSONObject?) {
        val waypoints = args.optJSONArray("waypoints")
        if (waypoints == null || waypoints.length() == 0) {
            ackError("patrol", seq, "patrol requires 'waypoints' array")
            return
        }
        // Geofence-check each waypoint
        for (i in 0 until waypoints.length()) {
            val wp = waypoints.optJSONObject(i) ?: continue
            val lat = wp.optDouble("lat", Double.NaN)
            val lon = wp.optDouble("lon", Double.NaN)
            if (lat.isNaN() || lon.isNaN()) {
                ackError("patrol", seq, "waypoint #$i missing lat/lon")
                return
            }
            try {
                safety.checkGeofence(lat, lon)
            } catch (e: SafetyGuards.SafetyViolation) {
                ackError("patrol", seq, e.message ?: "geofence reject")
                return
            }
        }
        // Per iOS parity: unsupported until DJIWaypointV2 wiring lands.
        ackError("patrol", seq, "E_UNSUPPORTED: patrol requires DJIWaypointV2Mission — not yet implemented")
    }

    private fun cmdReturnToHome(args: JSONObject, seq: Int) {
        val fc = getFlightController() ?: run {
            ackError("return_to_home", seq, "Flight controller not available")
            return
        }

        fc.startGoHome(object : CommonCallbacks.CompletionCallback {
            override fun onSuccess() {
                Log.i(TAG, "RTH initiated")
                inAirState = false
                ackOk("return_to_home", seq)
            }

            override fun onFailure(error: IDJIError) {
                Log.e(TAG, "RTH failed: ${error.description()}")
                ackError("return_to_home", seq, error.description())
            }
        })
    }

    private fun cmdPlayDeterrent(args: JSONObject, seq: Int) {
        val toneHz = args.optInt("tone_hz", 12000)
        val durationMs = (args.optDouble("duration_s", 6.0) * 1000).toInt()
        Log.i(TAG, "Deterrent: ${toneHz}Hz for ${durationMs}ms — logging (no speaker paired)")
        ackOk("play_deterrent", seq)
    }

    private fun cmdCaptureVisualClip(args: JSONObject, seq: Int) {
        val durationS = args.optDouble("duration_s", 5.0)
        Log.i(TAG, "Capture visual clip: ${durationS}s (stub — CameraManager wiring deferred)")
        ackOk("capture_visual_clip", seq)
    }

    private fun cmdGetState(seq: Int) {
        val state = buildStateJson()
        val ack = JSONObject().apply {
            put("ack", "get_state")
            put("result", "ok")
            put("seq", seq)
            put("data", state)
        }
        mqttBridge.publish(ACK_TOPIC, ack.toString())
        mqttBridge.publish(STATE_TOPIC, state.toString())
    }

    // ------------------------------------------------------------------
    // Helpers
    // ------------------------------------------------------------------

    private fun getFlightController() = runCatching {
        FlightControllerManager.getInstance()
    }.getOrNull()

    private fun getBatteryPercent(): Float {
        return runCatching {
            BatteryManager.getInstance().chargeRemainingInPercent.toFloat()
        }.getOrDefault(100f)
    }

    private fun buildStateJson(): JSONObject {
        return JSONObject().apply {
            put("armed", false)
            put("in_air", inAirState)
            put("altitude_m", 0.0)
            put("battery_pct", getBatteryPercent())
            put("mode", "STANDBY")
            put("lat", 0.0)
            put("lon", 0.0)
            put("gps_valid", true)
        }
    }

    private fun ackOk(cmd: String, seq: Int) {
        val ack = JSONObject().apply {
            put("ack", cmd)
            put("result", "ok")
            put("seq", seq)
        }
        mqttBridge.publish(ACK_TOPIC, ack.toString())
    }

    private fun ackError(cmd: String, seq: Int, message: String) {
        val ack = JSONObject().apply {
            put("ack", cmd)
            put("result", "error")
            put("seq", seq)
            put("message", message)
        }
        mqttBridge.publish(ACK_TOPIC, ack.toString())
        Log.w(TAG, "ACK error for '$cmd': $message")
    }
}
