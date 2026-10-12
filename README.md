# Industrial Data Space for Predictive Maintenance

> **A complete prototype enabling multiple factories to collaboratively improve predictive maintenance models through secure data sharing (Eclipse Dataspace Connector) and federated learning (Flower) — without centralizing sensitive industrial data.**

---

## 🎯 Project Overview

Modern factories deploy IoT sensors (temperature, vibration, pressure, humidity, power consumption) for real-time machine monitoring. This data is valuable for predictive maintenance but companies are reluctant to share it directly due to IP protection, GDPR, and competitive concerns.

**This project solves that by combining:**

| Technology | Role |
|------------|------|
| **Eclipse Dataspace Connector (EDC)** | Sovereign data exchange with contract negotiation, policy enforcement, and audit logging |
| **Flower (Federated Learning)** | Train ML models across factories without moving raw data — only model weights are shared |
| **IoT Simulation** | Realistic sensor data generation from the AI4I 2020 predictive maintenance dataset |
| **FastAPI + Streamlit Dashboard** | Real-time monitoring of factories, EDC connectors, model performance, and maintenance alerts |
| **Docker Compose / Kubernetes (Minikube/Kind)** | Full orchestration for local development and cluster deployment |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        KUBERNETES CLUSTER (Minikube/Kind)                    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     NAMESPACE: industrial-data-space                 │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │    │
│  │  │  FACTORY A   │  │  FACTORY B   │  │  FACTORY C   │              │    │
│  │  │  ┌────────┐  │  │  ┌────────┐  │  │  ┌────────┐  │              │    │
│  │  │  │IoT Sim │  │  │  │IoT Sim │  │  │  │IoT Sim │  │              │    │
│  │  │  └────┬───┘  │  │  └────┬───┘  │  │  └────┬───┘  │              │    │
│  │  │  ┌────▼────┐  │  │  ┌────▼────┐  │  │  ┌────▼────┐  │              │    │
│  │  │  │ MQTT   │  │  │  │ MQTT   │  │  │  │ MQTT   │  │              │    │
│  │  │  │Broker  │  │  │  │Broker  │  │  │  │Broker  │  │              │    │
│  │  │  └────┬───┘  │  │  └────┬───┘  │  │  └────┬───┘  │              │    │
│  │  │  ┌────▼────┐  │  │  ┌────▼────┐  │  │  ┌────▼────┐  │              │    │
│  │  │  │  EDC   │  │  │  │  EDC   │  │  │  │  EDC   │  │              │    │
│  │  │  │Connector│  │  │  │Connector│  │  │  │Connector│  │              │    │
│  │  │  └────┬───┘  │  │  └────┬───┘  │  │  └────┬───┘  │              │    │
│  │  │  ┌────▼────┐  │  │  ┌────▼────┐  │  │  ┌────▼────┐  │              │    │
│  │  │  │ML Client│  │  │  │ML Client│  │  │  │ML Client│  │              │    │
│  │  │  │(Flower) │  │  │  │(Flower) │  │  │  │(Flower) │  │              │    │
│  │  │  └────┬───┘  │  │  └────┬───┘  │  │  └────┬───┘  │              │    │
│  │  └───────┼──────┘  └───────┼──────┘  └───────┼──────┘              │    │
│  └──────────┼─────────────────┼─────────────────┼─────────────────────┘    │
│             │                 │                 │                          │
│      ┌──────▼─────────────────▼─────────────────▼──────┐                   │
│      │           FLOWER FEDERATION SERVER               │                   │
│      │  (FedAvg Aggregation + Model Checkpointing)      │                   │
│      └────────────────────────┬────────────────────────┘                   │
│                               │                                           │
│      ┌────────────────────────▼────────────────────────┐                   │
│      │            FASTAPI BACKEND (Dashboard API)       │                   │
│      │  • MQTT Telemetry Subscriber                     │                   │
│      │  • EDC Connector Health Checks                   │                   │
│      │  • Federated Metrics Persistence                 │                   │
│      │  • Simulation Control API                        │                   │
│      └────────────────────────┬────────────────────────┘                   │
│                               │                                           │
│      ┌────────────────────────▼────────────────────────┐                   │
│      │         STREAMLIT DASHBOARD (Port 8501)          │                   │
│      │  • Factory status & sensor trends                │                   │
│      │  • EDC connector health                          │                   │
│      │  • Federated model metrics (Acc/Prec/Rec/F1)     │                   │
│      │  • Maintenance alerts                            │                   │
│      └──────────────────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow Summary

