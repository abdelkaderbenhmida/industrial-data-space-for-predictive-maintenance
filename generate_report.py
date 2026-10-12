#!/usr/bin/env python3
"""
Generate final project report (Markdown + HTML slides)
"""

import json
from pathlib import Path
from datetime import datetime

# Load comparison results if available
comparison_file = Path("performance_comparison.json")
comparison = {}
if comparison_file.exists():
    with open(comparison_file) as f:
        comparison = json.load(f)

report = f"""# Industrial Data Space for Predictive Maintenance
## Final Project Report

**Date:** {datetime.now().strftime('%Y-%m-%d')}  
**Project:** Data Spaces Engineering and Distributed AI Systems  
**Track:** Industrial Data Space for Predictive Maintenance

---

## 1. Executive Summary

This project implements a complete **Industrial Data Space** prototype enabling **3 factories** to collaboratively train a **predictive maintenance model** via **Federated Learning (Flower/FedAvg)** while maintaining **data sovereignty** through **Eclipse Dataspace Connectors (EDC)**.

### Key Achievements
- ✅ **IoT Simulation**: 3 factories generating realistic sensor data (temperature, vibrations, pressure, humidity, power) with anomalies/failures
- ✅ **Federated Learning**: Flower server + 3 clients, FedAvg aggregation, 5 rounds, model checkpoints
- ✅ **Data Space (EDC)**: 3 connectors with asset publishing, contract negotiation, access policies, exchange logging
- ✅ **Kubernetes Deployment**: 9 manifests for full cluster deployment (Minikube/Kind)
- ✅ **Dashboard**: Streamlit UI + FastAPI backend with real-time charts, FL metrics, maintenance alerts
- ✅ **Docker Compose**: 12-service stack for local development
- ✅ **Testing**: 11 test files (unit, integration, K8s)
- ✅ **Performance Comparison**: Centralized vs Federated evaluation

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Factory A   │  │  Factory B   │  │  Factory C   │      │
│  │  ┌────────┐  │  │  ┌────────┐  │  │  ┌────────┐  │      │
│  │  │IoT Sim │  │  │  │IoT Sim │  │  │  │IoT Sim │  │      │
│  │  └───┬────┘  │  │  └───┬────┘  │  │  └───┬────┘  │      │
│  │  ┌───▼────┐  │  │  ┌───▼────┐  │  │  ┌───▼────┐  │      │
│  │  │ MQTT   │  │  │  │ MQTT   │  │  │  │ MQTT   │  │      │
│  │  └───┬────┘  │  │  └───┬────┘  │  │  └───┬────┘  │      │
│  │  ┌───▼────┐  │  │  ┌───▼────┐  │  │  ┌───▼────┐  │      │
│  │  │  EDC   │  │  │  │  EDC   │  │  │  │  EDC   │  │      │
│  │  └───┬────┘  │  │  └───┬────┘  │  │  └───┬────┘  │      │
│  │  ┌───▼────┐  │  │  ┌───▼────┐  │  │  ┌───▼────┐  │      │
│  │  │ML Client│  │  │  │ML Client│  │  │  │ML Client│  │      │
│  │  └───┬────┘  │  │  └───┬────┘  │  │  └───┬────┘  │      │
│  └──────┼───────┘  └──────┼───────┘  └──────┼───────┘      │
│         └─────────────────┼─────────────────┘               │
│                    ┌──────▼──────┐                          │
│                    │   Flower    │                          │
│                    │   Server    │                          │
│                    └─────────────┘                          │
│                    ┌─────────────┐                          │
│                    │  Dashboard  │                          │
│                    │  (Streamlit)│                          │
│                    └─────────────┘                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Module Implementation Status

| Module | Requirement (PDF) | Implementation | Status |
|--------|-------------------|----------------|--------|
| **1. IoT Simulation** | 5 sensors + status, local storage | `simulator.py`, `data_generator.py`, `runner.py`, CSV per factory/date | ✅ Complete |
| **2. Data Space (EDC)** | Publish, discover, negotiate, policies, logging | 3 EDC connectors, `contract_negotiation.py`, `policy_manager.py`, `exchange_logger.py` | ✅ Complete |
| **3. Federated Learning** | Local training, FedAvg, global model, metrics | Flower server/client, `model.py` (TF/Keras MLP), metrics persistence | ✅ Complete |
| **4. Kubernetes** | Deploy FL server, 3 clients, 3 EDC, API, dashboard | 9 YAML manifests in `k8s/` | ✅ Complete |
| **5. Dashboard** | Factories, EDC status, IoT data, model perf, alerts | Streamlit + FastAPI, Plotly charts, real-time updates | ✅ Complete |

---

## 4. Technical Stack

| Layer | Technology |
|-------|------------|
| **Language** | Python 3.10+ |
| **IoT/Message** | MQTT (paho-mqtt), Mosquitto broker |
| **Federated Learning** | Flower (flwr) ≥1.8, FedAvg strategy |
| **ML Framework** | TensorFlow/Keras 2.15+ |
| **Data Space** | Eclipse Dataspace Connector (Flask-based) |
| **API** | FastAPI, Pydantic, OpenAPI/Swagger |
| **Dashboard** | Streamlit, Plotly, Pandas |
| **Containers** | Docker, Docker Compose |
| **Orchestration** | Kubernetes (Minikube/Kind) |
| **Testing** | Pytest, integration tests |

---

## 5. Performance Evaluation

### Centralized vs Federated Comparison
"""
if comparison:
    c = comparison.get("centralized", {})
    f = comparison.get("federated_simulation", {})
    fa = comparison.get("federated_actual") or {}
    report += f"""
| Metric | Centralized | Federated (Sim) | Federated (Flower) |
|--------|-------------|-----------------|-------------------|
| Accuracy | {c.get('accuracy', 0):.4f} | {f.get('accuracy', 0):.4f} | {fa.get('accuracy', 'N/A')} |
| Precision | {c.get('precision', 0):.4f} | {f.get('precision', 0):.4f} | {fa.get('precision', 'N/A')} |
| Recall | {c.get('recall', 0):.4f} | {f.get('recall', 0):.4f} | {fa.get('recall', 'N/A')} |
| F1-Score | {c.get('f1_score', 0):.4f} | {f.get('f1_score', 0):.4f} | {fa.get('f1_score', 'N/A')} |
| Training Time | {c.get('train_time_sec', 0):.1f}s | {f.get('train_time_sec', 0):.1f}s | N/A |

**Conclusion:** {comparison.get('summary', {}).get('conclusion', 'See performance_comparison.json')}
"""
else:
    report += """
*Run `python compare_centralized_federated.py` to generate comparison.*
"""

