let mqttClient = null;
let detections = [];
let devices = {};
let audioContexts = {};
let micStreams = {};
let cameraIntervals = {};

function connectDashboardMQTT() {
    const server = document.getElementById('dMqttServer').value.trim();
    const port = document.getElementById('dMqttPort').value || 9001;
    const user = document.getElementById('dMqttUser').value.trim();
    const pass = document.getElementById('dMqttPass').value;

    if (!server) { alert('Enter MQTT server address'); return; }

    const clientId = 'admin_' + Math.random().toString(16).substr(2, 8);
    let connectUrl;
    if (port === 443 || port === '443' || port === 8884 || port === '8884') {
        connectUrl = `wss://${server}:${port}/mqtt`;
    } else {
        connectUrl = `ws://${server}:${port}/mqtt`;
    }

    try {
        if (mqttClient) mqttClient.end();

        mqttClient = mqtt.connect(connectUrl, {
            username: user || undefined,
            password: pass || undefined,
            clientId: clientId,
            clean: true,
            connectTimeout: 5000,
            reconnectPeriod: 3000
        });

        mqttClient.on('connect', () => {
            setDashStatus(true);
            addLogLine('SYSTEM', 'Connected to MQTT broker');
            mqttClient.subscribe('detected/sound/#');
            mqttClient.subscribe('device/+/status');
            mqttClient.subscribe('device/+/audio');
            mqttClient.subscribe('device/+/camera');
            addLogLine('SYSTEM', 'Subscribed to all topics');
        });

        mqttClient.on('error', (err) => {
            setDashStatus(false);
            addLogLine('ERROR', err.message);
        });

        mqttClient.on('close', () => setDashStatus(false));

        mqttClient.on('message', (topic, message) => {
            handleMQTTMessage(topic, message.toString());
        });

        localStorage.setItem('dash_mqtt', JSON.stringify({ server, port, user, pass }));
    } catch (e) {
        addLogLine('ERROR', 'Connect failed: ' + e.message);
    }
}

function setDashStatus(connected) {
    document.getElementById('dashConnStatus').className = 'status-dot ' + (connected ? 'connected' : 'disconnected');
    document.getElementById('dashConnText').textContent = connected ? 'Connected' : 'Disconnected';
}

function handleMQTTMessage(topic, payload) {
    addLogLine(topic, payload);

    // Device status heartbeat
    if (topic.match(/^device\/[^/]+\/status$/)) {
        const deviceName = topic.split('/')[1];
        try {
            const data = JSON.parse(payload);
            devices[deviceName] = {
                ...data,
                name: deviceName,
                lastSeen: Date.now(),
                online: true
            };
        } catch {
            devices[deviceName] = { name: deviceName, lastSeen: Date.now(), online: true };
        }
        updateDeviceGrid();
        return;
    }

    // Audio data from device
    if (topic.match(/^device\/[^/]+\/audio$/)) {
        const deviceName = topic.split('/')[1];
        playRemoteAudio(deviceName, payload);
        return;
    }

    // Camera frame from device
    if (topic.match(/^device\/[^/]+\/camera$/)) {
        const deviceName = topic.split('/')[1];
        showCameraFrame(deviceName, payload);
        return;
    }

    // Detection data
    if (topic.startsWith('detected/sound/') || topic.startsWith('detected/')) {
        try {
            const data = JSON.parse(payload);
            data._topic = topic;
            data._received_at = new Date().toISOString();
            detections.push(data);
            updateTable();
            updateStats();
            updateFilters();
        } catch (e) {
            console.log('Non-JSON detection:', payload);
        }
    }
}

// ==================== DEVICES ====================

function updateDeviceGrid() {
    const container = document.getElementById('deviceGrid');
    const deviceList = Object.values(devices);

    if (deviceList.length === 0) {
        container.innerHTML = '<p class="muted">No devices connected.</p>';
        document.getElementById('onlineDevices').textContent = '0';
        return;
    }

    const now = Date.now();
    deviceList.forEach(d => {
        d.online = (now - d.lastSeen) < 15000;
    });

    const online = deviceList.filter(d => d.online).length;
    document.getElementById('onlineDevices').textContent = online;

    container.innerHTML = deviceList.map(d => `
        <div class="device-card ${d.online ? 'online' : 'offline'}">
            <div class="device-header">
                <span class="device-name">${d.name}</span>
                <span class="device-status ${d.online ? 'online' : 'offline'}">${d.online ? 'ONLINE' : 'OFFLINE'}</span>
            </div>
            <div class="device-info">
                Last seen: ${d.lastSeen ? new Date(d.lastSeen).toLocaleTimeString() : 'never'}
                ${d.battery ? ' | Battery: ' + d.battery + '%' : ''}
            </div>
            <div class="device-actions">
                <button class="btn-sm btn-mic ${micStreams[d.name] ? 'active' : ''}"
                    onclick="toggleRemoteMic('${d.name}')">
                    ${micStreams[d.name] ? 'STOP MIC' : 'LISTEN'}
                </button>
                <button class="btn-sm btn-cam ${cameraIntervals[d.name] ? 'active' : ''}"
                    onclick="toggleRemoteCamera('${d.name}')">
                    ${cameraIntervals[d.name] ? 'STOP CAM' : 'CAMERA'}
                </button>
            </div>
            <div class="mic-visualizer ${micStreams[d.name] ? 'active' : ''}" id="viz-${d.name}">
                <div class="mic-bars" id="bars-${d.name}">
                    ${Array(32).fill(0).map(() => '<div class="mic-bar" style="height:2px"></div>').join('')}
                </div>
            </div>
            <div class="camera-view ${cameraIntervals[d.name] ? 'active' : ''}" id="cam-${d.name}">
                <img id="camimg-${d.name}" src="" alt="Camera" />
            </div>
        </div>
    `).join('');

    // Mark offline devices after 10s
    setTimeout(() => {
        const now2 = Date.now();
        Object.values(devices).forEach(d => {
            if ((now2 - d.lastSeen) > 15000) d.online = false;
        });
        updateDeviceGrid();
    }, 10000);
}