1. **IoT Simulation** → Generates sensor readings from AI4I 2020 dataset → Persists locally as CSV + publishes to MQTT
2. **MQTT Broker** → Streams telemetry to Dashboard API subscriber
3. **EDC Connectors** → Each factory exposes assets (sensor datasets), policies, contract definitions; negotiates access
4. **FL Clients** → Load local CSV data → Train local TF/Keras model → Send weights to Flower Server
5. **Flower Server** → FedAvg aggregation → Saves global model checkpoints + evaluation metrics (JSON)
6. **Dashboard API** → Reads MQTT telemetry, EDC health, federated metrics → Serves REST endpoints
7. **Streamlit Dashboard** → Polls API → Visualizes everything in real time

---

## 📁 Project Structure

```
industrial-data-space/
├── docker-compose.yml              # Local multi-service stack
├── README.md                       # This file
├── FINAL_REPORT.md                 # Project final report
├── presentation.html               # Project presentation slides
├── generate_report.py              # Report generator script
├── compare_centralized_federated.py # Centralized vs federated comparison
├── e2e_test.py                     # End-to-end integration test
├── run_federated.py                # Quick federated training runner
├── test_mqtt.py                    # MQTT connectivity test
├── mosquitto.conf                  # MQTT broker configuration
│
├── docs/
│   ├── PRD.md                      # Product Requirements Document
│   └── TECHNICAL.md                # Technical specification
│
├── iot-simulation/                 # Module 1: IoT Sensor Simulation
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── runner.py                   # Main entry: generates + publishes to MQTT
│   ├── simulator.py                # IoTSimulator class (CSV persistence + stats)
│   ├── data_generator.py           # AI4IDataGenerator (real data) + SensorDataGenerator (synthetic)
│   ├── mqtt_publisher.py           # MQTTPublisher class (paho-mqtt)
│   └── data/                       # Generated CSV files (per factory, per day)
│       ├── FactoryA/
│       ├── FactoryB/
│       └── FactoryC/
│
├── federated-learning/             # Module 3: Distributed ML (Flower)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── server.py                   # Flower Server (FedAvg + checkpointing + metrics)
│   ├── client.py                   # Flower Client (per-factory training/evaluation)
│   ├── model.py                    # Model architecture (shared)
│   └── checkpoints/                # Global model checkpoints (.keras)
│
├── data-space/                     # Module 2: Industrial Data Space (EDC)
│   ├── requirements.txt
│   ├── contract_negotiation.py     # Contract negotiation logic (if used)
│   ├── exchange_logger.py          # Exchange audit logging
│   ├── policy_manager.py           # Access policy management
│   └── edc-connector/              # EDC bootstrap assets and policies
│       ├── Dockerfile
│       ├── requirements.txt
│       ├── server.py               # Legacy prototype kept for reference
│       └── config/
│           └── config.properties   # EDC configuration
│
├── dashboard/                      # Module 5: Dashboard & API
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py                      # Streamlit frontend
│   ├── components/                 # Reusable Streamlit components (if any)
│   └── backend/                    # FastAPI backend
│       ├── main.py                 # FastAPI app + all REST endpoints
│       ├── models.py               # Pydantic models (SensorReading, Alerts, Metrics, etc.)
│       ├── telemetry.py            # MQTT subscriber (TelemetrySubscriber)
│       └── requirements.txt
│
├── k8s/                            # Module 4: Kubernetes Deployment
│   ├── namespace.yaml              # industrial-data-space namespace
│   ├── configmap.yaml              # Shared configuration
│   ├── mqtt-broker.yaml            # Mosquitto deployment + service
│   ├── iot-factories.yaml          # IoT simulator deployments (3 factories)
│   ├── flower-server.yaml          # Flower server deployment
│   ├── ml-client.yaml              # ML client deployments (3 factories)
│   ├── edc-connector.yaml          # EDC connector deployments (3 factories)
│   └── dashboard.yaml              # Dashboard API + Streamlit deployments
│
├── runtime/                        # Shared volume (metrics, checkpoints)
│   └── federated_metrics.json      # Persisted FL evaluation history
│
├── checkpoints/                    # Local model checkpoints (dev)
│
├── venv/                           # Python virtual environment
├── .pytest_cache/
└── __pycache__/
```

