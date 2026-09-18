package com.soundsense.drone.mqtt

import android.content.Context
import android.util.Log
import org.eclipse.paho.client.mqttv3.*
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import java.util.UUID
import java.util.concurrent.Executors

class MqttManager(private val context: Context) {

    companion object {
        private const val TAG = "MqttManager"
    }

    private var client: MqttAsyncClient? = null
    private val executor = Executors.newSingleThreadExecutor()

    private val _connectionState = MutableStateFlow(ConnectionState.DISCONNECTED)
    val connectionState: StateFlow<ConnectionState> = _connectionState

    private val _lastMessage = MutableStateFlow<Pair<String, String>?>(null)
    val lastMessage: StateFlow<Pair<String, String>?> = _lastMessage

    var onMessageReceived: ((topic: String, payload: String) -> Unit)? = null
    private var topicCallbacks = mutableMapOf<String, (topic: String, payload: String) -> Unit>()

    enum class ConnectionState {
        DISCONNECTED, CONNECTING, CONNECTED, ERROR
    }

    fun connect(server: String, port: Int, username: String = "", password: String = "") {
        executor.execute {
            try {
                _connectionState.value = ConnectionState.CONNECTING

                val clientId = "soundsense_${UUID.randomUUID().toString().substring(0, 8)}"
                val url = "tcp://$server:$port"

                client = MqttAsyncClient(url, clientId, MemoryPersistence())

                client?.setCallback(object : MqttCallbackExtended {
                    override fun connectComplete(reconnect: Boolean, serverURI: String?) {
                        Log.d(TAG, "Connected to $serverURI")
                        _connectionState.value = ConnectionState.CONNECTED
                        try {
                            client?.subscribe("detected/sound/#", 1)
                            topicCallbacks.keys.forEach { topic ->
                                client?.subscribe(topic, 1)
                            }
                        } catch (e: MqttException) {
                            Log.e(TAG, "Subscribe error", e)
                        }
                    }

                    override fun connectionLost(cause: Throwable?) {
                        Log.w(TAG, "Connection lost", cause)
                        _connectionState.value = ConnectionState.DISCONNECTED
                    }

                    override fun messageArrived(topic: String?, message: MqttMessage?) {
                        topic ?: return
                        message ?: return
                        val payload = String(message.payload)
                        Log.d(TAG, "Message on $topic: ${payload.take(100)}")
                        _lastMessage.value = Pair(topic, payload)
                        onMessageReceived?.invoke(topic, payload)
                        topicCallbacks[topic]?.invoke(topic, payload)
                    }

                    override fun deliveryComplete(token: IMqttDeliveryToken?) {}
                })

                val options = MqttConnectOptions().apply {
                    isCleanSession = true
                    keepAliveInterval = 60
                    connectionTimeout = 10
                    maxReconnectDelay = 3000
                    isAutomaticReconnect = true
                    if (username.isNotBlank()) {
                        userName = username
                        this.password = password.toCharArray()
                    }
                }

                client?.connect(options, null, object : IMqttActionListener {
                    override fun onSuccess(token: IMqttToken?) {
                        Log.d(TAG, "Connect onSuccess")
                    }

                    override fun onFailure(token: IMqttToken?, exception: Throwable?) {
                        Log.e(TAG, "Connect FAILED: ${exception?.message}", exception)
                        _connectionState.value = ConnectionState.ERROR
                    }
                })

            } catch (e: Exception) {
                Log.e(TAG, "Connect error", e)
                _connectionState.value = ConnectionState.ERROR
            }
        }
    }

    fun disconnect() {
        executor.execute {
            try {
                client?.apply {
                    if (isConnected) disconnect()
                    close()
                }
                client = null
                _connectionState.value = ConnectionState.DISCONNECTED
            } catch (e: Exception) {
                Log.e(TAG, "Disconnect error", e)
            }
        }
    }

    fun subscribe(topic: String, qos: Int = 1, callback: ((topic: String, payload: String) -> Unit)? = null) {
        callback?.let { topicCallbacks[topic] = it }
        executor.execute {
            try {
                if (client?.isConnected == true) {
                    client?.subscribe(topic, qos)
                    Log.d(TAG, "Subscribed to $topic")
                }
            } catch (e: MqttException) {
                Log.e(TAG, "Subscribe error: ${e.message}")
            }
        }
    }

    fun publish(topic: String, payload: String, qos: Int = 1): Boolean {
        return try {
            if (client?.isConnected == true) {
                val message = MqttMessage(payload.toByteArray()).apply {
                    this.qos = qos
                    isRetained = false
                }
                client?.publish(topic, message)
                true
            } else {
                Log.w(TAG, "Not connected, cannot publish")
                false
            }
        } catch (e: MqttException) {
            Log.e(TAG, "Publish error", e)
            false
        }
    }

    fun publishDetection(detection: DetectionData): Boolean {
        val json = GsonHolder.gson.toJson(detection)
        return publish("detected/sound/", json)
    }

    fun isConnected(): Boolean = client?.isConnected == true
}

object GsonHolder {
    val gson = com.google.gson.Gson()
}

data class DetectionData(
    val name: String,
    val detected_sound: String,
    val confidence: Double,
    val datetime: String,
    val lat: Double? = null,
    val long: Double? = null,
    val direction: Double? = null,
    val tilted_degree: Double? = null
)
