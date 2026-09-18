# Deployment Guide

This guide covers deploying the Industrial Data Space platform using Docker Compose (local development) and Kubernetes/Minikube (cluster deployment).

## Prerequisites

| Tool | Minimum Version | Purpose |
|------|----------------|---------|
| Python | 3.10+ | Runtime for all services |
| Docker | 24.0+ | Container builds |
| Docker Compose | 2.20+ | Multi-container orchestration |
| kubectl | 1.27+ | Kubernetes CLI |
| Minikube | 1.31+ | Local Kubernetes cluster |

Optional for development:
- `helm` 3.12+ (if extending with Helm charts)
- `k9s` or `lens` (Kubernetes dashboard UI)

---

## 1. Docker Compose Deployment (Local Development)

Docker Compose runs all services on a single machine with an internal bridge network. This is the fastest way to get the platform running.

### 1.1 Project Structure

```
industrial-data-space/
├── docker-compose.yml
├── federated-learning/
│   ├── Dockerfile
│   ├── server.py
│   ├── client.py
│   ├── model.py
│   └── requirements.txt
├── data-space/
│   ├── edc-connector/
│   │   ├── Dockerfile
│   │   ├── server.py
│   │   └── config/
│   │       ├── config.properties
│   │       ├── config-factory-b.properties
│   │       └── config-factory-c.properties
│   ├── contract_negotiation.py
│   ├── policy_manager.py
│   ├── exchange_logger.py
│   └── requirements.txt
├── iot-simulation/
│   ├── simulator.py
│   ├── mqtt_publisher.py
│   ├── data_generator.py
│   └── requirements.txt
├── dashboard/
│   └── backend/
│       ├── main.py
│       ├── models.py
│       └── requirements.txt
└── k8s/
    └── ... (Kubernetes manifests)
```

### 1.2 Build and Start

From the project root:

```bash
docker compose up --build -d
```

This builds three images and starts five containers:

| Container | Image | Port | Description |
|-----------|-------|------|-------------|
| `mqtt-broker` | `eclipse-mosquitto:2` | `1883` (MQTT), `9001` (WebSocket) | Message broker for IoT data |
| `flower-server` | Built from `federated-learning/Dockerfile` | `8083` → `8080` (gRPC) | Federated learning aggregation server |
| `edc-factory-a` | Built from `data-space/edc-connector/Dockerfile` | `8080` | EDC connector for Factory A |
| `edc-factory-b` | Same | `8081` → `8080` | EDC connector for Factory B |
| `edc-factory-c` | Same | `8082` → `8080` | EDC connector for Factory C |

### 1.3 Verify Services

```bash
# Check all containers are running
docker compose ps

# Check MQTT broker
docker exec mqtt-broker mosquitto_pub -t "test/ping" -m "hello"

# Check EDC connector (Factory A)
curl http://localhost:8080/health

# Check EDC connector (Factory B)
curl http://localhost:8081/health

# Check EDC connector (Factory C)
curl http://localhost:8082/health

# Check Flower server (gRPC — no HTTP health endpoint, check logs)
docker compose logs flower-server

# Check all logs
docker compose logs -f
```

Expected health response from EDC connectors:
```json
{
  "status": "healthy",
  "connectorId": "urn:connector:factory-a",
  "connectorName": "FactoryA",
  "port": 8080,
  "assets": 5,
  "contractDefinitions": 1,
  "negotiations": 0
}
```

### 1.4 Configuration

#### Environment Variables

