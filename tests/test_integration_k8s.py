from pathlib import Path

import pytest
import yaml


K8S_DIR = Path(__file__).resolve().parent.parent / "k8s"
EXPECTED_NAMESPACE = "industrial-data-space"


def load_all_documents(yaml_path):
    with open(yaml_path) as f:
        return list(yaml.safe_load_all(f))


@pytest.fixture(scope="module")
def namespace_manifest():
    docs = load_all_documents(K8S_DIR / "namespace.yaml")
    assert len(docs) == 1
    return docs[0]


@pytest.fixture(scope="module")
def flower_server_manifests():
    return load_all_documents(K8S_DIR / "flower-server.yaml")


@pytest.fixture(scope="module")
def ml_client_manifests():
    return load_all_documents(K8S_DIR / "ml-client.yaml")


@pytest.fixture(scope="module")
def dashboard_manifests():
    return load_all_documents(K8S_DIR / "dashboard.yaml")


@pytest.fixture(scope="module")
def edc_manifests():
    return load_all_documents(K8S_DIR / "edc-connector.yaml")


@pytest.fixture(scope="module")
def mqtt_manifests():
    return load_all_documents(K8S_DIR / "mqtt-broker.yaml")


@pytest.fixture(scope="module")
def configmap_manifests():
    return load_all_documents(K8S_DIR / "configmap.yaml")


class TestNamespaceManifest:
    def test_namespace_name(self, namespace_manifest):
        assert namespace_manifest["kind"] == "Namespace"
        assert namespace_manifest["metadata"]["name"] == "industrial-data-space"

    def test_namespace_has_labels(self, namespace_manifest):
        labels = namespace_manifest["metadata"].get("labels", {})
        assert "app.kubernetes.io/name" in labels

    def test_namespace_apiversion(self, namespace_manifest):
        assert namespace_manifest["apiVersion"] == "v1"


class TestFlowerServerManifests:
    def test_has_configmap_deployment_service(self, flower_server_manifests):
        kinds = [d["kind"] for d in flower_server_manifests]
        assert "ConfigMap" in kinds
        assert "Deployment" in kinds
        assert "Service" in kinds

    def test_configmap_namespace(self, flower_server_manifests):
        cm = [d for d in flower_server_manifests if d["kind"] == "ConfigMap"][0]
        assert cm["metadata"]["namespace"] == "industrial-data-space"

    def test_configmap_has_required_keys(self, flower_server_manifests):
        cm = [d for d in flower_server_manifests if d["kind"] == "ConfigMap"][0]
        data = cm["data"]
        assert "FLOWER_ROUNDS" in data
        assert "FLOWER_MIN_CLIENTS" in data
        assert "FLOWER_PORT" in data

    def test_deployment_replica_count(self, flower_server_manifests):
        deploy = [d for d in flower_server_manifests if d["kind"] == "Deployment"][0]
        assert deploy["spec"]["replicas"] == 1

    def test_deployment_has_container(self, flower_server_manifests):
        deploy = [d for d in flower_server_manifests if d["kind"] == "Deployment"][0]
        containers = deploy["spec"]["template"]["spec"]["containers"]
        assert len(containers) >= 1
        assert containers[0]["name"] == "flower-server"

    def test_deployment_has_resource_limits(self, flower_server_manifests):
        deploy = [d for d in flower_server_manifests if d["kind"] == "Deployment"][0]
        resources = deploy["spec"]["template"]["spec"]["containers"][0]["resources"]
        assert "requests" in resources
        assert "limits" in resources
        assert "cpu" in resources["requests"]
        assert "memory" in resources["requests"]

    def test_deployment_has_health_probes(self, flower_server_manifests):
        deploy = [d for d in flower_server_manifests if d["kind"] == "Deployment"][0]
        container = deploy["spec"]["template"]["spec"]["containers"][0]
        assert "livenessProbe" in container
        assert "readinessProbe" in container

    def test_service_type_clusterip(self, flower_server_manifests):
        svc = [d for d in flower_server_manifests if d["kind"] == "Service"][0]
        assert svc["spec"]["type"] == "ClusterIP"

    def test_service_ports(self, flower_server_manifests):
        svc = [d for d in flower_server_manifests if d["kind"] == "Service"][0]
        ports = svc["spec"]["ports"]
        assert len(ports) >= 1
        assert ports[0]["port"] == 8080


