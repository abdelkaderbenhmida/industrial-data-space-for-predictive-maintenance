import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest


class TestLoadFactoryData:
    def _make_csv(self, directory, filename, n_rows=50, include_all_columns=True):
        np.random.seed(hash(filename) % 2**31)
        data = {
            "temperature": np.random.uniform(20, 80, n_rows),
            "vibrations": np.random.uniform(0, 10, n_rows),
            "pressure": np.random.uniform(90, 110, n_rows),
            "humidity": np.random.uniform(30, 90, n_rows),
            "power_consumption": np.random.uniform(100, 500, n_rows),
            "status": np.random.choice(["normal", "failure"], n_rows, p=[0.8, 0.2]),
        }
        if not include_all_columns:
            del data["humidity"]
        df = pd.DataFrame(data)
        df.to_csv(directory / filename, index=False)

    def test_loads_single_csv(self):
        from client import load_factory_data
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            self._make_csv(d, "data.csv", n_rows=100)
            X_train, y_train, X_test, y_test = load_factory_data(str(d))
            assert X_train.shape[1] == 5
            assert X_test.shape[1] == 5
            assert len(X_train) + len(X_test) == 100
            assert y_train.dtype == np.float32
            assert y_test.dtype == np.float32

    def test_loads_multiple_csvs(self):
        from client import load_factory_data
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            self._make_csv(d, "batch1.csv", n_rows=30)
            self._make_csv(d, "batch2.csv", n_rows=20)
            X_train, y_train, X_test, y_test = load_factory_data(str(d))
            assert len(X_train) + len(X_test) == 50

    def test_train_test_split_ratio(self):
        from client import load_factory_data
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            self._make_csv(d, "data.csv", n_rows=100)
            X_train, y_train, X_test, y_test = load_factory_data(str(d))
            total = len(X_train) + len(X_test)
            train_ratio = len(X_train) / total
            assert 0.75 <= train_ratio <= 0.85

    def test_labels_mapped_correctly(self):
        from client import load_factory_data
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            np.random.seed(42)
            data = {
                "temperature": [50.0] * 10,
                "vibrations": [5.0] * 10,
                "pressure": [100.0] * 10,
                "humidity": [50.0] * 10,
                "power_consumption": [300.0] * 10,
                "status": ["normal"] * 5 + ["failure"] * 5,
            }
            pd.DataFrame(data).to_csv(d / "data.csv", index=False)
            X_train, y_train, X_test, y_test = load_factory_data(str(d))
            all_y = np.concatenate([y_train, y_test])
            assert set(all_y).issubset({0.0, 1.0})
            assert 0.0 in all_y
            assert 1.0 in all_y

    def test_raises_on_missing_directory(self):
        from client import load_factory_data
        with pytest.raises(FileNotFoundError, match="Data directory not found"):
            load_factory_data("/nonexistent/path/xyz")

    def test_raises_on_no_csv_files(self):
        from client import load_factory_data
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            (d / "readme.txt").write_text("no csv here")
            with pytest.raises(ValueError, match="No CSV files found"):
                load_factory_data(str(d))

    def test_raises_on_missing_columns(self):
        from client import load_factory_data
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            self._make_csv(d, "incomplete.csv", include_all_columns=False)
            with pytest.raises(ValueError, match="Missing columns"):
                load_factory_data(str(d))

    def test_feature_values_are_float32(self):
        from client import load_factory_data
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            self._make_csv(d, "data.csv", n_rows=20)
            X_train, y_train, X_test, y_test = load_factory_data(str(d))
            assert X_train.dtype == np.float32
            assert X_test.dtype == np.float32

    def test_handle_empty_directory(self):
        from client import load_factory_data
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="No CSV files found"):
                load_factory_data(tmpdir)


class TestCreateModel:
    def test_returns_keras_model(self):
        from client import create_model
        model = create_model()
        assert model is not None
        assert hasattr(model, "predict")

    def test_model_input_shape(self):
        from client import create_model
        model = create_model()
        assert model.input_shape == (None, 5)

    def test_model_output_shape(self):
        from client import create_model
        model = create_model()
        assert model.output_shape == (None, 1)

    def test_model_has_dense_and_dropout_layers(self):
        from client import create_model
        model = create_model()
        layer_types = [type(l).__name__ for l in model.layers]
        assert "Dense" in layer_types
        assert "Dropout" in layer_types

    def test_model_accepts_correct_input(self):
        from client import create_model
        model = create_model()
        x = np.random.rand(1, 5).astype(np.float32)
        output = model.predict(x, verbose=0)
        assert output.shape == (1, 1)
        assert 0.0 <= output[0, 0] <= 1.0

    def test_model_compiled_with_binary_crossentropy(self):
        from client import create_model
        model = create_model()
        assert model.loss is not None

    def test_model_has_dropout(self):
        from client import create_model
        model = create_model()
        dropout_layers = [l for l in model.layers if "dropout" in l.name.lower()]
        assert len(dropout_layers) == 2


