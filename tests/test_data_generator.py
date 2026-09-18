import math
from datetime import datetime
from unittest.mock import patch

from data_generator import SensorDataGenerator, MultiFactoryGenerator


class TestSensorDataGeneratorProfiles:
    def test_known_factory_uses_own_profile(self):
        gen = SensorDataGenerator("FactoryA", seed=42)
        assert gen.factory_id == "FactoryA"
        assert gen.profile["temperature"]["base"] == 65.0

    def test_unknown_factory_falls_back_to_factory_a(self):
        gen = SensorDataGenerator("UnknownFactory", seed=1)
        assert gen.profile == SensorDataGenerator.PROFILES["FactoryA"]

    def test_all_three_factories_have_profiles(self):
        for fid in ["FactoryA", "FactoryB", "FactoryC"]:
            gen = SensorDataGenerator(fid, seed=1)
            for sensor in ["temperature", "vibrations", "pressure", "humidity", "power_consumption"]:
                assert sensor in gen.profile
                assert "base" in gen.profile[sensor]
                assert "std" in gen.profile[sensor]
                assert "min" in gen.profile[sensor]
                assert "max" in gen.profile[sensor]


class TestSensorDataGeneratorReading:
    def test_reading_has_all_required_fields(self):
        gen = SensorDataGenerator("FactoryA", seed=42)
        ts = datetime(2025, 1, 15, 10, 30, 0)
        reading = gen.generate_reading(ts)
        required = [
            "factory_id", "timestamp", "temperature", "vibrations",
            "pressure", "humidity", "power_consumption", "status",
        ]
        for field in required:
            assert field in reading, f"Missing field: {field}"

    def test_reading_timestamp_is_iso_format(self):
        gen = SensorDataGenerator("FactoryB", seed=7)
        ts = datetime(2025, 6, 1, 14, 0, 0)
        reading = gen.generate_reading(ts)
        assert reading["timestamp"] == ts.isoformat()

    def test_reading_factory_id_matches(self):
        gen = SensorDataGenerator("FactoryC", seed=10)
        reading = gen.generate_reading(datetime.now())
        assert reading["factory_id"] == "FactoryC"

    def test_reading_status_is_normal_or_failure(self):
        gen = SensorDataGenerator("FactoryA", seed=99)
        statuses = set()
        for _ in range(200):
            reading = gen.generate_reading(datetime.now())
            statuses.add(reading["status"])
        assert statuses <= {"normal", "failure"}

    def test_sensor_values_are_within_bounds(self):
        gen = SensorDataGenerator("FactoryA", seed=42)
        ts = datetime(2025, 1, 1, 0, 0, 0)
        for i in range(100):
            reading = gen.generate_reading(ts)
            for sensor, cfg in gen.profile.items():
                val = reading[sensor]
                assert cfg["min"] <= val <= cfg["max"], (
                    f"{sensor}={val} out of range [{cfg['min']}, {cfg['max']}]"
                )

    def test_sensor_values_are_floats(self):
        gen = SensorDataGenerator("FactoryA", seed=1)
        reading = gen.generate_reading(datetime.now())
        for sensor in gen.profile:
            assert isinstance(reading[sensor], float)

    def test_deterministic_with_seed(self):
        ts = datetime(2025, 3, 10, 8, 0, 0)
        r1 = SensorDataGenerator("FactoryA", seed=123).generate_reading(ts)
        r2 = SensorDataGenerator("FactoryA", seed=123).generate_reading(ts)
        assert r1 == r2

    def test_different_seeds_produce_different_values(self):
        ts = datetime(2025, 3, 10, 8, 0, 0)
        r1 = SensorDataGenerator("FactoryA", seed=1).generate_reading(ts)
        r2 = SensorDataGenerator("FactoryA", seed=999).generate_reading(ts)
        assert r1["temperature"] != r2["temperature"]


