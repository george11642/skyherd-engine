package com.skyherd.companion

import android.os.Bundle
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import com.skyherd.companion.databinding.ActivityMainBinding
import dji.v5.manager.SDKManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/**
 * Main entry point for SkyHerdCompanion.
 *
 * Responsibilities:
 *  - Shows DJI SDK registration and drone connection status in a simple UI.
 *  - Starts [MQTTBridge] once the MQTT broker URL is configured.
 *  - Starts [DroneControl] which wires MQTT commands to DJI SDK calls.
 *
 * Configuration (set in the `.env` on the laptop, or via the in-app UI):
 *  - MQTT broker URL:  default ``tcp://192.168.1.100:1883``
 *  - All other settings are read from the MQTT bridge.
 */
class MainActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "SkyHerdMain"
        private const val POLL_INTERVAL_MS = 2_000L
    }

    private lateinit var binding: ActivityMainBinding
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())

    private lateinit var mqttBridge: MQTTBridge
    private lateinit var droneControl: DroneControl

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        mqttBridge = MQTTBridge(applicationContext)
        droneControl = DroneControl(applicationContext, mqttBridge)

        binding.btnConnect.setOnClickListener {
            val brokerUrl = binding.etBrokerUrl.text.toString().ifBlank {
                "tcp://192.168.1.100:1883"
            }
            startBridge(brokerUrl)
        }

        // Poll SDK + drone status every 2 s and update UI
        scope.launch {
            while (true) {
                updateStatus()
                delay(POLL_INTERVAL_MS)
            }
        }
    }

    private fun startBridge(brokerUrl: String) {
        Log.i(TAG, "Starting MQTT bridge → $brokerUrl")
        binding.tvStatus.text = "Connecting to MQTT: $brokerUrl"
        mqttBridge.connect(brokerUrl) { connected ->
            runOnUiThread {
                if (connected) {
                    binding.tvStatus.text = "MQTT: $brokerUrl connected"
                    droneControl.start()
                } else {
                    binding.tvStatus.text = "MQTT connection failed — check broker URL"
                }
            }
        }
    }

    private fun updateStatus() {
        val sdkOk = SkyHerdApp.sdkRegistered
        val product = runCatching { SDKManager.getInstance().product }.getOrNull()
        val sn = product?.let {
            runCatching { it.serialNumber?.value ?: "–" }.getOrDefault("–")
        } ?: "–"

        binding.tvSdkStatus.text = if (sdkOk) "DJI SDK: registered" else "DJI SDK: not registered"
        binding.tvDroneSerial.text = if (sn != "–") "Connected to DJI: $sn" else "Drone: not connected"
    }

    override fun onDestroy() {
        super.onDestroy()
        scope.cancel()
        mqttBridge.disconnect()
    }
}