EDC connectors are configured via environment variables in `docker-compose.yml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `EDC_CONNECTOR_NAME` | `FactoryA` | Human-readable connector name |
| `EDC_CONNECTOR_ID` | `urn:connector:factory-a` | Unique connector identifier |
| `EDC_CONNECTOR_PORT` | `8080` | HTTP port inside the container |
| `EDC_CONFIG_PATH` | `config/config.properties` | Path to `.properties` config file |
| `EDC_FLOWER_SERVER` | `flower-server:8080` | Flower server address for FL integration |
| `EDC_OTHER_CONNECTORS` | (comma-separated URLs) | List of peer connector addresses |

#### EDC Configuration Properties

Each factory has a `.properties` file in `data-space/edc-connector/config/`:

```properties
edc.connector.name=FactoryA
edc.connector.port=8080
edc.connector.host=edc-factory-a
edc.connector.protocol=http
edc.connector.ids.id=urn:connector:factory-a
edc.contract.negotiation.enabled=true
edc.contract.negotiation.timeout=300
edc.participant.id=urn:factory:factory-a
edc.participant.name=Factory A Connector
edc.data.address=http://localhost:8080
edc.control.address=http://localhost:8080
edc.management.address=http://localhost:8080
edc.asset.management.enabled=true
edc.contract.definition.enabled=true
edc.federatedlearning.enabled=true
edc.federatedlearning.flower.server=flower-server:8080
```

To add a new factory, duplicate an existing config file and update the `name`, `id`, `host`, and `participant` values. Then add a new service block in `docker-compose.yml`.

### 1.5 Networking

All services communicate over the `edc-network` bridge network. Service discovery uses Docker DNS (container names resolve automatically).

```
                    ┌─────────────────────────────────────────────────────┐
                    │                    edc-network (bridge)              │
                    │                                                     │
  localhost:1883 ◄──┤── mqtt-broker:1883                                  │
  localhost:8083 ◄──┤── flower-server:8080                                │
  localhost:8080 ◄──┤── edc-factory-a:8080                                │
  localhost:8081 ◄──┤── edc-factory-b:8080                                │
  localhost:8082 ◄──┤── edc-factory-c:8080                                │
                    │                                                     │
                    └─────────────────────────────────────────────────────┘
```

### 1.6 Stopping

```bash
docker compose down          # Stop containers (preserve volumes)
docker compose down -v       # Stop containers and remove volumes
```

---

## 2. Kubernetes Deployment (Minikube)

Kubernetes deployment runs each service as a separate pod in the `industrial-data-space` namespace. The manifests are in `k8s/`.

### 2.1 Start Minikube

```bash
# Start a Minikube cluster with sufficient resources
minikube start --cpus=4 --memory=8192 --driver=docker

# Enable the ingress addon (optional, for external access)
minikube addons enable ingress

# Verify cluster is ready
kubectl cluster-info
kubectl get nodes
```

### 2.2 Build Docker Images Inside Minikube

Since Minikube uses its own Docker daemon, you must build images inside it:

```bash
# Point shell to Minikube's Docker daemon
eval $(minikube docker-env)

# Build the federated learning server image
docker build -t federated-learning-server:latest \
  -f federated-learning/Dockerfile \
  federated-learning/

# Build the federated learning client image (same Dockerfile, used by ML clients)
docker build -t industrial-data-space/federated-learning:latest \
  -f federated-learning/Dockerfile \
  federated-learning/

# Build the EDC connector image
docker build -t industrial-data-space/edc-connector:latest \
  -f data-space/edc-connector/Dockerfile \
  data-space/edc-connector/

# Build the dashboard image (if a Dockerfile exists for it)
# docker build -t industrial-data-space/dashboard:latest \
#   -f dashboard/Dockerfile \
#   dashboard/

# Return to host Docker daemon
eval $(minikube docker-env --unset)
```

> **Important:** If you skip this step, Kubernetes pods will fail with `ImagePullBackOff` because the manifests use `imagePullPolicy: IfNotPresent` or `imagePullPolicy: Never`.

### 2.3 Deploy Services

Deploy in order — infrastructure first, then workloads:

```bash
# 1. Create namespace and configmaps
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml

# 2. Deploy MQTT broker
kubectl apply -f k8s/mqtt-broker.yaml

# 3. Deploy Flower server
kubectl apply -f k8s/flower-server.yaml

# 4. Deploy ML clients (one per factory)
kubectl apply -f k8s/ml-client.yaml

# 5. Deploy EDC connectors
kubectl apply -f k8s/edc-connector.yaml

# 6. Deploy dashboard API
kubectl apply -f k8s/dashboard.yaml
```

Or apply everything at once:

```bash
kubectl apply -f k8s/
```

### 2.4 Verify Deployment

```bash
# Check all pods are running
kubectl get pods -n industrial-data-space

