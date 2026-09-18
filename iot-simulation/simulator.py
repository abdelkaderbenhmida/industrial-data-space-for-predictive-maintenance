import csv
import os
import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from data_generator import MultiFactoryGenerator


class IoTSimulator:
    def __init__(
        self,
        data_dir: str = "data",
        factory_ids: list[str] | None = None,
        interval_seconds: int = 10,
        seed: int | None = None,
    ):
        self.data_dir = Path(data_dir)
        self.interval = interval_seconds
        self.running = False
        self.generator = MultiFactoryGenerator(factory_ids=factory_ids, seed=seed)
        self._file_handles: dict[str, any] = {}
        self._writers: dict[str, csv.DictWriter] = {}
        self._stats: dict[str, dict] = {}

        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum, frame):
        self.stop()

    def _ensure_factory_dir(self, factory_id: str) -> Path:
        factory_dir = self.data_dir / factory_id
        factory_dir.mkdir(parents=True, exist_ok=True)
        return factory_dir

    def _get_csv_path(self, factory_id: str, date_str: str) -> Path:
        factory_dir = self._ensure_factory_dir(factory_id)
        return factory_dir / f"readings_{date_str}.csv"

    def _get_writer(self, factory_id: str, date_str: str) -> csv.DictWriter:
        key = f"{factory_id}_{date_str}"
        if key in self._writers:
            return self._writers[key]

        csv_path = self._get_csv_path(factory_id, date_str)
        file_exists = csv_path.exists() and csv_path.stat().st_size > 0

        fh = open(csv_path, "a", newline="")
        fieldnames = [
            "factory_id", "timestamp", "temperature", "vibrations",
            "pressure", "humidity", "power_consumption", "status",
        ]
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()

        self._file_handles[key] = fh
        self._writers[key] = writer
        return writer

    def _init_stats(self, factory_id: str):
        if factory_id not in self._stats:
            self._stats[factory_id] = {
                "total": 0, "normal": 0, "failure": 0,
                "sensors": {
                    "temperature": {"min": float("inf"), "max": float("-inf"), "sum": 0.0, "count": 0},
                    "vibrations": {"min": float("inf"), "max": float("-inf"), "sum": 0.0, "count": 0},
                    "pressure": {"min": float("inf"), "max": float("-inf"), "sum": 0.0, "count": 0},
                    "humidity": {"min": float("inf"), "max": float("-inf"), "sum": 0.0, "count": 0},
                    "power_consumption": {"min": float("inf"), "max": float("-inf"), "sum": 0.0, "count": 0},
                },
            }

    def _update_stats(self, reading: dict):
        fid = reading["factory_id"]
        self._init_stats(fid)
        stats = self._stats[fid]
        stats["total"] += 1
        stats[reading["status"]] += 1
        for sensor in stats["sensors"]:
            val = reading[sensor]
            s = stats["sensors"][sensor]
            s["min"] = min(s["min"], val)
            s["max"] = max(s["max"], val)
            s["sum"] += val
            s["count"] += 1

    def _write_reading(self, reading: dict):
        ts = datetime.fromisoformat(reading["timestamp"])
        date_str = ts.strftime("%Y-%m-%d")
        writer = self._get_writer(reading["factory_id"], date_str)
        writer.writerow(reading)
        self._update_stats(reading)

    def _close_files(self):
        for fh in self._file_handles.values():
            try:
                fh.close()
            except Exception:
                pass
        self._file_handles.clear()
        self._writers.clear()

    def generate_batch(self, count: int, interval_seconds: int | None = None):
        interval = interval_seconds or self.interval
        start = datetime.now()
        for i in range(count):
            ts = start + timedelta(seconds=i * interval)
            readings = self.generator.generate_all(ts)
            for reading in readings:
                self._write_reading(reading)
        self._close_files()

    def run(self):
        self.running = True
        print(f"[IoT Simulator] Starting with factories: {self.generator.factory_ids}")
        print(f"[IoT Simulator] Interval: {self.interval}s | Data dir: {self.data_dir}")

        try:
            while self.running:
                now = datetime.now()
                readings = self.generator.generate_all(now)
                for reading in readings:
                    self._write_reading(reading)
                    status_tag = "FAIL" if reading["status"] == "failure" else " OK "
                    print(
                        f"[{status_tag}] {reading['factory_id']} "
                        f"T={reading['temperature']}°C V={reading['vibrations']} "
                        f"P={reading['pressure']} H={reading['humidity']} "
                        f"Pwr={reading['power_consumption']}W"
                    )
                time.sleep(self.interval)
        except KeyboardInterrupt:
            pass
        finally:
            self._close_files()
            self._print_summary()

    def stop(self):
        print("\n[IoT Simulator] Stopping...")
        self.running = False

    def _print_summary(self):
        print("\n[IoT Simulator] Session Summary")
        print("-" * 50)
        for fid, stats in self._stats.items():
            failure_pct = (stats["failure"] / stats["total"] * 100) if stats["total"] else 0
            print(f"  {fid}: {stats['total']} readings | "
                  f"Normal: {stats['normal']} | Failure: {stats['failure']} ({failure_pct:.1f}%)")
            for sensor, s in stats["sensors"].items():
                if s["count"] > 0:
                    avg = s["sum"] / s["count"]
                    print(f"    {sensor}: min={s['min']:.2f} max={s['max']:.2f} avg={avg:.2f}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="IoT Sensor Simulator")
    parser.add_argument("--factories", nargs="+", default=["FactoryA", "FactoryB", "FactoryC"])
    parser.add_argument("--interval", type=int, default=10, help="Seconds between readings")
    parser.add_argument("--data-dir", default="data", help="Output data directory")
    parser.add_argument("--batch", type=int, default=0, help="Generate N readings then exit (0=continuous)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    args = parser.parse_args()

    sim = IoTSimulator(
        data_dir=args.data_dir,
        factory_ids=args.factories,
        interval_seconds=args.interval,
        seed=args.seed,
    )

    if args.batch > 0:
        print(f"[IoT Simulator] Generating {args.batch} readings per factory...")
        sim.generate_batch(args.batch)
        sim._print_summary()
    else:
        sim.run()


if __name__ == "__main__":
    main()