class TestFailureSimulation:
    def test_failure_status_set_during_failure_mode(self):
        gen = SensorDataGenerator("FactoryA", seed=1)
        gen._in_failure = True
        gen._failure_remaining = 4
        ts = datetime.now()
        for _ in range(3):
            reading = gen.generate_reading(ts)
            assert reading["status"] == "failure"

    def test_failure_ends_after_remaining_reaches_zero(self):
        gen = SensorDataGenerator("FactoryA", seed=1)
        gen._in_failure = True
        gen._failure_remaining = 1
        ts = datetime.now()
        gen.generate_reading(ts)
        assert not gen._in_failure

    def test_failure_values_are_high(self):
        gen = SensorDataGenerator("FactoryA", seed=1)
        gen._in_failure = True
        gen._failure_remaining = 10
        ts = datetime.now()
        reading = gen.generate_reading(ts)
        cfg = gen.profile
        for sensor in cfg:
            assert reading[sensor] >= cfg[sensor]["base"] * 0.5

    def test_normal_to_failure_toggle(self):
        gen = SensorDataGenerator("FactoryA", seed=42)
        gen._in_failure = False
        gen._failure_remaining = 0
        ts = datetime.now()
        gen._maybe_toggle_failure()
        assert isinstance(gen._in_failure, bool)

    def test_failure_resets_state_on_exit(self):
        gen = SensorDataGenerator("FactoryA", seed=1)
        gen._in_failure = True
        gen._failure_remaining = 1
        gen._state["temperature"] = 999.0
        gen._trend["temperature"] = 5.0
        gen.generate_reading(datetime.now())
        assert not gen._in_failure
        base = gen.profile["temperature"]["base"]
        assert abs(gen._state["temperature"] - base) < 20
        assert abs(gen._trend["temperature"]) < 1.0


class TestAnomalyValues:
    def test_anomaly_can_produce_spike(self):
        gen = SensorDataGenerator("FactoryA", seed=1)
        gen._in_failure = False
        cfg = gen.profile["temperature"]
        spike = gen._anomaly_value("temperature", cfg)
        assert cfg["min"] <= spike <= cfg["max"]


class TestMultiFactoryGenerator:
    def test_default_factories(self):
        mfg = MultiFactoryGenerator(seed=1)
        assert mfg.factory_ids == ["FactoryA", "FactoryB", "FactoryC"]
        assert len(mfg.generators) == 3

    def test_custom_factories(self):
        mfg = MultiFactoryGenerator(factory_ids=["FactoryA", "FactoryC"], seed=1)
        assert mfg.factory_ids == ["FactoryA", "FactoryC"]
        assert len(mfg.generators) == 2
        assert "FactoryB" not in mfg.generators

    def test_generate_all_returns_one_per_factory(self):
        mfg = MultiFactoryGenerator(seed=1)
        ts = datetime.now()
        readings = mfg.generate_all(ts)
        assert len(readings) == 3
        fids = {r["factory_id"] for r in readings}
        assert fids == {"FactoryA", "FactoryB", "FactoryC"}

    def test_generate_all_readings_have_correct_structure(self):
        mfg = MultiFactoryGenerator(seed=42)
        readings = mfg.generate_all(datetime.now())
        for r in readings:
            assert "factory_id" in r
            assert "timestamp" in r
            assert "status" in r
            assert "temperature" in r

    def test_generate_batch_count(self):
        mfg = MultiFactoryGenerator(factory_ids=["FactoryA"], seed=1)
        start = datetime(2025, 1, 1)
        readings = mfg.generate_batch(start, count=5, interval_seconds=10)
        assert len(readings) == 5

    def test_generate_batch_interval_spacing(self):
        mfg = MultiFactoryGenerator(factory_ids=["FactoryA"], seed=1)
        start = datetime(2025, 1, 1, 0, 0, 0)
        readings = mfg.generate_batch(start, count=3, interval_seconds=30)
        ts0 = datetime.fromisoformat(readings[0]["timestamp"])
        ts1 = datetime.fromisoformat(readings[1]["timestamp"])
        ts2 = datetime.fromisoformat(readings[2]["timestamp"])
        assert (ts1 - ts0).total_seconds() == 30
        assert (ts2 - ts1).total_seconds() == 30

    def test_generate_batch_multiple_factories(self):
        mfg = MultiFactoryGenerator(factory_ids=["FactoryA", "FactoryB"], seed=1)
        readings = mfg.generate_batch(datetime.now(), count=2)
        assert len(readings) == 4

    def test_factory_specific_values_differ(self):
        mfg = MultiFactoryGenerator(seed=42)
        ts = datetime.now()
        readings = mfg.generate_all(ts)
        temp_by_factory = {r["factory_id"]: r["temperature"] for r in readings}
        assert len(set(temp_by_factory.values())) > 0
