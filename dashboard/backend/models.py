from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SensorStatus(str, Enum):
    normal = "normal"
    failure = "failure"


class SensorReading(BaseModel):
    factory_id: str
    timestamp: datetime
    temperature: float
    vibrations: float
    pressure: float
    humidity: float
    power_consumption: float
    status: SensorStatus


class FactoryInfo(BaseModel):
    factory_id: str
    status: str
    sensor_count: int = 5
    last_reading: SensorReading | None = None


class SensorStats(BaseModel):
    sensor_name: str
    min_value: float
    max_value: float
    avg_value: float
    reading_count: int


class FactorySensorSummary(BaseModel):
    factory_id: str
    total_readings: int
    normal_count: int
    failure_count: int
    failure_rate: float
    sensors: list[SensorStats]
    recent_readings: list[SensorReading]


class FederatedModelMetrics(BaseModel):
    model_id: str
    round: int
    accuracy: float = Field(ge=0.0, le=1.0)
    precision: float = Field(ge=0.0, le=1.0)
    recall: float = Field(ge=0.0, le=1.0)
    f1_score: float = Field(ge=0.0, le=1.0)
    loss: float = Field(ge=0.0)
    participating_factories: list[str]
    timestamp: datetime


class ModelPerformance(BaseModel):
    current_model: FederatedModelMetrics
    history: list[FederatedModelMetrics]


class AlertSeverity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class MaintenanceAlert(BaseModel):
    alert_id: str
    factory_id: str
    sensor_name: str
    severity: AlertSeverity
    message: str
    timestamp: datetime
    value: float
    threshold: float
    acknowledged: bool = False


class SimulationStatus(BaseModel):
    running: bool
    factory_ids: list[str]
    interval_seconds: int
    uptime_seconds: float | None = None
    readings_generated: int = 0


class SimulationStartRequest(BaseModel):
    factory_ids: list[str] = ["FactoryA", "FactoryB", "FactoryC"]
    interval_seconds: int = 10


class ErrorResponse(BaseModel):
    detail: str
    status_code: int