# Expected output:
# NAME                                  READY   STATUS    RESTARTS   AGE
# dashboard-xxxxx                       1/1     Running   0          1m
# edc-factory-a-xxxxx                   1/1     Running   0          1m
# edc-factory-b-xxxxx                   1/1     Running   0          1m
# edc-factory-c-xxxxx                   1/1     Running   0          1m
# flower-server-xxxxx                   1/1     Running   0          1m
# ml-client-factory-a-xxxxx             1/1     Running   0          1m
# ml-client-factory-b-xxxxx             1/1     Running   0          1m
# ml-client-factory-c-xxxxx             1/1     Running   0          1m
# mqtt-broker-xxxxx                     1/1     Running   0          1m

# Check services
kubectl get svc -n industrial-data-space

# Check logs for a specific pod
kubectl logs -n industrial-data-space deployment/flower-server -f
kubectl logs -n industrial-data-space deployment/mqtt-broker -f
kubectl logs -n industrial-data-space deployment/edc-factory-a -f

# Port-forward to access services from host
kubectl port-forward -n industrial-data-space svc/mqtt-broker 1883:1883 &
kubectl port-forward -n industrial-data-space svc/flower-server 8080:8080 &
kubectl port-forward -n industrial-data-space svc/edc-factory-a 8080:8080 &
kubectl port-forward -n industrial-data-space svc/dashboard-api 8000:8000 &

# Test EDC connector
curl http://localhost:8080/health
```

### 2.5 Kubernetes Resource Allocation

The manifests include resource requests and limits per container:

| Component | CPU Request | Memory Request | CPU Limit | Memory Limit |
|-----------|-------------|----------------|-----------|--------------|
| MQTT Broker | 100m | 64Mi | 250m | 128Mi |
| Flower Server | 250m | 512Mi | 1000m | 1Gi |
| ML Client (each) | 200m | 256Mi | 500m | 512Mi |
| EDC Connector (each) | 200m | 128Mi | 500m | 256Mi |
| Dashboard API | 200m | 128Mi | 500m | 256Mi |

Total minimum cluster capacity: ~1.35 CPU, ~2.3Gi memory for all replicas.

### 2.6 Health Checks

Every deployment includes liveness and readiness probes:

| Component | Probe Type | Endpoint/Port | Initial Delay | Period |
|-----------|------------|---------------|---------------|--------|
| MQTT Broker | TCP socket | port 1883 | 10s / 5s | 30s / 10s |
| Flower Server | TCP socket | port 8080 | 15s / 5s | 20s / 10s |
| EDC Connectors | HTTP GET | `/health` port 8080 | 15s / 10s | 30s / 10s |
| Dashboard | HTTP GET | `/api/factories` port 8000 | 15s / 10s | 30s / 10s |

---

## 3. Minikube Setup Guide

### 3.1 Install Minikube

```bash
# Linux (x86_64)
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# macOS
brew install minikube

# Windows
choco install minikube
```

### 3.2 Start Minikube

```bash
# Default (2 CPU, 2GB RAM) — may be insufficient
minikube start

# Recommended for this platform
minikube start \
  --cpus=4 \
  --memory=8192 \
  --disk-size=20g \
  --driver=docker \
  --kubernetes-version=v1.28.3
```

### 3.3 Configure kubectl

Minikube automatically configures `kubectl`. Verify:

```bash
kubectl config current-context   # Should show "minikube"
kubectl cluster-info
```

### 3.4 Build and Deploy

```bash
# Build images inside Minikube
eval $(minikube docker-env)

docker build -t federated-learning-server:latest -f federated-learning/Dockerfile federated-learning/
docker build -t industrial-data-space/federated-learning:latest -f federated-learning/Dockerfile federated-learning/
docker build -t industrial-data-space/edc-connector:latest -f data-space/edc-connector/Dockerfile data-space/edc-connector/

eval $(minikube docker-env --unset)

# Deploy
kubectl apply -f k8s/
```

### 3.5 Access Services

```bash
# Option A: Port forwarding
kubectl port-forward -n industrial-data-space svc/dashboard-api 8000:8000
# Dashboard API available at http://localhost:8000

kubectl port-forward -n industrial-data-space svc/edc-factory-a 8080:8080
# Factory A EDC available at http://localhost:8080

# Option B: Minikube service URLs (auto-opens browser)
minikube service list -n industrial-data-space
minikube service dashboard-api -n industrial-data-space --url

# Option C: Minikube tunnel (for LoadBalancer services)
minikube tunnel
```

### 3.6 Cleanup

```bash
# Delete all Kubernetes resources
kubectl delete namespace industrial-data-space

