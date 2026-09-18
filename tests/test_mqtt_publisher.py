import json
from datetime import datetime
from unittest.mock import MagicMock, patch, call

import pytest

from mqtt_publisher import MQTTPublisher


@pytest.fixture
def publisher():
    return MQTTPublisher(
        factory_id="FactoryA",
        broker_host="localhost",
        broker_port=1883,
        publish_interval=5.0,
        topic_prefix="factory",
    )


@pytest.fixture
def sample_reading():
    return {
        "factory_id": "FactoryA",
        "timestamp": "2025-01-15T10:30:00",
        "temperature": 65.0,
        "vibrations": 0.5,
        "pressure": 14.7,
        "humidity": 45.0,
        "power_consumption": 150.0,
        "status": "normal",
    }


class TestMQTTPublisherInit:
    def test_topic_format(self, publisher):
        assert publisher.topic == "factory/FactoryA/sensors"

    def test_custom_topic_prefix(self):
        pub = MQTTPublisher("FactoryB", topic_prefix="plant")
        assert pub.topic == "plant/FactoryB/sensors"

    def test_default_broker(self):
        pub = MQTTPublisher("FactoryA")
        assert pub.broker_host == "localhost"
        assert pub.broker_port == 1883

    def test_custom_broker(self):
        pub = MQTTPublisher("FactoryA", broker_host="mqtt.example.com", broker_port=8883)
        assert pub.broker_host == "mqtt.example.com"
        assert pub.broker_port == 8883

    def test_not_connected_initially(self, publisher):
        assert not publisher.is_connected

    def test_publish_count_zero_initially(self, publisher):
        assert publisher.publish_count == 0

    def test_qos_setting(self):
        pub = MQTTPublisher("FactoryA", qos=2)
        assert pub.qos == 2


class TestMQTTPublisherCallbacks:
    def test_on_connect_success(self, publisher):
        publisher._on_connect(None, None, {}, 0)
        assert publisher.is_connected

    def test_on_connect_failure_rc1(self, publisher):
        publisher._on_connect(None, None, {}, 1)
        assert not publisher.is_connected

    def test_on_connect_failure_rc3(self, publisher):
        publisher._on_connect(None, None, {}, 3)
        assert not publisher.is_connected

    def test_on_connect_failure_rc5(self, publisher):
        publisher._on_connect(None, None, {}, 5)
        assert not publisher.is_connected

    def test_on_disconnect_normal(self, publisher):
        publisher._connected = True
        publisher._on_disconnect(None, None, 0)
        assert not publisher.is_connected

    def test_on_disconnect_unexpected(self, publisher):
        publisher._connected = True
        publisher._on_disconnect(None, None, 1)
        assert not publisher.is_connected

    def test_on_publish_no_error(self, publisher):
        publisher._on_publish(None, None, 1)


class TestMQTTPublisherConnect:
    @patch("mqtt_publisher.mqtt.Client")
    def test_connect_success(self, MockClient):
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        pub = MQTTPublisher("FactoryA")
        result = pub.connect()
        assert result is True
        mock_client.connect.assert_called_once_with("localhost", 1883, 60)
        mock_client.loop_start.assert_called_once()

    @patch("mqtt_publisher.mqtt.Client")
    def test_connect_connection_refused(self, MockClient):
        mock_client = MagicMock()
        mock_client.connect.side_effect = ConnectionRefusedError
        MockClient.return_value = mock_client
        pub = MQTTPublisher("FactoryA")
        result = pub.connect()
        assert result is False

    @patch("mqtt_publisher.mqtt.Client")
    def test_connect_os_error(self, MockClient):
        mock_client = MagicMock()
        mock_client.connect.side_effect = OSError("Network unreachable")
        MockClient.return_value = mock_client
        pub = MQTTPublisher("FactoryA")
        result = pub.connect()
        assert result is False


