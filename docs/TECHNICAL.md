# Technical Specification

## Tech Stack
- **Language:** Python 3.10+
- **IoT Simulation:** Python + MQTT (paho-mqtt)
- **Data Space:** Eclipse Dataspace Connector (EDC) via Docker
- **Federated Learning:** Flower (flwr)
- **ML Libraries:** Scikit-learn, TensorFlow/PyTorch
- **Containerization:** Docker, Docker Compose
- **Orchestration:** Kubernetes (Minikube)
- **API:** FastAPI
- **Dashboard:** Streamlit or React
- **Message Broker:** MQTT (Mosquitto)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Factory A   │  │  Factory B   │  │  Factory C   │  │
│  │  ┌────────┐  │  │  ┌────────┐  │  │  ┌────────┐  │  │
│  │  │IoT Sim │  │  │  │IoT Sim │  │  │  │IoT Sim │  │  │
│  │  └───┬────┘  │  │  └───┬────┘  │  │  └───┬────┘  │  │
│  │      │       │  │      │       │  │      │       │  │
│  │  ┌───▼────┐  │  │  ┌───▼────┐  │  │  ┌───▼────┐  │  │
│  │  │ MQTT   │  │  │  │ MQTT   │  │  │  │ MQTT   │  │  │
│  │  └───┬────┘  │  │  └───┬────┘  │  │  └───┬────┘  │  │
│  │      │       │  │      │       │  │      │       │  │
│  │  ┌───▼────┐  │  │  ┌───▼────┐  │  │  ┌───▼────┐  │  │
│  │  │  EDC   │  │  │  │  EDC   │  │  │  │  EDC   │  │  │
│  │  └───┬────┘  │  │  └───┬────┘  │  │  └───┬────┘  │  │
│  │      │       │  │      │       │  │      │       │  │
│  │  ┌───▼────┐  │  │  ┌───▼────┐  │  │  ┌───▼────┐  │  │
│  │  │ML Client│  │  │  │ML Client│  │  │  │ML Client│  │  │
│  │  └───┬────┘  │  │  └───┬────┘  │  │  └───┬────┘  │  │
│  └──────┼───────┘  └──────┼───────┘  └──────┼───────┘  │
│         │                 │                 │            │
│         └─────────────────┼─────────────────┘            │
│                           │                              │
│                    ┌──────▼──────┐                       │
│                    │   Flower    │                       │
│                    │   Server    │                       │
│                    └─────────────┘                       │
│                                                          │
│                    ┌─────────────┐                       │
│                    │  Dashboard  │                       │
│                    │  (Streamlit)│                       │
│                    └─────────────┘                       │
└─────────────────────────────────────────────────────────┘
```

## Data Models

### SensorReading
```python
{
    "factory_id": str,
    "timestamp": datetime,
    "temperature": float,
    "vibrations": float,
    "pressure": float,
    "humidity": float,
    "power_consumption": float,
    "status": "normal" | "failure"
}
```

### FederatedModel
```python
{
    "model_id": str,
    "round": int,
    "accuracy": float,
    "precision": float,
    "recall": float,
    "f1_score": float,
    "participating_factories": List[str]
}
```

## API Design

### FastAPI Endpoints
- `GET /api/factories` - List connected factories
- `GET /api/factories/{id}/sensors` - Get sensor data
- `GET /api/model/performance` - Get model metrics
- `GET /api/alerts` - Get maintenance alerts
- `POST /api/simulation/start` - Start IoT simulation
- `POST /api/simulation/stop` - Stop IoT simulation

## File Structure

```
industrial-data-space/
├── docs/
│   ├── PRD.md
│   └── TECHNICAL.md
├── iot-simulation/
│   ├── simulator.py
│   ├── mqtt_publisher.py
│   └── requirements.txt
├── data-space/
│   ├── edc_connector/
│   │   ├── Dockerfile
│   │   └── config/
│   ├── contract_negotiation.py
│   └── requirements.txt
├── federated-learning/
│   ├── server.py
│   ├── client.py
│   ├── model.py
│   └── requirements.txt
├── dashboard/
│   ├── app.py
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

## Implementation Phases

### Phase 1: IoT Simulation (Week 1)
- Create sensor data simulator
- Implement MQTT publisher
- Store data locally per factory
- Dependencies: None

### Phase 2: Federated Learning (Week 1-2)
- Implement Flower server
- Create ML client for each factory
- Implement FedAvg aggregation
- Dependencies: Phase 1 (for data)

### Phase 3: EDC Integration (Week 2-3)
- Deploy EDC connectors via Docker
- Implement contract negotiation
- Add access control policies
- Dependencies: None (parallel with Phase 1-2)

### Phase 4: Dashboard (Week 3)
- Build Streamlit dashboard
- Connect to FastAPI backend
- Display real-time data
- Dependencies: Phase 1, 2

### Phase 5: Kubernetes Deployment (Week 3-4)
- Create K8s manifests
- Deploy all services to Minikube
- Test end-to-end
- Dependencies: All phases
