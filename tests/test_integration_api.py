import pytest
import json
from fastapi.testclient import TestClient


class TestDashboardAPIFactories:
    @pytest.fixture(autouse=True)
    def setup(self):
        from main import app
        self.client = TestClient(app)

    def test_list_factories_returns_three(self):
        response = self.client.get("/api/factories")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_list_factories_has_required_fields(self):
        response = self.client.get("/api/factories")
        for factory in response.json():
            assert "factory_id" in factory
            assert "status" in factory
            assert "sensor_count" in factory
            assert factory["status"] == "connected"
            assert factory["sensor_count"] == 5

    def test_list_factories_includes_all_factories(self):
        response = self.client.get("/api/factories")
        ids = {f["factory_id"] for f in response.json()}
        assert ids == {"FactoryA", "FactoryB", "FactoryC"}

    def test_list_factories_last_reading_present(self):
        response = self.client.get("/api/factories")
        for factory in response.json():
            assert "last_reading" in factory
            if factory["last_reading"] is not None:
                reading = factory["last_reading"]
                assert "temperature" in reading
                assert "status" in reading


class TestDashboardAPISensors:
    @pytest.fixture(autouse=True)
    def setup(self):
        from main import app
        self.client = TestClient(app)

    def test_get_sensors_returns_200(self):
        response = self.client.get("/api/factories/FactoryA/sensors")
        assert response.status_code == 200

    def test_get_sensors_has_required_fields(self):
        response = self.client.get("/api/factories/FactoryA/sensors")
        data = response.json()
        assert "factory_id" in data
        assert data["factory_id"] == "FactoryA"
        assert "total_readings" in data
        assert "normal_count" in data
        assert "failure_count" in data
        assert "failure_rate" in data
        assert "sensors" in data
        assert "recent_readings" in data

    def test_get_sensors_stats_per_sensor(self):
        response = self.client.get("/api/factories/FactoryB/sensors")
        data = response.json()
        sensor_names = {s["sensor_name"] for s in data["sensors"]}
        expected = {"temperature", "vibrations", "pressure", "humidity", "power_consumption"}
        assert sensor_names == expected
        for s in data["sensors"]:
            assert s["min_value"] <= s["avg_value"] <= s["max_value"] or s["min_value"] <= s["max_value"]

    def test_get_sensors_with_limit(self):
        response = self.client.get("/api/factories/FactoryA/sensors?limit=10")
        data = response.json()
        assert len(data["recent_readings"]) <= 10

    def test_get_sensors_unknown_factory_returns_404(self):
        response = self.client.get("/api/factories/UnknownFactory/sensors")
        assert response.status_code == 404

    def test_get_sensors_failure_rate_is_percentage(self):
        response = self.client.get("/api/factories/FactoryA/sensors")
        data = response.json()
        assert 0.0 <= data["failure_rate"] <= 100.0

    def test_get_sensors_count_totals(self):
        response = self.client.get("/api/factories/FactoryC/sensors")
        data = response.json()
        assert data["normal_count"] + data["failure_count"] == data["total_readings"]


class TestDashboardAPIModelPerformance:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        from main import app, state
        metrics_path = tmp_path / "federated_metrics.json"
        metrics_path.write_text(json.dumps([
            {
                "model_id": "fed_predictive_maintenance_v1", "round": round_number,
                "accuracy": 0.7 + round_number * 0.01, "precision": 0.65 + round_number * 0.01,
                "recall": 0.6 + round_number * 0.01, "f1_score": 0.62 + round_number * 0.01,
                "loss": 0.5, "participating_factories": ["FactoryA", "FactoryB", "FactoryC"],
                "timestamp": "2026-10-01T12:00:00Z",
            }
            for round_number in range(1, 4)
        ]))
        previous_path = state.metrics_file
        state.metrics_file = metrics_path
        self.client = TestClient(app)
        yield
        state.metrics_file = previous_path

    def test_model_performance_returns_200(self):
        response = self.client.get("/api/model/performance")
        assert response.status_code == 200

    def test_model_performance_structure(self):
        response = self.client.get("/api/model/performance")
        data = response.json()
        assert "current_model" in data
        assert "history" in data

    def test_current_model_metrics(self):
        response = self.client.get("/api/model/performance")
        current = response.json()["current_model"]
        assert "model_id" in current
        assert "round" in current
        assert "accuracy" in current
        assert "precision" in current
        assert "recall" in current
        assert "f1_score" in current
        assert "loss" in current

    def test_model_metrics_in_valid_range(self):
        response = self.client.get("/api/model/performance")
        current = response.json()["current_model"]
        assert 0.0 <= current["accuracy"] <= 1.0
        assert 0.0 <= current["precision"] <= 1.0
        assert 0.0 <= current["recall"] <= 1.0
        assert 0.0 <= current["f1_score"] <= 1.0
        assert current["loss"] >= 0.0

    def test_model_performance_rounds_parameter(self):
        response = self.client.get("/api/model/performance?rounds=3")
        history = response.json()["history"]
        assert len(history) == 3

    def test_model_participating_factories(self):
        response = self.client.get("/api/model/performance")
        factories = response.json()["current_model"]["participating_factories"]
        assert set(factories) == {"FactoryA", "FactoryB", "FactoryC"}