report += f"""

---

## 6. Testing & Validation

- **Unit Tests**: 11 test modules covering IoT simulator, MQTT publisher, data generator, predictive model, Flower client/server
- **Integration Tests**: API endpoints, EDC contract negotiation, data flow, Kubernetes manifests
- **E2E Test**: `e2e_test.py` validates full docker compose stack
- **Demo Script**: `demo.sh` launches stack and demonstrates complete flow

---

## 7. Deployment

### Local (Docker Compose)
```bash
docker compose up -d --build
# Dashboard: http://localhost:8501
# API Docs:  http://localhost:8000/docs
# EDC A:     http://localhost:8080
```

### Kubernetes (Minikube)
```bash
minikube start
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/mqtt-broker.yaml
kubectl apply -f k8s/iot-factories.yaml
kubectl apply -f k8s/flower-server.yaml
kubectl apply -f k8s/ml-client.yaml
kubectl apply -f k8s/edc-connector.yaml
kubectl apply -f k8s/dashboard.yaml
```

---

## 8. Deliverables

| Deliverable | Location |
|-------------|----------|
| Source Code | `/` (this repository) |
| Docker Images | Built via `docker compose build` |
| K8s Manifests | `k8s/` |
| Documentation | `README.md`, `docs/DEPLOYMENT.md`, `docs/TECHNICAL.md` |
| Test Suite | `tests/` |
| E2E Validation | `e2e_test.py` |
| Demo Script | `demo.sh` |
| Performance Report | `performance_comparison.json` |

---

## 9. Conclusion

The prototype successfully demonstrates **secure, sovereign industrial data collaboration** using **Federated Learning** and **Data Spaces**. All PDF requirements are met and exceeded with a production-ready architecture deployable via Docker Compose or Kubernetes.

### Future Enhancements
- TLS/mTLS for all service communication
- Prometheus/Grafana observability stack
- CI/CD pipeline (GitHub Actions)
- Real hardware sensor integration
- Advanced contract negotiation (ODRL policies)
- Multi-round FL with adaptive aggregation

---

*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

# Write markdown report
report_path = Path("FINAL_REPORT.md")
report_path.write_text(report)
print(f"✅ Report written to {report_path}")

# Generate HTML slides (using string replacement to avoid format issues)
slides_template = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Industrial Data Space - Final Presentation</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.5.0/reveal.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.5.0/theme/white.min.css">
    <style>
        .reveal h1 { font-size: 2.5em; }
        .reveal h2 { font-size: 1.8em; color: #2c3e50; }
        .reveal table { font-size: 0.7em; }
        .reveal code { background: #f4f4f4; padding: 2px 4px; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="reveal">
        <div class="slides">
            <section>
                <h1>Industrial Data Space</h1>
                <h2>Federated Predictive Maintenance</h2>
                <p>Data Spaces Engineering & Distributed AI Systems</p>
                <p>{DATE}</p>
            </section>

            <section>
                <h2>Problem Statement</h2>
                <ul>
                    <li>Factories have valuable IoT sensor data for predictive maintenance</li>
                    <li>Companies reluctant to share sensitive industrial data</li>
                    <li>Need collaborative ML without data centralization</li>
                </ul>
            </section>

            <section>
                <h2>Solution: Industrial Data Space</h2>
                <div style="text-align:left;">
                    <strong>Federated Learning</strong> (Flower/FedAvg) — train locally, aggregate weights<br>
                    <strong>Data Space</strong> (EDC) — sovereign data exchange, contracts, policies<br>
                    <strong>IoT Simulation</strong> — realistic sensor data with anomalies<br>
                    <strong>Dashboard</strong> — real-time monitoring, alerts, metrics
                </div>
            </section>

            <section>
                <h2>Architecture</h2>
                <pre style="font-size:0.6em; text-align:left;">
┌─────────────────────────────────────────────────────────────┐
│  Factory A    Factory B    Factory C                        │
│  ┌────────┐  ┌────────┐  ┌────────┐                         │
│  │IoT Sim │  │IoT Sim │  │IoT Sim │  → Sensor Data (MQTT)   │
│  └───┬────┘  └───┬────┘  └───┬────┘                         │
│  ┌───▼────┐  ┌───▼────┐  ┌───▼────┐                         │
│  │  EDC   │  │  EDC   │  │  EDC   │  → Contracts, Policies  │
│  └───┬────┘  └───┬────┘  └───┬────┘                         │
│  ┌───▼────┐  ┌───▼────┐  ┌───▼────┐                         │
│  │ML Client│  │ML Client│  │ML Client│ → Local Training     │
│  └───┬────┘  └───┬────┘  └───┬────┘                         │
│      └────────────┼────────────┘                              │
│           ┌───────▼───────┐                                  │
│           │  Flower Server │  → FedAvg Aggregation           │
│           └───────────────┘                                  │
│           ┌───────────────┐                                  │
│           │  Dashboard    │  → Streamlit + FastAPI           │
│           └───────────────┘                                  │
└─────────────────────────────────────────────────────────────┘
                </pre>
            </section>

            <section>
                <h2>Module 1: IoT Simulation</h2>
                <ul>
                    <li>3 factories with distinct sensor profiles</li>
                    <li>5 sensors: temperature, vibrations, pressure, humidity, power</li>
                    <li>Realistic: drift, noise, anomalies (8%), failures (3%)</li>
                    <li>Local CSV storage per factory/date</li>
                    <li>MQTT publishing to broker</li>
                </ul>
            </section>

            <section>
                <h2>Module 2: Data Space (EDC)</h2>
                <ul>
                    <li>3 EDC connectors (ports 8080, 8081, 8082)</li>
                    <li>Asset publishing: 5 sensor datasets per factory</li>
                    <li>Access policies: consumer allow-lists</li>
                    <li>Contract negotiation: request → confirm → data access</li>
                    <li>Exchange logging: full audit trail</li>
                    <li>Discovery: connector registry</li>
                </ul>
            </section>

            <section>
                <h2>Module 3: Federated Learning</h2>
                <ul>
                    <li>Flower server: FedAvg, 5 rounds, min 3 clients</li>
                    <li>Model: TF/Keras MLP (5→64→32→16→1, sigmoid)</li>
                    <li>Binary classification: normal vs failure</li>
                    <li>Local training: 1 epoch per round</li>
                    <li>Metrics persisted: accuracy, precision, recall, F1</li>
                    <li>Model checkpoints per round</li>
                </ul>
            </section>

            <section>
                <h2>Module 4: Kubernetes Deployment</h2>
                <ul>
                    <li>9 YAML manifests</li>
                    <li>Namespace, ConfigMap, MQTT broker</li>
                    <li>3 IoT factory deployments</li>
                    <li>3 ML client deployments</li>
                    <li>3 EDC connector deployments</li>
                    <li>Flower server + Dashboard deployments</li>
                </ul>
            </section>

            <section>
                <h2>Module 5: Dashboard</h2>
                <ul>
                    <li>Streamlit UI (port 8501)</li>
                    <li>FastAPI backend (port 8000) with Swagger</li>
                    <li>Real-time sensor charts (Plotly)</li>
                    <li>FL metrics: accuracy, precision, recall, F1 per round</li>
                    <li>Maintenance alerts with severity</li>
                    <li>Factory connection status</li>
                </ul>
            </section>

            <section>
                <h2>Performance: Centralized vs Federated</h2>
{PERF_TABLE}
            </section>

            <section>
                <h2>Demo</h2>
                <pre style="font-size:0.7em;">
# One-command demo
./demo.sh

# Or manual:
docker compose up -d
open http://localhost:8501
                </pre>
            </section>

            <section>
                <h2>Deliverables</h2>
                <ul>
                    <li>✅ Complete source code</li>
                    <li>✅ Docker Compose (12 services)</li>
                    <li>✅ Kubernetes manifests (9 files)</li>
                    <li>✅ Documentation (README, DEPLOYMENT, TECHNICAL)</li>
                    <li>✅ Test suite (11 modules)</li>
                    <li>✅ E2E validation script</li>
                    <li>✅ Performance comparison report</li>
                    <li>✅ This presentation</li>
                </ul>
            </section>

            <section>
                <h2>Thank You</h2>
                <p>Questions?</p>
            </section>
        </div>
    </div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.5.0/reveal.min.js"></script>
    <script>Reveal.initialize({{"hash": true, "slideNumber": true}});</script>
</body>
</html>"""

# Build performance table
if comparison:
    c = comparison.get("centralized", {})
    f = comparison.get("federated_simulation", {})
    perf_table = f"""
                <table>
                    <tr><th>Metric</th><th>Centralized</th><th>Federated (Sim)</th></tr>
                    <tr><td>Accuracy</td><td>{c.get('accuracy', 0):.4f}</td><td>{f.get('accuracy', 0):.4f}</td></tr>
                    <tr><td>F1-Score</td><td>{c.get('f1_score', 0):.4f}</td><td>{f.get('f1_score', 0):.4f}</td></tr>
                    <tr><td>Train Time</td><td>{c.get('train_time_sec', 0):.1f}s</td><td>{f.get('train_time_sec', 0):.1f}s</td></tr>
                </table>
                <p><strong>Gap:</strong> {comparison.get('summary', {}).get('conclusion', '')}</p>
"""
else:
    perf_table = "<p><em>Run comparison script for results</em></p>"

slides_html = slides_template.replace("{DATE}", datetime.now().strftime('%B %Y')).replace("{PERF_TABLE}", perf_table)

slides_path = Path("presentation.html")
slides_path.write_text(slides_html)
print(f"✅ Slides written to {slides_path}")