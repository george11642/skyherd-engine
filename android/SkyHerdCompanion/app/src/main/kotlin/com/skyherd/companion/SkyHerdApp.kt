package com.skyherd.companion

import android.app.Application
import android.util.Log
import dji.v5.common.error.IDJIError
import dji.v5.common.register.DJISDKInitEvent
import dji.v5.manager.SDKManager
import dji.v5.manager.interfaces.SDKManagerCallback

/**
 * Application subclass that registers the DJI SDK on startup.
 *
 * The SDK requires registration before any FlightController or camera
 * operations are permitted.  Registration result is logged; the
 * MainActivity observes [SkyHerdApp.sdkRegistered] to update the UI.
 */
class SkyHerdApp : Application() {

    companion object {
        private const val TAG = "SkyHerdApp"

        /** Becomes true once DJI SDK registration succeeds. */
        @Volatile
        var sdkRegistered: Boolean = false
            private set
    }

    override fun onCreate() {
        super.onCreate()
        registerDjiSdk()
    }

    private fun registerDjiSdk() {
        SDKManager.getInstance().init(this, object : SDKManagerCallback {
            override fun onRegisterSuccess() {
                sdkRegistered = true
                Log.i(TAG, "DJI SDK registered successfully")
            }

            override fun onRegisterFailure(error: IDJIError) {
                sdkRegistered = false
                Log.e(TAG, "DJI SDK registration failed: ${error.description()}")
            }

            override fun onProductDisconnect(productId: Int) {
                Log.w(TAG, "DJI product disconnected: productId=$productId")
            }

            override fun onProductConnect(productId: Int) {
                Log.i(TAG, "DJI product connected: productId=$productId")
            }

            override fun onProductChanged(productId: Int) {
                Log.i(TAG, "DJI product changed: productId=$productId")
            }

            override fun onInitProcess(event: DJISDKInitEvent, totalProcess: Int) {
                Log.d(TAG, "DJI SDK init: event=$event total=$totalProcess")
            }

            override fun onDatabaseDownloadProgress(current: Long, total: Long) {
                Log.d(TAG, "DJI DB download: $current/$total bytes")
            }
        })
    }
}