class TestDashboardAPIAlerts:
    @pytest.fixture(autouse=True)
    def setup(self):
        from main import app
        self.client = TestClient(app)

    def test_get_alerts_returns_list(self):
        response = self.client.get("/api/alerts")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_alerts_have_required_fields(self):
        response = self.client.get("/api/alerts")
        for alert in response.json():
            assert "alert_id" in alert
            assert "factory_id" in alert
            assert "sensor_name" in alert
            assert "severity" in alert
            assert "message" in alert
            assert "timestamp" in alert
            assert "value" in alert
            assert "threshold" in alert

    def test_alerts_filter_by_severity(self):
        response = self.client.get("/api/alerts?severity=critical")
        for alert in response.json():
            assert alert["severity"] == "critical"

    def test_alerts_filter_by_factory(self):
        response = self.client.get("/api/alerts?factory_id=FactoryA")
        for alert in response.json():
            assert alert["factory_id"] == "FactoryA"

    def test_alerts_severity_values_valid(self):
        response = self.client.get("/api/alerts")
        valid_severities = {"low", "medium", "high", "critical"}
        for alert in response.json():
            assert alert["severity"] in valid_severities

    def test_alerts_limit_parameter(self):
        response = self.client.get("/api/alerts?limit=5")
        assert len(response.json()) <= 5


class TestDashboardAPISimulation:
    @pytest.fixture(autouse=True)
    def setup(self):
        from main import app
        self.client = TestClient(app)
        self.client.post("/api/simulation/stop")

    def test_simulation_status_when_not_running(self):
        response = self.client.get("/api/simulation/status")
        assert response.status_code == 200
        data = response.json()
        assert data["running"] is False

    def test_start_simulation(self):
        response = self.client.post(
            "/api/simulation/start",
            json={"factory_ids": ["FactoryA"], "interval_seconds": 5},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["running"] is True
        assert "FactoryA" in data["factory_ids"]

    def test_start_simulation_already_running_returns_409(self):
        self.client.post(
            "/api/simulation/start",
            json={"factory_ids": ["FactoryA"], "interval_seconds": 5},
        )
        response = self.client.post(
            "/api/simulation/start",
            json={"factory_ids": ["FactoryB"], "interval_seconds": 5},
        )
        assert response.status_code == 409

    def test_stop_simulation(self):
        self.client.post(
            "/api/simulation/start",
            json={"factory_ids": ["FactoryA"], "interval_seconds": 5},
        )
        response = self.client.post("/api/simulation/stop")
        assert response.status_code == 200
        assert response.json()["running"] is False

    def test_stop_when_not_running_returns_ok(self):
        response = self.client.post("/api/simulation/stop")
        assert response.status_code == 200
        assert response.json()["running"] is False

    def test_simulation_status_fields(self):
        response = self.client.get("/api/simulation/status")
        data = response.json()
        assert "running" in data
        assert "factory_ids" in data
        assert "interval_seconds" in data
        assert "readings_generated" in data

    def test_start_simulation_generates_readings(self):
        import time
        self.client.post(
            "/api/simulation/start",
            json={"factory_ids": ["FactoryA"], "interval_seconds": 1},
        )
        time.sleep(2)
        response = self.client.get("/api/simulation/status")
        assert response.json()["readings_generated"] > 0
        self.client.post("/api/simulation/stop")


class TestDashboardAPIIntegration:
    @pytest.fixture(autouse=True)
    def setup(self):
        from main import app
        self.client = TestClient(app)

    def test_factories_then_sensors_flow(self):
        factories_resp = self.client.get("/api/factories")
        assert factories_resp.status_code == 200
        for factory in factories_resp.json():
            sensor_resp = self.client.get(
                f"/api/factories/{factory['factory_id']}/sensors"
            )
            assert sensor_resp.status_code == 200
            assert sensor_resp.json()["factory_id"] == factory["factory_id"]

    def test_model_and_alerts_independent(self):
        model_resp = self.client.get("/api/model/performance")
        alerts_resp = self.client.get("/api/alerts")
        assert model_resp.status_code in (200, 404)
        assert alerts_resp.status_code == 200

    def test_api_cors_headers(self):
        response = self.client.options(
            "/api/factories",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200

    def test_api_openapi_schema_available(self):
        response = self.client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "paths" in schema
        assert "/api/factories" in schema["paths"]
        assert "/api/model/performance" in schema["paths"]
        assert "/api/alerts" in schema["paths"]
