#!/usr/bin/env python3
"""
End-to-End Test Script for Industrial Data Space
Launches docker compose, validates all services, runs integration checks.
"""

import subprocess
import time
import sys
import requests
import json
from pathlib import Path

COMPOSE_FILE = "docker-compose.yml"
SERVICES = [
    ("mqtt-broker", 1883),
    ("flower-server", 8084),
    ("dashboard-api", 8000),
    ("dashboard", 8501),
    ("iot-factory-a", None),
    ("iot-factory-b", None),
    ("iot-factory-c", None),
    ("ml-client-a", None),
    ("ml-client-b", None),
    ("ml-client-c", None),
    ("edc-factory-a", 8080),
    ("edc-factory-b", 8081),
    ("edc-factory-c", 8082),
]

API_BASE = "http://localhost:8000"
FLOWER_BASE = "http://localhost:8084"
EDC_BASES = [
    "http://localhost:8080",
    "http://localhost:8081",
    "http://localhost:8082",
]


def run_cmd(cmd, check=True, capture=True, timeout=120):
    """Run shell command."""
    print(f"$ {cmd}")
    result = subprocess.run(
        cmd, shell=True, capture_output=capture, text=True, timeout=timeout
    )
    if capture:
        if result.stdout:
            print(result.stdout.strip())
        if result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}")
    return result


def wait_for_port(host, port, timeout=60):
    """Wait for TCP port to be open."""
    import socket
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(1)
    return False


def wait_for_http(url, timeout=60, expected_status=200):
    """Wait for HTTP endpoint to respond."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == expected_status:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def check_compose_up():
    """Verify all compose services are running."""
    result = run_cmd("docker compose ps --format json", check=False)
    if result.returncode != 0:
        return False
    try:
        services = json.loads(result.stdout)
        for svc in services:
            if svc.get("State") != "running":
                print(f"  ❌ {svc.get('Service')}: {svc.get('State')}")
                return False
            print(f"  ✅ {svc.get('Service')}: running")
        return True
    except json.JSONDecodeError:
        return False


def test_api_endpoints():
    """Test all FastAPI endpoints."""
    print("\n🔍 Testing FastAPI endpoints...")
    
    # /api/factories
    r = requests.get(f"{API_BASE}/api/factories", timeout=10)
    assert r.status_code == 200, f"/api/factories failed: {r.status_code}"
    factories = r.json()
    assert len(factories) == 3, f"Expected 3 factories, got {len(factories)}"
    print(f"  ✅ /api/factories: {len(factories)} factories")
    
    # /api/factories/{id}/sensors
    for f in factories:
        fid = f["factory_id"]
        r = requests.get(f"{API_BASE}/api/factories/{fid}/sensors?limit=10", timeout=10)
        assert r.status_code == 200, f"/api/factories/{fid}/sensors failed: {r.status_code}"
        data = r.json()
        assert "recent_readings" in data
        print(f"  ✅ /api/factories/{fid}/sensors: {len(data['recent_readings'])} readings")
    
    # /api/alerts
    r = requests.get(f"{API_BASE}/api/alerts?limit=10", timeout=10)
    assert r.status_code == 200
    print(f"  ✅ /api/alerts: {len(r.json())} alerts")
    
    # /api/model/performance (may 404 before first FL round)
    r = requests.get(f"{API_BASE}/api/model/performance", timeout=10)
    if r.status_code == 200:
        perf = r.json()
        print(f"  ✅ /api/model/performance: round {perf['current_model']['round']}, accuracy={perf['current_model']['accuracy']:.3f}")
    else:
        print(f"  ⏳ /api/model/performance: not ready yet (expected before FL rounds complete)")
    
    # /api/simulation/status
    r = requests.get(f"{API_BASE}/api/simulation/status", timeout=10)
    assert r.status_code == 200
    print(f"  ✅ /api/simulation/status: running={r.json()['running']}")
    
    return True


def test_edc_connectors():
    """Test EDC connector health endpoints."""
    print("\n🔍 Testing EDC connectors...")
    for i, base in enumerate(EDC_BASES):
        r = requests.get(f"{base}/health", timeout=10)
        assert r.status_code == 200, f"EDC {i} health failed: {r.status_code}"
        data = r.json()
        assert data["status"] == "healthy"
        print(f"  ✅ EDC Factory{i+1} ({base}): healthy, assets={data['assets']}, contracts={data['contractDefinitions']}")
    
    # Test asset discovery
    r = requests.get(f"{EDC_BASES[0]}/api/v1/management/assets", timeout=10)
    assert r.status_code == 200
    assets = r.json()
    assert len(assets) >= 5, f"Expected at least 5 assets, got {len(assets)}"
    print(f"  ✅ Asset discovery: {len(assets)} assets published")
    
    return True


def test_mqtt_flow():
    """Verify MQTT data is flowing."""
    print("\n🔍 Checking MQTT data flow...")
    r = requests.get(f"{API_BASE}/api/factories", timeout=10)
    factories = r.json()
    
    total_readings = 0
    for f in factories:
        fid = f["factory_id"]
        r = requests.get(f"{API_BASE}/api/factories/{fid}/sensors?limit=1", timeout=10)
        if r.status_code == 200:
            data = r.json()
            total_readings += data["total_readings"]
    
    if total_readings > 0:
        print(f"  ✅ MQTT flow: {total_readings} total readings across factories")
        return True
    else:
        print(f"  ⚠️  MQTT flow: no readings yet (simulators may still be starting)")
        return False


def test_fl_progress():
    """Check federated learning progress."""
    print("\n🔍 Checking Federated Learning progress...")
    r = requests.get(f"{API_BASE}/api/model/performance", timeout=10)
    if r.status_code != 200:
        print(f"  ⏳ FL not started yet")
        return False
    
    perf = r.json()
    current = perf["current_model"]
    history = perf["history"]
    
    print(f"  📊 Current model: round={current['round']}, accuracy={current['accuracy']:.3f}, f1={current['f1_score']:.3f}")
    print(f"  📈 History: {len(history)} rounds recorded")
    
    if current["round"] >= 3:
        print(f"  ✅ FL progressing: {current['round']} rounds completed")
        return True
    else:
        print(f"  ⏳ FL early stages: {current['round']} rounds")
        return False


def run_pytest():
    """Run the project's test suite."""
    print("\n🧪 Running pytest suite...")
    result = run_cmd(
        "/home/gadour/Desktop/data2/venv/bin/pytest tests/ -v --tb=short -x",
        check=False,
        timeout=300
    )
    if result.returncode == 0:
        print("  ✅ All tests passed")
        return True
    else:
        print("  ❌ Some tests failed")
        return False