---

## 🚀 Quick Start (Docker Compose)

### Prerequisites

- Docker 24+ & Docker Compose v2
- 4 GB+ free RAM
- Ports 1883, 8000, 8080–8082, 8084, 8501 available

### 1. Clone & Build

```bash
git clone <repository-url>
cd industrial-data-space
docker compose build
```

### 2. Start All Services

```bash
docker compose up -d
```

This launches **14 containers**:

| Service | Ports | Description |
|---------|-------|-------------|
| `mqtt-broker` | 1883, 9001 | Eclipse Mosquitto MQTT broker |
| `flower-server` | 8084→8080 | Federated learning aggregation server |
| `dashboard-api` | 8000 | FastAPI backend (REST + MQTT subscriber) |
| `dashboard` | 8501 | Streamlit dashboard UI |
| `iot-factory-a/b/c` | — | IoT simulators (3 factories) → MQTT + CSV |
| `ml-client-a/b/c` | — | Flower clients (3 factories) → train on local data |
| `edc-factory-a/b/c` | 8080, 8081, 8082 | EDC connectors (3 factories) |

### 3. Verify

```bash
docker compose ps
# All services should show "Up"
```

### 4. Access Dashboard

Open **http://localhost:8501** in your browser.

You'll see:
- **Factory status** (connected/disconnected)
- **EDC connector health** (3 connectors, assets count)
- **Live sensor charts** (temperature, vibrations, pressure, humidity, power)
- **Federated model metrics** (Accuracy, Precision, Recall, F1 per round)
- **Maintenance alerts** (auto-generated from failure readings)

### 5. API Endpoints (FastAPI on port 8000)

```bash
# List factories
curl http://localhost:8000/api/factories

# Sensor data for a factory
curl http://localhost:8000/api/factories/FactoryA/sensors?limit=50

# Federated model performance
curl http://localhost:8000/api/model/performance

# Maintenance alerts
curl http://localhost:8000/api/alerts

# EDC connector status
curl http://localhost:8000/api/edc/status

# Start/stop simulation
curl -X POST http://localhost:8000/api/simulation/start \
  -H "Content-Type: application/json" \
  -d '{"factory_ids": ["FactoryA", "FactoryB"], "interval_seconds": 5}'

curl -X POST http://localhost:8000/api/simulation/stop
```

### 6. Stop & Cleanup

```bash
docker compose down -v
```

---

## 🧪 Development Mode (Local Python)

Run components individually for debugging:

### IoT Simulation

```bash
cd iot-simulation
pip install -r requirements.txt

# Continuous simulation (Ctrl+C to stop)
python runner.py --factory-id FactoryA --broker localhost --interval 5

# Batch generation (for testing)
python simulator.py --factories FactoryA FactoryB --batch 100 --interval 1
```

### Federated Learning

```bash
cd federated-learning
pip install -r requirements.txt

# Terminal 1: Start server (5 rounds, min 3 clients)
python server.py --rounds 5 --min-clients 3 --port 8080

# Terminal 2-4: Start clients (one per factory)
python client.py --factory-id FactoryA --data-dir ../iot-simulation/data/FactoryA --server-address localhost:8080
python client.py --factory-id FactoryB --data-dir ../iot-simulation/data/FactoryB --server-address localhost:8080
python client.py --factory-id FactoryC --data-dir ../iot-simulation/data/FactoryC --server-address localhost:8080
```

