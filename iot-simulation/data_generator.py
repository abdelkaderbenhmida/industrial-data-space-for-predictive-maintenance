import random
import math
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np


class AI4IDataGenerator:
    """Generator that serves real data from the AI4I 2020 predictive maintenance dataset.

    Maps AI4I columns to expected sensor format:
    - Air temperature [K] → temperature (°C)
    - Process temperature [K] → power_consumption (derived)
    - Rotational speed [rpm] → vibrations (normalized)
    - Torque [Nm] → pressure (normalized)
    - Tool wear [min] → humidity (derived)
    - Machine failure / failure types → status

    Product Type (L/M/H) maps to FactoryA/FactoryB/FactoryC
    """

    TYPE_TO_FACTORY = {
        'L': 'FactoryA',  # Low
        'M': 'FactoryB',  # Medium
        'H': 'FactoryC',  # High
    }

    FACTORY_TO_TYPE = {v: k for k, v in TYPE_TO_FACTORY.items()}

    # Normalization ranges for derived sensors
    VIBRATION_RANGE = (0.0, 5.0)      # Rotational speed 1100-3000 rpm → 0-5
    PRESSURE_RANGE = (10.0, 25.0)     # Torque 3-80 Nm → 10-25
    HUMIDITY_RANGE = (10.0, 90.0)     # Tool wear 0-250 min → 10-90
    POWER_RANGE = (50.0, 500.0)       # Process temp 305-315 K → 50-500
    TEMP_C_RANGE = (20.0, 120.0)      # Air temp 295-305 K → 20-32°C → scaled

    def __init__(self, factory_id: str, csv_path: str = "ai4i2020.csv", seed: int | None = None):
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        self.factory_id = factory_id
        self.product_type = self.FACTORY_TO_TYPE.get(factory_id, 'L')

        # Load and filter dataset
        self.csv_path = Path(csv_path)
        if not self.csv_path.exists():
            # Try relative to project root
            self.csv_path = Path(__file__).parent.parent / csv_path

        self.df = pd.read_csv(self.csv_path)
        self.factory_data = self.df[self.df['Type'] == self.product_type].copy().reset_index(drop=True)

        if len(self.factory_data) == 0:
            raise ValueError(f"No data for factory {factory_id} (type {self.product_type})")

        self.index = 0
        self._precompute_normalized()

    def _precompute_normalized(self):
        """Pre-compute normalized sensor values for efficiency."""
        df = self.factory_data

        # Temperature: Air temp K → °C
        self.factory_data['temp_c'] = df['Air temperature [K]'] - 273.15

        # Vibrations: Rotational speed → normalized 0-5
        rpm_min, rpm_max = df['Rotational speed [rpm]'].min(), df['Rotational speed [rpm]'].max()
        self.factory_data['vibrations'] = np.interp(
            df['Rotational speed [rpm]'], [rpm_min, rpm_max], list(self.VIBRATION_RANGE)
        )

        # Pressure: Torque → normalized 10-25
        torque_min, torque_max = df['Torque [Nm]'].min(), df['Torque [Nm]'].max()
        self.factory_data['pressure'] = np.interp(
            df['Torque [Nm]'], [torque_min, torque_max], list(self.PRESSURE_RANGE)
        )

        # Humidity: Tool wear → normalized 10-90
        wear_min, wear_max = df['Tool wear [min]'].min(), df['Tool wear [min]'].max()
        self.factory_data['humidity'] = np.interp(
            df['Tool wear [min]'], [wear_min, wear_max], list(self.HUMIDITY_RANGE)
        )

        # Power consumption: Process temperature → normalized 50-500
        pt_min, pt_max = df['Process temperature [K]'].min(), df['Process temperature [K]'].max()
        self.factory_data['power_consumption'] = np.interp(
            df['Process temperature [K]'], [pt_min, pt_max], list(self.POWER_RANGE)
        )

        # Status: any failure type = failure
        failure_cols = ['Machine failure', 'TWF', 'HDF', 'PWF', 'OSF', 'RNF']
        self.factory_data['status'] = df[failure_cols].any(axis=1).map({True: 'failure', False: 'normal'})

        # Add small noise for realism
        noise_factor = 0.02
        for col in ['temp_c', 'vibrations', 'pressure', 'humidity', 'power_consumption']:
            noise = np.random.normal(0, self.factory_data[col].std() * noise_factor, len(self.factory_data))
            self.factory_data[col] += noise

    def generate_reading(self, timestamp: datetime) -> dict:
        """Get next reading from dataset, looping when exhausted."""
        row = self.factory_data.iloc[self.index % len(self.factory_data)]
        self.index += 1

        return {
            "factory_id": self.factory_id,
            "timestamp": timestamp.isoformat(),
            "temperature": round(float(row['temp_c']), 2),
            "vibrations": round(float(row['vibrations']), 2),
            "pressure": round(float(row['pressure']), 2),
            "humidity": round(float(row['humidity']), 2),
            "power_consumption": round(float(row['power_consumption']), 2),
            "status": row['status'],
        }


class SensorDataGenerator:
    """Fallback synthetic generator (kept for compatibility)."""
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
    """Generator that uses AI4I real data for each factory."""

    def __init__(self, factory_ids: list[str] | None = None, csv_path: str = "ai4i2020.csv", seed: int | None = None, use_real_data: bool = True):
        self.factory_ids = factory_ids or ["FactoryA", "FactoryB", "FactoryC"]
        dataset_path = Path(csv_path)
        if not dataset_path.exists():
            dataset_path = Path(__file__).parent.parent / csv_path
        # Container images may intentionally omit the large source dataset.
        # Keep the simulator operational with the deterministic synthetic model.
        self.use_real_data = use_real_data and dataset_path.exists()

        if self.use_real_data:
            self.generators = {
                fid: AI4IDataGenerator(fid, csv_path=str(dataset_path), seed=seed)
                for fid in self.factory_ids
            }
        else:
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
