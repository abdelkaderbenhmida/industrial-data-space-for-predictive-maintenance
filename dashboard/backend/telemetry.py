import json
import logging
import os

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class TelemetrySubscriber:
    def __init__(self, on_reading):
        self.on_reading = on_reading
        self.host = os.environ.get("MQTT_BROKER_HOST", "localhost")
        self.port = int(os.environ.get("MQTT_BROKER_PORT", "1883"))
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="dashboard-api")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            client.subscribe("factory/+/sensors", qos=1)
            logger.info("Subscribed to factory telemetry")
        else:
            logger.error("MQTT subscriber connection failed: rc=%s", rc)

    def _on_message(self, client, userdata, message):
        try:
            self.on_reading(json.loads(message.payload.decode("utf-8")))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            logger.warning("Discarded invalid MQTT payload: %s", exc)

    def start(self):
        try:
            self.client.connect_async(self.host, self.port, 60)
            self.client.loop_start()
        except OSError as exc:
            logger.warning("MQTT subscriber unavailable at %s:%s: %s", self.host, self.port, exc)

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()
