import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import flwr as fl
import numpy as np
import pytest


class TestLoadModel:
    def test_returns_keras_model(self):
        from server import load_model
        model = load_model()
        assert model is not None
        assert hasattr(model, "predict")
        assert hasattr(model, "get_weights")
        assert hasattr(model, "set_weights")

    def test_model_input_shape(self):
        from server import load_model
        model = load_model()
        input_shape = model.input_shape
        assert input_shape == (None, 6)

    def test_model_output_shape(self):
        from server import load_model
        model = load_model()
        output_shape = model.output_shape
        assert output_shape == (None, 1)

    def test_model_has_three_layers(self):
        from server import load_model
        model = load_model()
        non_input_layers = [l for l in model.layers if not isinstance(l, type(model.layers[0])) or l.get_config().get("activation") is not None]
        dense_layers = [l for l in model.layers if "dense" in l.name.lower() or "dropout" in l.name.lower()]
        assert len(dense_layers) >= 4

    def test_model_loss_is_binary_crossentropy(self):
        from server import load_model
        model = load_model()
        assert model.loss is not None

    def test_model_optimizer_is_adam(self):
        from server import load_model
        model = load_model()
        assert model.optimizer is not None

    def test_model_accepts_correct_input(self):
        from server import load_model
        model = load_model()
        x = np.random.rand(1, 6).astype(np.float32)
        output = model.predict(x, verbose=0)
        assert output.shape == (1, 1)
        assert 0.0 <= output[0, 0] <= 1.0

    def test_model_weights_are_settable(self):
        from server import load_model
        model = load_model()
        weights = model.get_weights()
        new_weights = [w * 0.5 for w in weights]
        model.set_weights(new_weights)
        updated = model.get_weights()
        for i, (orig, new_w) in enumerate(zip(weights, new_weights)):
            np.testing.assert_array_equal(new_w, updated[i])


class TestSaveCheckpoint:
    def test_creates_checkpoint_directory(self):
        from server import save_checkpoint, load_model
        model = load_model()
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                save_checkpoint(model, 1)
                assert os.path.isdir("checkpoints")
            finally:
                os.chdir(old_cwd)

    def test_saves_model_file(self):
        from server import save_checkpoint, load_model
        model = load_model()
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                save_checkpoint(model, 5)
                expected = Path("checkpoints/global_model_round_5.keras")
                assert expected.exists()
            finally:
                os.chdir(old_cwd)

    def test_saves_with_correct_round_number(self):
        from server import save_checkpoint, load_model
        model = load_model()
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                for r in [1, 3, 7]:
                    save_checkpoint(model, r)
                assert Path("checkpoints/global_model_round_1.keras").exists()
                assert Path("checkpoints/global_model_round_3.keras").exists()
                assert Path("checkpoints/global_model_round_7.keras").exists()
            finally:
                os.chdir(old_cwd)


def _make_fit_result(weights, num_examples=100):
    params = fl.common.ndarrays_to_parameters(weights)
    status = fl.common.Status(code=0, message="OK")
    return MagicMock(), fl.common.FitRes(
        status=status,
        parameters=params,
        num_examples=num_examples,
        metrics={},
    )


class TestFedAvgStrategy:
    def test_init_sets_save_every(self):
        from server import FedAvg
        strategy = FedAvg(save_every=3)
        assert strategy.save_every == 3

    def test_init_default_save_every(self):
        from server import FedAvg
        strategy = FedAvg()
        assert strategy.save_every == 1

    def test_aggregate_fit_returns_params_and_metrics(self):
        from server import FedAvg, load_model
        model = load_model()
        weights = model.get_weights()
        client, fit_res = _make_fit_result(weights, num_examples=100)

        strategy = FedAvg(save_every=1)
        result_params, result_metrics = strategy.aggregate_fit(
            server_round=1,
            results=[(client, fit_res)],
            failures=[],
        )
        assert result_params is not None
        assert isinstance(result_metrics, dict)

    def test_aggregate_fit_with_multiple_clients(self):
        from server import FedAvg, load_model
        model = load_model()
        base_weights = model.get_weights()

        clients = []
        for i in range(3):
            noisy = [w + np.random.normal(0, 0.01, w.shape).astype(np.float32) for w in base_weights]
            c, fr = _make_fit_result(noisy, num_examples=100)
            clients.append((c, fr))

        strategy = FedAvg(save_every=1)
        result_params, result_metrics = strategy.aggregate_fit(
            server_round=1,
            results=clients,
            failures=[],
        )
        assert result_params is not None

    def test_aggregate_fit_saves_checkpoint(self):
        from server import FedAvg, load_model
        model = load_model()
        weights = model.get_weights()
        client, fit_res = _make_fit_result(weights, num_examples=100)

        strategy = FedAvg(save_every=1)
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                strategy.aggregate_fit(server_round=1, results=[(client, fit_res)], failures=[])
                assert Path("checkpoints/global_model_round_1.keras").exists()
            finally:
                os.chdir(old_cwd)

    def test_aggregate_fit_skips_checkpoint_when_not_divisible(self):
        from server import FedAvg, load_model
        model = load_model()
        weights = model.get_weights()
        client, fit_res = _make_fit_result(weights, num_examples=100)

        strategy = FedAvg(save_every=2)
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                strategy.aggregate_fit(server_round=1, results=[(client, fit_res)], failures=[])
                assert not Path("checkpoints").exists()
            finally:
                os.chdir(old_cwd)

    def test_aggregate_fit_saves_every_n_rounds(self):
        from server import FedAvg, load_model
        model = load_model()
        weights = model.get_weights()
        client, fit_res = _make_fit_result(weights, num_examples=100)

        strategy = FedAvg(save_every=2)
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                strategy.aggregate_fit(server_round=2, results=[(client, fit_res)], failures=[])
                assert Path("checkpoints/global_model_round_2.keras").exists()
            finally:
                os.chdir(old_cwd)

    def test_aggregate_fit_with_no_results_returns_none(self):
        from server import FedAvg
        strategy = FedAvg(save_every=1)
        result_params, result_metrics = strategy.aggregate_fit(
            server_round=1, results=[], failures=[]
        )
        assert result_params is None

    def test_aggregate_fit_with_failures(self):
        from server import FedAvg, load_model
        model = load_model()
        weights = model.get_weights()
        client, fit_res = _make_fit_result(weights, num_examples=100)

        strategy = FedAvg(save_every=1)
        failure = MagicMock()
        result_params, result_metrics = strategy.aggregate_fit(
            server_round=1, results=[(client, fit_res)], failures=[failure]
        )
        assert result_params is not None

    def test_aggregate_fit_weight_averaging(self):
        from server import FedAvg, load_model
        model = load_model()
        base_weights = model.get_weights()
        w1 = [w.copy() for w in base_weights]
        w2 = [w.copy() for w in base_weights]
        w1[0] = np.ones_like(w1[0]) * 1.0
        w2[0] = np.ones_like(w2[0]) * 3.0

        c1, fr1 = _make_fit_result(w1, num_examples=100)
        c2, fr2 = _make_fit_result(w2, num_examples=100)

        strategy = FedAvg(save_every=1)
        result_params, _ = strategy.aggregate_fit(
            server_round=1, results=[(c1, fr1), (c2, fr2)], failures=[]
        )
        assert result_params is not None
        ndarrays = fl.common.parameters_to_ndarrays(result_params)
        expected_avg = np.ones_like(w1[0]) * 2.0
        np.testing.assert_array_almost_equal(ndarrays[0], expected_avg)
