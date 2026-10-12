import os
import argparse
import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd
import tensorflow as tf
import flwr as fl


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FEATURE_COLUMNS = [
    "temperature",
    "vibrations",
    "pressure",
    "humidity",
    "power_consumption",
]

LABEL_COLUMN = "status"


def load_factory_data(data_dir: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    data_path = Path(data_dir)
    if not data_path.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    # The simulator creates a daily file before its first record is flushed.
    # Ignore transient empty files so clients can retry instead of crashing.
    csv_files = sorted(path for path in data_path.glob("*.csv") if path.stat().st_size > 0)
    if not csv_files:
        raise ValueError(f"No CSV files found in {data_dir}")

    frames = []
    for csv_file in csv_files:
        try:
            frames.append(pd.read_csv(csv_file))
        except pd.errors.EmptyDataError:
            continue
    if not frames:
        raise ValueError(f"No readable CSV files found in {data_dir}")
    df = pd.concat(frames, ignore_index=True)

    missing = [c for c in FEATURE_COLUMNS + [LABEL_COLUMN] if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in data: {missing}")

    X = df[FEATURE_COLUMNS].values.astype(np.float32)
    y = df[LABEL_COLUMN].map({"normal": 0, "failure": 1}).values.astype(np.float32)

    split = int(len(X) * 0.8)
    indices = np.random.permutation(len(X))
    train_idx, test_idx = indices[:split], indices[split:]

    return X[train_idx], y[train_idx], X[test_idx], y[test_idx]


def create_model() -> tf.keras.Model:
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(len(FEATURE_COLUMNS),)),
        tf.keras.layers.Dense(64, activation="relu"),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Dense(32, activation="relu"),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(16, activation="relu"),
        tf.keras.layers.Dense(1, activation="sigmoid"),
    ])
    model.compile(
        optimizer="adam",
        loss="binary_crossentropy",
        metrics=["accuracy"],
    )
    return model


class FactoryClient(fl.client.NumPyClient):
    def __init__(self, factory_id: str, data_dir: str, server_address: str):
        self.factory_id = factory_id
        self.data_dir = data_dir
        self.server_address = server_address
        self.model = create_model()
        self.x_train, self.y_train, self.x_test, self.y_test = load_factory_data(
            data_dir
        )
        logger.info(
            "Factory %s loaded %d train / %d test samples",
            factory_id,
            len(self.x_train),
            len(self.x_test),
        )

    def get_parameters(self, config: dict) -> list[np.ndarray]:
        return self.model.get_weights()

    def set_parameters(self, parameters: list[np.ndarray]) -> None:
        self.model.set_weights(parameters)

    def fit(
        self, parameters: list[np.ndarray], config: dict
    ) -> tuple[list[np.ndarray], int, dict]:
        self.set_parameters(parameters)
        epochs = config.get("local_epochs", 1)
        batch_size = config.get("batch_size", 32)
        self.model.fit(
            self.x_train,
            self.y_train,
            epochs=epochs,
            batch_size=batch_size,
            verbose=0,
        )
        return self.model.get_weights(), len(self.x_train), {}

    def evaluate(
        self, parameters: list[np.ndarray], config: dict
    ) -> tuple[float, int, dict]:
        self.set_parameters(parameters)
        loss, accuracy = self.model.evaluate(self.x_test, self.y_test, verbose=0)
        probabilities = self.model.predict(self.x_test, verbose=0).reshape(-1)
        predicted = (probabilities >= 0.5).astype(np.int32)
        actual = self.y_test.astype(np.int32)
        true_positive = int(np.sum((predicted == 1) & (actual == 1)))
        false_positive = int(np.sum((predicted == 1) & (actual == 0)))
        false_negative = int(np.sum((predicted == 0) & (actual == 1)))
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
        f1_score = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        return loss, len(self.x_test), {
            "accuracy": float(accuracy),
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            f"participant_{self.factory_id}": 1.0,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Flower ML Client for Factory")
    parser.add_argument(
        "--factory-id",
        type=str,
        required=True,
        help="Unique factory identifier",
    )
    parser.add_argument(
        "--data-wait-seconds",
        type=int,
        default=60,
        help="Wait for local factory CSV data before failing",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Path to factory CSV data directory",
    )
    parser.add_argument(
        "--server-address",
        type=str,
        default="localhost:8080",
        help="Flower server address (host:port)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_dir = args.data_dir or f"iot-simulation/data/{args.factory_id}"

    logger.info("Starting client for factory %s", args.factory_id)
    logger.info("Data directory: %s", data_dir)
    logger.info("Server: %s", args.server_address)

    deadline = time.monotonic() + args.data_wait_seconds
    while True:
        try:
            client = FactoryClient(args.factory_id, data_dir, args.server_address)
            break
        except (FileNotFoundError, ValueError) as exc:
            if time.monotonic() >= deadline:
                raise RuntimeError(f"Factory data did not become available: {data_dir}") from exc
            logger.info("Waiting for local data in %s", data_dir)
            time.sleep(2)

    fl.client.start_client(
        server_address=args.server_address,
        client=client.to_client(),
    )
    logger.info("Client for factory %s disconnected", args.factory_id)


if __name__ == "__main__":
    main()
