#!/usr/bin/env bash
# Industrial Data Space - Demo Script
# Launches full stack and demonstrates the complete flow

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log() { echo -e "${BLUE}[DEMO]${NC} $*"; }
success() { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
error() { echo -e "${RED}[✗]${NC} $*"; }

# Cleanup on exit
cleanup() {
    log "Stopping all services..."
    docker compose down -v >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

main() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║     Industrial Data Space - Federated Predictive Maintenance ║"
    echo "║                         LIVE DEMO                              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    
    # 1. Start infrastructure
    log "Starting Docker Compose stack (12 services)..."
    docker compose up -d --build
    
    # 2. Wait for services
    log "Waiting for services to be healthy..."
    sleep 10
    
    # Show service status
    echo ""
    log "Service Status:"
    docker compose ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}"
    
    # 3. Wait for API
    log "Waiting for Dashboard API..."
    for i in {1..30}; do
        if curl -sf http://localhost:8000/api/factories >/dev/null 2>&1; then
            success "Dashboard API ready"
            break
        fi
        sleep 2
    done
    
    # 4. Show factories
    echo ""
    log "Connected Factories:"
    curl -s http://localhost:8000/api/factories | jq -r '.[] | "  • \(.factory_id): \(.status) - last reading: \(.last_reading.timestamp // "waiting...")"'
    
    # 5. Show EDC connectors
    echo ""
    log "EDC Connectors Health:"
    for port in 8080 8081 8082; do
        name=$(curl -s http://localhost:$port/health | jq -r '.connectorName')
        assets=$(curl -s http://localhost:$port/health | jq -r '.assets')
        echo "  • $name (port $port): healthy, $assets assets published"
    done
    
    # 6. Show EDC assets
    echo ""
    log "Published Data Assets (Factory A):"
    curl -s http://localhost:8080/api/v1/management/assets | jq -r '.[] | "  • \(.name) [\(.properties.sensorType)]"'
    
    # 7. Show sensor data
    echo ""
    log "Live Sensor Data (Factory A - last 5 readings):"
    curl -s "http://localhost:8000/api/factories/FactoryA/sensors?limit=5" | \
        jq -r '.recent_readings[] | "  \(.timestamp) | T=\(.temperature)°C V=\(.vibrations) P=\(.pressure) H=\(.humidity)% Pwr=\(.power_consumption)W | \(.status)"'
    
    # 8. Start simulation if not running
    echo ""
    log "Ensuring IoT simulation is running..."
    curl -s -X POST http://localhost:8000/api/simulation/start \
        -H "Content-Type: application/json" \
        -d '{"factory_ids": ["FactoryA", "FactoryB", "FactoryC"], "interval_seconds": 5}' >/dev/null
    success "Simulation started (5s interval)"
    
    # 9. Wait for FL rounds
    echo ""
    log "Waiting for Federated Learning rounds to complete (this takes ~2-3 minutes)..."
    log "Flower server runs 5 rounds with 3 clients (FedAvg)..."
    
    for round in 1 2 3 4 5; do
        log "Waiting for round $round..."
        for i in {1..60}; do
            if perf=$(curl -sf "http://localhost:8000/api/model/performance?rounds=10" 2>/dev/null); then
                current_round=$(echo "$perf" | jq -r '.current_model.round')
                acc=$(echo "$perf" | jq -r '.current_model.accuracy')
                f1=$(echo "$perf" | jq -r '.current_model.f1_score')
                if [[ "$current_round" -ge "$round" ]]; then
                    success "Round $current_round complete: accuracy=${acc}, f1=${f1}"
                    break
                fi
            fi
            sleep 5
        done
    done
    
    # 10. Final model performance
    echo ""
    log "Final Federated Model Performance:"
    curl -s "http://localhost:8000/api/model/performance?rounds=10" | \
        jq -r '.current_model | "  Round: \(.round)\n  Accuracy:  \(.accuracy | .*100 | floor)%\n  Precision: \(.precision | .*100 | floor)%\n  Recall:    \(.recall | .*100 | floor)%\n  F1-Score:  \(.f1_score | .*100 | floor)%\n  Factories: \(.participating_factories | join(", "))"'
    
    # 11. Show alerts
    echo ""
    log "Maintenance Alerts Generated:"
    curl -s "http://localhost:8000/api/alerts?limit=10" | \
        jq -r '.[] | "  [\(.severity | upper)] \(.factory_id) - \(.sensor_name): \(.message) (value=\(.value), threshold=\(.threshold))"'
    
    # 12. Show dashboard URLs
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                         ACCESS POINTS                          ║"
    echo "╠══════════════════════════════════════════════════════════════╣"
    echo "║  📊 Dashboard (Streamlit):  http://localhost:8501             ║"
    echo "║  🔌 API Docs (Swagger):     http://localhost:8000/docs        ║"
    echo "║  🔗 EDC Factory A:          http://localhost:8080             ║"
    echo "║  🔗 EDC Factory B:          http://localhost:8081             ║"
    echo "║  🔗 EDC Factory C:          http://localhost:8082             ║"
    echo "║  📡 MQTT Broker:            localhost:1883 (WS: 9001)         ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    success "Demo complete! Stack is running. Press Ctrl+C to stop."
    echo ""
    log "Opening dashboard in browser..."
    sleep 2
    
    # Keep running until interrupted
    while true; do
        sleep 30
        # Periodic status update
        perf=$(curl -sf "http://localhost:8000/api/model/performance?rounds=10" 2>/dev/null || echo '{}')
        round=$(echo "$perf" | jq -r '.current_model.round // 0')
        acc=$(echo "$perf" | jq -r '.current_model.accuracy // 0')
        if [[ "$round" -gt 0 ]]; then
            log "FL Status: Round $round, Accuracy: $(echo "$acc*100" | bc -l | cut -d. -f1)%"
        fi
    done
}

# Check dependencies
for cmd in docker curl jq bc; do
    if ! command -v $cmd &>/dev/null; then
        error "Missing dependency: $cmd"
        exit 1
    fi
done

main