#!/bin/sh
set -eu

create_connector_assets() {
  connector="$1"
  factory="$2"
  management="http://${connector}:8081/management"

  until curl -fsS "http://${connector}:8080/api/check/readiness" >/dev/null; do
    sleep 2
  done

  for sensor in temperature vibrations pressure humidity power_consumption; do
    curl -fsS -X POST "${management}/v3/assets" \
      -H "X-Api-Key: ${EDC_API_KEY}" \
      -H 'Content-Type: application/json' \
      -d "{\"@context\":{},\"@id\":\"${factory}-${sensor}\",\"properties\":{\"name\":\"${factory} ${sensor} data\",\"sensorType\":\"${sensor}\",\"factory\":\"${factory}\"},\"dataAddress\":{\"@type\":\"DataAddress\",\"type\":\"HttpData\",\"baseUrl\":\"http://dashboard-api:8000/api/factories/${factory}/sensors\"}}" \
      >/dev/null || true
  done

  curl -fsS -X POST "${management}/v3/policydefinitions" \
    -H "X-Api-Key: ${EDC_API_KEY}" \
    -H 'Content-Type: application/json' \
    -d "{\"@context\":{\"@vocab\":\"https://w3id.org/edc/v0.0.1/ns/\",\"odrl\":\"http://www.w3.org/ns/odrl/2/\"},\"@id\":\"${factory}-public-policy\",\"policy\":{\"@context\":\"http://www.w3.org/ns/odrl.jsonld\",\"@type\":\"Set\",\"permission\":[],\"prohibition\":[],\"obligation\":[]}}" \
    >/dev/null || true

  curl -fsS -X POST "${management}/v3/contractdefinitions" \
    -H "X-Api-Key: ${EDC_API_KEY}" \
    -H 'Content-Type: application/json' \
    -d "{\"@context\":{},\"@id\":\"${factory}-sensor-contract\",\"@type\":\"ContractDefinition\",\"accessPolicyId\":\"${factory}-public-policy\",\"contractPolicyId\":\"${factory}-public-policy\",\"assetsSelector\":[]}" \
    >/dev/null || true
}

create_connector_assets edc-factory-a FactoryA
create_connector_assets edc-factory-b FactoryB
create_connector_assets edc-factory-c FactoryC
echo "Real EDC assets and contract definitions initialized."
