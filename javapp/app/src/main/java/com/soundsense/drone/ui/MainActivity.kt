package com.soundsense.drone.ui

import android.Manifest
import android.content.ComponentName
import android.content.Intent
import android.content.ServiceConnection
import android.content.pm.PackageManager
import android.os.Bundle
import android.os.IBinder
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.soundsense.drone.audio.AudioDetectionService
import com.soundsense.drone.databinding.ActivityMainBinding
import com.soundsense.drone.mqtt.MqttManager
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

    companion object {
        private const val PERMISSION_REQUEST = 100
    }

    private lateinit var binding: ActivityMainBinding
    private var mqttManager: MqttManager? = null
    private var detectionService: AudioDetectionService? = null
    private var isBound = false
    private var isListening = false

    private val serviceConnection = object : ServiceConnection {
        override fun onServiceConnected(name: ComponentName?, binder: IBinder?) {
            val localBinder = binder as AudioDetectionService.DetectionBinder
            detectionService = localBinder.getService()
            isBound = true
            detectionService?.onDetection = { soundType, confidence ->
                runOnUiThread { showDetection(soundType, confidence) }
            }
            detectionService?.onAudioLevel = { level ->
                runOnUiThread { binding.audioLevel.progress = (level * 100).toInt() }
            }
            mqttManager?.let { detectionService?.setMqttManager(it) }
        }

        override fun onServiceDisconnected(name: ComponentName?) {
            detectionService = null
            isBound = false
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        mqttManager = MqttManager(this)
        observeMqttState()

        checkPermissions()

        binding.btnConnect.setOnClickListener { connectMqtt() }
        binding.btnDetect.setOnClickListener { toggleDetection() }
        binding.btnDashboard.setOnClickListener {
            startActivity(Intent(this, DashboardActivity::class.java))
        }

        loadSavedConfig()

        Intent(this, AudioDetectionService::class.java).also { intent ->
            startForegroundService(intent)
            bindService(intent, serviceConnection, BIND_AUTO_CREATE)
        }
    }

    private fun observeMqttState() {
        lifecycleScope.launch {
            mqttManager?.connectionState?.collectLatest { state ->
                runOnUiThread {
                    when (state) {
                        MqttManager.ConnectionState.CONNECTED -> {
                            binding.connStatus.text = "Connected"
                            binding.connStatus.setTextColor(ContextCompat.getColor(this@MainActivity, android.R.color.holo_green_dark))
                            binding.btnConnect.text = "Disconnect"
                        }
                        MqttManager.ConnectionState.CONNECTING -> {
                            binding.connStatus.text = "Connecting..."
                            binding.connStatus.setTextColor(ContextCompat.getColor(this@MainActivity, android.R.color.holo_orange_dark))
                            binding.btnConnect.text = "Cancel"
                        }
                        MqttManager.ConnectionState.ERROR -> {
                            binding.connStatus.text = "Connection failed - check IP & credentials"
                            binding.connStatus.setTextColor(ContextCompat.getColor(this@MainActivity, android.R.color.holo_red_dark))
                            binding.btnConnect.text = "Connect"
                        }
                        else -> {
                            binding.connStatus.text = "Disconnected"
                            binding.connStatus.setTextColor(ContextCompat.getColor(this@MainActivity, android.R.color.holo_red_dark))
                            binding.btnConnect.text = "Connect"
                        }
                    }
                }
            }
        }

        lifecycleScope.launch {
            mqttManager?.lastMessage?.collectLatest { msg ->
                msg?.let {
                    runOnUiThread {
                        binding.lastMessage.text = "[${it.first}] ${it.second.take(100)}"
                    }
                }
            }
        }
    }

    private fun connectMqtt() {
        val server = binding.mqttServer.text.toString().trim()
        val port = binding.mqttPort.text.toString().trim().toIntOrNull() ?: 1883
        val user = binding.mqttUser.text.toString().trim()
        val pass = binding.mqttPass.text.toString().trim()
        val name = binding.deviceName.text.toString().trim().ifBlank { "android-sensor" }

        if (server.isEmpty()) {
            Toast.makeText(this, "Enter MQTT server", Toast.LENGTH_SHORT).show()
            return
        }

        if (mqttManager?.isConnected() == true) {
            mqttManager?.disconnect()
        } else if (mqttManager?.connectionState?.value == MqttManager.ConnectionState.CONNECTING) {
            mqttManager?.disconnect()
        } else {
            mqttManager?.connect(server, port, user, pass)
            saveConfig(server, port, user, name)
        }
    }

    private fun toggleDetection() {
        if (!hasAudioPermission()) {
            checkPermissions()
            return
        }

        if (isListening) {
            detectionService?.stopDetection()
            isListening = false
            binding.btnDetect.text = "START"
            binding.detectStatus.text = "Stopped"
            binding.audioLevel.progress = 0
        } else {
            detectionService?.startDetection()
            isListening = true
            binding.btnDetect.text = "STOP"
            binding.detectStatus.text = "Listening..."
        }
    }

    private fun showDetection(soundType: String, confidence: Double) {
        binding.detectionResult.text = soundType
        binding.detectionConfidence.text = String.format("%.1f%%", confidence * 100)
        binding.detectStatus.text = "Detected: $soundType (${(confidence * 100).toInt()}%)"

        val time = java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.US).format(java.util.Date())
        val entry = "$time - $soundType (${(confidence * 100).toInt()}%)\n"
        binding.detectionLog.append(entry)

        val logLines = binding.detectionLog.text.lines()
        if (logLines.size > 30) {
            binding.detectionLog.text = logLines.takeLast(30).joinToString("\n")
        }
    }

    private fun saveConfig(server: String, port: Int, user: String, name: String) {
        getSharedPreferences("mqtt_config", MODE_PRIVATE).edit().apply {
            putString("server", server)
            putInt("port", port)
            putString("user", user)
            putString("pass", binding.mqttPass.text.toString().trim())
            putString("name", name)
            apply()
        }
    }

    private fun loadSavedConfig() {
        val prefs = getSharedPreferences("mqtt_config", MODE_PRIVATE)
        binding.mqttServer.setText(prefs.getString("server", ""))
        binding.mqttPort.setText(prefs.getInt("port", 1883).toString())
        binding.mqttUser.setText(prefs.getString("user", "tamir"))
        binding.mqttPass.setText(prefs.getString("pass", "@ns!bl3"))
        binding.deviceName.setText(prefs.getString("name", ""))
    }

    private fun hasAudioPermission(): Boolean {
        return ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED
    }

    private fun checkPermissions() {
        val needed = mutableListOf<String>()
        if (!hasAudioPermission()) needed.add(Manifest.permission.RECORD_AUDIO)
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            needed.add(Manifest.permission.ACCESS_FINE_LOCATION)
        }
        if (needed.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, needed.toTypedArray(), PERMISSION_REQUEST)
        }
    }

    override fun onDestroy() {
        if (isBound) {
            unbindService(serviceConnection)
            isBound = false
        }
        super.onDestroy()
    }
}