class TestMLClientManifests:
    def test_has_three_deployments(self, ml_client_manifests):
        deployments = [d for d in ml_client_manifests if d["kind"] == "Deployment"]
        assert len(deployments) == 3

    def test_all_factories_represented(self, ml_client_manifests):
        deployments = [d for d in ml_client_manifests if d["kind"] == "Deployment"]
        names = {d["metadata"]["name"] for d in deployments}
        assert "ml-client-factory-a" in names
        assert "ml-client-factory-b" in names
        assert "ml-client-factory-c" in names

    def test_all_factories_in_correct_namespace(self, ml_client_manifests):
        deployments = [d for d in ml_client_manifests if d["kind"] == "Deployment"]
        for deploy in deployments:
            assert deploy["metadata"]["namespace"] == EXPECTED_NAMESPACE

    def test_all_have_resource_limits(self, ml_client_manifests):
        deployments = [d for d in ml_client_manifests if d["kind"] == "Deployment"]
        for deploy in deployments:
            resources = deploy["spec"]["template"]["spec"]["containers"][0]["resources"]
            assert "requests" in resources
            assert "limits" in resources

    def test_all_have_volume_mounts(self, ml_client_manifests):
        deployments = [d for d in ml_client_manifests if d["kind"] == "Deployment"]
        for deploy in deployments:
            container = deploy["spec"]["template"]["spec"]["containers"][0]
            assert "volumeMounts" in container

    def test_selectors_match_labels(self, ml_client_manifests):
        deployments = [d for d in ml_client_manifests if d["kind"] == "Deployment"]
        for deploy in deployments:
            selector = deploy["spec"]["selector"]["matchLabels"]
            template_labels = deploy["spec"]["template"]["metadata"]["labels"]
            for key, val in selector.items():
                assert template_labels[key] == val


class TestDashboardManifests:
    def test_has_deployment_and_service(self, dashboard_manifests):
        kinds = [d["kind"] for d in dashboard_manifests]
        assert "Deployment" in kinds
        assert "Service" in kinds

    def test_deployment_in_correct_namespace(self, dashboard_manifests):
        deploy = [d for d in dashboard_manifests if d["kind"] == "Deployment"][0]
        assert deploy["metadata"]["namespace"] == EXPECTED_NAMESPACE

    def test_deployment_has_fastapi_container(self, dashboard_manifests):
        deploy = [d for d in dashboard_manifests if d["kind"] == "Deployment"][0]
        containers = deploy["spec"]["template"]["spec"]["containers"]
        container_names = {c["name"] for c in containers}
        assert "fastapi-backend" in container_names

    def test_deployment_has_http_probes(self, dashboard_manifests):
        deploy = [d for d in dashboard_manifests if d["kind"] == "Deployment"][0]
        container = deploy["spec"]["template"]["spec"]["containers"][0]
        assert "livenessProbe" in container
        assert container["livenessProbe"]["httpGet"]["path"] == "/api/factories"
        assert "readinessProbe" in container

    def test_deployment_references_configmap(self, dashboard_manifests):
        deploy = [d for d in dashboard_manifests if d["kind"] == "Deployment"][0]
        env = deploy["spec"]["template"]["spec"]["containers"][0].get("env", [])
        configmap_refs = [
            e for e in env
            if "valueFrom" in e and "configMapKeyRef" in e.get("valueFrom", {})
        ]
        assert len(configmap_refs) >= 1

    def test_service_port_8000(self, dashboard_manifests):
        svc = [d for d in dashboard_manifests if d["kind"] == "Service"][0]
        assert svc["spec"]["ports"][0]["port"] == 8000

    def test_service_type_clusterip(self, dashboard_manifests):
        svc = [d for d in dashboard_manifests if d["kind"] == "Service"][0]
        assert svc["spec"]["type"] == "ClusterIP"