# Stop Minikube (preserves cluster state)
minikube stop

# Delete Minikube entirely
minikube delete
```

---

## 4. Service Configuration Reference

### 4.1 ConfigMaps

The platform uses three ConfigMaps in the `industrial-data-space` namespace:

#### `platform-config` — Shared environment settings

| Key | Value | Used By |
|-----|-------|---------|
| `MQTT_BROKER_HOST` | `mqtt-broker` | Dashboard, ML clients |
| `MQTT_BROKER_PORT` | `1883` | Dashboard, ML clients |
| `FLOWER_SERVER_HOST` | `flower-server` | Dashboard, ML clients |
| `FLOWER_SERVER_PORT` | `8080` | Dashboard, ML clients |
| `FASTAPI_HOST` | `0.0.0.0` | Dashboard API |
| `FASTAPI_PORT` | `8000` | Dashboard API |
| `STREAMLIT_PORT` | `8501` | Dashboard UI |
| `IOT_SIM_INTERVAL` | `10` | IoT simulator |
| `IOT_DATA_DIR` | `/data` | IoT simulator, ML clients |
| `FACTORY_IDS` | `FactoryA,FactoryB,FactoryC` | All services |

#### `mosquitto-config` — MQTT broker configuration

```conf
listener 1883
allow_anonymous true
persistence true
persistence_location /mosquitto/data/
log_dest file /mosquitto/log/mosquitto.log
listener 9001
protocol websockets
```

#### `edc-config` — Per-factory EDC connector properties

Contains `config-factory-a.properties`, `config-factory-b.properties`, `config-factory-c.properties` as sub-keys. Mounted into each EDC connector pod at `/app/config/config.properties`.

### 4.2 Flower Server Configuration

The Flower server is configured via its own ConfigMap (`flower-server-config`):

| Key | Default | Description |
|-----|---------|-------------|
| `FLOWER_ROUNDS` | `10` | Number of federated training rounds |
| `FLOWER_MIN_CLIENTS` | `2` | Minimum clients required per round |
| `FLOWER_PORT` | `8080` | gRPC server port |
| `FLOWER_SAVE_EVERY` | `1` | Save checkpoint every N rounds |
| `TF_CPP_MIN_LOG_LEVEL` | `2` | TensorFlow log verbosity (2=WARNING) |

The server accepts CLI arguments that override these defaults:

```bash
python server.py \
  --rounds 10 \
  --min-clients 2 \
  --port 8080 \
  --save-every 1
```

### 4.3 ML Client Configuration

Each ML client deployment passes CLI arguments:

```bash
python client.py \
  --factory-id FactoryA \
  --server-address flower-server:8080
```

| Argument | Description |
|----------|-------------|
| `--factory-id` | Factory identifier (must match a directory under `iot-simulation/data/`) |
| `--data-dir` | Path to CSV data files (defaults to `iot-simulation/data/{factory-id}`) |
| `--server-address` | Flower server `host:port` |

### 4.4 EDC Connector API Endpoints

Each EDC connector exposes:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/v1/management/assets` | List registered assets |
| `POST` | `/api/v1/management/assets` | Register a new asset |
| `GET` | `/api/v1/management/assets/<id>` | Get asset details |
| `DELETE` | `/api/v1/management/assets/<id>` | Delete an asset |
| `GET` | `/api/v1/management/contractdefinitions` | List contract definitions |
| `POST` | `/api/v1/management/contractdefinitions` | Create contract definition |
| `GET` | `/api/v1/management/contractnegotiations` | List negotiations |
| `POST` | `/api/v1/management/contractnegotiations` | Start negotiation |
| `POST` | `/api/v1/management/contractnegotiations/<id>/accept` | Accept negotiation |
| `GET` | `/api/v1/ids/metadata` | IDS metadata |
| `GET` | `/api/v1/ids/connector` | Connector identity |
| `GET` | `/api/v1/discovery` | Discover known connectors |
| `POST` | `/api/v1/discovery/register` | Register a peer connector |
| `POST` | `/api/v1/discovery/register-all` | Register multiple peers |
| `GET` | `/api/v1/federatedlearning/status` | FL server status |

