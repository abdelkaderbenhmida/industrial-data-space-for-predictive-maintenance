import asyncio
import random
import threading
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
import json
import os
from pathlib import Path
import csv

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

try:  # Package import when launched as ``backend.main`` in Docker/Kubernetes.
    from .models import (
        AlertSeverity,
        ErrorResponse,
        FactoryInfo,
        FactorySensorSummary,
        MaintenanceAlert,
        ModelPerformance,
        SensorReading,
        SensorStats,
        SensorStatus,
        SimulationStartRequest,
        SimulationStatus,
        FederatedModelMetrics,
    )
    from .telemetry import TelemetrySubscriber
except ImportError:  # Direct import used by the local test suite.
    from models import (
        AlertSeverity,
        ErrorResponse,
        FactoryInfo,
        FactorySensorSummary,
        MaintenanceAlert,
        ModelPerformance,
        SensorReading,
        SensorStats,
        SensorStatus,
        SimulationStartRequest,
        SimulationStatus,
        FederatedModelMetrics,
    )
    from telemetry import TelemetrySubscriber

FACTORY_IDS = ["FactoryA", "FactoryB", "FactoryC"]

SENSOR_BASELINES = {
    "FactoryA": {
        "temperature": 65.0,
        "vibrations": 0.5,
        "pressure": 14.7,
        "humidity": 45.0,
        "power_consumption": 150.0,
    },
    "FactoryB": {
        "temperature": 72.0,
        "vibrations": 0.8,
        "pressure": 15.0,
        "humidity": 50.0,
        "power_consumption": 200.0,
    },
    "FactoryC": {
        "temperature": 60.0,
        "vibrations": 0.3,
        "pressure": 14.0,
        "humidity": 55.0,
        "power_consumption": 180.0,
    },
}

SENSOR_RANGES = {
    "temperature": (20.0, 120.0, 5.0),
    "vibrations": (0.0, 5.0, 0.15),
    "pressure": (10.0, 25.0, 1.2),
    "humidity": (10.0, 90.0, 8.0),
    "power_consumption": (50.0, 500.0, 20.0),
}


