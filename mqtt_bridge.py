import json
import threading
import paho.mqtt.client as mqtt


class MQTTBridge:
    def __init__(self, server='localhost', port=1883, username='', password='', on_message_callback=None):
        self.server = server
        self.port = port
        self.username = username
        self.password = password
        self.client = mqtt.Client(client_id=f"soundsense_{__import__('uuid').uuid4().hex[:8]}")
        self.is_connected = False
        self.on_message_callback = on_message_callback
        self.name = 'unknown'

        if username:
            self.client.username_pw_set(username, password)

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.is_connected = True
            client.subscribe('detected/sound/#')
            print(f"[MQTT] Connected to {self.server}:{self.port}")
        else:
            self.is_connected = False
            print(f"[MQTT] Connection failed, code={rc}")

    def _on_disconnect(self, client, userdata, rc):
        self.is_connected = False
        print(f"[MQTT] Disconnected (rc={rc})")

    def _on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode('utf-8')
            if self.on_message_callback:
                self.on_message_callback(msg.topic, payload)
        except Exception as e:
            print(f"[MQTT] Message error: {e}")

    def connect(self):
        try:
            self.client.connect_async(self.server, self.port, keepalive=60)
            self.client.loop_start()
            import time
            time.sleep(1)
            return self.is_connected
        except Exception as e:
            print(f"[MQTT] Connect error: {e}")
            return False

    def disconnect(self):
        try:
            self.client.loop_stop()
            self.client.disconnect()
            self.is_connected = False
        except Exception:
            pass

    def publish(self, topic, payload):
        if self.is_connected:
            if isinstance(payload, dict):
                payload = json.dumps(payload)
            self.client.publish(topic, payload, qos=1)
            return True
        return False

    def publish_detection(self, detection_data):
        topic = 'detected/sound/'
        payload = json.dumps(detection_data)
        return self.publish(topic, payload)
