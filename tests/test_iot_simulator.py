import csv
import os
import signal
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from simulator import IoTSimulator


@pytest.fixture
def tmp_data_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def sim(tmp_data_dir):
    return IoTSimulator(
        data_dir=tmp_data_dir,
        factory_ids=["FactoryA"],
        interval_seconds=1,
        seed=42,
    )


@pytest.fixture
def sim_multi(tmp_data_dir):
    return IoTSimulator(
        data_dir=tmp_data_dir,
        factory_ids=["FactoryA", "FactoryB", "FactoryC"],
        interval_seconds=5,
        seed=42,
    )


class TestIoTSimulatorInit:
    def test_data_dir_created(self, tmp_data_dir):
        IoTSimulator(data_dir=tmp_data_dir)
        assert Path(tmp_data_dir).exists()

    def test_default_factories(self, tmp_data_dir):
        sim = IoTSimulator(data_dir=tmp_data_dir)
        assert len(sim.generator.factory_ids) == 3

    def test_custom_factories(self, tmp_data_dir):
        sim = IoTSimulator(data_dir=tmp_data_dir, factory_ids=["FactoryX"])
        assert sim.generator.factory_ids == ["FactoryX"]

    def test_interval_setting(self, tmp_data_dir):
        sim = IoTSimulator(data_dir=tmp_data_dir, interval_seconds=30)
        assert sim.interval == 30

    def test_not_running_initially(self, tmp_data_dir):
        sim = IoTSimulator(data_dir=tmp_data_dir)
        assert sim.running is False

    def test_empty_stats_initially(self, tmp_data_dir):
        sim = IoTSimulator(data_dir=tmp_data_dir)
        assert sim._stats == {}

    def test_seed_determinism(self, tmp_data_dir):
        import random
        ts = datetime(2025, 1, 1)
        random.seed(100)
        s1 = IoTSimulator(data_dir=tmp_data_dir, factory_ids=["FactoryA"], seed=100)
        r1 = s1.generator.generate_all(ts)
        random.seed(100)
        s2 = IoTSimulator(data_dir=tmp_data_dir, factory_ids=["FactoryA"], seed=100)
        r2 = s2.generator.generate_all(ts)
        assert r1 == r2


class TestIoTSimulatorSignalHandling:
    def test_signal_handlers_registered(self):
        sim = IoTSimulator(data_dir="/tmp/test_sim")
        assert signal.getsignal(signal.SIGINT) != signal.SIG_DFL
        assert signal.getsignal(signal.SIGTERM) != signal.SIG_DFL

    def test_stop_sets_running_false(self, sim):
        sim.running = True
        sim.stop()
        assert sim.running is False


