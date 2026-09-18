package com.soundsense.drone

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build

class SoundSenseApp : Application() {

    companion object {
        const val CHANNEL_ID = "soundsense_detection"
        const val CHANNEL_NAME = "Sound Detection"
        lateinit var instance: SoundSenseApp
            private set
    }

    override fun onCreate() {
        super.onCreate()
        instance = this
        createNotificationChannel()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                CHANNEL_NAME,
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Active sound detection notifications"
                setShowBadge(false)
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }
}