### EDC Connectors

Docker Compose now runs the official Tractus-X EDC runtime-memory image (`0.13.0`) for the three factories. It exposes the EDC readiness API on ports 8080–8082 and the management APIs on ports 8180–8182. The `edc-bootstrap` service creates the sensor assets, an open demo policy, and contract definitions through the real `/management/v3` API. The memory runtime is for local development/demo only; a persistent PostgreSQL/Vault runtime is required for production.

```bash
cd data-space/edc-connector
pip install -r requirements.txt

# Factory A (port 8080)
EDC_CONNECTOR_NAME=FactoryA EDC_CONNECTOR_ID=urn:connector:factory-a \
EDC_OTHER_CONNECTORS=http://localhost:8081,http://localhost:8082 \
python server.py

# Factory B (port 8081) — new terminal
EDC_CONNECTOR_NAME=FactoryB EDC_CONNECTOR_ID=urn:connector:factory-b \
EDC_OTHER_CONNECTORS=http://localhost:8080,http://localhost:8082 \
python server.py

# Factory C (port 8082) — new terminal
EDC_CONNECTOR_NAME=FactoryC EDC_CONNECTOR_ID=urn:connector:factory-c \
EDC_OTHER_CONNECTORS=http://localhost:8080,http://localhost:8081 \
python server.py
```

### Dashboard

```bash
cd dashboard
pip install -r requirements.txt
cd backend
pip install -r requirements.txt

# Terminal 1: API
uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2: Streamlit
cd ..
streamlit run app.py
```

---

## ☸️ Kubernetes Deployment (Minikube / Kind)

### Prerequisites

- Minikube v1.30+ (`minikube start --cpus=4 --memory=8g`)
- kubectl configured
- Docker images built locally or pushed to registry

### 1. Build Images for Minikube

```bash
eval $(minikube docker-env)

docker build -t iot-simulation:latest ./iot-simulation
docker build -t federated-learning:latest ./federated-learning
docker build -t edc-connector:latest ./data-space/edc-connector
docker build -t dashboard-api:latest ./dashboard
docker build -t dashboard:latest ./dashboard
```

### 2. Deploy

```bash
# Namespace & config
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml

# Infrastructure
kubectl apply -f k8s/mqtt-broker.yaml

# Factories (IoT + EDC + ML clients)
kubectl apply -f k8s/iot-factories.yaml
kubectl apply -f k8s/edc-connector.yaml
kubectl apply -f k8s/ml-client.yaml

# Federation server
kubectl apply -f k8s/flower-server.yaml

# Dashboard
kubectl apply -f k8s/dashboard.yaml
```

### 3. Verify

```bash
kubectl get pods -n industrial-data-space
kubectl get svc -n industrial-data-space

# Port-forward dashboard
kubectl port-forward -n industrial-data-space svc/dashboard 8501:8501
# Open http://localhost:8501

# Port-forward API
kubectl port-forward -n industrial-data-space svc/dashboard-api 8000:8000
```

### 4. Cleanup

```bash
kubectl delete namespace industrial-data-space
```

---

## 🔬 Module Deep Dive

### Module 1: IoT Simulation (`iot-simulation/`)

**Purpose:** Simulate multiple factories with realistic sensor data for predictive maintenance.

#### Key Components

| File | Responsibility |
|------|----------------|
| `data_generator.py` | **`AI4IDataGenerator`** — Loads the [AI4I 2020](https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance) dataset (500k+ rows), maps columns to sensor schema, filters by Product Type (L/M/H → FactoryA/B/C). **`SensorDataGenerator`** — Synthetic fallback with configurable profiles, anomaly injection, and failure state machines. |
| `simulator.py` | **`IoTSimulator`** — Orchestrates generation, writes daily CSV files per factory (`data/FactoryA/readings_YYYY-MM-DD.csv`), computes running statistics (min/max/avg per sensor), handles graceful shutdown. |
| `runner.py` | **Main entrypoint** for containers. Instantiates simulator + `MQTTPublisher`, loops: generate → persist → publish to MQTT. |
| `mqtt_publisher.py` | **`MQTTPublisher`** — Robust paho-mqtt wrapper with auto-reconnect, QoS 1, topic `factory/{factory_id}/sensors`, publish callbacks. |

