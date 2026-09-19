from typing import Tuple

import numpy as np
import tensorflow as tf
from tensorflow import keras
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score


class PredictiveMaintenanceModel:
    """Binary classifier for machine failure prediction.

    Sensor features: temperature, vibrations, pressure, humidity, power_consumption.
    Label: 0 = normal, 1 = failure.
    """

    SENSOR_FEATURES = 5

    def __init__(self, input_dim: int = SENSOR_FEATURES) -> None:
        self.input_dim = input_dim
        self.model = self._build_model()
        self.history = None

    def _build_model(self) -> keras.Model:
        model = keras.Sequential([
            keras.layers.Input(shape=(self.input_dim,)),
            keras.layers.Dense(64, activation="relu"),
            keras.layers.Dropout(0.3),
            keras.layers.Dense(32, activation="relu"),
            keras.layers.Dropout(0.3),
            keras.layers.Dense(16, activation="relu"),
            keras.layers.Dense(1, activation="sigmoid"),
        ])
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss="binary_crossentropy",
            metrics=["accuracy"],
        )
        return model

    def train(
        self,
        x_train: np.ndarray,
        y_train: np.ndarray,
        x_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
        epochs: int = 10,
        batch_size: int = 32,
    ) -> keras.callbacks.History:
        validation_data = None
        if x_val is not None and y_val is not None:
            validation_data = (x_val, y_val)

        self.history = self.model.fit(
            x_train,
            y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_data=validation_data,
            verbose=0,
        )
        return self.history

    def predict(self, x: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        probs = self.model.predict(x, verbose=0)
        return (probs >= threshold).astype(int).flatten()

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        return self.model.predict(x, verbose=0).flatten()

    def evaluate(
        self, x_test: np.ndarray, y_test: np.ndarray
    ) -> dict[str, float]:
        y_pred = self.predict(x_test)
        y_true = y_test.astype(int).flatten()
        return {
            "loss": float(self.model.evaluate(x_test, y_true, verbose=0)[0]),
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "precision": float(precision_score(y_true, y_pred, zero_division=0)),
            "recall": float(recall_score(y_true, y_pred, zero_division=0)),
            "f1_score": float(f1_score(y_true, y_pred, zero_division=0)),
        }

    def get_weights(self) -> list[np.ndarray]:
        return self.model.get_weights()

    def set_weights(self, weights: list[np.ndarray]) -> None:
        self.model.set_weights(weights)

    def save(self, path: str) -> None:
        self.model.save(path)

    @classmethod
    def load(cls, path: str) -> "PredictiveMaintenanceModel":
        instance = cls.__new__(cls)
        instance.model = keras.models.load_model(path)
        instance.input_dim = instance.model.input_shape[-1]
        instance.history = None
        return instance
