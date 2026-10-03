"""Generate factory telemetry, persist it locally, and publish the same readings to MQTT."""
import argparse
import time
from datetime import datetime

from data_generator import MultiFactoryGenerator
from mqtt_publisher import MQTTPublisher
from simulator import IoTSimulator


def main():
    parser = argparse.ArgumentParser(description="Industrial IoT telemetry runner")
    parser.add_argument("--factory-id", required=True)
    parser.add_argument("--data-dir", default="/data")
    parser.add_argument("--broker", default="mqtt-broker")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--interval", type=float, default=5)
    args = parser.parse_args()

    simulator = IoTSimulator(data_dir=args.data_dir, factory_ids=[args.factory_id])
    publisher = MQTTPublisher(args.factory_id, args.broker, args.port)
    if not publisher.connect():
        raise SystemExit("MQTT broker is unavailable")
    try:
        while True:
            reading = simulator.generator.generate_all(datetime.now())[0]
            simulator._write_reading(reading)
            publisher.publish(reading)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        simulator._close_files()
        publisher.disconnect()


if __name__ == "__main__":
    main()
