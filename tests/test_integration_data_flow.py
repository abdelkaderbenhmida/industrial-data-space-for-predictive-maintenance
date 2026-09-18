import csv
import json
import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestSensorDataGeneratorIntegration:
    def test_generator_produces_valid_readings(self):
        from data_generator import SensorDataGenerator
        gen = SensorDataGenerator("FactoryA", seed=42)
        ts = datetime.now()
        reading = gen.generate_reading(ts)
        assert reading["factory_id"] == "FactoryA"
        assert "timestamp" in reading
        assert "temperature" in reading
        assert "vibrations" in reading
        assert "pressure" in reading
        assert "humidity" in reading
        assert "power_consumption" in reading
        assert reading["status"] in ("normal", "failure")

    def test_generator_respects_sensor_bounds(self):
        from data_generator import SensorDataGenerator
        gen = SensorDataGenerator("FactoryB", seed=42)
        ts = datetime.now()
        for _ in range(200):
            reading = gen.generate_reading(ts)
            assert 20.0 <= reading["temperature"] <= 120.0
            assert 0.0 <= reading["vibrations"] <= 5.0
            assert 10.0 <= reading["pressure"] <= 25.0
            assert 10.0 <= reading["humidity"] <= 90.0
            assert 50.0 <= reading["power_consumption"] <= 500.0

    def test_multi_factory_generator_produces_all_factories(self):
        from data_generator import MultiFactoryGenerator
        gen = MultiFactoryGenerator(seed=42)
        ts = datetime.now()
        readings = gen.generate_all(ts)
        factory_ids = {r["factory_id"] for r in readings}
        assert factory_ids == {"FactoryA", "FactoryB", "FactoryC"}
        assert len(readings) == 3

    def test_multi_factory_batch_generation(self):
        from data_generator import MultiFactoryGenerator
        gen = MultiFactoryGenerator(seed=42)
        start = datetime(2025, 1, 1, 0, 0, 0)
        readings = gen.generate_batch(start, count=5, interval_seconds=10)
        assert len(readings) == 15
        timestamps = {r["timestamp"] for r in readings}
        assert len(timestamps) == 5


class TestIoTSimulatorToFileSystemIntegration:
    def test_generate_batch_writes_csv_files(self):
        from simulator import IoTSimulator
        with tempfile.TemporaryDirectory() as tmpdir:
            sim = IoTSimulator(
                data_dir=tmpdir,
                factory_ids=["FactoryA", "FactoryB"],
                interval_seconds=1,
                seed=42,
            )
            sim.generate_batch(count=3, interval_seconds=1)
            factory_a_dir = Path(tmpdir) / "FactoryA"
            assert factory_a_dir.exists()
            csv_files = list(factory_a_dir.glob("readings_*.csv"))
            assert len(csv_files) == 1
            with open(csv_files[0]) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            assert len(rows) == 3
            assert rows[0]["factory_id"] == "FactoryA"

    def test_batch_writes_all_factories(self):
        from simulator import IoTSimulator
        with tempfile.TemporaryDirectory() as tmpdir:
            sim = IoTSimulator(
                data_dir=tmpdir,
                factory_ids=["FactoryA", "FactoryB", "FactoryC"],
                seed=42,
            )
            sim.generate_batch(count=2)
            for fid in ["FactoryA", "FactoryB", "FactoryC"]:
                assert (Path(tmpdir) / fid).exists()
                csv_files = list((Path(tmpdir) / fid).glob("readings_*.csv"))
                assert len(csv_files) == 1
                with open(csv_files[0]) as f:
                    rows = list(csv.DictReader(f))
                assert len(rows) == 2

    def test_csv_has_correct_headers(self):
        from simulator import IoTSimulator
        with tempfile.TemporaryDirectory() as tmpdir:
            sim = IoTSimulator(data_dir=tmpdir, seed=42)
            sim.generate_batch(count=1)
            csv_files = list(Path(tmpdir).glob("FactoryA/readings_*.csv"))
            with open(csv_files[0]) as f:
                reader = csv.reader(f)
                headers = next(reader)
            expected = [
                "factory_id", "timestamp", "temperature", "vibrations",
                "pressure", "humidity", "power_consumption", "status",
            ]
            assert headers == expected

    def test_csv_status_values_are_valid(self):
        from simulator import IoTSimulator
        with tempfile.TemporaryDirectory() as tmpdir:
            sim = IoTSimulator(data_dir=tmpdir, seed=42)
            sim.generate_batch(count=20)
            csv_files = list(Path(tmpdir).glob("FactoryA/readings_*.csv"))
            with open(csv_files[0]) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    assert row["status"] in ("normal", "failure")

    def test_simulator_tracks_statistics(self):
        from simulator import IoTSimulator
        with tempfile.TemporaryDirectory() as tmpdir:
            sim = IoTSimulator(data_dir=tmpdir, seed=42)
            sim.generate_batch(count=10)
            assert "FactoryA" in sim._stats
            stats = sim._stats["FactoryA"]
            assert stats["total"] == 10
            assert stats["normal"] + stats["failure"] == 10

    def test_sensor_stats_are_tracked_per_sensor(self):
        from simulator import IoTSimulator
        with tempfile.TemporaryDirectory() as tmpdir:
            sim = IoTSimulator(data_dir=tmpdir, seed=42)
            sim.generate_batch(count=5)
            stats = sim._stats["FactoryA"]["sensors"]
            for sensor in ["temperature", "vibrations", "pressure", "humidity", "power_consumption"]:
                assert sensor in stats
                assert stats[sensor]["count"] == 5
                assert stats[sensor]["min"] <= stats[sensor]["max"]


