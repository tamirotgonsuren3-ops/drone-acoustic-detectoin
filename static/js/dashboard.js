let mqttClient = null;
let detections = [];

// Connect
function connectDashboardMQTT() {
    const server = document.getElementById('dMqttServer').value.trim();
    const port = document.getElementById('dMqttPort').value || 1883;
    const user = document.getElementById('dMqttUser').value.trim();
    const pass = document.getElementById('dMqttPass').value;

    if (!server) {
        alert('Enter MQTT server address');
        return;
    }

    const clientId = 'dashboard_' + Math.random().toString(16).substr(2, 8);

    let connectUrl;
    if (port === 443 || port === '443') {
        connectUrl = `wss://${server}:${port}/mqtt`;
    } else {
        connectUrl = `ws://${server}:${port}/mqtt`;
    }

    try {
        if (mqttClient) {
            mqttClient.end();
        }

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
            mqttClient.subscribe('detected/#');
            addLogLine('SYSTEM', 'Subscribed to detected/sound/#');
        });

        mqttClient.on('error', (err) => {
            setDashStatus(false);
            addLogLine('ERROR', err.message);
        });

        mqttClient.on('close', () => {
            setDashStatus(false);
            addLogLine('SYSTEM', 'Connection closed');
        });

        mqttClient.on('message', (topic, message) => {
            handleMQTTMessage(topic, message.toString());
        });

        localStorage.setItem('dash_mqtt', JSON.stringify({ server, port, user, pass }));
    } catch (e) {
        addLogLine('ERROR', 'Connect failed: ' + e.message);
    }
}

function setDashStatus(connected) {
    const dot = document.getElementById('dashConnStatus');
    const text = document.getElementById('dashConnText');
    if (connected) {
        dot.className = 'status-dot connected';
        text.textContent = 'Connected';
    } else {
        dot.className = 'status-dot disconnected';
        text.textContent = 'Disconnected';
    }
}

function handleMQTTMessage(topic, payload) {
    addLogLine(topic, payload);

    try {
        const data = JSON.parse(payload);
        data._topic = topic;
        data._received_at = new Date().toISOString();
        detections.push(data);

        updateTable();
        updateStats();
        updateFilters();
    } catch (e) {
        console.log('Non-JSON message:', payload);
    }
}

function updateTable() {
    const filtered = getFilteredDetections();
    const tbody = document.getElementById('detectionBody');

    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="no-data">No detections yet</td></tr>';
        return;
    }

    tbody.innerHTML = filtered.map((d, i) => `
        <tr>
            <td>${i + 1}</td>
            <td>${formatTime(d.datetime || d._received_at)}</td>
            <td>${d.name || '-'}</td>
            <td><strong>${d.detected_sound || '-'}</strong></td>
            <td>${d.confidence ? (d.confidence * 100).toFixed(1) + '%' : '-'}</td>
            <td>${d.lat != null ? d.lat.toFixed(5) : '-'}</td>
            <td>${d.long != null ? d.long.toFixed(5) : '-'}</td>
            <td>${d.direction || '-'}</td>
            <td>${d.tilted_degree != null ? d.tilted_degree.toFixed(1) + '\u00B0' : '-'}</td>
        </tr>
    `).join('');

    tbody.parentElement.scrollTop = tbody.parentElement.scrollHeight;
}

function updateStats() {
    document.getElementById('totalDetections').textContent = detections.length;

    const devices = new Set(detections.map(d => d.name).filter(Boolean));
    document.getElementById('uniqueDevices').textContent = devices.size;

    const sounds = new Set(detections.map(d => d.detected_sound).filter(Boolean));
    document.getElementById('uniqueSounds').textContent = sounds.size;
}

function updateFilters() {
    const deviceSelect = document.getElementById('filterDevice');
    const soundSelect = document.getElementById('filterSound');

    const currentDevice = deviceSelect.value;
    const currentSound = soundSelect.value;

    const devices = [...new Set(detections.map(d => d.name).filter(Boolean))].sort();
    const sounds = [...new Set(detections.map(d => d.detected_sound).filter(Boolean))].sort();

    deviceSelect.innerHTML = '<option value="">All Devices</option>' +
        devices.map(d => `<option value="${d}" ${d === currentDevice ? 'selected' : ''}>${d}</option>`).join('');

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

function applyFilters() {
    updateTable();
}

function clearFilters() {
    document.getElementById('filterDevice').value = '';
    document.getElementById('filterSound').value = '';
    updateTable();
}

function exportCSV() {
    const filtered = getFilteredDetections();
    if (filtered.length === 0) {
        alert('No data to export');
        return;
    }

    const headers = ['Time', 'Device', 'Sound', 'Confidence', 'Latitude', 'Longitude', 'Direction', 'Tilt'];
    const rows = filtered.map(d => [
        d.datetime || d._received_at || '',
        d.name || '',
        d.detected_sound || '',
        d.confidence || '',
        d.lat || '',
        d.long || '',
        d.direction || '',
        d.tilted_degree || ''
    ]);

    let csv = headers.join(',') + '\n';
    rows.forEach(row => {
        csv += row.map(v => `"${v}"`).join(',') + '\n';
    });

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
    line.innerHTML = `<span class="timestamp">[${time}]</span> <span class="topic">${topic}</span> <span class="payload">${payload.length > 200 ? payload.substring(0, 200) + '...' : payload}</span>`;
    container.appendChild(line);

    while (container.children.length > 100) {
        container.removeChild(container.firstChild);
    }

    container.scrollTop = container.scrollHeight;
}

function formatTime(isoString) {
    if (!isoString) return '-';
    try {
        const d = new Date(isoString);
        return d.toLocaleString();
    } catch {
        return isoString;
    }
}

// Load previous messages
async function loadMessages() {
    try {
        const resp = await fetch('/api/mqtt/messages');
        const msgs = await resp.json();
        msgs.forEach(m => handleMQTTMessage(m._topic || 'unknown', JSON.stringify(m)));
    } catch (e) {
        console.log('No previous messages');
    }
}

// Init
window.addEventListener('load', () => {
    const saved = localStorage.getItem('dash_mqtt');
    if (saved) {
        const cfg = JSON.parse(saved);
        document.getElementById('dMqttServer').value = cfg.server || '';
        document.getElementById('dMqttPort').value = cfg.port || 1883;
        document.getElementById('dMqttUser').value = cfg.user || '';
        document.getElementById('dMqttPass').value = cfg.pass || '';
    }
    loadMessages();
});
