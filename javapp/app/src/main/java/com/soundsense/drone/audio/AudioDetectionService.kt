package com.soundsense.drone.audio

import android.Manifest
import android.app.Notification
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.PackageManager
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.IBinder
import android.util.Log
import androidx.core.app.ActivityCompat
import com.soundsense.drone.SoundSenseApp
import com.soundsense.drone.ml.AudioClassifier
import com.soundsense.drone.mqtt.DetectionData
import com.soundsense.drone.mqtt.MqttManager
import com.soundsense.drone.ui.MainActivity
import kotlinx.coroutines.*
import java.text.SimpleDateFormat
import java.util.*

class AudioDetectionService : Service() {

    private val binder = DetectionBinder()

    inner class DetectionBinder : android.os.Binder() {
        fun getService(): AudioDetectionService = this@AudioDetectionService
    }

    override fun onBind(intent: Intent?): IBinder = binder

    companion object {
        private const val TAG = "AudioDetectionService"
        private const val SAMPLE_RATE = 22050
        private const val CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO
        private const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT
        private const val DETECTION_COOLDOWN_MS = 2000L
    }

    private var audioRecord: AudioRecord? = null
    private var isRecording = false
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var classifier: AudioClassifier? = null
    private var mqttManager: MqttManager? = null
    private var deviceName = "unknown"
    private var lastDetectionTime = 0L

    var onDetection: ((soundType: String, confidence: Double) -> Unit)? = null
    var onAudioLevel: ((Float) -> Unit)? = null

    override fun onCreate() {
        super.onCreate()
        classifier = AudioClassifier(this)
        startForeground(1, createNotification())
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        deviceName = intent?.getStringExtra("device_name") ?: "unknown"
        return START_STICKY
    }

    fun setMqttManager(manager: MqttManager) {
        mqttManager = manager
    }

    fun startDetection() {
        if (isRecording) return

        val bufferSize = AudioRecord.getMinBufferSize(SAMPLE_RATE, CHANNEL_CONFIG, AUDIO_FORMAT)
        if (bufferSize == AudioRecord.ERROR || bufferSize == AudioRecord.ERROR_BAD_VALUE) {
            Log.e(TAG, "Invalid buffer size")
            return
        }

        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED
        ) {
            Log.e(TAG, "Audio permission not granted")
            return
        }

        try {
            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.MIC,
                SAMPLE_RATE,
                CHANNEL_CONFIG,
                AUDIO_FORMAT,
                bufferSize * 2
            )

            if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
                Log.e(TAG, "AudioRecord failed to initialize")
                return
            }

            isRecording = true
            audioRecord?.startRecording()
            Log.d(TAG, "Recording started")

            scope.launch {
                val buffer = ShortArray(bufferSize)
                val audioBuffer = FloatArray(22050)

                while (isRecording) {
                    val read = audioRecord?.read(buffer, 0, buffer.size) ?: 0
                    if (read > 0) {
                        val samples = ShortArray(read)
                        System.arraycopy(buffer, 0, samples, 0, read)

                        val floatSamples = FloatArray(samples.size) { it.toFloat() / Short.MAX_VALUE }

                        val rms = kotlin.math.sqrt(samples.map { it.toFloat() * it.toFloat() }.average()).toFloat()
                        val normalizedLevel = (rms / Short.MAX_VALUE).coerceIn(0f, 1f)
                        withContext(Dispatchers.Main) {
                            onAudioLevel?.invoke(normalizedLevel)
                        }

                        if (normalizedLevel > 0.02f) {
                            val now = System.currentTimeMillis()
                            if (now - lastDetectionTime > DETECTION_COOLDOWN_MS) {
                                val result = classifier?.classify(floatSamples, SAMPLE_RATE)
                                if (result != null && result.confidence > 0.4) {
                                    lastDetectionTime = now
                                    withContext(Dispatchers.Main) {
                                        onDetection?.invoke(result.label, result.confidence)
                                    }
                                    publishDetection(result.label, result.confidence)
                                }
                            }
                        }
                    }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Start detection error", e)
        }
    }

    fun stopDetection() {
        isRecording = false
        scope.launch {
            delay(200)
            try {
                audioRecord?.stop()
                audioRecord?.release()
                audioRecord = null
            } catch (e: Exception) {
                Log.e(TAG, "Stop error", e)
            }
        }
    }

    private fun publishDetection(soundType: String, confidence: Double) {
        val mqtt = mqttManager ?: return
        if (!mqtt.isConnected()) return

        val sdf = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS", Locale.US)
        val detection = DetectionData(
            name = deviceName,
            detected_sound = soundType,
            confidence = confidence,
            datetime = sdf.format(Date())
        )
        mqtt.publishDetection(detection)
    }

    private fun createNotification(): Notification {
        val pendingIntent = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        return Notification.Builder(this, SoundSenseApp.CHANNEL_ID)
            .setContentTitle("SoundSense Active")
            .setContentText("Listening for sounds...")
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()
    }

    override fun onDestroy() {
        stopDetection()
        scope.cancel()
        super.onDestroy()
    }
}