class TestIoTToMQTTFlow:
    def test_mqtt_publisher_topic_format(self):
        from mqtt_publisher import MQTTPublisher
        pub = MQTTPublisher("FactoryA")
        assert pub.topic == "factory/FactoryA/sensors"

    def test_mqtt_publisher_custom_topic_prefix(self):
        from mqtt_publisher import MQTTPublisher
        pub = MQTTPublisher("FactoryB", topic_prefix="industrial")
        assert pub.topic == "industrial/FactoryB/sensors"

    def test_mqtt_publisher_initial_state(self):
        from mqtt_publisher import MQTTPublisher
        pub = MQTTPublisher("FactoryC")
        assert not pub.is_connected
        assert pub.publish_count == 0
        assert pub.factory_id == "FactoryC"

    def test_mqtt_publish_fails_when_not_connected(self):
        from mqtt_publisher import MQTTPublisher
        pub = MQTTPublisher("FactoryA")
        result = pub.publish({"temperature": 65.0, "status": "normal"})
        assert result is False
        assert pub.publish_count == 0

    def test_mqtt_publish_json_fails_when_not_connected(self):
        from mqtt_publisher import MQTTPublisher
        pub = MQTTPublisher("FactoryA")
        result = pub.publish_json('{"temperature": 65.0}')
        assert result is False

    def test_mqtt_publish_callback_invoked(self):
        from mqtt_publisher import MQTTPublisher
        callback = MagicMock()
        pub = MQTTPublisher("FactoryA", on_publish_callback=callback)
        pub._connected = True
        pub._client = MagicMock()
        pub._client.publish.return_value = MagicMock(rc=0)
        sensor_data = {"temperature": 65.0, "status": "normal"}
        result = pub.publish(sensor_data)
        assert result is True
        callback.assert_called_once()
        assert callback.call_args[0][0] == "factory/FactoryA/sensors"
        assert callback.call_args[0][1] == sensor_data

    def test_mqtt_disconnect_resets_state(self):
        from mqtt_publisher import MQTTPublisher
        pub = MQTTPublisher("FactoryA")
        pub._connected = True
        pub._running = True
        pub._client = MagicMock()
        pub.disconnect()
        assert not pub.is_connected
        assert not pub._running


class TestEndToEndDataFlow:
    def test_generate_write_and_read_csv(self):
        from simulator import IoTSimulator
        with tempfile.TemporaryDirectory() as tmpdir:
            sim = IoTSimulator(data_dir=tmpdir, seed=42)
            sim.generate_batch(count=5)
            csv_path = list(Path(tmpdir).glob("FactoryA/readings_*.csv"))[0]
            with open(csv_path) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            assert len(rows) == 5
            first = rows[0]
            assert float(first["temperature"]) > 0
            assert first["status"] in ("normal", "failure")

    def test_sensor_data_matches_mqtt_payload_format(self):
        from data_generator import MultiFactoryGenerator
        gen = MultiFactoryGenerator(seed=42)
        ts = datetime.now()
        readings = gen.generate_all(ts)
        for reading in readings:
            payload = json.dumps(reading, default=str)
            parsed = json.loads(payload)
            assert "factory_id" in parsed
            assert "timestamp" in parsed
            assert "temperature" in parsed
            assert "status" in parsed

    def test_multiple_factories_independent_generation(self):
        from data_generator import SensorDataGenerator
        gen_a = SensorDataGenerator("FactoryA", seed=42)
        gen_b = SensorDataGenerator("FactoryB", seed=42)
        ts = datetime.now()
        reading_a = gen_a.generate_reading(ts)
        reading_b = gen_b.generate_reading(ts)
        assert reading_a["factory_id"] == "FactoryA"
        assert reading_b["factory_id"] == "FactoryB"
        assert reading_a["factory_id"] != reading_b["factory_id"]

    def test_full_pipeline_generate_to_file_with_all_sensors(self):
        from simulator import IoTSimulator
        with tempfile.TemporaryDirectory() as tmpdir:
            sim = IoTSimulator(data_dir=tmpdir, seed=42)
            sim.generate_batch(count=10)
            csv_path = list(Path(tmpdir).glob("FactoryA/readings_*.csv"))[0]
            with open(csv_path) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            assert len(rows) == 10
            for row in rows:
                for sensor in ["temperature", "vibrations", "pressure", "humidity", "power_consumption"]:
                    val = float(row[sensor])
                    assert isinstance(val, float)

    def test_failure_readings_captured_in_stats(self):
        from simulator import IoTSimulator
        with tempfile.TemporaryDirectory() as tmpdir:
            sim = IoTSimulator(data_dir=tmpdir, seed=42)
            sim.generate_batch(count=100)
            total = sum(sim._stats[fid]["total"] for fid in sim._stats)
            assert total == 300
            failure_total = sum(sim._stats[fid]["failure"] for fid in sim._stats)
            assert failure_total >= 0
