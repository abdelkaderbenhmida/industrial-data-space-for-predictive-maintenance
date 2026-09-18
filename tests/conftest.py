import sys
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
FEDERATED_LEARNING_DIR = ROOT_DIR / "federated-learning"
IOT_SIMULATION_DIR = ROOT_DIR / "iot-simulation"
DATA_SPACE_DIR = ROOT_DIR / "data-space"
DASHBOARD_BACKEND_DIR = ROOT_DIR / "dashboard" / "backend"

for p in [FEDERATED_LEARNING_DIR, IOT_SIMULATION_DIR, DATA_SPACE_DIR, DASHBOARD_BACKEND_DIR]:
    if p.exists():
        sys.path.insert(0, str(p))


@pytest.fixture
def sample_sensor_data():
    n_samples = 100
    np.random.seed(42)
    X = np.random.rand(n_samples, 5).astype(np.float32)
    y = np.random.randint(0, 2, size=(n_samples,)).astype(np.float32)
    return X, y


@pytest.fixture
def small_train_data():
    np.random.seed(0)
    X = np.random.rand(32, 5).astype(np.float32)
    y = np.random.randint(0, 2, size=(32,)).astype(np.float32)
    return X, y


@pytest.fixture
def small_test_data():
    np.random.seed(1)
    X = np.random.rand(8, 5).astype(np.float32)
    y = np.random.randint(0, 2, size=(8,)).astype(np.float32)
    return X, y


@pytest.fixture
def sample_weights():
    np.random.seed(99)
    return [np.random.rand(*shape).astype(np.float32) for shape in [
        (5, 64), (64,), (64, 32), (32,), (32, 16), (16,), (16, 1), (1,),
    ]]


@pytest.fixture
def server_sample_weights():
    np.random.seed(42)
    return [np.random.rand(*shape).astype(np.float32) for shape in [
        (6, 64), (64,), (64, 32), (32,), (32, 1), (1,),
    ]]