class TestIoTSimulatorCSV:
    def test_csv_created_with_header(self, sim):
        reading = {
            "factory_id": "FactoryA",
            "timestamp": "2025-01-15T10:00:00",
            "temperature": 65.0,
            "vibrations": 0.5,
            "pressure": 14.7,
            "humidity": 45.0,
            "power_consumption": 150.0,
            "status": "normal",
        }
        sim._write_reading(reading)
        sim._close_files()

        factory_dir = Path(sim.data_dir) / "FactoryA"
        csv_files = list(factory_dir.glob("readings_*.csv"))
        assert len(csv_files) == 1

        with open(csv_files[0]) as f:
            reader = csv.reader(f)
            header = next(reader)
            assert "factory_id" in header
            assert "temperature" in header
            assert "status" in header

    def test_csv_row_written(self, sim):
        reading = {
            "factory_id": "FactoryA",
            "timestamp": "2025-01-15T10:00:00",
            "temperature": 65.0,
            "vibrations": 0.5,
            "pressure": 14.7,
            "humidity": 45.0,
            "power_consumption": 150.0,
            "status": "normal",
        }
        sim._write_reading(reading)
        sim._close_files()

        factory_dir = Path(sim.data_dir) / "FactoryA"
        csv_files = list(factory_dir.glob("readings_*.csv"))
        with open(csv_files[0]) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]["factory_id"] == "FactoryA"
            assert rows[0]["temperature"] == "65.0"

    def test_multiple_rows_same_file(self, sim):
        ts_base = datetime(2025, 1, 15, 10, 0, 0)
        for i in range(5):
            reading = {
                "factory_id": "FactoryA",
                "timestamp": ts_base.isoformat(),
                "temperature": 65.0 + i,
                "vibrations": 0.5,
                "pressure": 14.7,
                "humidity": 45.0,
                "power_consumption": 150.0,
                "status": "normal",
            }
            sim._write_reading(reading)
        sim._close_files()

        factory_dir = Path(sim.data_dir) / "FactoryA"
        csv_files = list(factory_dir.glob("readings_*.csv"))
        with open(csv_files[0]) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 5

    def test_separate_files_per_date(self, sim):
        reading1 = {
            "factory_id": "FactoryA",
            "timestamp": "2025-01-15T10:00:00",
            "temperature": 65.0,
            "vibrations": 0.5,
            "pressure": 14.7,
            "humidity": 45.0,
            "power_consumption": 150.0,
            "status": "normal",
        }
        reading2 = {
            "factory_id": "FactoryA",
            "timestamp": "2025-01-16T10:00:00",
            "temperature": 70.0,
            "vibrations": 0.6,
            "pressure": 15.0,
            "humidity": 50.0,
            "power_consumption": 160.0,
            "status": "normal",
        }
        sim._write_reading(reading1)
        sim._write_reading(reading2)
        sim._close_files()

        factory_dir = Path(sim.data_dir) / "FactoryA"
        csv_files = list(factory_dir.glob("readings_*.csv"))
        assert len(csv_files) == 2
        filenames = {f.name for f in csv_files}
        assert "readings_2025-01-15.csv" in filenames
        assert "readings_2025-01-16.csv" in filenames

    def test_separate_dirs_per_factory(self, sim_multi):
        readings = sim_multi.generator.generate_all(datetime(2025, 1, 15, 10, 0, 0))
        for r in readings:
            sim_multi._write_reading(r)
        sim_multi._close_files()

        for fid in ["FactoryA", "FactoryB", "FactoryC"]:
            factory_dir = Path(sim_multi.data_dir) / fid
            assert factory_dir.exists()
            assert factory_dir.is_dir()

    def test_header_not_duplicated_on_append(self, sim):
        reading = {
            "factory_id": "FactoryA",
            "timestamp": "2025-01-15T10:00:00",
            "temperature": 65.0,
            "vibrations": 0.5,
            "pressure": 14.7,
            "humidity": 45.0,
            "power_consumption": 150.0,
            "status": "normal",
        }
        sim._write_reading(reading)
        sim._close_files()

        sim2 = IoTSimulator(
            data_dir=str(sim.data_dir),
            factory_ids=["FactoryA"],
            seed=42,
        )
        sim2._write_reading(reading)
        sim2._close_files()

        factory_dir = Path(sim.data_dir) / "FactoryA"
        csv_files = list(factory_dir.glob("readings_*.csv"))
        with open(csv_files[0]) as f:
            lines = f.readlines()
            header_lines = [l for l in lines if l.startswith("factory_id")]
            assert len(header_lines) == 1


