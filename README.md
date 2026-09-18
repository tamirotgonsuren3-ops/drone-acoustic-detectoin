# Python version 3.10
conda activate py310

# SoundSense - IoT Sound Detection System

Real-time sound detection system with MQTT integration. Upload sound samples, train ML model, detect sounds from phone microphone, and view all detections on a dashboard.

## Architecture

```
Phone (Browser)          Server (Flask)          MQTT Broker          Dashboard
┌─────────────┐         ┌─────────────┐        ┌─────────────┐      ┌─────────────┐
│ Register     │         │ REST API    │        │ HiveMQ /    │      │ MQTT Table  │
│ Upload audio ├────────>│ Audio ML    │◄──────>│ Mosquitto   │◄────>│ Real-time   │
│ Train model  │         │ MQTT Bridge │        │             │      │ CSV Export  │
│ Mic detect   │◄────────│ SocketIO    │        └─────────────┘      └─────────────┘
│ MQTT publish │         └─────────────┘
└─────────────┘
```

## Features

- **Device Registration**: Configure MQTT server, credentials, device name
- **Audio Upload**: Upload MP3/MP4/WAV files with sound type labels
- **ML Training**: Train sklearn model on uploaded audio (MFCC features + neural network)
- **Live Detection**: Phone microphone listens in real-time, detects trained sounds
- **Background Mode**: Wake Lock API keeps detection running when screen is off
- **MQTT Publish**: Sends `detected_sound`, `lat`, `long`, `name`, `datetime`, `direction`, `tilted_degree` to `detected/sound/` topic
- **Dashboard**: Real-time MQTT table viewer with filtering, statistics, CSV export

## MQTT Message Format

Published to `detected/sound/`:

```json
{
    "name": "sensor-01",
    "detected_sound": "dog",
    "confidence": 0.87,
    "datetime": "2026-09-15T17:30:00.000Z",
    "lat": 47.9184,
    "long": 106.9177,
    "direction": "NE",
    "tilted_degree": 15.3
}
```

## Prerequisites

- Python 3.9+
- MQTT Broker (HiveMQ Cloud, Mosquitto, etc.)
- Modern browser with Web Audio API support (Chrome, Edge, Firefox)

## Installation

```bash
# 1. Create virtual environment
python -m venv venv

# 2. Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the server
python app.py
```

Server starts at `http://localhost:5000`

## Usage Guide

### Step 1: Mobile App - Register

1. Open `http://<server-ip>:5000` on your phone
2. Go to **Register** tab
3. Enter:
   - **Device Name**: e.g. `sensor-01`
   - **MQTT Server**: e.g. `broker.hivemq.com`
   - **MQTT Port**: `1883` (or `8884` for WebSocket SSL)
   - **MQTT Username**: your broker username
   - **MQTT Password**: your broker password
4. Tap **Connect**

### Step 2: Upload Sound Samples

1. Go to **Upload** tab
2. Enter **Sound Type Label** (e.g. `dog`, `drone`, `car`)
3. Select an audio file (MP3, MP4, WAV)
4. Tap **Upload**
5. Repeat for each sound type (upload multiple samples per type for better accuracy)

### Step 3: Train Model

1. Go to **Train** tab
2. Set **Training Epochs** (50-100 recommended)
3. Tap **Start Training**
4. Wait for training to complete
5. Check **Model Status** shows "Trained"

### Step 4: Detect Sounds

1. Go to **Detect** tab
2. Tap **MIC** button to start listening
3. Grant microphone permission when prompted
4. The app will detect sounds in real-time
5. Detections are automatically published to MQTT `detected/sound/` topic
6. Works in background when screen is locked (Wake Lock API)

### Step 5: Dashboard

1. Open `http://<server-ip>:5000/dashboard` on any device
2. Enter MQTT broker connection details
3. Click **Connect**
4. All incoming detections appear in the table in real-time
5. Use filters to filter by device or sound type
6. Export data as CSV

## File Structure

```
project/
├── app.py                  # Flask server + REST API + SocketIO
├── mqtt_bridge.py          # MQTT client bridge
├── audio_ml.py             # ML training (sklearn + librosa)
├── requirements.txt        # Python dependencies
├── templates/
│   ├── index.html          # Mobile app UI
│   └── dashboard.html      # Dashboard UI
├── static/
│   ├── css/
│   │   └── styles.css      # All styles
│   └── js/
│       ├── app.js          # Mobile app logic + mic detection
│       └── dashboard.js    # Dashboard logic
├── models/                 # Trained ML models (auto-created)
└── uploads/                # Uploaded audio files (auto-created)
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Mobile app page |
| GET | `/dashboard` | Dashboard page |
| POST | `/api/mqtt/connect` | Connect to MQTT broker |
| GET | `/api/mqtt/status` | Check MQTT connection |
| GET | `/api/mqtt/messages` | Get stored MQTT messages |
| POST | `/api/mqtt/publish` | Publish MQTT message |
| POST | `/api/upload` | Upload audio file |
| GET | `/api/upload/list` | List uploaded files |
| POST | `/api/train` | Train ML model |
| GET | `/api/model/status` | Check model training status |
| POST | `/api/predict` | Predict sound from audio file |

## Troubleshooting

- **Microphone not working**: Ensure HTTPS or localhost. Browsers require secure context for `getUserMedia`.
- **MQTT connection fails**: Check server/port. For HiveMQ Cloud use port `8884` with WebSocket SSL (`wss://`).
- **Training fails**: Ensure at least 2 different sound types uploaded with multiple samples each.
- **Background detection stops**: Use Chrome/Edge on Android for best Wake Lock support.

## License

MIT