class TestEDCConnectorManifests:
    def test_has_three_deployments_and_services(self, edc_manifests):
        kinds = [d["kind"] for d in edc_manifests]
        assert kinds.count("Deployment") == 3
        assert kinds.count("Service") == 3

    def test_all_factories_present(self, edc_manifests):
        deployments = [d for d in edc_manifests if d["kind"] == "Deployment"]
        names = {d["metadata"]["name"] for d in deployments}
        assert "edc-factory-a" in names
        assert "edc-factory-b" in names
        assert "edc-factory-c" in names

    def test_all_in_correct_namespace(self, edc_manifests):
        for doc in edc_manifests:
            assert doc["metadata"]["namespace"] == EXPECTED_NAMESPACE

    def test_all_have_health_probes(self, edc_manifests):
        deployments = [d for d in edc_manifests if d["kind"] == "Deployment"]
        for deploy in deployments:
            container = deploy["spec"]["template"]["spec"]["containers"][0]
            assert "livenessProbe" in container
            assert "readinessProbe" in container
            assert container["livenessProbe"]["httpGet"]["path"] == "/health"

    def test_all_have_resource_limits(self, edc_manifests):
        deployments = [d for d in edc_manifests if d["kind"] == "Deployment"]
        for deploy in deployments:
            resources = deploy["spec"]["template"]["spec"]["containers"][0]["resources"]
            assert "requests" in resources
            assert "limits" in resources

    def test_all_reference_configmap_volume(self, edc_manifests):
        deployments = [d for d in edc_manifests if d["kind"] == "Deployment"]
        for deploy in deployments:
            volumes = deploy["spec"]["template"]["spec"].get("volumes", [])
            configmap_volumes = [v for v in volumes if "configMap" in v]
            assert len(configmap_volumes) >= 1

    def test_services_are_clusterip(self, edc_manifests):
        services = [d for d in edc_manifests if d["kind"] == "Service"]
        for svc in services:
            assert svc["spec"]["type"] == "ClusterIP"


class TestMQTTBrokerManifests:
    def test_has_deployment_and_service(self, mqtt_manifests):
        kinds = [d["kind"] for d in mqtt_manifests]
        assert "Deployment" in kinds
        assert "Service" in kinds

    def test_uses_mosquitto_image(self, mqtt_manifests):
        deploy = [d for d in mqtt_manifests if d["kind"] == "Deployment"][0]
        image = deploy["spec"]["template"]["spec"]["containers"][0]["image"]
        assert "mosquitto" in image.lower()

    def test_mqtt_ports_exposed(self, mqtt_manifests):
        svc = [d for d in mqtt_manifests if d["kind"] == "Service"][0]
        ports = {p["port"] for p in svc["spec"]["ports"]}
        assert 1883 in ports

    def test_has_resource_limits(self, mqtt_manifests):
        deploy = [d for d in mqtt_manifests if d["kind"] == "Deployment"][0]
        resources = deploy["spec"]["template"]["spec"]["containers"][0]["resources"]
        assert "requests" in resources
        assert "limits" in resources

    def test_has_health_probes(self, mqtt_manifests):
        deploy = [d for d in mqtt_manifests if d["kind"] == "Deployment"][0]
        container = deploy["spec"]["template"]["spec"]["containers"][0]
        assert "livenessProbe" in container
        assert "readinessProbe" in container

    def test_namespace_correct(self, mqtt_manifests):
        for doc in mqtt_manifests:
            assert doc["metadata"]["namespace"] == EXPECTED_NAMESPACE

    def test_has_volume_mounts(self, mqtt_manifests):
        deploy = [d for d in mqtt_manifests if d["kind"] == "Deployment"][0]
        container = deploy["spec"]["template"]["spec"]["containers"][0]
        assert "volumeMounts" in container
        volumes = deploy["spec"]["template"]["spec"].get("volumes", [])
        assert len(volumes) >= 1


