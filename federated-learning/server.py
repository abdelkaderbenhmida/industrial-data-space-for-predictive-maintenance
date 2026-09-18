import argparse
import logging
import os
from typing import Optional

import flwr as fl
import numpy as np
import tensorflow as tf

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

CHECKPOINT_DIR = "checkpoints"


def load_model() -> tf.keras.Model:
    model = tf.keras.Sequential([
        tf.keras.layers.Dense(64, activation="relu", input_shape=(6,)),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(32, activation="relu"),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(1, activation="sigmoid"),
    ])
    model.compile(
        optimizer="adam",
        loss="binary_crossentropy",
        metrics=["accuracy"],
    )
    return model


def save_checkpoint(model: tf.keras.Model, round_num: int) -> None:
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    path = os.path.join(CHECKPOINT_DIR, f"global_model_round_{round_num}.keras")
    model.save(path)
    logger.info("Checkpoint saved: %s", path)


class FedAvg(fl.server.strategy.FedAvg):
    def __init__(self, save_every: int = 1, **kwargs):
        super().__init__(**kwargs)
        self.save_every = save_every

    def aggregate_fit(
        self,
        server_round: int,
        results: list,
        failures: list,
    ) -> tuple[Optional[fl.common.Parameters], dict]:
        aggregated_params, aggregated_metrics = super().aggregate_fit(
            server_round, results, failures
        )

        if aggregated_params is not None:
            ndarrays = fl.common.parameters_to_ndarrays(aggregated_params)
            model = load_model()
            model.set_weights(
                [np.array(w, dtype=np.float32) for w in ndarrays]
            )

            if server_round % self.save_every == 0:
                save_checkpoint(model, server_round)

            logger.info(
                "Round %d complete — %d clients participated",
                server_round,
                len(results),
            )

        return aggregated_params, aggregated_metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Federated Learning Server")
    parser.add_argument(
        "--rounds", type=int, default=5, help="Number of training rounds (default: 5)"
    )
    parser.add_argument(
        "--min-clients",
        type=int,
        default=2,
        help="Minimum number of clients per round (default: 2)",
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="Server port (default: 8080)"
    )
    parser.add_argument(
        "--save-every",
        type=int,
        default=1,
        help="Save checkpoint every N rounds (default: 1)",
    )
    args = parser.parse_args()

    model = load_model()
    initial_params = fl.common.ndarrays_to_parameters(model.get_weights())

    strategy = FedAvg(
        save_every=args.save_every,
        fraction_fit=1.0,
        fraction_evaluate=1.0,
        min_fit_clients=args.min_clients,
        min_evaluate_clients=args.min_clients,
        min_available_clients=args.min_clients,
        initial_parameters=initial_params,
    )

    logger.info(
        "Starting Flower server — rounds=%d, min_clients=%d, port=%d",
        args.rounds,
        args.min_clients,
        args.port,
    )

    fl.server.start_server(
        server_address=f"0.0.0.0:{args.port}",
        strategy=strategy,
        config=fl.server.ServerConfig(num_rounds=args.rounds),
    )

    logger.info("Training complete. Final checkpoint in %s/", CHECKPOINT_DIR)


if __name__ == "__main__":
    main()