// ==================== REMOTE MIC ====================

function toggleRemoteMic(deviceName) {
    if (micStreams[deviceName]) {
        stopRemoteMic(deviceName);
    } else {
        startRemoteMic(deviceName);
    }
}

function startRemoteMic(deviceName) {
    if (!mqttClient || !mqttClient.connected) {
        alert('Connect to MQTT first');
        return;
    }

    mqttClient.publish(`device/${deviceName}/cmd`, JSON.stringify({ cmd: 'mic_start' }));
    micStreams[deviceName] = true;
    addLogLine('CMD', `Mic START -> ${deviceName}`);

    document.getElementById('remotePanel').style.display = 'block';
    updateDeviceGrid();
}

function stopRemoteMic(deviceName) {
    if (!mqttClient || !mqttClient.connected) return;

    mqttClient.publish(`device/${deviceName}/cmd`, JSON.stringify({ cmd: 'mic_stop' }));
    addLogLine('CMD', `Mic STOP -> ${deviceName}`);

    if (audioContexts[deviceName]) {
        audioContexts[deviceName].close();
        delete audioContexts[deviceName];
    }
    delete micStreams[deviceName];

    const viz = document.getElementById(`viz-${deviceName}`);
    if (viz) viz.classList.remove('active');
    updateDeviceGrid();
}

function playRemoteAudio(deviceName, base64Data) {
    if (!micStreams[deviceName]) return;

    try {
        const raw = atob(base64Data);
        const samples = new Float32Array(raw.length / 2);
        const view = new DataView(new ArrayBuffer(raw.length));
        for (let i = 0; i < raw.length; i++) view.setUint8(i, raw.charCodeAt(i));
        for (let i = 0; i < samples.length; i++) {
            samples[i] = view.getInt16(i * 2, true) / 32768.0;
        }

        if (!audioContexts[deviceName]) {
            audioContexts[deviceName] = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
        }
        const ctx = audioContexts[deviceName];
        const buffer = ctx.createBuffer(1, samples.length, 16000);
        buffer.getChannelData(0).set(samples);

        const source = ctx.createBufferSource();
        source.buffer = buffer;
        source.connect(ctx.destination);
        source.start();

        // Update visualizer
        const bars = document.getElementById(`bars-${deviceName}`);
        if (bars) {
            const barEls = bars.querySelectorAll('.mic-bar');
            const chunkSize = Math.floor(samples.length / barEls.length);
            for (let i = 0; i < barEls.length; i++) {
                const chunk = samples.slice(i * chunkSize, (i + 1) * chunkSize);
                const rms = Math.sqrt(chunk.reduce((s, v) => s + v * v, 0) / chunk.length);
                const h = Math.max(2, Math.min(56, rms * 400));
                barEls[i].style.height = h + 'px';
            }
        }
    } catch (e) {
        console.error('Audio play error:', e);
    }
}

// ==================== REMOTE CAMERA ====================

function toggleRemoteCamera(deviceName) {
    if (cameraIntervals[deviceName]) {
        stopRemoteCamera(deviceName);
    } else {
        startRemoteCamera(deviceName);
    }
}

function startRemoteCamera(deviceName) {
    if (!mqttClient || !mqttClient.connected) {
        alert('Connect to MQTT first');
        return;
    }

    mqttClient.publish(`device/${deviceName}/cmd`, JSON.stringify({ cmd: 'camera_start' }));
    cameraIntervals[deviceName] = true;
    addLogLine('CMD', `Camera START -> ${deviceName}`);

    document.getElementById('cameraPanel').style.display = 'block';
    updateDeviceGrid();
}

function stopRemoteCamera(deviceName) {
    if (!mqttClient || !mqttClient.connected) return;

    mqttClient.publish(`device/${deviceName}/cmd`, JSON.stringify({ cmd: 'camera_stop' }));
    addLogLine('CMD', `Camera STOP -> ${deviceName}`);

    delete cameraIntervals[deviceName];

    const cam = document.getElementById(`cam-${deviceName}`);
    if (cam) cam.classList.remove('active');
    updateDeviceGrid();
}