class TestIoTSimulatorStats:
    def test_init_stats_creates_structure(self, sim):
        sim._init_stats("FactoryA")
        assert "FactoryA" in sim._stats
        stats = sim._stats["FactoryA"]
        assert stats["total"] == 0
        assert stats["normal"] == 0
        assert stats["failure"] == 0
        assert "sensors" in stats
        assert "temperature" in stats["sensors"]
        assert "min" in stats["sensors"]["temperature"]

    def test_update_stats_increments_total(self, sim):
        sim._init_stats("FactoryA")
        reading = {
            "factory_id": "FactoryA",
            "timestamp": "2025-01-15T10:00:00",
            "temperature": 65.0,
            "vibrations": 0.5,
            "pressure": 14.7,
            "humidity": 45.0,
            "power_consumption": 150.0,
            "status": "normal",
        }
        sim._update_stats(reading)
        assert sim._stats["FactoryA"]["total"] == 1
        assert sim._stats["FactoryA"]["normal"] == 1
        assert sim._stats["FactoryA"]["failure"] == 0

    def test_update_stats_failure_count(self, sim):
        sim._init_stats("FactoryA")
        reading = {
            "factory_id": "FactoryA",
            "timestamp": "2025-01-15T10:00:00",
            "temperature": 110.0,
            "vibrations": 4.0,
            "pressure": 23.0,
            "humidity": 85.0,
            "power_consumption": 480.0,
            "status": "failure",
        }
        sim._update_stats(reading)
        assert sim._stats["FactoryA"]["failure"] == 1

    def test_update_stats_sensor_min_max(self, sim):
        sim._init_stats("FactoryA")
        readings = [
            {"factory_id": "FactoryA", "timestamp": "2025-01-15T10:00:00",
             "temperature": 60.0, "vibrations": 0.3, "pressure": 14.0,
             "humidity": 40.0, "power_consumption": 120.0, "status": "normal"},
            {"factory_id": "FactoryA", "timestamp": "2025-01-15T10:00:10",
             "temperature": 75.0, "vibrations": 0.8, "pressure": 16.0,
             "humidity": 55.0, "power_consumption": 200.0, "status": "normal"},
        ]
        for r in readings:
            sim._update_stats(r)

        stats = sim._stats["FactoryA"]
        assert stats["sensors"]["temperature"]["min"] == 60.0
        assert stats["sensors"]["temperature"]["max"] == 75.0
        assert stats["sensors"]["temperature"]["sum"] == 135.0
        assert stats["sensors"]["temperature"]["count"] == 2

    def test_print_summary_does_not_crash(self, sim, capsys):
        sim._init_stats("FactoryA")
        sim._stats["FactoryA"]["total"] = 10
        sim._stats["FactoryA"]["normal"] = 8
        sim._stats["FactoryA"]["failure"] = 2
        sim._print_summary()
        captured = capsys.readouterr()
        assert "FactoryA" in captured.out


class TestIoTSimulatorBatch:
    def test_generate_batch_creates_files(self, sim):
        sim.generate_batch(count=3)
        factory_dir = Path(sim.data_dir) / "FactoryA"
        csv_files = list(factory_dir.glob("readings_*.csv"))
        assert len(csv_files) == 1

    def test_generate_batch_row_count(self, sim):
        sim.generate_batch(count=5)
        factory_dir = Path(sim.data_dir) / "FactoryA"
        csv_files = list(factory_dir.glob("readings_*.csv"))
        with open(csv_files[0]) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 5

    def test_generate_batch_multi_factory(self, sim_multi):
        sim_multi.generate_batch(count=2)
        for fid in ["FactoryA", "FactoryB", "FactoryC"]:
            factory_dir = Path(sim_multi.data_dir) / fid
            csv_files = list(factory_dir.glob("readings_*.csv"))
            assert len(csv_files) == 1
            with open(csv_files[0]) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                assert len(rows) == 2

    def test_generate_batch_files_closed(self, sim):
        sim.generate_batch(count=3)
        assert sim._file_handles == {}
        assert sim._writers == {}

    def test_generate_batch_stats_updated(self, sim):
        sim.generate_batch(count=10)
        assert "FactoryA" in sim._stats
        assert sim._stats["FactoryA"]["total"] == 10


class TestIoTSimulatorRun:
    def test_run_and_stop(self, sim):
        sim.running = True
        sim.stop()
        assert sim.running is False

    def test_generate_batch_zero_count(self, sim):
        sim.generate_batch(count=0)
        factory_dir = Path(sim.data_dir) / "FactoryA"
        csv_files = list(factory_dir.glob("readings_*.csv"))
        assert len(csv_files) == 0


class TestIoTSimulatorCloseFiles:
    def test_close_files_clears_handles(self, sim):
        reading = {
            "factory_id": "FactoryA",
            "timestamp": "2025-01-15T10:00:00",
            "temperature": 65.0,
            "vibrations": 0.5,
            "pressure": 14.7,
            "humidity": 45.0,
            "power_consumption": 150.0,
            "status": "normal",
        }
        sim._write_reading(reading)
        assert len(sim._file_handles) > 0
        sim._close_files()
        assert len(sim._file_handles) == 0
        assert len(sim._writers) == 0

    def test_close_files_handles_already_closed(self, sim):
        mock_fh = MagicMock()
        mock_fh.close.side_effect = ValueError("I/O operation on closed file.")
        sim._file_handles["test"] = mock_fh
        sim._close_files()
        assert sim._file_handles == {}