#### Sensor Data Schema

```json
{
  "factory_id": "FactoryA",
  "timestamp": "2026-01-15T10:30:00.000Z",
  "temperature": 72.5,          // °C
  "vibrations": 0.42,           // normalized 0–5
  "pressure": 101.3,            // normalized 10–25
  "humidity": 45.0,             // normalized 10–90
  "power_consumption": 120.8,   // normalized 50–500
  "status": "normal"            // "normal" | "failure"
}
```

#### AI4I Column Mapping

| AI4I Column | Mapped Sensor | Transformation |
|-------------|---------------|----------------|
| Air temperature [K] | temperature | K → °C |
| Process temperature [K] | power_consumption | Normalized 50–500 |
| Rotational speed [rpm] | vibrations | Normalized 0–5 |
| Torque [Nm] | pressure | Normalized 10–25 |
| Tool wear [min] | humidity | Normalized 10–90 |
| Machine failure + TWF/HDF/PWF/OSF/RNF | status | Any true → "failure" |

#### Factory Profiles (Product Type)

| Factory | Product Type | Characteristics |
|---------|--------------|-----------------|
| FactoryA | L (Low) | Lower temp, moderate vibration |
| FactoryB | M (Medium) | Higher temp, higher vibration |
| FactoryC | H (High) | Lower temp, low vibration, higher humidity |

---

### Module 2: Industrial Data Space (`data-space/`)

**Purpose:** Provide sovereign data exchange between factories using Eclipse Dataspace Connector patterns.

#### EDC Connector API (`edc-connector/server.py`)

A legacy Flask prototype implementing a subset of EDC management and data-plane endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/management/assets` | GET/POST | List/create data assets (sensor datasets) |
| `/api/v1/management/assets/<id>` | GET/DELETE | Get/delete specific asset |
| `/api/v1/management/policies` | GET/POST | List/create access policies (allowed consumer IDs) |
| `/api/v1/management/contractdefinitions` | GET/POST | List/create contract definitions (asset selectors + policies) |
| `/api/v1/management/contractnegotiations` | GET/POST | Initiate/list contract negotiations |
| `/api/v1/management/contractnegotiations/<id>/accept` | POST | Accept negotiation (policy-gated) |
| `/api/v1/data/<asset_id>` | GET | **Data plane** — Policy-gated data access (returns data reference) |
| `/api/v1/discovery` | GET | List known connectors (peer discovery) |
| `/api/v1/discovery/register` | POST | Register a peer connector |
| `/api/v1/ids/metadata` | GET | IDS metadata endpoint |
| `/api/v1/ids/connector` | GET | Connector self-description |
| `/api/v1/federatedlearning/status` | GET | Proxy to Flower server status |
| `/health` | GET | Health check (used by dashboard) |

#### Key Features Implemented

- **Asset Publishing** — Each connector auto-registers 5 sensor assets + 1 FL training data contract on startup
- **Policy Enforcement** — `allowedConsumerIds` list checked on negotiation accept & data access
- **Contract Negotiation** — State machine: `REQUESTED` → `CONFIRMED` / `DECLINED`
- **Peer Discovery** — Connectors register with each other via `EDC_OTHER_CONNECTORS` env var
- **Audit Logging** — `exchange_logger.py` logs all data exchanges (extendable)

#### Configuration (`config/config.properties`)

```properties
edc.connector.name=FactoryA
edc.connector.ids.id=urn:connector:factory-a
edc.connector.port=8080
edc.flower.server=flower-server:8080
```

#### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EDC_CONNECTOR_NAME` | FactoryA | Display name |
| `EDC_CONNECTOR_ID` | urn:connector:factory-a | Unique IDS ID |
| `EDC_CONNECTOR_PORT` | 8080 | HTTP port |
| `EDC_OTHER_CONNECTORS` | — | Comma-separated peer URLs for auto-registration |
| `EDC_FLOWER_SERVER` | flower-server:8080 | Flower server for FL status proxy |

