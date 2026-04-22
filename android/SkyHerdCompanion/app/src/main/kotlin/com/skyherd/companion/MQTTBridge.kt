package com.skyherd.companion

import android.content.Context
import android.util.Log
import org.eclipse.paho.android.service.MqttAndroidClient
import org.eclipse.paho.client.mqttv3.IMqttActionListener
import org.eclipse.paho.client.mqttv3.IMqttDeliveryToken
import org.eclipse.paho.client.mqttv3.IMqttToken
import org.eclipse.paho.client.mqttv3.MqttCallback
import org.eclipse.paho.client.mqttv3.MqttConnectOptions
import org.eclipse.paho.client.mqttv3.MqttMessage

/**
 * Paho MQTT client bridge connecting to the laptop's Mosquitto broker.
 *
 * Topic scheme:
 *   Inbound  (broker → app): ``skyherd/drone/cmd/#``
 *   Outbound (app → broker): ``skyherd/drone/state/#``
 *
 * Command messages arrive as JSON: ``{"cmd":"takeoff","args":{"alt_m":5.0},"seq":1}``
 * ACK messages are published as JSON: ``{"ack":"takeoff","result":"ok","seq":1}``
 *
 * The bridge simply receives raw bytes and forwards them to [DroneControl]
 * via the registered [commandListener].  DroneControl handles parsing and
 * executes the DJI SDK calls, then calls [publish] to send the ACK.
 */
class MQTTBridge(private val context: Context) {

    companion object {
        private const val TAG = "SkyHerdMQTT"
        const val TOPIC_CMD = "skyherd/drone/cmd/#"
        const val TOPIC_STATE_BASE = "skyherd/drone/state/"
        private const val CLIENT_ID = "skyherd-companion-android"
    }

    private var client: MqttAndroidClient? = null

    /** Called by DroneControl to handle inbound command JSON strings. */
    var commandListener: ((topic: String, payload: String) -> Unit)? = null

    /**
     * Connect to the MQTT broker at [brokerUrl] (e.g. ``tcp://192.168.1.100:1883``).
     *
     * [onResult] is invoked on the main thread with ``true`` on success,
     * ``false`` on failure.
     */
    fun connect(brokerUrl: String, onResult: (Boolean) -> Unit) {
        val mqttClient = MqttAndroidClient(context, brokerUrl, CLIENT_ID)
        client = mqttClient

        mqttClient.setCallback(object : MqttCallback {
            override fun connectionLost(cause: Throwable?) {
                Log.w(TAG, "MQTT connection lost: ${cause?.message}")
            }

            override fun messageArrived(topic: String, message: MqttMessage) {
                val payload = String(message.payload)
                Log.d(TAG, "MQTT ← [$topic] $payload")
                commandListener?.invoke(topic, payload)
            }

            override fun deliveryComplete(token: IMqttDeliveryToken?) {
                // no-op
            }
        })

        val options = MqttConnectOptions().apply {
            isCleanSession = true
            connectionTimeout = 10
            keepAliveInterval = 30
            isAutomaticReconnect = true
        }

        mqttClient.connect(options, null, object : IMqttActionListener {
            override fun onSuccess(asyncActionToken: IMqttToken?) {
                Log.i(TAG, "MQTT connected to $brokerUrl")
                subscribeToCommands()
                onResult(true)
            }

            override fun onFailure(asyncActionToken: IMqttToken?, exception: Throwable?) {
                Log.e(TAG, "MQTT connection failed: ${exception?.message}")
                onResult(false)
            }
        })
    }

    private fun subscribeToCommands() {
        client?.subscribe(TOPIC_CMD, 1, null, object : IMqttActionListener {
            override fun onSuccess(asyncActionToken: IMqttToken?) {
                Log.i(TAG, "Subscribed to $TOPIC_CMD")
            }
            override fun onFailure(asyncActionToken: IMqttToken?, exception: Throwable?) {
                Log.e(TAG, "Subscribe failed: ${exception?.message}")
            }
        })
    }

    /**
     * Publish a JSON payload to [topic].
     *
     * Used by DroneControl to send ACKs and telemetry back to the laptop.
     */
    fun publish(topic: String, payload: String) {
        val msg = MqttMessage(payload.toByteArray()).apply { qos = 1 }
        client?.publish(topic, msg)
        Log.d(TAG, "MQTT → [$topic] $payload")
    }

    fun disconnect() {
        try {
            client?.disconnect()
        } catch (e: Exception) {
            Log.w(TAG, "MQTT disconnect error: ${e.message}")
        }
    }

    val isConnected: Boolean
        get() = client?.isConnected == true
}
