# Industrial Data Space

A prototype platform enabling multiple factories to collaboratively improve predictive maintenance models through secure data sharing and federated learning — without centralizing sensitive industrial data.

## Overview

Modern factories deploy IoT sensors (temperature, vibration, pressure, power consumption) for real-time machine monitoring. This data is valuable for predictive maintenance but companies are reluctant to share it directly.

This project solves that by combining:

- **Federated Learning** (Flower) — train models across factories without moving data
- **Eclipse Dataspace Connector (EDC)** — sovereign data exchange with contract negotiation
- **IoT Simulation** — generate realistic sensor data for testing
- **Real-time Dashboard** — monitor factories, model performance, and alerts
- **Kubernetes Deployment** — orchestrate all services on Minikube

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Factory A   │  │  Factory B   │  │  Factory C   │  │
│  │  ┌────────┐  │  │  ┌────────┐  │  │  ┌────────┐  │  │
│  │  │IoT Sim │  │  │  │IoT Sim │  │  │  │IoT Sim │  │  │
│  │  └───┬────┘  │  │  └───┬────┘  │  │  └───┬────┘  │  │
│  │  ┌───▼────┐  │  │  ┌───▼────┐  │  │  ┌───▼────┐  │  │
│  │  │ MQTT   │  │  │  │ MQTT   │  │  │  │ MQTT   │  │  │
│  │  └───┬────┘  │  │  └───┬────┘  │  │  └───┬────┘  │  │
│  │  ┌───▼────┐  │  │  ┌───▼────┐  │  │  ┌───▼────┐  │  │
│  │  │  EDC   │  │  │  │  EDC   │  │  │  │  EDC   │  │  │
│  │  └───┬────┘  │  │  └───┬────┘  │  │  └───┬────┘  │  │
│  │  ┌───▼────┐  │  │  ┌───▼────┐  │  │  ┌───▼────┐  │  │
│  │  │ML Client│  │  │  │ML Client│  │  │  │ML Client│  │  │
│  │  └───┬────┘  │  │  └───┬────┘  │  │  └───┬────┘  │  │
│  └──────┼───────┘  └──────┼───────┘  └──────┼───────┘  │
│         └─────────────────┼─────────────────┘            │
│                    ┌──────▼──────┐                       │
│                    │   Flower    │                       │
│                    │   Server    │                       │
│                    └─────────────┘                       │
│                    ┌─────────────┐                       │
│                    │  Dashboard  │                       │
│                    │  (Streamlit)│                       │
│                    └─────────────┘                       │
└─────────────────────────────────────────────────────────┘
```

Each factory runs its own IoT simulator, MQTT broker, EDC connector, and federated learning client. A central Flower server aggregates model updates. A Streamlit dashboard provides visibility.

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.10+ | Core runtime |
| Docker | 24.0+ | Containerization |
| Docker Compose | v2.20+ | Local multi-service orchestration |
| Minikube | v1.30+ | Local Kubernetes cluster |
| kubectl | 1.28+ | Kubernetes CLI |
| Git | 2.30+ | Version control |

## Project Structure

```
industrial-data-space/
├── docs/
│   ├── PRD.md              # Product requirements
│   └── TECHNICAL.md        # Technical specification
├── iot-simulation/
│   ├── simulator.py        # Sensor data generator
│   ├── mqtt_publisher.py   # MQTT message publisher
│   └── requirements.txt
├── data-space/
│   ├── edc_connector/
│   │   ├── Dockerfile
│   │   └── config/
│   ├── contract_negotiation.py
│   └── requirements.txt
├── federated-learning/
│   ├── server.py           # Flower server (aggregator)
│   ├── client.py           # Flower client (per factory)
│   ├── model.py            # ML model definition
│   └── requirements.txt
├── dashboard/
│   ├── app.py              # Streamlit application
│   ├── components/
│   └── requirements.txt
├── k8s/
│   ├── namespace.yaml
│   ├── flower-server.yaml
│   ├── ml-client.yaml
│   ├── edc-connector.yaml
│   └── dashboard.yaml
├── docker-compose.yml
├── Dockerfile
└── README.md
```

## Setup

### 1. Clone and install

```bash
git clone <repository-url>
cd industrial-data-space

# Python dependencies
pip install -r iot-simulation/requirements.txt
pip install -r data-space/requirements.txt
pip install -r federated-learning/requirements.txt
pip install -r dashboard/requirements.txt
```

### 2. Start infrastructure with Docker Compose

```bash
docker compose up -d
```

This starts:
- **Mosquitto** MQTT broker on port `1883`
- **EDC Connector** on port `8080`
- **Flower Server** on port `8084`

The compose stack also starts three IoT publishers, three FL clients, the API, and
the Streamlit dashboard. Factory CSVs remain in `iot-simulation/data/`; dashboard
telemetry arrives through MQTT and FL metrics come from the Flower server.

### 3. Verify services

```bash
docker compose ps
```

All services should show `Up` status.

### 4. Kubernetes deployment (alternative)

```bash
# Start Minikube
minikube start