---

### Module 3: Federated Learning (`federated-learning/`)

**Purpose:** Train a global predictive maintenance model across factories without sharing raw data.

#### Architecture

- **Framework:** Flower (flwr) with TensorFlow/Keras backend
- **Algorithm:** FedAvg (Federated Averaging)
- **Model:** Binary classifier (failure vs normal) — 5 input features → 64→32→16→1 (sigmoid)
- **Aggregation:** Sample-weighted averaging of model weights
- **Evaluation:** Server-side aggregated metrics (accuracy, precision, recall, F1)

#### Server (`server.py`)

```python
# Key features:
- Custom FedAvg strategy with checkpointing every N rounds
- Sample-weighted metrics aggregation (accuracy, precision, recall, F1)
- Persistent metrics to JSON (runtime/federated_metrics.json) for dashboard
- Model checkpoints saved as .keras files (checkpoints/global_model_round_X.keras)
- Configurable: rounds, min_clients, port, save_every
```

#### Client (`client.py`)

```python
# Key features:
- Loads local factory CSV data (80/20 train/test split)
- Local training: configurable epochs, batch size
- Local evaluation: computes precision, recall, F1 from predictions
- Returns participant marker (participant_FactoryA=1.0) for server tracking
- Waits for local data to appear (configurable timeout)
```

#### Model (`model.py`)

Shared Keras architecture:

```python
Input(5) → Dense(64, relu) → Dropout(0.3) → Dense(32, relu) → Dropout(0.2) → Dense(16, relu) → Dense(1, sigmoid)
Loss: binary_crossentropy | Optimizer: adam | Metrics: accuracy
```

#### Features & Label

| Features (5) | Label |
|--------------|-------|
| temperature, vibrations, pressure, humidity, power_consumption | status (0=normal, 1=failure) |

#### Metrics Persistence

Server writes to `runtime/federated_metrics.json`:

```json
[
  {
    "model_id": "fed_predictive_maintenance_v1",
    "round": 1,
    "loss": 0.423,
    "accuracy": 0.812,
    "precision": 0.78,
    "recall": 0.85,
    "f1_score": 0.81,
    "participating_factories": ["FactoryA", "FactoryB", "FactoryC"],
    "timestamp": "2026-01-15T10:30:00.000Z"
  }
]
```

---

### Module 4: Kubernetes Deployment (`k8s/`)

All manifests target namespace `industrial-data-space`.

| File | Resources |
|------|-----------|
| `namespace.yaml` | Namespace |
| `configmap.yaml` | Shared env vars (MQTT broker, Flower server, EDC endpoints) |
| `mqtt-broker.yaml` | Deployment (1 replica) + Service (ClusterIP 1883, 9001) |
| `iot-factories.yaml` | 3 Deployments (iot-factory-a/b/c) — runner.py with factory-specific args |
| `flower-server.yaml` | Deployment (1 replica) + Service (ClusterIP 8080) |
| `ml-client.yaml` | 3 Deployments (ml-client-a/b/c) — client.py, depend on flower-server |
| `edc-connector.yaml` | 3 Deployments (edc-factory-a/b/c) + Services (8080, 8081, 8082) |
| `dashboard.yaml` | 2 Deployments (dashboard-api, dashboard) + Services (8000, 8501) |

#### Key Design Decisions

- **IoT simulators** run as Deployments (not Jobs) for continuous telemetry
- **ML clients** restart on failure; depend on `flower-server` readiness
- **EDC connectors** expose NodePorts (8080–8082) for external dashboard health checks
- **Shared volume** `runtime` (emptyDir or PVC) for federated metrics persistence
- **ConfigMap** centralizes all service addresses for easy reconfiguration

---

### Module 5: Dashboard (`dashboard/`)