class TestFactoryClient:
    def _make_csv(self, directory, n_rows=50):
        np.random.seed(42)
        data = {
            "temperature": np.random.uniform(20, 80, n_rows),
            "vibrations": np.random.uniform(0, 10, n_rows),
            "pressure": np.random.uniform(90, 110, n_rows),
            "humidity": np.random.uniform(30, 90, n_rows),
            "power_consumption": np.random.uniform(100, 500, n_rows),
            "status": np.random.choice(["normal", "failure"], n_rows, p=[0.8, 0.2]),
        }
        pd.DataFrame(data).to_csv(directory / "data.csv", index=False)

    def test_init_stores_attributes(self):
        from client import FactoryClient
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            self._make_csv(d)
            fc = FactoryClient("factory-A", str(d), "localhost:8080")
            assert fc.factory_id == "factory_A" or fc.factory_id == "factory-A"
            assert fc.data_dir == str(d)
            assert fc.server_address == "localhost:8080"

    def test_init_creates_model(self):
        from client import FactoryClient
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            self._make_csv(d)
            fc = FactoryClient("factory-A", str(d), "localhost:8080")
            assert fc.model is not None

    def test_init_loads_data(self):
        from client import FactoryClient
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            self._make_csv(d, n_rows=100)
            fc = FactoryClient("factory-A", str(d), "localhost:8080")
            assert len(fc.x_train) > 0
            assert len(fc.y_train) > 0
            assert len(fc.x_test) > 0
            assert len(fc.y_test) > 0

    def test_get_parameters_returns_list_of_ndarrays(self):
        from client import FactoryClient
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            self._make_csv(d)
            fc = FactoryClient("factory-A", str(d), "localhost:8080")
            params = fc.get_parameters(config={})
            assert isinstance(params, list)
            assert all(isinstance(p, np.ndarray) for p in params)

    def test_set_parameters_updates_model(self):
        from client import FactoryClient
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            self._make_csv(d)
            fc = FactoryClient("factory-A", str(d), "localhost:8080")
            old_weights = fc.get_parameters(config={})
            new_weights = [w * 0.0 for w in old_weights]
            fc.set_parameters(new_weights)
            updated = fc.get_parameters(config={})
            for old, new in zip(old_weights, updated):
                np.testing.assert_array_equal(new, np.zeros_like(old))

    def test_fit_returns_weights_and_num_examples(self):
        from client import FactoryClient
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            self._make_csv(d, n_rows=100)
            fc = FactoryClient("factory-A", str(d), "localhost:8080")
            params = fc.get_parameters(config={})
            weights, num_examples, metrics = fc.fit(
                parameters=params,
                config={"local_epochs": 1, "batch_size": 32},
            )
            assert isinstance(weights, list)
            assert num_examples == len(fc.x_train)
            assert isinstance(metrics, dict)

    def test_fit_trains_model(self):
        from client import FactoryClient
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            self._make_csv(d, n_rows=100)
            fc = FactoryClient("factory-A", str(d), "localhost:8080")
            old_params = fc.get_parameters(config={})
            new_params, _, _ = fc.fit(
                parameters=old_params,
                config={"local_epochs": 2, "batch_size": 16},
            )
            changed = False
            for o, n in zip(old_params, new_params):
                if not np.allclose(o, n):
                    changed = True
                    break
            assert changed

    def test_fit_with_default_config(self):
        from client import FactoryClient
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            self._make_csv(d, n_rows=100)
            fc = FactoryClient("factory-A", str(d), "localhost:8080")
            params = fc.get_parameters(config={})
            weights, num_examples, metrics = fc.fit(parameters=params, config={})
            assert isinstance(weights, list)
            assert num_examples > 0

    def test_evaluate_returns_loss_and_metrics(self):
        from client import FactoryClient
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            self._make_csv(d, n_rows=100)
            fc = FactoryClient("factory-A", str(d), "localhost:8080")
            params = fc.get_parameters(config={})
            loss, num_examples, metrics = fc.evaluate(parameters=params, config={})
            assert isinstance(loss, float)
            assert loss >= 0
            assert num_examples == len(fc.x_test)
            assert "accuracy" in metrics
            assert 0.0 <= metrics["accuracy"] <= 1.0

    def test_evaluate_with_set_parameters(self):
        from client import FactoryClient
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            self._make_csv(d, n_rows=100)
            fc = FactoryClient("factory-A", str(d), "localhost:8080")
            zero_params = [np.zeros_like(w) for w in fc.get_parameters(config={})]
            loss, num_examples, metrics = fc.evaluate(parameters=zero_params, config={})
            assert isinstance(loss, float)
            assert loss >= 0

    def test_init_raises_on_missing_data_dir(self):
        from client import FactoryClient
        with pytest.raises(FileNotFoundError):
            FactoryClient("factory-A", "/nonexistent/path", "localhost:8080")


class TestParseArgs:
    def test_required_factory_id(self):
        from client import parse_args
        with patch("sys.argv", ["client.py", "--factory-id", "factory-A"]):
            args = parse_args()
            assert args.factory_id == "factory-A"

    def test_default_data_dir(self):
        from client import parse_args
        with patch("sys.argv", ["client.py", "--factory-id", "factory-A"]):
            args = parse_args()
            assert args.data_dir is None

    def test_custom_data_dir(self):
        from client import parse_args
        with patch("sys.argv", ["client.py", "--factory-id", "f1", "--data-dir", "/data/f1"]):
            args = parse_args()
            assert args.data_dir == "/data/f1"

    def test_default_server_address(self):
        from client import parse_args
        with patch("sys.argv", ["client.py", "--factory-id", "f1"]):
            args = parse_args()
            assert args.server_address == "localhost:8080"

    def test_custom_server_address(self):
        from client import parse_args
        with patch("sys.argv", ["client.py", "--factory-id", "f1", "--server-address", "10.0.0.1:9090"]):
            args = parse_args()
            assert args.server_address == "10.0.0.1:9090"