class AppState:
    def __init__(self):
        self.sensor_readings: dict[str, list[SensorReading]] = {
            fid: [] for fid in FACTORY_IDS
        }
        self.alerts: list[MaintenanceAlert] = []
        self.model_history: list[FederatedModelMetrics] = []
        self.simulation_running: bool = False
        self.simulation_start_time: float | None = None
        self.simulation_interval: int = 10
        self.simulation_factory_ids: list[str] = list(FACTORY_IDS)
        self.readings_generated: int = 0
        self._sim_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._sensor_state: dict[str, dict[str, float]] = {
            fid: dict(baselines) for fid, baselines in SENSOR_BASELINES.items()
        }
        self._alert_counter = 0
        self.metrics_file = Path(os.environ.get("METRICS_FILE", "runtime/federated_metrics.json"))
        self.load_local_telemetry()

    def load_local_telemetry(self) -> None:
        """Restore recent, locally owned factory CSV telemetry on API restart."""
        data_dir = Path(os.environ.get("LOCAL_DATA_DIR", "iot-simulation/data"))
        if not data_dir.exists():
            return
        for csv_path in sorted(data_dir.glob("*/readings_*.csv")):
            try:
                with csv_path.open(newline="", encoding="utf-8") as stream:
                    for row in csv.DictReader(stream):
                        self.record_reading(row)
            except (OSError, ValueError):
                continue

    def _generate_reading(self, factory_id: str, timestamp: datetime) -> SensorReading:
        state = self._sensor_state.get(factory_id, SENSOR_BASELINES.get(factory_id, SENSOR_BASELINES["FactoryA"]))
        sensor_vals = {}
        for sensor, current in state.items():
            _, _, std = SENSOR_RANGES[sensor]
            noise = random.gauss(0, std * 0.3)
            new_val = current + noise
            sensor_vals[sensor] = round(max(SENSOR_RANGES[sensor][0], min(SENSOR_RANGES[sensor][1], new_val)), 2)
        self._sensor_state[factory_id] = sensor_vals
        status = SensorStatus.normal
        if random.random() < 0.05:
            status = SensorStatus.failure
            for sensor in sensor_vals:
                _, mx, _ = SENSOR_RANGES[sensor]
                sensor_vals[sensor] = round(mx * random.uniform(0.85, 0.98), 2)
        return SensorReading(
            factory_id=factory_id,
            timestamp=timestamp,
            temperature=sensor_vals["temperature"],
            vibrations=sensor_vals["vibrations"],
            pressure=sensor_vals["pressure"],
            humidity=sensor_vals["humidity"],
            power_consumption=sensor_vals["power_consumption"],
            status=status,
        )

    def _create_alert(self, reading: SensorReading):
        self._alert_counter += 1
        alerts_map = {
            "temperature": ("High temperature detected", 100.0, AlertSeverity.high),
            "vibrations": ("Abnormal vibrations", 3.0, AlertSeverity.critical),
            "pressure": ("Pressure anomaly", 20.0, AlertSeverity.medium),
            "humidity": ("Humidity out of range", 75.0, AlertSeverity.low),
            "power_consumption": ("Power consumption spike", 400.0, AlertSeverity.medium),
        }
        worst_sensor = max(
            alerts_map.keys(),
            key=lambda s: getattr(reading, s, 0),
        )
        msg, threshold, severity = alerts_map[worst_sensor]
        self.alerts.append(
            MaintenanceAlert(
                alert_id=f"ALT-{self._alert_counter:04d}",
                factory_id=reading.factory_id,
                sensor_name=worst_sensor,
                severity=severity,
                message=msg,
                timestamp=reading.timestamp,
                value=getattr(reading, worst_sensor),
                threshold=threshold,
            )
        )

    def record_reading(self, payload: dict) -> SensorReading:
        """Accept one validated record from the MQTT subscriber or ingest API."""
        reading = SensorReading.model_validate(payload)
        if reading.factory_id not in FACTORY_IDS:
            raise ValueError(f"Unknown factory '{reading.factory_id}'")
        self.sensor_readings[reading.factory_id].append(reading)
        self.sensor_readings[reading.factory_id] = self.sensor_readings[reading.factory_id][-500:]
        self.readings_generated += 1
        if reading.status == SensorStatus.failure:
            self._create_alert(reading)
        return reading

    def load_model_history(self) -> list[FederatedModelMetrics]:
        if not self.metrics_file.exists():
            return []
        try:
            with self.metrics_file.open(encoding="utf-8") as stream:
                return [FederatedModelMetrics.model_validate(item) for item in json.load(stream)]
        except (OSError, json.JSONDecodeError, ValueError):
            return []

    def _simulation_loop(self):
        while not self._stop_event.is_set():
            now = datetime.now()
            for fid in self.simulation_factory_ids:
                reading = self._generate_reading(fid, now)
                self.record_reading(reading.model_dump())
            self._stop_event.wait(timeout=self.simulation_interval)

    def start_simulation(self, req: SimulationStartRequest) -> SimulationStatus:
        if self.simulation_running:
            return self.get_simulation_status()
        self.simulation_running = True
        self.simulation_start_time = time.time()
        self.simulation_interval = req.interval_seconds
        self.simulation_factory_ids = req.factory_ids
        self._stop_event.clear()
        self._sim_thread = threading.Thread(target=self._simulation_loop, daemon=True)
        self._sim_thread.start()
        return self.get_simulation_status()

    def stop_simulation(self) -> SimulationStatus:
        if not self.simulation_running:
            return self.get_simulation_status()
        self._stop_event.set()
        if self._sim_thread:
            self._sim_thread.join(timeout=5)
        self.simulation_running = False
        self.simulation_start_time = None
        return self.get_simulation_status()

    def get_simulation_status(self) -> SimulationStatus:
        uptime = None
        if self.simulation_running and self.simulation_start_time:
            uptime = round(time.time() - self.simulation_start_time, 1)
        return SimulationStatus(
            running=self.simulation_running,
            factory_ids=self.simulation_factory_ids,
            interval_seconds=self.simulation_interval,
            uptime_seconds=uptime,
            readings_generated=self.readings_generated,
        )


state = AppState()
telemetry_subscriber = TelemetrySubscriber(state.record_reading)


@asynccontextmanager
async def lifespan(app: FastAPI):
    telemetry_subscriber.start()
    yield
    telemetry_subscriber.stop()
    state.stop_simulation()


