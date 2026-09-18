import random
import math
from datetime import datetime, timedelta


class SensorDataGenerator:
    # Sensor baselines and ranges per factory profile
    PROFILES = {
        "FactoryA": {
            "temperature": {"base": 65.0, "std": 5.0, "min": 20.0, "max": 120.0},
            "vibrations": {"base": 0.5, "std": 0.15, "min": 0.0, "max": 5.0},
            "pressure": {"base": 14.7, "std": 1.2, "min": 10.0, "max": 25.0},
            "humidity": {"base": 45.0, "std": 8.0, "min": 10.0, "max": 90.0},
            "power_consumption": {"base": 150.0, "std": 20.0, "min": 50.0, "max": 500.0},
        },
        "FactoryB": {
            "temperature": {"base": 72.0, "std": 4.0, "min": 20.0, "max": 120.0},
            "vibrations": {"base": 0.8, "std": 0.2, "min": 0.0, "max": 5.0},
            "pressure": {"base": 15.0, "std": 1.5, "min": 10.0, "max": 25.0},
            "humidity": {"base": 50.0, "std": 10.0, "min": 10.0, "max": 90.0},
            "power_consumption": {"base": 200.0, "std": 30.0, "min": 50.0, "max": 500.0},
        },
        "FactoryC": {
            "temperature": {"base": 60.0, "std": 6.0, "min": 20.0, "max": 120.0},
            "vibrations": {"base": 0.3, "std": 0.1, "min": 0.0, "max": 5.0},
            "pressure": {"base": 14.0, "std": 1.0, "min": 10.0, "max": 25.0},
            "humidity": {"base": 55.0, "std": 7.0, "min": 10.0, "max": 90.0},
            "power_consumption": {"base": 180.0, "std": 25.0, "min": 50.0, "max": 500.0},
        },
    }

    FAILURE_THRESHOLD = 0.03
    ANOMALY_THRESHOLD = 0.08

    def __init__(self, factory_id: str, seed: int | None = None):
        if seed is not None:
            random.seed(seed)
        self.factory_id = factory_id
        self.profile = self.PROFILES.get(factory_id, self.PROFILES["FactoryA"])
        self._state = {k: v["base"] for k, v in self.profile.items()}
        self._trend = {k: 0.0 for k in self.profile}
        self._in_failure = False
        self._failure_remaining = 0

    def generate_reading(self, timestamp: datetime) -> dict:
        self._maybe_toggle_failure()

        reading = {"factory_id": self.factory_id, "timestamp": timestamp.isoformat()}
        for sensor, cfg in self.profile.items():
            value = self._generate_sensor_value(sensor, cfg)
            reading[sensor] = round(value, 2)

        reading["status"] = "failure" if self._in_failure else "normal"
        return reading

    def _generate_sensor_value(self, sensor: str, cfg: dict) -> float:
        if self._in_failure:
            return self._failure_value(sensor, cfg)

        if random.random() < self.ANOMALY_THRESHOLD:
            return self._anomaly_value(sensor, cfg)

        trend = self._trend[sensor]
        noise = random.gauss(0, cfg["std"] * 0.3)
        self._state[sensor] += trend + noise

        drift = random.gauss(0, cfg["std"] * 0.02)
        self._trend[sensor] = max(-cfg["std"] * 0.1, min(cfg["std"] * 0.1, trend + drift))

        self._state[sensor] += math.sin(random.uniform(0, 2 * math.pi)) * cfg["std"] * 0.1

        value = max(cfg["min"], min(cfg["max"], self._state[sensor]))
        self._state[sensor] = value
        return value

    def _failure_value(self, sensor: str, cfg: dict) -> float:
        failure_modes = {
            "temperature": cfg["max"] * 0.95,
            "vibrations": cfg["max"] * 0.9,
            "pressure": cfg["max"] * 0.92,
            "humidity": cfg["max"] * 0.88,
            "power_consumption": cfg["max"] * 0.97,
        }
        target = failure_modes.get(sensor, cfg["max"])
        current = self._state[sensor]
        self._state[sensor] = current + (target - current) * 0.3 + random.gauss(0, cfg["std"] * 0.5)
        value = max(cfg["min"], min(cfg["max"], self._state[sensor]))
        self._state[sensor] = value
        return value

    def _anomaly_value(self, sensor: str, cfg: dict) -> float:
        direction = random.choice([-1, 1])
        spike = direction * random.uniform(2.0, 4.0) * cfg["std"]
        value = self._state[sensor] + spike
        return max(cfg["min"], min(cfg["max"], value))

    def _maybe_toggle_failure(self):
        if self._in_failure:
            self._failure_remaining -= 1
            if self._failure_remaining <= 0:
                self._in_failure = False
                for sensor in self.profile:
                    self._state[sensor] = self.profile[sensor]["base"]
                    self._trend[sensor] = 0.0
        else:
            if random.random() < self.FAILURE_THRESHOLD:
                self._in_failure = True
                self._failure_remaining = random.randint(5, 20)


class MultiFactoryGenerator:
    def __init__(self, factory_ids: list[str] | None = None, seed: int | None = None):
        self.factory_ids = factory_ids or ["FactoryA", "FactoryB", "FactoryC"]
        self.generators = {
            fid: SensorDataGenerator(fid, seed=seed)
            for fid in self.factory_ids
        }

    def generate_all(self, timestamp: datetime) -> list[dict]:
        return [gen.generate_reading(timestamp) for gen in self.generators.values()]

    def generate_batch(self, start: datetime, count: int, interval_seconds: int = 10) -> list[dict]:
        readings = []
        for i in range(count):
            ts = start + timedelta(seconds=i * interval_seconds)
            readings.extend(self.generate_all(ts))
        return readings