function showCameraFrame(deviceName, base64Data) {
    if (!cameraIntervals[deviceName]) return;

    const cam = document.getElementById(`cam-${deviceName}`);
    const img = document.getElementById(`camimg-${deviceName}`);
    if (cam && img) {
        cam.classList.add('active');
        img.src = 'data:image/jpeg;base64,' + base64Data;
    }
}

// ==================== TABLE / STATS ====================

function updateTable() {
    const filtered = getFilteredDetections();
    const tbody = document.getElementById('detectionBody');

    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="no-data">No detections yet</td></tr>';
        return;
    }

    tbody.innerHTML = filtered.slice(-100).reverse().map((d, i) => `
        <tr>
            <td>${i + 1}</td>
            <td>${formatTime(d.datetime || d._received_at)}</td>
            <td>${d.name || '-'}</td>
            <td><strong>${d.detected_sound || '-'}</strong></td>
            <td>${d.confidence ? (d.confidence * 100).toFixed(1) + '%' : '-'}</td>
            <td>${d.lat != null ? d.lat.toFixed(5) : '-'}</td>
            <td>${d.long != null ? d.long.toFixed(5) : '-'}</td>
        </tr>
    `).join('');
}

function updateStats() {
    document.getElementById('totalDetections').textContent = detections.length;
    const sounds = new Set(detections.map(d => d.detected_sound).filter(Boolean));
    document.getElementById('uniqueSounds').textContent = sounds.size;
}

function updateFilters() {
    const deviceSelect = document.getElementById('filterDevice');
    const soundSelect = document.getElementById('filterSound');
    const currentDevice = deviceSelect.value;
    const currentSound = soundSelect.value;

    const devicesList = [...new Set(detections.map(d => d.name).filter(Boolean))].sort();
    const sounds = [...new Set(detections.map(d => d.detected_sound).filter(Boolean))].sort();

    deviceSelect.innerHTML = '<option value="">All Devices</option>' +
        devicesList.map(d => `<option value="${d}" ${d === currentDevice ? 'selected' : ''}>${d}</option>`).join('');

    soundSelect.innerHTML = '<option value="">All Sounds</option>' +
        sounds.map(s => `<option value="${s}" ${s === currentSound ? 'selected' : ''}>${s}</option>`).join('');
}

function getFilteredDetections() {
    const device = document.getElementById('filterDevice').value;
    const sound = document.getElementById('filterSound').value;
    return detections.filter(d => {
        if (device && d.name !== device) return false;
        if (sound && d.detected_sound !== sound) return false;
        return true;
    });
}

function applyFilters() { updateTable(); }

function clearFilters() {
    document.getElementById('filterDevice').value = '';
    document.getElementById('filterSound').value = '';
    updateTable();
}

function exportCSV() {
    const filtered = getFilteredDetections();
    if (filtered.length === 0) { alert('No data to export'); return; }

    const headers = ['Time', 'Device', 'Sound', 'Confidence', 'Latitude', 'Longitude'];
    const rows = filtered.map(d => [
        d.datetime || d._received_at || '',
        d.name || '',
        d.detected_sound || '',
        d.confidence || '',
        d.lat || '',
        d.long || ''
    ]);

    let csv = headers.join(',') + '\n';
    rows.forEach(row => { csv += row.map(v => `"${v}"`).join(',') + '\n'; });

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `detections_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
}

function addLogLine(topic, payload) {
    const container = document.getElementById('realtimeLog');
    const time = new Date().toLocaleTimeString();
    const line = document.createElement('div');
    line.className = 'log-line';
    const shortPayload = payload.length > 150 ? payload.substring(0, 150) + '...' : payload;
    line.innerHTML = `<span class="timestamp">[${time}]</span> <span class="topic">${topic}</span> <span class="payload">${shortPayload}</span>`;
    container.appendChild(line);

    while (container.children.length > 100) container.removeChild(container.firstChild);
    container.scrollTop = container.scrollHeight;
}

function formatTime(isoString) {
    if (!isoString) return '-';
    try { return new Date(isoString).toLocaleString(); } catch { return isoString; }
}

async function loadMessages() {
    try {
        const resp = await fetch('/api/mqtt/messages');
        const msgs = await resp.json();
        msgs.forEach(m => handleMQTTMessage(m._topic || 'unknown', JSON.stringify(m)));
    } catch (e) { console.log('No previous messages'); }
}

window.addEventListener('load', () => {
    const saved = localStorage.getItem('dash_mqtt');
    if (saved) {
        const cfg = JSON.parse(saved);
        document.getElementById('dMqttServer').value = cfg.server || '';
        document.getElementById('dMqttPort').value = cfg.port || 9001;
        document.getElementById('dMqttUser').value = cfg.user || '';
        document.getElementById('dMqttPass').value = cfg.pass || '';
    }
    loadMessages();
});
