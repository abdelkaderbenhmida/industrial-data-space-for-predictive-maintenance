import json
import logging
from typing import Any, Callable, Optional

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MQTTPublisher:
    def __init__(
        self,
        factory_id: str,
        broker_host: str = "localhost",
        broker_port: int = 1883,
        publish_interval: float = 5.0,
        topic_prefix: str = "factory",
        client_id: str = "",
        username: Optional[str] = None,
        password: Optional[str] = None,
        keepalive: int = 60,
        qos: int = 1,
        on_publish_callback: Optional[Callable[[str, Any], None]] = None,
    ):
        self.factory_id = factory_id
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.publish_interval = publish_interval
        self.topic_prefix = topic_prefix
        self.qos = qos
        self.keepalive = keepalive
        self.on_publish_callback = on_publish_callback

        self.topic = f"{topic_prefix}/{factory_id}/sensors"

        self._client = mqtt.Client(
            client_id=client_id or f"factory-{factory_id}",
            protocol=mqtt.MQTTv311,
        )

        if username is not None:
            self._client.username_pw_set(username, password)

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_publish = self._on_publish

        self._connected = False
        self._running = False
        self._publish_count = 0

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: dict,
        rc: int,
    ) -> None:
        if rc == 0:
            self._connected = True
            logger.info(
                "Connected to MQTT broker at %s:%s (factory=%s)",
                self.broker_host,
                self.broker_port,
                self.factory_id,
            )
        else:
            self._connected = False
            rc_descriptions = {
                1: "incorrect protocol version",
                2: "invalid client identifier",
                3: "server unavailable",
                4: "bad username or password",
                5: "not authorized",
            }
            description = rc_descriptions.get(rc, f"unknown error (rc={rc})")
            logger.error(
                "MQTT connection failed for factory %s: %s",
                self.factory_id,
                description,
            )

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        rc: int,
    ) -> None:
        self._connected = False
        if rc != 0:
            logger.warning(
                "Unexpected MQTT disconnect from factory %s (rc=%s)",
                self.factory_id,
                rc,
            )

    def _on_publish(
        self,
        client: mqtt.Client,
        userdata: Any,
        mid: int,
    ) -> None:
        logger.debug(
            "Published message mid=%s on factory %s topic=%s",
            mid,
            self.factory_id,
            self.topic,
        )

    def connect(self) -> bool:
        try:
            self._client.connect(
                self.broker_host,
                self.broker_port,
                self.keepalive,
            )
            self._client.loop_start()
            logger.info(
                "MQTT client connecting for factory %s...",
                self.factory_id,
            )
            return True
        except ConnectionRefusedError:
            logger.error(
                "MQTT broker refused connection at %s:%s",
                self.broker_host,
                self.broker_port,
            )
            return False
        except OSError as e:
            logger.error(
                "MQTT connection error for factory %s: %s",
                self.factory_id,
                e,
            )
            return False

    def disconnect(self) -> None:
        self._running = False
        self._client.loop_stop()
        self._client.disconnect()
        self._connected = False
        logger.info("MQTT client disconnected for factory %s", self.factory_id)

    def publish(self, sensor_data: dict) -> bool:
        if not self._connected:
            logger.warning(
                "Cannot publish — not connected (factory=%s)",
                self.factory_id,
            )
            return False

        payload = json.dumps(sensor_data, default=str)
        result = self._client.publish(self.topic, payload, qos=self.qos)

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            self._publish_count += 1
            logger.debug(
                "Published sensor data for factory %s (msg #%s)",
                self.factory_id,
                self._publish_count,
            )
            if self.on_publish_callback:
                self.on_publish_callback(self.topic, sensor_data)
            return True
        else:
            logger.error(
                "Publish failed for factory %s (rc=%s)",
                self.factory_id,
                result.rc,
            )
            return False

    def publish_json(self, payload: str) -> bool:
        if not self._connected:
            logger.warning(
                "Cannot publish — not connected (factory=%s)",
                self.factory_id,
            )
            return False

        result = self._client.publish(self.topic, payload, qos=self.qos)

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            self._publish_count += 1
            return True
        else:
            logger.error(
                "Publish failed for factory %s (rc=%s)",
                self.factory_id,
                result.rc,
            )
            return False

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def publish_count(self) -> int:
        return self._publish_count

    def __enter__(self) -> "MQTTPublisher":
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.disconnect()
