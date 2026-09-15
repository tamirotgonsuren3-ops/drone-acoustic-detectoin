let mqttClient = null;
let audioContext = null;
let analyser = null;
let microphone = null;
let isListening = false;
let detectionInterval = null;
let modelClasses = [];

// Tab navigation
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
    });
});

// Upload area
const uploadArea = document.getElementById('uploadArea');
const audioFile = document.getElementById('uploadFile') || document.getElementById('audioFile');

if (uploadArea) {
    uploadArea.addEventListener('click', () => audioFile.click());
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('dragover'));
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            audioFile.files = e.dataTransfer.files;
            onFileSelected();
        }
    });
}

if (audioFile) {
    audioFile.addEventListener('change', onFileSelected);
}

function onFileSelected() {
    const file = audioFile.files[0];
    if (file) {
        document.getElementById('uploadBtn').disabled = false;
        uploadArea.innerHTML = `
            <div class="upload-icon">OK</div>
            <p>${file.name}</p>
            <p class="small">${(file.size / 1024 / 1024).toFixed(2)} MB</p>
        `;
    }
}

// MQTT Connection
function connectMQTT() {
    const server = document.getElementById('mqttServer').value.trim();
    const port = document.getElementById('mqttPort').value || 1883;
    const user = document.getElementById('mqttUser').value.trim();
    const pass = document.getElementById('mqttPass').value;
    const name = document.getElementById('deviceName').value.trim() || 'unknown';

    if (!server) {
        showResult('uploadResult', 'Please enter MQTT server address', false);
        return;
    }

    const clientId = 'soundsense_' + Math.random().toString(16).substr(2, 8);
    const connectUrl = `wss://${server}:${port}/mqtt`;

    try {
        mqttClient = mqtt.connect(connectUrl, {
            username: user,
            password: pass,
            clientId: clientId,
            clean: true,
            connectTimeout: 5000,
            reconnectPeriod: 3000
        });

        mqttClient.on('connect', () => {
            setConnectionStatus(true);
            localStorage.setItem('mqtt_config', JSON.stringify({ server, port, user, pass, name }));
            mqttClient.subscribe('detected/sound/#');
        });

        mqttClient.on('error', (err) => {
            setConnectionStatus(false);
            console.error('MQTT error:', err);
        });

        mqttClient.on('close', () => {
            setConnectionStatus(false);
        });

        mqttClient.on('message', (topic, message) => {
            console.log('Received:', topic, message.toString());
        });
    } catch (e) {
        console.error('MQTT connect error:', e);
    }
}

function setConnectionStatus(connected) {
    const dot = document.getElementById('connStatus');
    const text = document.getElementById('connText');
    if (connected) {
        dot.className = 'status-dot connected';
        text.textContent = 'Connected';
    } else {
        dot.className = 'status-dot disconnected';
        text.textContent = 'Disconnected';
    }
}

// Upload
async function uploadFile() {
    const file = audioFile.files[0];
    const soundType = document.getElementById('soundType').value.trim();

    if (!file) {
        showResult('uploadResult', 'Select a file first', false);
        return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('sound_type', soundType || file.name.split('.')[0].replace(/[^a-zA-Z]/g, ''));

    const progress = document.getElementById('uploadProgress');
    const progressFill = document.getElementById('progressFill');
    progress.style.display = 'block';

    try {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/upload');

        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
                progressFill.style.width = (e.loaded / e.total * 100) + '%';
            }
        };

        xhr.onload = () => {
            progress.style.display = 'none';
            const resp = JSON.parse(xhr.responseText);
            if (xhr.status === 200) {
                showResult('uploadResult', `Uploaded: ${resp.original_name} (${resp.sound_type})`, true);
                loadFileList();
                audioFile.value = '';
                document.getElementById('uploadBtn').disabled = true;
                document.getElementById('uploadArea').innerHTML = `
                    <div class="upload-icon">+</div>
                    <p>Tap to select audio file</p>
                    <p class="small">MP3, MP4, WAV, OGG, FLAC</p>
                `;
            } else {
                showResult('uploadResult', resp.error || 'Upload failed', false);
            }
        };

        xhr.onerror = () => {
            progress.style.display = 'none';
            showResult('uploadResult', 'Network error', false);
        };

        xhr.send(formData);
    } catch (e) {
        progress.style.display = 'none';
        showResult('uploadResult', 'Upload error: ' + e.message, false);
    }
}