app = FastAPI(
    title="Industrial IoT Dashboard API",
    description="Backend API for the federated learning industrial dashboard",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Liveness endpoint used by Docker and Kubernetes probes."""
    return {"status": "healthy", "service": "dashboard-api"}


@app.get("/api/factories", response_model=list[FactoryInfo])
async def list_factories():
    factories = []
    for fid in FACTORY_IDS:
        readings = state.sensor_readings.get(fid, [])
        last = readings[-1] if readings else None
        factories.append(
            FactoryInfo(
                factory_id=fid,
                status="connected",
                sensor_count=5,
                last_reading=last,
            )
        )
    return factories


@app.get(
    "/api/factories/{factory_id}/sensors",
    response_model=FactorySensorSummary,
    responses={404: {"model": ErrorResponse}},
)
async def get_factory_sensors(
    factory_id: str,
    limit: int = Query(default=50, ge=1, le=500),
):
    if factory_id not in FACTORY_IDS:
        raise HTTPException(status_code=404, detail=f"Factory '{factory_id}' not found")

    readings = state.sensor_readings.get(factory_id, [])
    if not readings:
        raise HTTPException(status_code=404, detail=f"No sensor data for factory '{factory_id}'")

    recent = readings[-limit:]
    sensor_names = ["temperature", "vibrations", "pressure", "humidity", "power_consumption"]

    stats_list = []
    for sensor in sensor_names:
        values = [getattr(r, sensor) for r in readings]
        stats_list.append(
            SensorStats(
                sensor_name=sensor,
                min_value=round(min(values), 2),
                max_value=round(max(values), 2),
                avg_value=round(sum(values) / len(values), 2),
                reading_count=len(values),
            )
        )

    normal_count = sum(1 for r in readings if r.status == SensorStatus.normal)
    failure_count = len(readings) - normal_count
    failure_rate = round(failure_count / len(readings) * 100, 2) if readings else 0.0

    return FactorySensorSummary(
        factory_id=factory_id,
        total_readings=len(readings),
        normal_count=normal_count,
        failure_count=failure_count,
        failure_rate=failure_rate,
        sensors=stats_list,
        recent_readings=recent,
    )


@app.get("/api/model/performance", response_model=ModelPerformance)
async def get_model_performance(
    rounds: int = Query(default=10, ge=1, le=100),
):
    history = state.load_model_history()
    if not history:
        raise HTTPException(status_code=404, detail="No model metrics available")
    history = history[-rounds:]
    current = history[-1]
    return ModelPerformance(current_model=current, history=history)


@app.post("/api/telemetry", response_model=SensorReading, status_code=201)
async def ingest_telemetry(reading: SensorReading):
    """Ingest a validated reading; production telemetry normally arrives via MQTT."""
    try:
        return state.record_reading(reading.model_dump(mode="json"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/alerts", response_model=list[MaintenanceAlert])
async def get_alerts(
    severity: AlertSeverity | None = Query(default=None),
    factory_id: str | None = Query(default=None),
    acknowledged: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    filtered = list(state.alerts)
    if severity:
        filtered = [a for a in filtered if a.severity == severity]
    if factory_id:
        filtered = [a for a in filtered if a.factory_id == factory_id]
    if acknowledged is not None:
        filtered = [a for a in filtered if a.acknowledged == acknowledged]
    filtered.sort(key=lambda a: a.timestamp, reverse=True)
    return filtered[:limit]


@app.get("/api/edc/status")
async def get_edc_status():
    """Return the health of the configured factory connectors."""
    import requests

    endpoints = [
        value.strip()
        for value in os.environ.get(
            "EDC_CONNECTORS",
            "http://localhost:8080,http://localhost:8081,http://localhost:8082",
        ).split(",")
        if value.strip()
    ]
    statuses = []
    for endpoint in endpoints:
        try:
            response = requests.get(f"{endpoint.rstrip('/')}/health", timeout=2)
            payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            statuses.append({
                "endpoint": endpoint,
                "status": payload.get("status", "unhealthy") if response.ok else "unhealthy",
                "connector_id": payload.get("connectorId"),
                "connector_name": payload.get("connectorName"),
                "assets": payload.get("assets", 0),
                "contract_definitions": payload.get("contractDefinitions", 0),
            })
        except (requests.RequestException, ValueError):
            statuses.append({"endpoint": endpoint, "status": "unavailable"})
    return statuses


@app.post(
    "/api/simulation/start",
    response_model=SimulationStatus,
    responses={409: {"model": ErrorResponse}},
)
async def start_simulation(req: SimulationStartRequest):
    if state.simulation_running:
        raise HTTPException(status_code=409, detail="Simulation already running")
    return state.start_simulation(req)


@app.post("/api/simulation/stop", response_model=SimulationStatus)
async def stop_simulation():
    return state.stop_simulation()


@app.get("/api/simulation/status", response_model=SimulationStatus)
async def simulation_status():
    return state.get_simulation_status()