#### Backend (`dashboard/backend/main.py`)

**FastAPI** application with:

- **MQTT Subscriber** (`telemetry.py`) → Subscribes to `factory/+/sensors`, validates payloads, feeds `AppState`
- **AppState** — In-memory store (last 500 readings/factory), alert generation, simulation control
- **REST Endpoints:**

| Endpoint | Response Model | Description |
|----------|----------------|-------------|
| `GET /api/factories` | `List[FactoryInfo]` | Factory list + last reading |
| `GET /api/factories/{id}/sensors` | `FactorySensorSummary` | Stats (min/max/avg), recent readings, failure rate |
| `GET /api/model/performance` | `ModelPerformance` | Current + historical federated metrics |
| `GET /api/alerts` | `List[MaintenanceAlert]` | Filterable by severity, factory, acknowledged |
| `GET /api/edc/status` | `List[EDCStatus]` | Health check of all 3 EDC connectors |
| `POST /api/simulation/start` | `SimulationStatus` | Start built-in synthetic simulation |
| `POST /api/simulation/stop` | `SimulationStatus` | Stop simulation |
| `GET /api/simulation/status` | `SimulationStatus` | Current simulation state |
| `POST /api/telemetry` | `SensorReading` | Direct ingestion (backup for MQTT) |

#### Frontend (`dashboard/app.py`)

**Streamlit** single-page dashboard with auto-refresh:

- **Top metrics row:** Factories reporting, active alerts, latest timestamp
- **EDC Connectors:** Grid of connector health + asset counts
- **Factory Telemetry:** Per-factory expandable sections with Plotly line charts (5 sensors)
- **Federated Model:** 4 metric cards (Acc/Prec/Rec/F1) + historical trend chart
- **Maintenance Alerts:** Sortable table with severity color coding

---

## 📊 Sensor Data & ML Details

### Training Data Source

- **Primary:** AI4I 2020 Predictive Maintenance Dataset (UCI ML Repository)
- **Size:** ~500,000 rows across 3 product types (L/M/H)
- **Split:** 80% train / 20% test per factory (client-side)
- **Features:** 5 normalized sensor readings
- **Target:** Binary (Machine failure: any of TWF, HDF, PWF, OSF, RNF)

### Failure Types in Dataset

| Code | Name | Description |
|------|------|-------------|
| TWF | Tool Wear Failure | Tool degradation over time |
| HDF | Heat Dissipation Failure | Overheating |
| PWF | Power Failure | Electrical issues |
| OSF | Overstrain Failure | Mechanical overload |
| RNF | Random Failure | Stochastic |

### Model Performance Expectations

| Setup | Accuracy | Precision | Recall | F1 |
|-------|----------|-----------|--------|-----|
| Centralized (all data) | ~0.95 | ~0.93 | ~0.96 | ~0.94 |
| Federated (3 clients, 5 rounds) | ~0.90–0.94 | ~0.88–0.92 | ~0.90–0.95 | ~0.89–0.93 |

*Federated typically reaches 95–99% of centralized performance with 5–10 rounds.*

---

## ⚙️ Configuration Reference

### Environment Variables (Docker Compose / K8s)

| Variable | Services | Default | Description |
|----------|----------|---------|-------------|
| `MQTT_BROKER_HOST` | dashboard-api, iot-factories | mqtt-broker | MQTT broker hostname |
| `MQTT_BROKER_PORT` | dashboard-api, iot-factories | 1883 | MQTT broker port |
| `METRICS_FILE` | flower-server, dashboard-api | /runtime/federated_metrics.json | FL metrics persistence |
| `LOCAL_DATA_DIR` | dashboard-api | /data | Mount path for factory CSVs |
| `EDC_CONNECTORS` | dashboard-api | http://edc-factory-a:8080,... | Comma-separated EDC health endpoints |
| `DASHBOARD_API_URL` | dashboard (Streamlit) | http://localhost:8000 | Backend API base URL |
| `EDC_CONNECTOR_NAME` | edc-connector | FactoryA | Connector display name |
| `EDC_CONNECTOR_ID` | edc-connector | urn:connector:factory-a | IDS identifier |
| `EDC_OTHER_CONNECTORS` | edc-connector | — | Peer connector URLs for discovery |
| `EDC_FLOWER_SERVER` | edc-connector | flower-server:8080 | FL server for status proxy |

