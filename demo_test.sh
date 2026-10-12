#!/usr/bin/env bash
# Demonstration and validation script for the Industrial Data Space project.
# Starts the complete Docker Compose stack, checks the main flows, and leaves
# the services running so the dashboard can be shown.

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}[INFO]${NC} $*"; }
ok() { echo -e "${GREEN}[ OK ]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
fail() { echo -e "${RED}[FAIL]${NC} $*" >&2; exit 1; }

require_command() {
    command -v "$1" >/dev/null 2>&1 || fail "Commande manquante: $1"
}

wait_http() {
    local url="$1"
    local timeout="${2:-90}"
    local start now
    start=$(date +%s)
    while true; do
        if curl -fsS --max-time 5 "$url" >/dev/null 2>&1; then
            return 0
        fi
        now=$(date +%s)
        (( now - start >= timeout )) && return 1
        sleep 2
    done
}

check_json() {
    local label="$1"
    local url="$2"
    local filter="$3"
    local value
    value=$(curl -fsS "$url" | jq -r "$filter") || fail "$label: réponse invalide"
    [[ -n "$value" && "$value" != "null" ]] || fail "$label: résultat vide"
    ok "$label: $value"
}

require_command docker
require_command curl
require_command jq

docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 est requis"

echo
echo "=============================================================="
echo " Industrial Data Space - DEMO + TEST AUTOMATIQUE"
echo "=============================================================="
echo

info "Arrêt d'une ancienne instance éventuelle..."
docker compose down >/dev/null 2>&1 || true

info "Construction et démarrage des services..."
docker compose up --build -d

info "Attente de l'API Dashboard..."
wait_http "http://localhost:8000/api/factories" 120 \
    || fail "Dashboard API indisponible. Voir: docker compose logs dashboard-api"
ok "Dashboard API disponible"

info "Vérification des trois factories..."
factory_count=$(curl -fsS http://localhost:8000/api/factories | jq 'length')
[[ "$factory_count" == "3" ]] || fail "Factories trouvées: $factory_count (attendu: 3)"
ok "3 factories détectées"

for factory in FactoryA FactoryB FactoryC; do
    check_json "$factory - données capteurs" \
        "http://localhost:8000/api/factories/${factory}/sensors?limit=1" \
        '.total_readings'
done

info "Vérification des connecteurs EDC..."
for entry in "FactoryA:8080" "FactoryB:8081" "FactoryC:8082"; do
    factory="${entry%%:*}"
    port="${entry##*:}"
    if wait_http "http://localhost:${port}/api/check/readiness" 30; then
        ok "$factory - EDC readiness disponible"
    elif wait_http "http://localhost:${port}/health" 10; then
        check_json "$factory - EDC health" "http://localhost:${port}/health" '.status'
    else
        fail "$factory - connecteur EDC indisponible"
    fi
done

if assets_count=$(curl -fsS -H 'X-Api-Key: password' \
    http://localhost:8180/management/v3/assets | jq 'length' 2>/dev/null); then
    ok "Assets EDC FactoryA: $assets_count"
else
    check_json "Assets EDC FactoryA" \
        "http://localhost:8080/api/v1/management/assets" 'length'
fi

check_json "MQTT / statut simulation" \
    "http://localhost:8000/api/simulation/status" '.running'

info "Attente de la progression Federated Learning (maximum 180 secondes)..."
fl_ready=0
for _ in $(seq 1 90); do
    if performance=$(curl -fsS http://localhost:8000/api/model/performance 2>/dev/null); then
        round=$(echo "$performance" | jq -r '.current_model.round // 0')
        if [[ "$round" != "0" && "$round" != "null" ]]; then
            accuracy=$(echo "$performance" | jq -r '.current_model.accuracy // 0')
            f1=$(echo "$performance" | jq -r '.current_model.f1_score // 0')
            ok "Federated Learning: round ${round}, accuracy ${accuracy}, F1 ${f1}"
            fl_ready=1
            break
        fi
    fi
    sleep 2
done

if [[ "$fl_ready" == "0" ]]; then
    warn "Aucun round FL terminé dans le délai. Vérifier: docker compose logs flower-server"
fi

echo
echo "=============================================================="
echo " DEMO PRÊTE"
echo "=============================================================="
echo " Dashboard : http://localhost:8501"
echo " API Docs  : http://localhost:8000/docs"
echo " EDC A     : http://localhost:8080/health"
echo " EDC B     : http://localhost:8081/health"
echo " EDC C     : http://localhost:8082/health"
echo
echo "Pour voir les logs : docker compose logs -f"
echo "Pour arrêter     : docker compose down"
echo