class TestMQTTPublisherDisconnect:
    @patch("mqtt_publisher.mqtt.Client")
    def test_disconnect(self, MockClient):
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        pub = MQTTPublisher("FactoryA")
        pub._connected = True
        pub.disconnect()
        mock_client.loop_stop.assert_called_once()
        mock_client.disconnect.assert_called_once()
        assert not pub.is_connected


class TestMQTTPublisherPublish:
    def test_publish_when_not_connected(self, publisher):
        result = publisher.publish({"foo": "bar"})
        assert result is False

    def test_publish_success(self, publisher, sample_reading):
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.rc = 0
        mock_client.publish.return_value = mock_result
        publisher._client = mock_client
        publisher._connected = True

        result = publisher.publish(sample_reading)
        assert result is True
        assert publisher.publish_count == 1
        mock_client.publish.assert_called_once()

    def test_publish_failure_rc(self, publisher, sample_reading):
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.rc = 1
        mock_client.publish.return_value = mock_result
        publisher._client = mock_client
        publisher._connected = True

        result = publisher.publish(sample_reading)
        assert result is False
        assert publisher.publish_count == 0

    def test_publish_callback_triggered(self, publisher, sample_reading):
        callback = MagicMock()
        publisher.on_publish_callback = callback

        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.rc = 0
        mock_client.publish.return_value = mock_result
        publisher._client = mock_client
        publisher._connected = True

        publisher.publish(sample_reading)
        callback.assert_called_once_with(publisher.topic, sample_reading)

    def test_publish_json_success(self, publisher):
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.rc = 0
        mock_client.publish.return_value = mock_result
        publisher._client = mock_client
        publisher._connected = True

        payload = json.dumps({"key": "value"})
        result = publisher.publish_json(payload)
        assert result is True
        assert publisher.publish_count == 1

    def test_publish_json_not_connected(self, publisher):
        result = publisher.publish_json('{"key": "value"}')
        assert result is False

    def test_publish_json_failure(self, publisher):
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.rc = 1
        mock_client.publish.return_value = mock_result
        publisher._client = mock_client
        publisher._connected = True

        result = publisher.publish_json('{"key": "value"}')
        assert result is False

    def test_publish_payload_is_json(self, publisher, sample_reading):
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.rc = 0
        mock_client.publish.return_value = mock_result
        publisher._client = mock_client
        publisher._connected = True

        publisher.publish(sample_reading)
        args, kwargs = mock_client.publish.call_args
        payload_str = args[1]
        parsed = json.loads(payload_str)
        assert parsed["factory_id"] == "FactoryA"
        assert parsed["temperature"] == 65.0

    def test_publish_increments_count(self, publisher, sample_reading):
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.rc = 0
        mock_client.publish.return_value = mock_result
        publisher._client = mock_client
        publisher._connected = True

        for i in range(5):
            publisher.publish(sample_reading)
        assert publisher.publish_count == 5


class TestMQTTPublisherAuth:
    @patch("mqtt_publisher.mqtt.Client")
    def test_username_password_set(self, MockClient):
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        pub = MQTTPublisher("FactoryA", username="user", password="pass")
        mock_client.username_pw_set.assert_called_once_with("user", "pass")

    @patch("mqtt_publisher.mqtt.Client")
    def test_no_auth_when_none(self, MockClient):
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        MQTTPublisher("FactoryA")
        mock_client.username_pw_set.assert_not_called()


class TestMQTTPublisherContextManager:
    @patch("mqtt_publisher.mqtt.Client")
    def test_enter_calls_connect(self, MockClient):
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        pub = MQTTPublisher("FactoryA")
        with pub:
            mock_client.connect.assert_called_once()
            mock_client.loop_start.assert_called_once()

    @patch("mqtt_publisher.mqtt.Client")
    def test_exit_calls_disconnect(self, MockClient):
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        pub = MQTTPublisher("FactoryA")
        with pub:
            pass
        mock_client.loop_stop.assert_called()
        mock_client.disconnect.assert_called()
