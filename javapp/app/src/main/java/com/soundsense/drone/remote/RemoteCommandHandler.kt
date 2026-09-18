package com.soundsense.drone.remote

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.ImageFormat
import android.graphics.SurfaceTexture
import android.hardware.camera2.*
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.ImageReader
import android.media.MediaRecorder
import android.os.Handler
import android.os.HandlerThread
import android.util.Base64
import android.util.Log
import androidx.core.app.ActivityCompat
import com.soundsense.drone.mqtt.MqttManager
import kotlinx.coroutines.*
import java.io.ByteArrayOutputStream
import java.util.concurrent.Executors

class RemoteCommandHandler(
    private val context: Context,
    private val mqttManager: MqttManager,
    private val deviceName: String
) {

    companion object {
        private const val TAG = "RemoteCmdHandler"
        private const val MIC_SAMPLE_RATE = 16000
        private const val MIC_CHUNK_MS = 100
        private const val CAM_FRAME_INTERVAL_MS = 500L
        private const val HEARTBEAT_INTERVAL_MS = 5000L
    }

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var micJob: Job? = null
    private var camJob: Job? = null
    private var heartbeatJob: Job? = null

    private var audioRecord: AudioRecord? = null
    private var cameraDevice: CameraDevice? = null
    private var cameraSession: CameraCaptureSession? = null
    private var imageReader: ImageReader? = null
    private var cameraThread: HandlerThread? = null
    private var cameraHandler: Handler? = null

    var onCommandResult: ((String) -> Unit)? = null

    fun start() {
        subscribeToCommands()
        startHeartbeat()
    }

    fun stop() {
        micJob?.cancel()
        camJob?.cancel()
        heartbeatJob?.cancel()
        stopMic()
        stopCamera()
        scope.cancel()
    }

    // ==================== MQTT COMMANDS ====================

    private fun subscribeToCommands() {
        val topic = "device/$deviceName/cmd"
        mqttManager.subscribe(topic, 1) { _, payload ->
            handleCommand(payload)
        }
        Log.d(TAG, "Subscribed to $topic")
    }

    private fun handleCommand(payload: String) {
        try {
            val json = org.json.JSONObject(payload)
            val cmd = json.optString("cmd", "")
            Log.d(TAG, "Command received: $cmd")

            when (cmd) {
                "mic_start" -> startMicStream()
                "mic_stop" -> stopMic()
                "camera_start" -> startCameraStream()
                "camera_stop" -> stopCamera()
                else -> Log.w(TAG, "Unknown command: $cmd")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Parse command error: ${e.message}")
        }
    }

    // ==================== HEARTBEAT ====================

    private fun startHeartbeat() {
        heartbeatJob = scope.launch {
            while (isActive) {
                try {
                    val json = org.json.JSONObject().apply {
                        put("online", true)
                        put("device", deviceName)
                        put("mic_active", micJob?.isActive == true)
                        put("camera_active", camJob?.isActive == true)
                        put("timestamp", System.currentTimeMillis())
                    }
                    mqttManager.publish("device/$deviceName/status", json.toString(), 0)
                } catch (e: Exception) {
                    Log.e(TAG, "Heartbeat error: ${e.message}")
                }
                delay(HEARTBEAT_INTERVAL_MS)
            }
        }
    }

    // ==================== MIC STREAMING ====================

    private fun startMicStream() {
        if (micJob?.isActive == true) return

        if (ActivityCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED
        ) {
            Log.e(TAG, "No RECORD_AUDIO permission")
            return
        }

        val bufferSize = AudioRecord.getMinBufferSize(
            MIC_SAMPLE_RATE,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT
        )
        if (bufferSize == AudioRecord.ERROR || bufferSize == AudioRecord.ERROR_BAD_VALUE) {
            Log.e(TAG, "Invalid mic buffer size")
            return
        }

        try {
            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.MIC,
                MIC_SAMPLE_RATE,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                bufferSize * 2
            )

            if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
                Log.e(TAG, "AudioRecord init failed")
                audioRecord?.release()
                audioRecord = null
                return
            }

            audioRecord?.startRecording()
            Log.d(TAG, "Mic streaming started")

            micJob = scope.launch {
                val samplesPerChunk = MIC_SAMPLE_RATE * MIC_CHUNK_MS / 1000
                val buffer = ShortArray(samplesPerChunk)

                while (isActive) {
                    val read = audioRecord?.read(buffer, 0, buffer.size) ?: 0
                    if (read > 0) {
                        val bytes = ByteArrayOutputStream()
                        for (i in 0 until read) {
                            val v = buffer[i].toInt()
                            bytes.write(v and 0xFF)
                            bytes.write((v shr 8) and 0xFF)
                        }
                        val encoded = Base64.encodeToString(bytes.toByteArray(), Base64.NO_WRAP)
                        mqttManager.publish("device/$deviceName/audio", encoded, 0)
                    }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Start mic error", e)
        }
    }

    private fun stopMic() {
        micJob?.cancel()
        micJob = null
        try {
            audioRecord?.stop()
            audioRecord?.release()
        } catch (_: Exception) {}
        audioRecord = null
        Log.d(TAG, "Mic streaming stopped")
    }

    // ==================== CAMERA STREAMING ====================

    private fun startCameraStream() {
        if (camJob?.isActive == true) return

        if (ActivityCompat.checkSelfPermission(context, Manifest.permission.CAMERA)
            != PackageManager.PERMISSION_GRANTED
        ) {
            Log.e(TAG, "No CAMERA permission")
            onCommandResult?.invoke("Camera permission not granted")
            return
        }

        try {
            imageReader = ImageReader.newInstance(640, 480, ImageFormat.JPEG, 2)
            cameraThread = HandlerThread("CameraThread").also { it.start() }
            cameraHandler = Handler(cameraThread!!.looper)

            val manager = context.getSystemService(Context.CAMERA_SERVICE) as CameraManager
            val cameraId = findBackCamera(manager) ?: run {
                Log.e(TAG, "No back camera found")
                return
            }

            manager.openCamera(cameraId, object : CameraDevice.StateCallback() {
                override fun onOpened(camera: CameraDevice) {
                    cameraDevice = camera
                    createCaptureSession()
                }
                override fun onDisconnected(camera: CameraDevice) {
                    camera.close()
                    cameraDevice = null
                }
                override fun onError(camera: CameraDevice, error: Int) {
                    camera.close()
                    cameraDevice = null
                    Log.e(TAG, "Camera error: $error")
                }
            }, cameraHandler)

            Log.d(TAG, "Camera streaming started")
        } catch (e: Exception) {
            Log.e(TAG, "Start camera error", e)
        }
    }

    private fun findBackCamera(manager: CameraManager): String? {
        for (id in manager.cameraIdList) {
            val chars = manager.getCameraCharacteristics(id)
            val facing = chars.get(android.hardware.camera2.CameraCharacteristics.LENS_FACING)
            if (facing == android.hardware.camera2.CameraCharacteristics.LENS_FACING_BACK) {
                return id
            }
        }
        return null
    }

    private fun createCaptureSession() {
        val camera = cameraDevice ?: return
        val reader = imageReader ?: return

        try {
            camera.createCaptureSession(
                listOf(reader.surface),
                object : CameraCaptureSession.StateCallback() {
                    override fun onConfigured(session: CameraCaptureSession) {
                        cameraSession = session
                        startFrameCapture(session)
                    }
                    override fun onConfigureFailed(session: CameraCaptureSession) {
                        Log.e(TAG, "Capture session config failed")
                    }
                },
                cameraHandler
            )
        } catch (e: Exception) {
            Log.e(TAG, "Create session error", e)
        }
    }

    private fun startFrameCapture(session: CameraCaptureSession) {
        val camera = cameraDevice ?: return
        val reader = imageReader ?: return

        try {
            val request = camera.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW).apply {
                addTarget(reader.surface)
                set(android.hardware.camera2.CaptureRequest.CONTROL_MODE, android.hardware.camera2.CaptureRequest.CONTROL_MODE_AUTO)
            }

            camJob = scope.launch {
                while (isActive) {
                    try {
                        session.capture(request.build(), null, cameraHandler)
                    } catch (e: Exception) {
                        Log.e(TAG, "Capture frame error: ${e.message}")
                        break
                    }
                    delay(CAM_FRAME_INTERVAL_MS)
                }
            }

            reader.setOnImageAvailableListener({ reader ->
                val image = reader.acquireLatestImage() ?: return@setOnImageAvailableListener
                try {
                    val buffer = image.planes[0].buffer
                    val bytes = ByteArray(buffer.remaining())
                    buffer.get(bytes)
                    val encoded = Base64.encodeToString(bytes, Base64.NO_WRAP)
                    mqttManager.publish("device/$deviceName/camera", encoded, 0)
                } finally {
                    image.close()
                }
            }, cameraHandler)
        } catch (e: Exception) {
            Log.e(TAG, "Start frame capture error", e)
        }
    }

    private fun stopCamera() {
        camJob?.cancel()
        camJob = null
        try {
            cameraSession?.close()
            cameraDevice?.close()
            imageReader?.close()
            cameraThread?.quitSafely()
        } catch (_: Exception) {}
        cameraSession = null
        cameraDevice = null
        imageReader = null
        cameraThread = null
        cameraHandler = null
        Log.d(TAG, "Camera streaming stopped")
    }
}
