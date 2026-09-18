import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score


class TestPredictiveMaintenanceModelInit:
    def test_creates_model_instance(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        assert mpm is not None
        assert mpm.model is not None

    def test_default_input_dim(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        assert mpm.input_dim == 5

    def test_custom_input_dim(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel(input_dim=10)
        assert mpm.input_dim == 10
        assert mpm.model.input_shape == (None, 10)

    def test_history_is_none_initially(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        assert mpm.history is None

    def test_sensor_features_constant(self):
        from model import PredictiveMaintenanceModel
        assert PredictiveMaintenanceModel.SENSOR_FEATURES == 5


class TestBuildModel:
    def test_model_has_sequential_structure(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        assert mpm.model is not None
        assert hasattr(mpm.model, "layers")

    def test_model_input_shape_default(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        assert mpm.model.input_shape == (None, 5)

    def test_model_output_shape(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        assert mpm.model.output_shape == (None, 1)

    def test_model_has_dense_layers(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        dense_count = sum(1 for l in mpm.model.layers if "dense" in l.name.lower() or "dense" in type(l).__name__.lower())
        assert dense_count >= 3

    def test_model_has_dropout_layers(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        dropout_count = sum(1 for l in mpm.model.layers if "dropout" in l.name.lower() or "dropout" in type(l).__name__.lower())
        assert dropout_count >= 2

    def test_model_accepts_batch_input(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        x = np.random.rand(10, 5).astype(np.float32)
        output = mpm.model.predict(x, verbose=0)
        assert output.shape == (10, 1)

    def test_model_output_in_valid_range(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        x = np.random.rand(5, 5).astype(np.float32)
        output = mpm.model.predict(x, verbose=0)
        assert np.all(output >= 0.0)
        assert np.all(output <= 1.0)

    def test_model_is_compiled(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        assert mpm.model.optimizer is not None
        assert mpm.model.loss is not None

    def test_model_layer_count(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        assert len(mpm.model.layers) >= 5


class TestTrain:
    def test_train_returns_history(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        np.random.seed(42)
        X = np.random.rand(100, 5).astype(np.float32)
        y = np.random.randint(0, 2, size=(100,)).astype(np.float32)
        history = mpm.train(X, y, epochs=2, batch_size=32)
        assert history is not None
        assert "loss" in history.history
        assert "accuracy" in history.history

    def test_train_stores_history(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        np.random.seed(42)
        X = np.random.rand(100, 5).astype(np.float32)
        y = np.random.randint(0, 2, size=(100,)).astype(np.float32)
        mpm.train(X, y, epochs=2)
        assert mpm.history is not None

    def test_train_with_validation_data(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        np.random.seed(42)
        X_train = np.random.rand(80, 5).astype(np.float32)
        y_train = np.random.randint(0, 2, size=(80,)).astype(np.float32)
        X_val = np.random.rand(20, 5).astype(np.float32)
        y_val = np.random.randint(0, 2, size=(20,)).astype(np.float32)
        history = mpm.train(X_train, y_train, x_val=X_val, y_val=y_val, epochs=2)
        assert "val_loss" in history.history
        assert "val_accuracy" in history.history

    def test_train_without_validation(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        np.random.seed(42)
        X = np.random.rand(50, 5).astype(np.float32)
        y = np.random.randint(0, 2, size=(50,)).astype(np.float32)
        history = mpm.train(X, y, epochs=1)
        assert "val_loss" not in history.history

    def test_train_loss_decreases(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        np.random.seed(42)
        X = np.random.rand(200, 5).astype(np.float32)
        y = (X[:, 0] > 0.5).astype(np.float32)
        history = mpm.train(X, y, epochs=10, batch_size=32)
        losses = history.history["loss"]
        assert losses[-1] <= losses[0]

    def test_train_custom_batch_size(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        np.random.seed(42)
        X = np.random.rand(100, 5).astype(np.float32)
        y = np.random.randint(0, 2, size=(100,)).astype(np.float32)
        history = mpm.train(X, y, epochs=1, batch_size=16)
        assert "loss" in history.history

    def test_train_single_epoch(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        np.random.seed(42)
        X = np.random.rand(32, 5).astype(np.float32)
        y = np.random.randint(0, 2, size=(32,)).astype(np.float32)
        history = mpm.train(X, y, epochs=1)
        assert len(history.history["loss"]) == 1


class TestPredict:
    def test_predict_returns_binary_labels(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        np.random.seed(42)
        X = np.random.rand(10, 5).astype(np.float32)
        preds = mpm.predict(X)
        assert preds.shape == (10,)
        assert set(np.unique(preds)).issubset({0, 1})

    def test_predict_with_custom_threshold(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        np.random.seed(42)
        X = np.random.rand(10, 5).astype(np.float32)
        preds_low = mpm.predict(X, threshold=0.1)
        preds_high = mpm.predict(X, threshold=0.9)
        assert np.sum(preds_low) >= np.sum(preds_high)

    def test_predict_single_sample(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        x = np.random.rand(1, 5).astype(np.float32)
        preds = mpm.predict(x)
        assert preds.shape == (1,)
        assert preds[0] in (0, 1)

    def test_predict_default_threshold(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        np.random.seed(42)
        X = np.random.rand(20, 5).astype(np.float32)
        preds = mpm.predict(X)
        assert all(p in (0, 1) for p in preds)


class TestPredictProba:
    def test_predict_proba_returns_floats(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        np.random.seed(42)
        X = np.random.rand(10, 5).astype(np.float32)
        probs = mpm.predict_proba(X)
        assert probs.shape == (10,)
        assert probs.dtype in (np.float32, np.float64)

    def test_predict_proba_values_in_range(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        np.random.seed(42)
        X = np.random.rand(20, 5).astype(np.float32)
        probs = mpm.predict_proba(X)
        assert np.all(probs >= 0.0)
        assert np.all(probs <= 1.0)

    def test_predict_proba_single_sample(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        x = np.random.rand(1, 5).astype(np.float32)
        prob = mpm.predict_proba(x)
        assert prob.shape == (1,)
        assert 0.0 <= prob[0] <= 1.0

    def test_predict_proba_matches_model_output(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        np.random.seed(42)
        X = np.random.rand(5, 5).astype(np.float32)
        probs = mpm.predict_proba(X)
        raw = mpm.model.predict(X, verbose=0).flatten()
        np.testing.assert_array_almost_equal(probs, raw)


class TestEvaluate:
    def test_evaluate_returns_all_metrics(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        np.random.seed(42)
        X = np.random.rand(50, 5).astype(np.float32)
        y = np.random.randint(0, 2, size=(50,)).astype(np.float32)
        mpm.train(X, y, epochs=2)
        metrics = mpm.evaluate(X, y)
        assert "loss" in metrics
        assert "accuracy" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1_score" in metrics

    def test_evaluate_loss_is_nonnegative(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        np.random.seed(42)
        X = np.random.rand(50, 5).astype(np.float32)
        y = np.random.randint(0, 2, size=(50,)).astype(np.float32)
        mpm.train(X, y, epochs=2)
        metrics = mpm.evaluate(X, y)
        assert metrics["loss"] >= 0

    def test_evaluate_accuracy_in_range(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        np.random.seed(42)
        X = np.random.rand(50, 5).astype(np.float32)
        y = np.random.randint(0, 2, size=(50,)).astype(np.float32)
        mpm.train(X, y, epochs=2)
        metrics = mpm.evaluate(X, y)
        assert 0.0 <= metrics["accuracy"] <= 1.0

    def test_evaluate_precision_in_range(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        np.random.seed(42)
        X = np.random.rand(50, 5).astype(np.float32)
        y = np.random.randint(0, 2, size=(50,)).astype(np.float32)
        mpm.train(X, y, epochs=2)
        metrics = mpm.evaluate(X, y)
        assert 0.0 <= metrics["precision"] <= 1.0

    def test_evaluate_recall_in_range(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        np.random.seed(42)
        X = np.random.rand(50, 5).astype(np.float32)
        y = np.random.randint(0, 2, size=(50,)).astype(np.float32)
        mpm.train(X, y, epochs=2)
        metrics = mpm.evaluate(X, y)
        assert 0.0 <= metrics["recall"] <= 1.0

    def test_evaluate_f1_in_range(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        np.random.seed(42)
        X = np.random.rand(50, 5).astype(np.float32)
        y = np.random.randint(0, 2, size=(50,)).astype(np.float32)
        mpm.train(X, y, epochs=2)
        metrics = mpm.evaluate(X, y)
        assert 0.0 <= metrics["f1_score"] <= 1.0

    def test_evaluate_matches_sklearn(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        np.random.seed(42)
        X = np.random.rand(50, 5).astype(np.float32)
        y = np.random.randint(0, 2, size=(50,)).astype(np.float32)
        mpm.train(X, y, epochs=2)
        metrics = mpm.evaluate(X, y)
        y_pred = mpm.predict(X)
        y_true = y.astype(int).flatten()
        assert abs(metrics["accuracy"] - accuracy_score(y_true, y_pred)) < 1e-6
        assert abs(metrics["precision"] - precision_score(y_true, y_pred, zero_division=0)) < 1e-6
        assert abs(metrics["recall"] - recall_score(y_true, y_pred, zero_division=0)) < 1e-6
        assert abs(metrics["f1_score"] - f1_score(y_true, y_pred, zero_division=0)) < 1e-6


class TestGetSetWeights:
    def test_get_weights_returns_list(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        weights = mpm.get_weights()
        assert isinstance(weights, list)
        assert all(isinstance(w, np.ndarray) for w in weights)

    def test_set_weights_updates_model(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        original = mpm.get_weights()
        new_weights = [np.zeros_like(w) for w in original]
        mpm.set_weights(new_weights)
        updated = mpm.get_weights()
        for o, u in zip(original, updated):
            np.testing.assert_array_equal(u, np.zeros_like(o))

    def test_get_set_roundtrip(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        w1 = mpm.get_weights()
        mpm.set_weights(w1)
        w2 = mpm.get_weights()
        for a, b in zip(w1, w2):
            np.testing.assert_array_almost_equal(a, b)

    def test_set_weights_with_modified_values(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        original = mpm.get_weights()
        modified = [w * 2.0 for w in original]
        mpm.set_weights(modified)
        result = mpm.get_weights()
        for mod, res in zip(modified, result):
            np.testing.assert_array_almost_equal(mod, res)


class TestSaveLoad:
    def test_save_creates_file(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "model.keras"
            mpm.save(str(path))
            assert path.exists()

    def test_load_restores_model(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "model.keras"
            mpm.save(str(path))
            loaded = PredictiveMaintenanceModel.load(str(path))
            assert loaded is not None
            assert loaded.model is not None

    def test_loaded_model_has_same_input_shape(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel(input_dim=5)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "model.keras"
            mpm.save(str(path))
            loaded = PredictiveMaintenanceModel.load(str(path))
            assert loaded.input_dim == 5
            assert loaded.model.input_shape == (None, 5)

    def test_loaded_model_predicts(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "model.keras"
            mpm.save(str(path))
            loaded = PredictiveMaintenanceModel.load(str(path))
            x = np.random.rand(1, 5).astype(np.float32)
            pred = loaded.predict(x)
            assert pred.shape == (1,)
            assert pred[0] in (0, 1)

    def test_loaded_model_has_same_weights(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "model.keras"
            mpm.save(str(path))
            original_weights = mpm.get_weights()
            loaded = PredictiveMaintenanceModel.load(str(path))
            loaded_weights = loaded.get_weights()
            for o, l in zip(original_weights, loaded_weights):
                np.testing.assert_array_almost_equal(o, l)

    def test_loaded_model_history_is_none(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "model.keras"
            mpm.train(np.random.rand(32, 5).astype(np.float32),
                      np.random.randint(0, 2, size=(32,)).astype(np.float32), epochs=1)
            mpm.save(str(path))
            loaded = PredictiveMaintenanceModel.load(str(path))
            assert loaded.history is None

    def test_save_load_multiple_times(self):
        from model import PredictiveMaintenanceModel
        mpm = PredictiveMaintenanceModel()
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(3):
                path = Path(tmpdir) / f"model_{i}.keras"
                mpm.save(str(path))
                assert path.exists()
                loaded = PredictiveMaintenanceModel.load(str(path))
                x = np.random.rand(1, 5).astype(np.float32)
                assert loaded.predict(x).shape == (1,)
