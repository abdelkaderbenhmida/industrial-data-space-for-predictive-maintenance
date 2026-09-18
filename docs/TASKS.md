# TaskList

## Status legend: [ ] todo  [~] running  [x] done  [!] blocked

## Wave 1 - Foundation (Parallel)
- [ ] T1 [SETUP] Create project structure and base files
- [ ] T2 [SETUP] Configure Docker and dependencies
- [ ] T3 [SETUP] Initialize Git repository with branches

## Wave 2 - Core Modules (Parallel)
- [ ] T4 [BACKEND] Implement IoT sensor simulator
- [ ] T5 [BACKEND] Create MQTT publisher for sensor data
- [ ] T6 [BACKEND] Implement Flower federated learning server
- [ ] T7 [BACKEND] Create ML client for federated training
- [ ] T8 [BACKEND] Implement predictive maintenance model

## Wave 3 - Integration (Parallel)
- [ ] T9 [BACKEND] Deploy EDC connectors via Docker
- [ ] T10 [BACKEND] Implement contract negotiation logic
- [ ] T11 [BACKEND] Create FastAPI backend for dashboard
- [ ] T12 [FRONTEND] Build Streamlit dashboard UI
- [ ] T13 [FRONTEND] Implement real-time data visualization

## Wave 4 - Kubernetes (Parallel)
- [ ] T14 [SETUP] Create Kubernetes manifests
- [ ] T15 [SETUP] Deploy flower-server to K8s
- [ ] T16 [SETUP] Deploy ML clients to K8s
- [ ] T17 [SETUP] Deploy EDC connectors to K8s
- [ ] T18 [SETUP] Deploy dashboard to K8s

## Wave 5 - Testing & Docs
- [ ] T19 [QA] Write unit tests for IoT simulator
- [ ] T20 [QA] Write unit tests for federated learning
- [ ] T21 [QA] Write integration tests
- [ ] T22 [DOCS] Create README documentation
- [ ] T23 [DOCS] Create deployment guide

## Parallel Execution Map
```
Wave 1 (T1, T2, T3) - Foundation
    ↓
Wave 2 (T4, T5, T6, T7, T8) - Core Modules
    ↓
Wave 3 (T9, T10, T11, T12, T13) - Integration
    ↓
Wave 4 (T14, T15, T16, T17, T18) - Kubernetes
    ↓
Wave 5 (T19, T20, T21, T22, T23) - Testing & Docs
```
