import json
import os
import time
import uuid
from datetime import datetime

import requests
import yaml
from flask import Flask, jsonify, request

app = Flask(__name__)

CONNECTOR_NAME = os.environ.get("EDC_CONNECTOR_NAME", "FactoryA")
CONNECTOR_ID = os.environ.get("EDC_CONNECTOR_ID", "urn:connector:factory-a")
CONNECTOR_PORT = int(os.environ.get("EDC_CONNECTOR_PORT", "8080"))
FLOWER_SERVER = os.environ.get("EDC_FLOWER_SERVER", "flower-server:8080")

assets = {}
contract_definitions = {}
contract_negotiations = {}
known_connectors = {}
access_policies = {}


def load_config():
    global CONNECTOR_NAME, CONNECTOR_ID
    config_path = os.environ.get("EDC_CONFIG_PATH", "config/config.properties")
    if os.path.exists(config_path):
        with open(config_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    if key == "edc.connector.name" and "EDC_CONNECTOR_NAME" not in os.environ:
                        CONNECTOR_NAME = value
                    elif key == "edc.connector.ids.id" and "EDC_CONNECTOR_ID" not in os.environ:
                        CONNECTOR_ID = value


@app.route("/api/v1/management/assets", methods=["GET"])
def list_assets():
    return jsonify(list(assets.values()))


@app.route("/api/v1/management/assets", methods=["POST"])
def create_asset():
    data = request.get_json(silent=True) or {}
    asset_id = data.get("id", str(uuid.uuid4()))
    asset = {
        "id": asset_id,
        "name": data.get("name", asset_id),
        "type": data.get("type", "data"),
        "description": data.get("description", ""),
        "properties": data.get("properties", {}),
        "policyId": data.get("policyId"),
        "createdAt": datetime.utcnow().isoformat(),
        "connectorId": CONNECTOR_ID,
    }
    assets[asset_id] = asset
    return jsonify(asset), 201


@app.route("/api/v1/management/policies", methods=["GET", "POST"])
def manage_policies():
    if request.method == "GET":
        return jsonify(list(access_policies.values()))
    data = request.get_json(silent=True) or {}
    policy_id = data.get("id", str(uuid.uuid4()))
    consumers = data.get("allowedConsumerIds", [])
    if not isinstance(consumers, list):
        return jsonify({"error": "allowedConsumerIds must be a list"}), 400
    policy = {
        "id": policy_id,
        "allowedConsumerIds": consumers,
        "purpose": data.get("purpose", "predictive-maintenance"),
        "createdAt": datetime.utcnow().isoformat(),
    }
    access_policies[policy_id] = policy
    return jsonify(policy), 201


@app.route("/api/v1/management/assets/<asset_id>", methods=["GET"])
def get_asset(asset_id):
    if asset_id not in assets:
        return jsonify({"error": "Asset not found"}), 404
    return jsonify(assets[asset_id])


@app.route("/api/v1/management/assets/<asset_id>", methods=["DELETE"])
def delete_asset(asset_id):
    if asset_id not in assets:
        return jsonify({"error": "Asset not found"}), 404
    del assets[asset_id]
    return jsonify({"success": True})


@app.route("/api/v1/management/contractdefinitions", methods=["GET"])
def list_contract_definitions():
    return jsonify(list(contract_definitions.values()))


@app.route("/api/v1/management/contractdefinitions", methods=["POST"])
def create_contract_definition():
    data = request.get_json(silent=True) or {}
    contract_id = data.get("id", str(uuid.uuid4()))
    contract_def = {
        "id": contract_id,
        "name": data.get("name", contract_id),
        "description": data.get("description", ""),
        "accessPolicyId": data.get("accessPolicyId", "public"),
        "contractPolicyId": data.get("contractPolicyId", "public"),
        "assetsSelector": data.get("assetsSelector", []),
        "createdAt": datetime.utcnow().isoformat(),
        "connectorId": CONNECTOR_ID,
    }
    contract_definitions[contract_id] = contract_def
    return jsonify(contract_def), 201


@app.route("/api/v1/management/contractdefinitions/<contract_id>", methods=["GET"])
def get_contract_definition(contract_id):
    if contract_id not in contract_definitions:
        return jsonify({"error": "Contract definition not found"}), 404
    return jsonify(contract_definitions[contract_id])


@app.route("/api/v1/management/contractnegotiations", methods=["GET"])
def list_negotiations():
    return jsonify(list(contract_negotiations.values()))


@app.route("/api/v1/management/contractnegotiations", methods=["POST"])
def start_negotiation():
    data = request.get_json(silent=True) or {}
    offer_id = data.get("contractOfferId", "")
    if offer_id and offer_id not in contract_definitions:
        return jsonify({"error": "Contract offer not found"}), 404
    policy_id = (data.get("policy") or {}).get("policyId")
    if policy_id and policy_id not in access_policies:
        return jsonify({"error": "Policy not found"}), 400
    negotiation_id = str(uuid.uuid4())
    negotiation = {
        "id": negotiation_id,
        "state": "REQUESTED",
        "counterPartyAddress": data.get("counterPartyAddress", ""),
        "contractOfferId": offer_id,
        "policy": data.get("policy", {}),
        "createdAt": datetime.utcnow().isoformat(),
        "connectorId": CONNECTOR_ID,
    }
    contract_negotiations[negotiation_id] = negotiation
    return jsonify(negotiation), 201


@app.route("/api/v1/management/contractnegotiations/<negotiation_id>", methods=["GET"])
def get_negotiation(negotiation_id):
    if negotiation_id not in contract_negotiations:
        return jsonify({"error": "Negotiation not found"}), 404
    return jsonify(contract_negotiations[negotiation_id])


@app.route("/api/v1/management/contractnegotiations/<negotiation_id>/accept", methods=["POST"])
def accept_negotiation(negotiation_id):
    if negotiation_id not in contract_negotiations:
        return jsonify({"error": "Negotiation not found"}), 404
    negotiation = contract_negotiations[negotiation_id]
    consumer_id = request.headers.get("X-Consumer-Id", "")
    policy_id = negotiation.get("policy", {}).get("policyId")
    policy = access_policies.get(policy_id) if policy_id else None
    if policy_id and policy is None:
        negotiation["state"] = "DECLINED"
        negotiation["reason"] = "policy not found"
        return jsonify(negotiation), 403
    if policy and consumer_id not in policy["allowedConsumerIds"]:
        negotiation["state"] = "DECLINED"
        negotiation["reason"] = "consumer is not allowed by policy"
        return jsonify(negotiation), 403
    negotiation["state"] = "CONFIRMED"
    negotiation["confirmedAt"] = datetime.utcnow().isoformat()
    return jsonify(negotiation)


@app.route("/api/v1/data/<asset_id>", methods=["GET"])
def request_data_access(asset_id):
    """Policy-gated data-plane entry point.

    The prototype deliberately returns the local data reference rather than proxying
    a factory's raw telemetry through the connector.
    """
    asset = assets.get(asset_id)
    if not asset:
        return jsonify({"error": "Asset not found"}), 404
    policy_id = asset.get("policyId")
    policy = access_policies.get(policy_id) if policy_id else None
    if policy_id and policy is None:
        return jsonify({"error": "Access policy not found"}), 403
    consumer_id = request.headers.get("X-Consumer-Id", "")
    if policy and consumer_id not in policy["allowedConsumerIds"]:
        return jsonify({"error": "Access denied by policy"}), 403
    return jsonify({
        "assetId": asset_id,
        "provider": CONNECTOR_ID,
        "dataAddress": asset["properties"].get("dataAddress", "local-only"),
        "accessGranted": True,
    })


@app.route("/api/v1/ids/metadata", methods=["GET"])
def ids_metadata():
    return jsonify({
        "id": CONNECTOR_ID,
        "description": f"EDC Connector for {CONNECTOR_NAME}",
        "version": "1.0.0",
        "availableProperties": [
            "connector.name",
            "connector.id",
            "connector.participant.id",
        ],
    })


@app.route("/api/v1/ids/connector", methods=["GET"])
def ids_connector():
    return jsonify({
        "id": CONNECTOR_ID,
        "description": f"EDC Connector for {CONNECTOR_NAME}",
        "version": "1.0.0",
    })


@app.route("/api/v1/discovery", methods=["GET"])
def discover_connectors():
    return jsonify({
        "knownConnectors": list(known_connectors.values()),
        "self": {
            "id": CONNECTOR_ID,
            "name": CONNECTOR_NAME,
            "address": f"http://localhost:{CONNECTOR_PORT}",
        },
    })


@app.route("/api/v1/discovery/register", methods=["POST"])
def register_connector():
    data = request.get_json(silent=True) or {}
    connector_id = data.get("id", str(uuid.uuid4()))
    connector = {
        "id": connector_id,
        "name": data.get("name", "Unknown"),
        "address": data.get("address", ""),
        "registeredAt": datetime.utcnow().isoformat(),
    }
    known_connectors[connector_id] = connector
    return jsonify({"success": True, "connector": connector})


@app.route("/api/v1/discovery/register-all", methods=["POST"])
def register_all_connectors():
    data = request.get_json(silent=True) or {}
    connectors = data.get("connectors", [])
    for c in connectors:
        known_connectors[c["id"]] = c
    return jsonify({
        "success": True,
        "registered": len(connectors),
        "knownConnectors": list(known_connectors.values()),
    })


@app.route("/api/v1/federatedlearning/status", methods=["GET"])
def fl_status():
    try:
        response = requests.get(f"http://{FLOWER_SERVER}/api/v1/status", timeout=5)
        return jsonify(response.json())
    except Exception:
        return jsonify({"status": "unavailable", "flowerServer": FLOWER_SERVER})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "connectorId": CONNECTOR_ID,
        "connectorName": CONNECTOR_NAME,
        "port": CONNECTOR_PORT,
        "assets": len(assets),
        "contractDefinitions": len(contract_definitions),
        "negotiations": len(contract_negotiations),
    })


