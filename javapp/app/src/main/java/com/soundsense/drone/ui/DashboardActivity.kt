package com.soundsense.drone.ui

import android.os.Bundle
import android.widget.ArrayAdapter
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.soundsense.drone.databinding.ActivityDashboardBinding
import com.soundsense.drone.mqtt.GsonHolder
import com.soundsense.drone.mqtt.MqttManager
import com.google.gson.JsonObject
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

class DashboardActivity : AppCompatActivity() {

    private lateinit var binding: ActivityDashboardBinding
    private var mqttManager: MqttManager? = null
    private val detections = mutableListOf<DetectionEntry>()
    private val devices = mutableSetOf<String>()
    private val soundTypes = mutableSetOf<String>()

    data class DetectionEntry(
        val time: String,
        val device: String,
        val sound: String,
        val confidence: String,
        val lat: String,
        val lon: String,
        val direction: String,
        val tilt: String
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)

        mqttManager = MqttManager(this)

        binding.btnDashConnect.setOnClickListener { connectFromDashboard() }
        binding.btnClear.setOnClickListener { clearDetections() }

        observeMessages()
    }

    private fun connectFromDashboard() {
        val server = binding.dashServer.text.toString().trim()
        val port = binding.dashPort.text.toString().trim().toIntOrNull() ?: 1883
        val user = binding.dashUser.text.toString().trim()
        val pass = binding.dashPass.text.toString().trim()

        if (server.isEmpty()) {
            Toast.makeText(this, "Enter server", Toast.LENGTH_SHORT).show()
            return
        }

        mqttManager?.connect(server, port, user, pass)
        observeMqttState()
    }

    private fun observeMqttState() {
        lifecycleScope.launch {
            mqttManager?.connectionState?.collectLatest { state ->
                runOnUiThread {
                    val text = when (state) {
                        MqttManager.ConnectionState.CONNECTED -> "Connected"
                        MqttManager.ConnectionState.CONNECTING -> "Connecting..."
                        else -> "Disconnected"
                    }
                    binding.dashConnStatus.text = text
                }
            }
        }
    }

    private fun observeMessages() {
        lifecycleScope.launch {
            mqttManager?.lastMessage?.collectLatest { msg ->
                msg?.let { (topic, payload) ->
                    runOnUiThread { processMessage(topic, payload) }
                }
            }
        }
    }

    private fun processMessage(topic: String, payload: String) {
        try {
            val json = GsonHolder.gson.fromJson(payload, JsonObject::class.java)
            val device = json.get("name")?.asString ?: "unknown"
            val sound = json.get("detected_sound")?.asString ?: "unknown"
            val confidence = json.get("confidence")?.asDouble ?: 0.0
            val time = json.get("datetime")?.asString ?: SimpleDateFormat("HH:mm:ss", Locale.US).format(Date())
            val lat = json.get("lat")?.let { if (it.isJsonNull) "-" else String.format("%.5f", it.asDouble) } ?: "-"
            val lon = json.get("long")?.let { if (it.isJsonNull) "-" else String.format("%.5f", it.asDouble) } ?: "-"
            val dir = json.get("direction")?.let { if (it.isJsonNull) "-" else "${it.asDouble}deg" } ?: "-"
            val tilt = json.get("tilted_degree")?.let { if (it.isJsonNull) "-" else "${it.asDouble}deg" } ?: "-"

            devices.add(device)
            soundTypes.add(sound)

            val entry = DetectionEntry(time, device, sound, String.format("%.1f%%", confidence * 100), lat, lon, dir, tilt)
            detections.add(0, entry)

            binding.totalDetections.text = detections.size.toString()
            binding.uniqueDevices.text = devices.size.toString()
            binding.uniqueSounds.text = soundTypes.size.toString()

            updateTable()
            updateLog(topic, payload)
        } catch (e: Exception) {
            updateLog(topic, payload)
        }
    }

    private fun updateTable() {
        val rows = detections.take(100).mapIndexed { i, d ->
            "${i + 1}|${d.time}|${d.device}|${d.sound}|${d.confidence}|${d.lat}|${d.lon}|${d.direction}|${d.tilt}"
        }
        binding.tableText.text = "# | Time | Device | Sound | Conf | Lat | Lon | Dir | Tilt\n" +
            "-----|------|--------|-------|------|-----|-----|-----|-----\n" +
            rows.joinToString("\n")
    }

    private fun updateLog(topic: String, payload: String) {
        val time = SimpleDateFormat("HH:mm:ss", Locale.US).format(Date())
        val shortPayload = payload.take(120)
        binding.realtimeLog.append("[$time] $topic: $shortPayload\n")

        val lines = binding.realtimeLog.text.lines()
        if (lines.size > 50) {
            binding.realtimeLog.text = lines.takeLast(50).joinToString("\n")
        }
    }

    private fun clearDetections() {
        detections.clear()
        devices.clear()
        soundTypes.clear()
        binding.totalDetections.text = "0"
        binding.uniqueDevices.text = "0"
        binding.uniqueSounds.text = "0"
        binding.tableText.text = "No detections yet."
        binding.realtimeLog.text = ""
    }
}