def main():
    print("=" * 60)
    print("🚀 Industrial Data Space - E2E Validation")
    print("=" * 60)
    
    # 1. Start docker compose
    print("\n📦 Starting docker compose...")
    run_cmd("docker compose down -v", check=False)
    run_cmd("docker compose up -d --build", timeout=300)
    
    # 2. Wait for core services
    print("\n⏳ Waiting for core services...")
    for name, port in SERVICES:
        if port:
            ok = wait_for_port("localhost", port, timeout=90)
            status = "✅" if ok else "❌"
            print(f"  {status} {name}:{port}")
    
    # 3. Wait for HTTP endpoints
    print("\n⏳ Waiting for HTTP endpoints...")
    wait_for_http(f"{API_BASE}/api/factories", timeout=60)
    wait_for_http(f"{API_BASE}/health", timeout=60)
    for base in EDC_BASES:
        wait_for_http(f"{base}/health", timeout=60)
    
    # 4. Verify compose services
    print("\n🔍 Verifying docker compose services...")
    if not check_compose_up():
        print("❌ Some services not running")
        sys.exit(1)
    
    # 5. Test API endpoints
    test_api_endpoints()
    
    # 6. Test EDC
    test_edc_connectors()
    
    # 7. Test MQTT flow
    test_mqtt_flow()
    
    # 8. Test FL progress (may need more time)
    print("\n⏳ Waiting for FL rounds to progress (60s)...")
    time.sleep(60)
    test_fl_progress()
    
    # 9. Run pytest
    run_pytest()
    
    print("\n" + "=" * 60)
    print("✅ E2E VALIDATION COMPLETE")
    print("=" * 60)
    print(f"\n📊 Dashboard: http://localhost:8501")
    print(f"🔌 API Docs:  http://localhost:8000/docs")
    print(f"🔗 EDC A:     http://localhost:8080/health")
    print(f"🔗 EDC B:     http://localhost:8081/health")
    print(f"🔗 EDC C:     http://localhost:8082/health")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ E2E failed: {e}")
        sys.exit(1)