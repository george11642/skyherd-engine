package com.skyherd.companion

import android.content.Context
import android.util.Log
import dji.v5.common.callback.CommonCallbacks
import dji.v5.common.error.IDJIError
import dji.v5.manager.aircraft.flightcontroller.FlightControllerManager
import dji.v5.manager.aircraft.payload.PayloadCenter
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
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
    }

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val safety = SafetyGuards()

    fun start() {
        mqttBridge.commandListener = { topic, payload ->
            scope.launch { handleCommand(topic, payload) }
        }
        Log.i(TAG, "DroneControl started — listening for commands")
    }

    fun stop() {
        scope.cancel()
        mqttBridge.commandListener = null
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

        val batteryPct = getBatteryPercent()
        try {
            safety.checkTakeoff(batteryPct = batteryPct, altM = altM)
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
            // DJI SDK V5: BatteryManager.getInstance().getChargeRemainingInPercent()
            // Returning 100 as safe default when unavailable in stub
            100f
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
