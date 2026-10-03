#!/usr/bin/env python3
"""Test MQTT publisher with live sensor data."""
import subprocess
import time
import sys
import os
import json

def main():
    venv_python = os.path.join(os.path.dirname(__file__), "venv", "bin", "python")
    iot_dir = os.path.join(os.path.dirname(__file__), "iot-simulation")
    
    print("=" * 60)
    print("MQTT SENSOR DATA PUBLISHER TEST")
    print("=" * 60)
    
    # Generate sensor data and publish to MQTT
    print("\n[1/2] Generating sensor data and publishing to MQTT...")
    print("  Factories: FactoryA, FactoryB, FactoryC")
    print("  Broker: localhost:1884")
    print("  Topic: factory/{factory_id}/sensors")
    print()
    
    # Run simulator with MQTT publisher
    result = subprocess.run(
        [venv_python, "-c", """
import sys
sys.path.insert(0, 'iot-simulation')
from data_generator import MultiFactoryGenerator
from mqtt_publisher import MQTTPublisher
import time
import json

generator = MultiFactoryGenerator()
factory_ids = ["FactoryA", "FactoryB", "FactoryC"]

publishers = {}
for fid in factory_ids:
    publishers[fid] = MQTTPublisher(
        factory_id=fid,
        broker_host="localhost",
        broker_port=1884,
    )

# Connect all publishers
for fid, pub in publishers.items():
    try:
        pub.connect()
        print(f"  Connected: {fid}")
    except Exception as e:
        print(f"  Failed to connect {fid}: {e}")

# Generate and publish 10 readings per factory
print()
print("Publishing sensor data...")
for i in range(10):
    from datetime import datetime
    readings = generator.generate_all(datetime.now())
    for reading in readings:
        fid = reading["factory_id"]
        if fid in publishers and publishers[fid].connected:
            publishers[fid].publish_json(reading)
            status = "FAIL" if reading["status"] == "failure" else " OK "
            print(f"  [{status}] {fid}: T={reading['temperature']:.1f}°C V={reading['vibrations']:.2f} P={reading['pressure']:.1f}")
    time.sleep(1)

# Disconnect
for fid, pub in publishers.items():
    pub.disconnect()
    print(f"  Disconnected: {fid}")

print()
print("MQTT publish test complete!")
"""],
        cwd=os.path.dirname(__file__),
        capture_output=True,
        text=True,
    )
    
    print(result.stdout)
    if result.stderr:
        # Filter out TensorFlow warnings
        errors = [l for l in result.stderr.split("\n") if "ERROR" in l or "Traceback" in l]
        if errors:
            print("ERRORS:")
            print("\n".join(errors))
    
    # Check MQTT broker
    print("\n[2/2] Verifying MQTT broker...")
    result2 = subprocess.run(
        ["docker", "exec", "mosquitto-industrial", "mosquitto_pub", "-t", "test/topic", "-m", "test"],
        capture_output=True,
        text=True,
    )
    
    if result2.returncode == 0:
        print("  MQTT broker responding: OK")
    else:
        print(f"  MQTT broker error: {result2.stderr}")
    
    print("\n" + "=" * 60)
    print("MQTT TEST COMPLETE")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