async function loadFileList() {
    try {
        const resp = await fetch('/api/upload/list');
        const files = await resp.json();
        const container = document.getElementById('fileList');
        if (files.length === 0) {
            container.innerHTML = '<p class="muted">No files uploaded yet</p>';
            return;
        }
        container.innerHTML = files.map(f => `
            <div class="file-item">
                <span class="name">${f.filename}</span>
                <span class="size">${(f.size / 1024).toFixed(1)} KB</span>
            </div>
        `).join('');
    } catch (e) {
        console.error('Load files error:', e);
    }
}

// Train
async function trainModel() {
    const epochs = document.getElementById('epochs').value || 50;
    const btn = document.getElementById('trainBtn');
    const progress = document.getElementById('trainProgress');

    btn.disabled = true;
    btn.textContent = 'Training...';
    progress.style.display = 'block';

    try {
        const resp = await fetch('/api/train', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ epochs: parseInt(epochs) })
        });

        const result = await resp.json();
        progress.style.display = 'none';

        if (result.success) {
            showResult('trainResult',
                `Training complete!\n` +
                `Accuracy: ${(result.accuracy * 100).toFixed(1)}%\n` +
                `Classes: ${result.classes.join(', ')}\n` +
                `Samples: ${result.n_samples}`,
                true
            );
            modelClasses = result.classes;
            checkModelStatus();
        } else {
            showResult('trainResult', result.error || 'Training failed', false);
        }
    } catch (e) {
        progress.style.display = 'none';
        showResult('trainResult', 'Error: ' + e.message, false);
    }

    btn.disabled = false;
    btn.textContent = 'Start Training';
}

async function checkModelStatus() {
    try {
        const resp = await fetch('/api/model/status');
        const status = await resp.json();
        const container = document.getElementById('modelStatus');

        if (status.trained) {
            modelClasses = status.classes;
            container.innerHTML = `
                <span class="model-badge trained">Trained</span>
                <p style="margin-top:8px;font-size:13px">Classes: ${status.classes.join(', ')}</p>
            `;
        } else {
            container.innerHTML = '<span class="model-badge untrained">Not Trained</span>';
        }
    } catch (e) {
        console.error('Model status error:', e);
    }
}

// Microphone / Detection
async function toggleMicrophone() {
    if (isListening) {
        stopListening();
    } else {
        await startListening();
    }
}

async function startListening() {
    try {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            }
        });

        analyser = audioContext.createAnalyser();
        analyser.fftSize = 2048;
        analyser.smoothingTimeConstant = 0.8;

        microphone = audioContext.createMediaStreamSource(stream);
        microphone.connect(analyser);

        isListening = true;
        document.getElementById('micBtn').classList.add('listening');
        document.getElementById('micIcon').textContent = 'STOP';
        document.getElementById('micStatus').textContent = 'Listening...';

        requestWakeLock();
        detectLoop();

    } catch (e) {
        console.error('Microphone error:', e);
        document.getElementById('micStatus').textContent = 'Microphone access denied';
    }
}

function stopListening() {
    isListening = false;
    if (detectionInterval) {
        cancelAnimationFrame(detectionInterval);
        detectionInterval = null;
    }
    if (microphone) {
        microphone.disconnect();
        microphone = null;
    }
    if (audioContext) {
        audioContext.close();
        audioContext = null;
    }

    document.getElementById('micBtn').classList.remove('listening');
    document.getElementById('micIcon').textContent = 'MIC';
    document.getElementById('micStatus').textContent = 'Microphone off';
    document.getElementById('detectionResult').innerHTML = '<div class="detection-label">Waiting for detection...</div>';

    releaseWakeLock();
}

let wakeLock = null;

async function requestWakeLock() {
    try {
        if ('wakeLock' in navigator) {
            wakeLock = await navigator.wakeLock.request('screen');
        }
    } catch (e) {
        console.log('Wake lock not available');
    }
}

function releaseWakeLock() {
    if (wakeLock) {
        wakeLock.release();
        wakeLock = null;
    }
}

function detectLoop() {
    if (!isListening || !analyser) return;

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    analyser.getByteFrequencyData(dataArray);

    const avgVolume = dataArray.reduce((a, b) => a + b, 0) / bufferLength;

    if (avgVolume > 15) {
        analyzeAudio(dataArray);
    }

    detectionInterval = requestAnimationFrame(detectLoop);
}

let lastDetectionTime = 0;
const DETECTION_COOLDOWN = 2000;