class TestConfigMaps:
    def test_platform_configmap_exists(self, configmap_manifests):
        names = {d["metadata"]["name"] for d in configmap_manifests}
        assert "platform-config" in names

    def test_mosquitto_configmap_exists(self, configmap_manifests):
        names = {d["metadata"]["name"] for d in configmap_manifests}
        assert "mosquitto-config" in names

    def test_edc_configmap_exists(self, configmap_manifests):
        names = {d["metadata"]["name"] for d in configmap_manifests}
        assert "edc-config" in names

    def test_platform_config_has_mqtt_settings(self, configmap_manifests):
        platform = [d for d in configmap_manifests if d["metadata"]["name"] == "platform-config"][0]
        data = platform["data"]
        assert "MQTT_BROKER_HOST" in data
        assert "MQTT_BROKER_PORT" in data
        assert "FLOWER_SERVER_HOST" in data

    def test_edc_config_has_all_factories(self, configmap_manifests):
        edc = [d for d in configmap_manifests if d["metadata"]["name"] == "edc-config"][0]
        data = edc["data"]
        assert "config-factory-a.properties" in data
        assert "config-factory-b.properties" in data
        assert "config-factory-c.properties" in data

    def test_all_configmaps_in_correct_namespace(self, configmap_manifests):
        for cm in configmap_manifests:
            assert cm["metadata"]["namespace"] == "industrial-data-space"

    def test_edc_configs_have_flower_server(self, configmap_manifests):
        edc = [d for d in configmap_manifests if d["metadata"]["name"] == "edc-config"][0]
        for key, value in edc["data"].items():
            if key.startswith("config-factory"):
                assert "flower-server" in value


class TestCrossManifestConsistency:
    VALID_NAMESPACES = {"industrial-data-space", "industrial-dataspace"}

    def test_all_services_in_same_namespace(self):
        for yaml_file in ["flower-server.yaml", "ml-client.yaml", "dashboard.yaml", "edc-connector.yaml", "mqtt-broker.yaml"]:
            docs = load_all_documents(K8S_DIR / yaml_file)
            for doc in docs:
                if doc["kind"] == "Service":
                    assert doc["metadata"]["namespace"] in self.VALID_NAMESPACES

    def test_all_deployments_in_same_namespace(self):
        for yaml_file in ["flower-server.yaml", "ml-client.yaml", "dashboard.yaml", "edc-connector.yaml", "mqtt-broker.yaml"]:
            docs = load_all_documents(K8S_DIR / yaml_file)
            for doc in docs:
                if doc["kind"] == "Deployment":
                    assert doc["metadata"]["namespace"] in self.VALID_NAMESPACES

    def test_all_deployments_have_replicas(self):
        for yaml_file in ["flower-server.yaml", "ml-client.yaml", "dashboard.yaml", "edc-connector.yaml", "mqtt-broker.yaml"]:
            docs = load_all_documents(K8S_DIR / yaml_file)
            for doc in docs:
                if doc["kind"] == "Deployment":
                    assert "replicas" in doc["spec"]
                    assert doc["spec"]["replicas"] >= 1

    def test_all_deployments_have_selector_match_labels(self):
        for yaml_file in ["flower-server.yaml", "ml-client.yaml", "dashboard.yaml", "edc-connector.yaml", "mqtt-broker.yaml"]:
            docs = load_all_documents(K8S_DIR / yaml_file)
            for doc in docs:
                if doc["kind"] == "Deployment":
                    assert "selector" in doc["spec"]
                    assert "matchLabels" in doc["spec"]["selector"]

    def test_flower_server_service_reachable_by_ml_clients(self):
        flower_docs = load_all_documents(K8S_DIR / "flower-server.yaml")
        flower_svc = [d for d in flower_docs if d["kind"] == "Service"][0]
        flower_port = flower_svc["spec"]["ports"][0]["port"]

        ml_docs = load_all_documents(K8S_DIR / "ml-client.yaml")
        ml_deploys = [d for d in ml_docs if d["kind"] == "Deployment"]
        for deploy in ml_deploys:
            args = deploy["spec"]["template"]["spec"]["containers"][0].get("args", [])
            args_str = " ".join(str(a) for a in args)
            if "server-address" in args_str:
                assert str(flower_port) in args_str