### 4.5 Dashboard API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/factories` | List connected factories |
| `GET` | `/api/factories/{id}/sensors` | Get sensor data for a factory |
| `GET` | `/api/model/performance` | Get federated model metrics |
| `GET` | `/api/alerts` | Get maintenance alerts |
| `POST` | `/api/simulation/start` | Start IoT simulation |
| `POST` | `/api/simulation/stop` | Stop IoT simulation |
| `GET` | `/api/simulation/status` | Get simulation status |

---

## 5. Troubleshooting

### Pods stuck in `ImagePullBackOff`

**Cause:** Kubernetes cannot find the Docker image locally.

**Fix:** Rebuild images inside Minikube:
```bash
eval $(minikube docker-env)
docker build -t federated-learning-server:latest -f federated-learning/Dockerfile federated-learning/
docker build -t industrial-data-space/federated-learning:latest -f federated-learning/Dockerfile federated-learning/
docker build -t industrial-data-space/edc-connector:latest -f data-space/edc-connector/Dockerfile data-space/edc-connector/
eval $(minikube docker-env --unset)
kubectl delete pod -l app=flower-server -n industrial-data-space
```

### Pods stuck in `CrashLoopBackOff`

**Cause:** Application error or missing dependency.

**Fix:** Check logs:
```bash
kubectl logs -n industrial-data-space <pod-name> --previous
```

Common issues:
- Missing `requirements.txt` dependencies (rebuild image)
- Wrong `--factory-id` argument (must match a data directory)
- Flower server not ready yet (ML clients will retry)

### MQTT broker not accepting connections

**Cause:** Mosquitto 2.x requires explicit `allow_anonymous true` in config.

**Fix:** Verify the ConfigMap is applied:
```bash
kubectl get configmap mosquitto-config -n industrial-data-space -o yaml
```

The `mosquitto.conf` must include:
```
listener 1883
allow_anonymous true
```

### EDC connectors cannot reach Flower server

**Cause:** Network policy or incorrect service name.

**Fix:**
1. Verify `flower-server` service exists:
   ```bash
   kubectl get svc flower-server -n industrial-data-space
   ```
2. Check that `EDC_FLOWER_SERVER` is set to `flower-server:8080` (not `localhost`).
3. Test connectivity from inside a pod:
   ```bash
   kubectl exec -n industrial-data-space deployment/edc-factory-a -- \
     python -c "import requests; print(requests.get('http://flower-server:8080/api/v1/status').text)"
   ```

### Docker Compose: containers exit immediately

**Cause:** Port conflict or missing config file.

**Fix:**
```bash
# Check if ports are in use
lsof -i :8080 -i :8081 -i :8082 -i :1883

# Rebuild and restart
docker compose down -v
docker compose up --build
```

### Minikube runs out of resources

**Cause:** Insufficient CPU or memory allocation.

**Fix:**
```bash
minikube stop
minikube start --cpus=4 --memory=8192
```

### ML client cannot load data

**Cause:** No CSV files in the data directory.

**Fix:** Start the IoT simulator first (or run a batch generation):
```bash
# Docker Compose
docker compose run iot-simulator python simulator.py --batch 100

# Kubernetes (generate data via a job or exec into a pod)
kubectl exec -n industrial-data-space deployment/ml-client-factory-a -- \
  python iot-simulation/simulator.py --batch 100 --data-dir /app/iot-simulation/data
```

---

## 6. Cleanup

### Docker Compose

```bash
docker compose down -v    # Remove containers and volumes
docker system prune -f    # Clean up dangling images
```

### Kubernetes / Minikube

```bash
# Delete all platform resources
kubectl delete namespace industrial-data-space

# Or delete individually
kubectl delete -f k8s/

# Full Minikube cleanup
minikube delete
```

---

## 7. Port Reference

| Service | Docker Compose Port | Kubernetes Service Port | Protocol |
|---------|--------------------|-----------------------|----------|
| MQTT Broker | `1883` | `1883` (ClusterIP) | TCP |
| MQTT WebSocket | `9001` | `9001` (ClusterIP) | TCP |
| Flower Server | `8083` → `8080` | `8080` (ClusterIP) | gRPC |
| EDC Factory A | `8080` | `8080` (ClusterIP) | HTTP |
| EDC Factory B | `8081` → `8080` | `8080` (ClusterIP) | HTTP |
| EDC Factory C | `8082` → `8080` | `8080` (ClusterIP) | HTTP |
| Dashboard API | — | `8000` (ClusterIP) | HTTP |