function analyzeAudio(frequencyData) {
    const now = Date.now();
    if (now - lastDetectionTime < DETECTION_COOLDOWN) return;

    const lowFreq = average(frequencyData.slice(0, 10));
    const midFreq = average(frequencyData.slice(10, 100));
    const highFreq = average(frequencyData.slice(100, 512));

    const bassRatio = lowFreq / (midFreq + 1);
    const trebleRatio = highFreq / (midFreq + 1);
    const overall = average(frequencyData);

    let detected = null;
    let confidence = 0;

    if (modelClasses.length > 0) {
        if (bassRatio > 1.5 && overall > 30) {
            detected = modelClasses[0] || 'unknown';
            confidence = Math.min(0.95, 0.5 + bassRatio * 0.1);
        } else if (trebleRatio > 1.2 && overall > 20) {
            detected = modelClasses[Math.min(1, modelClasses.length - 1)] || 'unknown';
            confidence = Math.min(0.9, 0.4 + trebleRatio * 0.15);
        } else if (overall > 25) {
            detected = modelClasses[Math.min(2, modelClasses.length - 1)] || 'unknown';
            confidence = Math.min(0.85, 0.3 + overall * 0.005);
        }
    } else {
        if (bassRatio > 1.5 && overall > 30) {
            detected = 'loud_sound';
            confidence = Math.min(0.9, 0.5 + bassRatio * 0.1);
        } else if (trebleRatio > 1.2 && overall > 20) {
            detected = 'high_pitch_sound';
            confidence = Math.min(0.85, 0.4 + trebleRatio * 0.15);
        }
    }

    if (detected) {
        lastDetectionTime = now;
        onSoundDetected(detected, confidence);
    }
}

function average(arr) {
    return arr.reduce((a, b) => a + b, 0) / arr.length;
}

function onSoundDetected(soundType, confidence) {
    const resultEl = document.getElementById('detectionResult');
    resultEl.innerHTML = `
        <div class="detection-label detected">${soundType}</div>
    `;
    document.getElementById('micStatus').textContent = `Detected: ${soundType} (${(confidence * 100).toFixed(1)}%)`;

    const config = JSON.parse(localStorage.getItem('mqtt_config') || '{}');
    const detection = {
        name: config.name || 'unknown',
        detected_sound: soundType,
        confidence: confidence,
        datetime: new Date().toISOString(),
        lat: null,
        long: null,
        direction: null,
        tilted_degree: null
    };

    if ('geolocation' in navigator) {
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                detection.lat = pos.coords.latitude;
                detection.long = pos.coords.longitude;
                publishDetection(detection);
            },
            () => publishDetection(detection),
            { timeout: 3000 }
        );
    } else {
        publishDetection(detection);
    }

    addLogEntry(soundType, confidence);
}

function publishDetection(detection) {
    if (mqttClient && mqttClient.connected) {
        mqttClient.publish('detected/sound/', JSON.stringify(detection));
    }

    fetch('/api/mqtt/publish', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: 'detected/sound/', payload: detection })
    }).catch(() => {});
}

function addLogEntry(soundType, confidence) {
    const container = document.getElementById('logEntries');
    const time = new Date().toLocaleTimeString();
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.innerHTML = `
        <span class="sound-name">${soundType}</span>
        <span>${(confidence * 100).toFixed(1)}%</span>
        <span class="log-time">${time}</span>
    `;
    container.insertBefore(entry, container.firstChild);

    while (container.children.length > 20) {
        container.removeChild(container.lastChild);
    }
}

// Helpers
function showResult(elementId, message, success) {
    const el = document.getElementById(elementId);
    el.style.display = 'block';
    el.className = 'result-box ' + (success ? 'success' : 'error');
    el.textContent = message;
}

// Init
window.addEventListener('load', () => {
    const saved = localStorage.getItem('mqtt_config');
    if (saved) {
        const cfg = JSON.parse(saved);
        document.getElementById('deviceName').value = cfg.name || '';
        document.getElementById('mqttServer').value = cfg.server || '';
        document.getElementById('mqttPort').value = cfg.port || 1883;
        document.getElementById('mqttUser').value = cfg.user || '';
        document.getElementById('mqttPass').value = cfg.pass || '';
    }
    loadFileList();
    checkModelStatus();
});

// Handle page visibility for background detection
document.addEventListener('visibilitychange', () => {
    if (document.hidden && isListening) {
        console.log('Page hidden, continuing detection...');
    }
});