def register_with_other_connectors():
    other_factories = os.environ.get("EDC_OTHER_CONNECTORS", "")
    if not other_factories:
        return

    for addr in other_factories.split(","):
        addr = addr.strip()
        if not addr:
            continue
        try:
            requests.post(
                f"{addr}/api/v1/discovery/register",
                json={
                    "id": CONNECTOR_ID,
                    "name": CONNECTOR_NAME,
                    "address": f"http://{CONNECTOR_NAME.lower().replace(' ', '-')}:8080",
                },
                timeout=5,
            )
        except Exception:
            pass


def register_sample_assets():
    asset_prefix = CONNECTOR_NAME.lower().replace(" ", "")
    sensor_types = ["temperature", "vibrations", "pressure", "humidity", "power_consumption"]
    for sensor in sensor_types:
        asset_id = f"{asset_prefix}-{sensor}"
        if asset_id not in assets:
            assets[asset_id] = {
                "id": asset_id,
                "name": f"{CONNECTOR_NAME} {sensor} data",
                "type": "data",
                "description": f"Sensor readings for {sensor} from {CONNECTOR_NAME}",
                "properties": {
                    "sensorType": sensor,
                    "factory": CONNECTOR_NAME,
                },
                "createdAt": datetime.utcnow().isoformat(),
                "connectorId": CONNECTOR_ID,
            }

    contract_id = f"{asset_prefix}-fl-training-data"
    if contract_id not in contract_definitions:
        contract_definitions[contract_id] = {
            "id": contract_id,
            "name": f"{CONNECTOR_NAME} FL Training Data",
            "description": f"Contract for sharing {CONNECTOR_NAME} training data with Flower server",
            "accessPolicyId": "public",
            "contractPolicyId": "public",
            "assetsSelector": [
                {"left": "asset.type", "op": "=", "right": "data"},
            ],
            "createdAt": datetime.utcnow().isoformat(),
            "connectorId": CONNECTOR_ID,
        }


if __name__ == "__main__":
    load_config()
    register_sample_assets()
    register_with_other_connectors()
    app.run(host="0.0.0.0", port=CONNECTOR_PORT, debug=False)
