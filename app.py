import os
import json
import uuid
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename
from mqtt_bridge import MQTTBridge
from audio_ml import AudioMLTrainer

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24).hex()
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['MODEL_FOLDER'] = os.path.join(os.path.dirname(__file__), 'models')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['MODEL_FOLDER'], exist_ok=True)

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

mqtt_bridge = None
mqtt_messages = []
devices = {}
trainer = AudioMLTrainer(app.config['MODEL_FOLDER'])

ALLOWED_EXTENSIONS = {'mp3', 'mp4', 'wav', 'ogg', 'flac', 'm4a'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify({
        'mqtt_server': os.environ.get('MQTT_SERVER', 'localhost'),
        'mqtt_port': int(os.environ.get('MQTT_PORT', 1883)),
    })


@app.route('/api/mqtt/connect', methods=['POST'])
def mqtt_connect():
    global mqtt_bridge
    data = request.json
    server = data.get('server', 'localhost')
    port = int(data.get('port', 1883))
    user = data.get('username', '')
    password = data.get('password', '')
    name = data.get('name', 'unknown')

    if mqtt_bridge:
        mqtt_bridge.disconnect()

    mqtt_bridge = MQTTBridge(
        server=server,
        port=port,
        username=user,
        password=password,
        on_message_callback=on_mqtt_message
    )
    mqtt_bridge.name = name
    connected = mqtt_bridge.connect()
    return jsonify({'connected': connected, 'name': name})


@app.route('/api/mqtt/status', methods=['GET'])
def mqtt_status():
    connected = mqtt_bridge.is_connected if mqtt_bridge else False
    return jsonify({'connected': connected})


@app.route('/api/mqtt/messages', methods=['GET'])
def mqtt_messages_list():
    return jsonify(mqtt_messages[-200:])


@app.route('/api/mqtt/publish', methods=['POST'])
def mqtt_publish():
    global mqtt_bridge
    if not mqtt_bridge or not mqtt_bridge.is_connected:
        return jsonify({'error': 'MQTT not connected'}), 400
    data = request.json
    topic = data.get('topic', 'detected/sound/')
    payload = data.get('payload', {})
    mqtt_bridge.publish(topic, json.dumps(payload))
    return jsonify({'published': True})


@app.route('/api/upload', methods=['POST'])
def upload_audio():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    sound_type = request.form.get('sound_type', '').strip()

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    if not sound_type:
        return jsonify({'error': 'Sound type is required'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed. Use mp3, mp4, wav, ogg, flac, m4a'}), 400

    filename = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
    file.save(filepath)

    return jsonify({
        'filename': unique_name,
        'original_name': filename,
        'sound_type': sound_type,
        'size': os.path.getsize(filepath)
    })


@app.route('/api/upload/list', methods=['GET'])
def list_uploads():
    files = []
    for f in os.listdir(app.config['UPLOAD_FOLDER']):
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f)
        files.append({
            'filename': f,
            'size': os.path.getsize(filepath)
        })
    return jsonify(files)


@app.route('/api/train', methods=['POST'])
def train_model():
    data = request.json or {}
    epochs = int(data.get('epochs', 50))

    uploaded_files = os.listdir(app.config['UPLOAD_FOLDER'])
    if not uploaded_files:
        return jsonify({'error': 'No uploaded files to train on'}), 400

    result = trainer.train(app.config['UPLOAD_FOLDER'], epochs=epochs)

    if result.get('success'):
        return jsonify({
            'success': True,
            'classes': result['classes'],
            'accuracy': result.get('accuracy', 0),
            'model_path': result.get('model_path', '')
        })
    else:
        return jsonify({'error': result.get('error', 'Training failed')}), 500


@app.route('/api/model/status', methods=['GET'])
def model_status():
    model_file = os.path.join(app.config['MODEL_FOLDER'], 'model.json')
    exists = os.path.exists(model_file)
    classes = []
    if exists:
        meta_file = os.path.join(app.config['MODEL_FOLDER'], 'model_meta.json')
        if os.path.exists(meta_file):
            with open(meta_file, 'r') as f:
                meta = json.load(f)
                classes = meta.get('classes', [])
    return jsonify({'trained': exists, 'classes': classes})


@app.route('/models/<path:filename>')
def serve_model(filename):
    return send_from_directory(app.config['MODEL_FOLDER'], filename)


@app.route('/api/predict', methods=['POST'])
def predict_audio():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{uuid.uuid4().hex[:8]}.wav")
    file.save(temp_path)

    try:
        result = trainer.predict(temp_path)
        return jsonify(result)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def on_mqtt_message(topic, payload):
    try:
        msg_data = json.loads(payload)
        msg_data['_topic'] = topic
        msg_data['_received_at'] = __import__('datetime').datetime.now().isoformat()
        mqtt_messages.append(msg_data)
        if len(mqtt_messages) > 500:
            mqtt_messages.pop(0)
        socketio.emit('mqtt_message', msg_data)
    except (json.JSONDecodeError, Exception):
        pass


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