---

## 🧪 Testing

### Run All Tests

```bash
# Unit/integration tests
pytest tests/ -v

# End-to-end test (requires running stack)
python e2e_test.py

# MQTT connectivity test
python test_mqtt.py

# Federated training quick test
python run_federated.py
```

### Test Coverage Areas

- IoT simulator CSV output format & statistics
- MQTT publish/subscribe round-trip
- EDC asset/policy/contract CRUD
- Flower client/server parameter exchange
- Dashboard API schema validation
- Federated metrics persistence & retrieval

---

## 🐛 Troubleshooting

### Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Dashboard shows "Waiting for MQTT telemetry" | IoT simulators not publishing | Check `docker compose logs iot-factory-a`; verify MQTT broker reachable |
| EDC connectors show "unavailable" | Containers not healthy | `docker compose logs edc-factory-a`; check port conflicts (8080–8082) |
| Flower server "connection refused" | Server not ready | Wait for `flower-server` logs showing "Starting Flower server" |
| ML clients exit immediately | No local CSV data | Ensure `iot-simulation/data/FactoryX` has CSV files; check volume mounts |
| Dashboard API 500 on `/api/model/performance` | No federated metrics yet | Run at least 1 FL round; check `runtime/federated_metrics.json` exists |
| Minikube pods `CrashLoopBackOff` | Image pull / resource limits | `minikube docker-env` + rebuild images; check `kubectl describe pod` |

### Debug Commands

```bash
# View logs for any service
docker compose logs -f <service-name>

# Check MQTT messages
docker exec -it <mqtt-container> mosquitto_sub -t 'factory/+/sensors' -v

# Inspect generated CSV data
ls -la iot-simulation/data/FactoryA/
head -5 iot-simulation/data/FactoryA/readings_*.csv

# Check federated metrics
cat runtime/federated_metrics.json | jq .

# Check model checkpoints
ls -la federated-learning/checkpoints/
ls -la checkpoints/
```

---

## 📈 Extending the Project

### Add New Sensor Types

1. Update `FEATURE_COLUMNS` in `federated-learning/server.py` and `client.py`
2. Extend `SENSOR_RANGES` in `dashboard/backend/main.py`
3. Add column mapping in `iot-simulation/data_generator.py`
4. Retrain model (architecture auto-adapts to input dim)

### Add More Factories

1. Add factory ID to `FACTORY_IDS` in `dashboard/backend/main.py`
2. Add profile to `SENSOR_BASELINES` / `SENSOR_RANGES`
3. Add deployment in `k8s/iot-factories.yaml`, `k8s/ml-client.yaml`, `k8s/edc-connector.yaml`
4. Add service entry in `docker-compose.yml` and `EDC_CONNECTORS` env var

### Use Real EDC (Eclipse Dataspace Connector)

The Docker Compose path already uses the official Tractus-X EDC control/data-plane runtime. The legacy Flask server remains in the repository only for comparison and older local experiments.

### Add Differential Privacy / Secure Aggregation

- **DP:** Add Gaussian noise in `client.py` `fit()` before returning weights
- **Secure Agg:** Use Flower's `SecAgg+` strategy (requires TEE or MPC setup)

---

## 📄 License

This project is open source. See `LICENSE` file for details.

---

## 🙏 Acknowledgments

- **AI4I 2020 Dataset** — UCI Machine Learning Repository
- **Flower** — Friendly federated learning framework
- **Eclipse Dataspace Connector** — Reference implementation for IDS
- **Mosquitto** — Lightweight MQTT broker
- **Streamlit & FastAPI** — Rapid dashboard + API development

---

*Built as a prototype for Industrial Data Spaces Engineering & Distributed AI Systems.*
