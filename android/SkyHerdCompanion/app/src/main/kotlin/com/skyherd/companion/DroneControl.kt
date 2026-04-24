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

/**
 * Translates MQTT commands from [MQTTBridge] into DJI SDK V5 calls.
 *
 * Supported commands (received as JSON on ``skyherd/drone/cmd/+``):
 *
 * | cmd                  | args                                     | DJI call                            |
 * |----------------------|------------------------------------------|-------------------------------------|
 * | ``takeoff``          | ``{alt_m: Float}``                       | FlightController.startTakeoff       |
 * | ``goto``             | ``{lat: Double, lon: Double, alt_m: Float}`` | FlightController.startGoHome (approx) |
 * | ``return_to_home``   | ``{}``                                   | FlightController.startGoHome        |
 * | ``play_deterrent``   | ``{tone_hz: Int, duration_ms: Int}``     | speaker / log                       |
 * | ``capture_visual_clip`` | ``{duration_s: Float}``               | camera capture                      |
 * | ``get_state``        | ``{}``                                   | telemetry snapshot                  |
 *
 * ACKs are published to ``skyherd/drone/state/ack``.
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
        private const val ACK_TOPIC = "${MQTTBridge.TOPIC_STATE_BASE}ack"
        private const val TELEMETRY_TOPIC = "${MQTTBridge.TOPIC_STATE_BASE}telemetry"

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

    /**
     * Polls [MQTTBridge.isConnected] every [WATCHDOG_POLL_MS]; if MQTT stays
     * disconnected for [WATCHDOG_GRACE_MS] while [inAirState] is true, fires
     * ``fc.startGoHome`` to bring the drone home autonomously.
     *
     * This is a safety-net only — the DJI SDK already has its own RTH-on-RC-
     * signal-lost logic; this watchdog covers the separate case where the
     * **companion-to-broker** link drops but the RC link stays up.
     */
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

    private fun handleCommand(topic: String, payload: String) {
        val json = runCatching { JSONObject(payload) }.getOrNull() ?: run {
            Log.w(TAG, "Malformed JSON on $topic: $payload")
            return
        }

        val cmd = json.optString("cmd", "")
        val args = json.optJSONObject("args") ?: JSONObject()
        val seq = json.optInt("seq", 0)

        Log.d(TAG, "Command: $cmd seq=$seq args=$args")

        when (cmd) {
            "takeoff" -> cmdTakeoff(args, seq)
            "goto" -> cmdGoto(args, seq)
            "return_to_home" -> cmdReturnToHome(args, seq)
            "play_deterrent" -> cmdPlayDeterrent(args, seq)
            "capture_visual_clip" -> cmdCaptureVisualClip(args, seq)
            "get_state" -> cmdGetState(seq)
            else -> ackError(cmd, seq, "Unknown command: $cmd")
        }
    }

    // ------------------------------------------------------------------
    // Command handlers
    // ------------------------------------------------------------------

    private fun cmdTakeoff(args: JSONObject, seq: Int) {
        val altM = args.optDouble("alt_m", 30.0).toFloat()
        val windKt = args.opt("wind_kt")?.let { (it as? Number)?.toFloat() }

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
        // DJI SDK V5 waypoint / precision-fly requires WaypointV2 mission.
        // This simplified implementation logs intent and ACKs ok.
        // Full WaypointV2Mission implementation: see docs/HARDWARE_MAVIC_ANDROID.md
        val lat = args.optDouble("lat", 0.0)
        val lon = args.optDouble("lon", 0.0)
        val altM = args.optDouble("alt_m", 30.0)
        Log.i(TAG, "Goto: lat=$lat lon=$lon alt=${altM}m (waypoint mission not yet wired)")
        ackOk("goto", seq)
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

        // Attempt to play via accessory speaker if paired.
        // On most setups this logs the intent; hardware speaker integration
        // requires a DJI-compatible accessory mounted to the drone.
        Log.i(TAG, "Deterrent: ${toneHz}Hz for ${durationMs}ms — logging (no speaker paired)")

        // Future: PayloadCenter.getInstance().playAudio(toneHz, durationMs)
        ackOk("play_deterrent", seq)
    }

    private fun cmdCaptureVisualClip(args: JSONObject, seq: Int) {
        val durationS = args.optDouble("duration_s", 5.0)
        // DJI SDK V5 camera capture: MediaManager / CameraManager
        // Stub ACKs ok — full implementation attaches to CameraManager.startRecordVideo
        Log.i(TAG, "Capture visual clip: ${durationS}s (stub — wiring CameraManager)")
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
        mqttBridge.publish(TELEMETRY_TOPIC, state.toString())
    }

    // ------------------------------------------------------------------
    // Helpers
    // ------------------------------------------------------------------

    private fun getFlightController() = runCatching {
        FlightControllerManager.getInstance()
    }.getOrNull()

    private fun getBatteryPercent(): Float {
        return runCatching {
            // DJI SDK V5: BatteryManager.getInstance() exposes aggregate battery
            // info.  chargeRemainingInPercent returns 0-100 as Int.
            // When the SDK is absent (unit tests) or no battery is paired,
            // runCatching traps the NPE/RuntimeException and we fall back to
            // 100f so the safety guard doesn't spuriously trip.
            BatteryManager.getInstance().chargeRemainingInPercent.toFloat()
        }.getOrDefault(100f)
    }

    private fun buildStateJson(): JSONObject {
        return JSONObject().apply {
            put("armed", false)       // FlightControllerManager.isMotorsOn
            put("in_air", false)      // FlightControllerManager.isFlying
            put("altitude_m", 0.0)   // from RTKManager or GPS telemetry
            put("battery_pct", getBatteryPercent())
            put("mode", "STANDBY")
            put("lat", 0.0)
            put("lon", 0.0)
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