# Create namespace
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/mqtt-broker.yaml
kubectl apply -f k8s/iot-factories.yaml

# Deploy services
kubectl apply -f k8s/flower-server.yaml
kubectl apply -f k8s/ml-client.yaml
kubectl apply -f k8s/edc-connector.yaml
kubectl apply -f k8s/dashboard.yaml

# Verify
kubectl get pods -n industrial-data-space
```

## Usage

### Start IoT simulation

```bash
# From one terminal — start sensor data generation
python iot-simulation/simulator.py --factory factory_a --interval 5

# In another terminal — start publisher
python iot-simulation/mqtt_publisher.py --broker localhost --port 1883
```

### Launch federated learning

```bash
# Start Flower aggregation server
python federated-learning/server.py --rounds 10 --min-clients 3

# Start ML clients (one per factory)
python federated-learning/client.py --factory factory_a --server localhost:8084
python federated-learning/client.py --factory factory_b --server localhost:8084
python federated-learning/client.py --factory factory_c --server localhost:8084
```

### Launch dashboard

```bash
streamlit run dashboard/app.py
```

Open `http://localhost:8501` in your browser.

### API endpoints

The FastAPI backend exposes:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/factories` | List connected factories |
| `GET` | `/api/factories/{id}/sensors` | Get sensor data for a factory |
| `GET` | `/api/model/performance` | Get federated model metrics |
| `GET` | `/api/alerts` | Get maintenance alerts |
| `POST` | `/api/simulation/start` | Start IoT simulation |
| `POST` | `/api/simulation/stop` | Stop IoT simulation |

Example:

```bash
# List factories
curl http://localhost:8000/api/factories

# Get sensor readings
curl http://localhost:8000/api/factories/factory_a/sensors

# Start simulation
curl -X POST http://localhost:8000/api/simulation/start
```

## Configuration

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MQTT_BROKER` | `localhost` | MQTT broker hostname |
| `MQTT_PORT` | `1883` | MQTT broker port |
| `FLOWER_SERVER` | `localhost:8084` | Flower server address |
| `EDC_ENDPOINT` | `http://localhost:8080` | EDC connector URL |
| `DASHBOARD_PORT` | `8501` | Streamlit port |

### Sensor data model

Each sensor reading contains:

```json
{
  "factory_id": "factory_a",
  "timestamp": "2026-01-15T10:30:00Z",
  "temperature": 72.5,
  "vibrations": 0.42,
  "pressure": 101.3,
  "humidity": 45.0,
  "power_consumption": 120.8,
  "status": "normal"
}
```

`status` is either `"normal"` or `"failure"`.

### Model metrics

Federated model results include:

```json
{
  "model_id": "fedavg_v1",
  "round": 10,
  "accuracy": 0.94,
  "precision": 0.92,
  "recall": 0.95,
  "f1_score": 0.93,
  "participating_factories": ["factory_a", "factory_b", "factory_c"]
}
```

## Troubleshooting

### MQTT broker not reachable

```bash
# Check if Mosquitto is running
docker compose logs mosquitto

# Restart it
docker compose restart mosquitto
```

### EDC connector fails to start

```bash
# Check logs
docker compose logs edc-connector

# Common fix: ensure ports are free
lsof -i :8080
```

### Flower server won't connect

```bash
# Verify server is listening
netstat -tlnp | grep 8084

# Check firewall
sudo ufw status
```

### Minikube pods in CrashLoopBackOff

```bash
# Check pod logs
kubectl logs <pod-name> -n industrial-data-space

# Restart the pod
kubectl delete pod <pod-name> -n industrial-data-space
```

### Dashboard shows no data

1. Ensure the FastAPI backend is running (`uvicorn dashboard.app:app`)
2. Verify MQTT broker is publishing data
3. Check browser console for connection errors
4. Confirm the simulation is started via `POST /api/simulation/start`

### Sensor data looks flat / no anomalies

The simulator uses probability-based anomaly injection. Increase anomaly rate:

```bash
python iot-simulation/simulator.py --factory factory_a --anomaly-rate 0.3
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10+ |
| IoT Simulation | paho-mqtt |
| Data Space | Eclipse Dataspace Connector (EDC) |
| Federated Learning | Flower (flwr) |
| ML Libraries | Scikit-learn, TensorFlow / PyTorch |
| Containers | Docker, Docker Compose |
| Orchestration | Kubernetes (Minikube) |
| API | FastAPI |
| Dashboard | Streamlit |
| Message Broker | Mosquitto (MQTT) |

## License

Open source — see LICENSE file for details.
