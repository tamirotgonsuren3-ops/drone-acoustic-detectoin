# SoundSense Android App

Native Android client for the SoundSense drone acoustic detection system.
Connects to the same MQTT broker as the web app and provides on-device
audio classification with ML inference.

## Prerequisites

- **JDK 17** or later
- **Android SDK** (API 34)
- **Android device** with API 26+ (Android 8.0+) or emulator

### Install JDK 17 (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install openjdk-17-jdk
java -version
```

### Install Android SDK

Option A: Install Android Studio from https://developer.android.com/studio

Option B: Command-line only:
```bash
# Download Android command-line tools
mkdir -p ~/android-sdk/cmdline-tools
cd ~/android-sdk/cmdline-tools
wget https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
unzip commandlinetools-linux-11076708_latest.zip
mv cmdline-tools latest

# Set environment
export ANDROID_HOME=~/android-sdk
export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools

# Accept licenses and install SDK
sdkmanager --licenses
sdkmanager "platforms;android-34" "build-tools;34.0.0" "platform-tools"
```

## Building

### Quick Build (Debug APK)

```bash
cd javapp
chmod +x build.sh
./build.sh debug
```

### Build Both Debug and Release

```bash
./build.sh all
```

### Build with Gradle directly

```bash
cd javapp
./gradlew assembleDebug
```

The debug APK will be at:
```
javapp/app/build/outputs/apk/debug/app-debug.apk
```

## Installation

### Option 1: Direct install via ADB

```bash
# Connect Android device via USB with USB debugging enabled
adb devices
adb install javapp/app/build/outputs/apk/debug/app-debug.apk
```

### Option 2: Transfer APK to device

1. Build the APK: `./build.sh debug`
2. Copy `SoundSense-debug.apk` to your device (USB, email, cloud)
3. On the device, open the APK file
4. Enable "Install from unknown sources" if prompted
5. Tap "Install"

### Enabling USB Debugging

1. Go to **Settings > About Phone**
2. Tap **Build Number** 7 times (enables Developer Options)
3. Go to **Settings > Developer Options**
4. Enable **USB Debugging**
5. Connect device via USB and approve the connection

## App Features

### Main Screen
- **MQTT Connection** - Connect to your MQTT broker
- **Live Detection** - Start/stop real-time audio classification
- **Detection Log** - View recent detections with timestamps
- **Audio Level** - Visual indicator of microphone input level

### Dashboard Screen
- **Connection Status** - Monitor MQTT connection
- **Statistics** - Total detections, unique devices, sound types
- **Detections Table** - Detailed table of all received detections
- **Real-time Log** - Raw MQTT message stream

### MQTT Protocol

The app publishes to `detected/sound/` topic with this JSON payload:

```json
{
  "name": "device-name",
  "detected_sound": "drone",
  "confidence": 0.87,
  "datetime": "2025-01-15T10:30:00.000",
  "lat": 32.12345,
  "long": 34.67890,
  "direction": null,
  "tilted_degree": null
}
```

Subscribes to `detected/sound/#` for receiving detections from other devices.

### Using a Custom ML Model

Train a model using the web app, then transfer these files to the Android device:

```bash
# Files to copy to device's app storage
adb push model.bin /data/data/com.soundsense.drone/files/
adb push labels.txt /data/data/com.soundsense.drone/files/
```

Without a custom model, the app uses built-in frequency-based rules for
sound classification (drone, loud sound, high-pitch sound, ambient noise).

## Configuration

### MQTT Settings

| Field | Description | Default |
|-------|-------------|---------|
| Device Name | Unique identifier for this sensor | android-sensor |
| MQTT Server | Broker hostname or IP | - |
| MQTT Port | Broker port | 1883 |
| Username | MQTT auth username (optional) | - |
| Password | MQTT auth password (optional) | - |

### Required Permissions

| Permission | Purpose |
|------------|---------|
| RECORD_AUDIO | Microphone access for sound detection |
| INTERNET | MQTT communication |
| ACCESS_FINE_LOCATION | GPS coordinates in detection reports |
| FOREGROUND_SERVICE | Background audio detection |
| WAKE_LOCK | Keep device awake during detection |

## Troubleshooting

### Build fails with "SDK not found"
Set `ANDROID_HOME`:
```bash
export ANDROID_HOME=~/Android/Sdk
```

### "Could not resolve all dependencies"
Check internet connection and ensure repositories are accessible.

### App crashes on start
Ensure microphone permission is granted and Android API is 26+.

### No detections
- Verify MQTT connection status shows "Connected"
- Check broker is running and accessible from the device
- Ensure sound type labels match expected format
