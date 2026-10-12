#!/usr/bin/env python3
"""
Centralized vs Federated Learning Performance Comparison
Trains the same model architecture on:
1. Centralized data (all factories combined)
2. Federated learning (Flower FedAvg)
Compares accuracy, F1, training time, communication overhead.
"""

import os
import json
import time
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split
from pathlib import Path

# ─── Configuration ───
DATA_DIR = Path("iot-simulation/data")
FACTORIES = ["FactoryA", "FactoryB", "FactoryC"]
FEATURE_COLS = ["temperature", "vibrations", "pressure", "humidity", "power_consumption"]
LABEL_COL = "status"
LABEL_MAP = {"normal": 0, "failure": 1}

# Model architecture (must match federated-learning/model.py)
def create_model(input_dim=5):
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(input_dim,)),
        tf.keras.layers.Dense(64, activation="relu"),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Dense(32, activation="relu"),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(16, activation="relu"),
        tf.keras.layers.Dense(1, activation="sigmoid"),
    ])
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss="binary_crossentropy",
        metrics=["accuracy"],
    )
    return model


def load_factory_data(factory_id):
    """Load all CSV files for a factory."""
    factory_dir = DATA_DIR / factory_id
    if not factory_dir.exists():
        return None, None
    
    csv_files = sorted(factory_dir.glob("readings_*.csv"))
    if not csv_files:
        return None, None
    
    frames = [pd.read_csv(f) for f in csv_files]
    df = pd.concat(frames, ignore_index=True)
    
    X = df[FEATURE_COLS].values.astype(np.float32)
    y = df[LABEL_COL].map(LABEL_MAP).values.astype(np.float32)
    return X, y


def load_all_data():
    """Load and combine data from all factories."""
    all_X, all_y = [], []
    for fid in FACTORIES:
        X, y = load_factory_data(fid)
        if X is not None:
            all_X.append(X)
            all_y.append(y)
            print(f"  {fid}: {len(X)} samples")
    if not all_X:
        raise RuntimeError("No data found. Run IoT simulator first.")
    return np.vstack(all_X), np.concatenate(all_y)


def evaluate_model(model, X_test, y_test, name):
    """Evaluate and return metrics."""
    y_pred_proba = model.predict(X_test, verbose=0).flatten()
    y_pred = (y_pred_proba >= 0.5).astype(int)
    y_true = y_test.astype(int)
    
    metrics = {
        "name": name,
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1_score": float(f1_score(y_true, y_pred, zero_division=0)),
        "test_samples": len(y_test),
        "positive_rate": float(y_true.mean()),
    }
    return metrics


def train_centralized(X, y, epochs=20, test_size=0.2, seed=42):
    """Train model on all data combined (centralized baseline)."""
    print("\n📊 Training CENTRALIZED model (all factories combined)...")
    start = time.time()
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed, stratify=y
    )
    
    model = create_model()
    history = model.fit(
        X_train, y_train,
        epochs=epochs,
        batch_size=32,
        validation_data=(X_test, y_test),
        verbose=0,
    )
    
    train_time = time.time() - start
    metrics = evaluate_model(model, X_test, y_test, "Centralized")
    metrics["train_time_sec"] = train_time
    metrics["epochs"] = epochs
    metrics["train_samples"] = len(X_train)
    
    print(f"  ✅ Centralized: acc={metrics['accuracy']:.4f}, f1={metrics['f1_score']:.4f}, time={train_time:.1f}s")
    return model, metrics, history


def train_federated_simulation(X, y, rounds=10, local_epochs=1, seed=42):
    """
    Simulate federated learning by splitting data per factory
    and doing FedAvg manually (for comparison without Flower server).
    """
    print("\n🔄 Simulating FEDERATED training (FedAvg)...")
    start = time.time()
    
    # Split data by factory (simulate non-IID)
    factory_data = {}
    for fid in FACTORIES:
        X_f, y_f = load_factory_data(fid)
        if X_f is not None:
            # Split each factory's data into train/test
            X_tr, X_te, y_tr, y_te = train_test_split(
                X_f, y_f, test_size=0.2, random_state=seed, stratify=y_f
            )
            factory_data[fid] = {
                "X_train": X_tr, "y_train": y_tr,
                "X_test": X_te, "y_test": y_te,
                "n_train": len(X_tr), "n_test": len(X_te),
            }
            print(f"  {fid}: train={len(X_tr)}, test={len(X_te)}")
    
    # Global test set (combined)
    X_test_all = np.vstack([v["X_test"] for v in factory_data.values()])
    y_test_all = np.concatenate([v["y_test"] for v in factory_data.values()])
    
    # Initialize global model
    global_model = create_model()
    global_weights = global_model.get_weights()
    
    round_metrics = []
    
    for rnd in range(1, rounds + 1):
        round_start = time.time()
        client_weights = []
        client_samples = []
        client_metrics = []
        
        # Each client trains locally
        for fid, data in factory_data.items():
            client_model = create_model()
            client_model.set_weights(global_weights)
            
            # Local training
            client_model.fit(
                data["X_train"], data["y_train"],
                epochs=local_epochs,
                batch_size=32,
                verbose=0,
            )
            
            # Evaluate locally
            local_metrics = evaluate_model(client_model, data["X_test"], data["y_test"], fid)
            client_metrics.append(local_metrics)
            
            client_weights.append(client_model.get_weights())
            client_samples.append(data["n_train"])
        
        # FedAvg aggregation (weighted by samples)
        total_samples = sum(client_samples)
        new_weights = []
        for layer_idx in range(len(global_weights)):
            weighted_sum = np.zeros_like(global_weights[layer_idx])
            for cw, n in zip(client_weights, client_samples):
                weighted_sum += cw[layer_idx] * (n / total_samples)
            new_weights.append(weighted_sum)
        
        global_model.set_weights(new_weights)
        global_weights = new_weights
        
        # Evaluate global model
        global_metrics = evaluate_model(global_model, X_test_all, y_test_all, f"FedAvg-Round{rnd}")
        global_metrics["round"] = rnd
        global_metrics["round_time_sec"] = time.time() - round_start
        round_metrics.append(global_metrics)
        
        print(f"  Round {rnd}: acc={global_metrics['accuracy']:.4f}, f1={global_metrics['f1_score']:.4f}")
    
    total_time = time.time() - start
    
    final_metrics = {
        "name": "Federated (FedAvg simulation)",
        "accuracy": round_metrics[-1]["accuracy"],
        "precision": round_metrics[-1]["precision"],
        "recall": round_metrics[-1]["recall"],
        "f1_score": round_metrics[-1]["f1_score"],
        "train_time_sec": total_time,
        "rounds": rounds,
        "local_epochs": local_epochs,
        "round_history": round_metrics,
    }
    
    print(f"  ✅ Federated: acc={final_metrics['accuracy']:.4f}, f1={final_metrics['f1_score']:.4f}, time={total_time:.1f}s")
    return global_model, final_metrics


def load_actual_fl_metrics():
    """Load actual Flower FL metrics from runtime file."""
    metrics_file = Path("runtime/federated_metrics.json")
    if not metrics_file.exists():
        return None
    with open(metrics_file) as f:
        history = json.load(f)
    if not history:
        return None
    latest = history[-1]
    return {
        "name": "Federated (Flower actual)",
        "accuracy": latest.get("accuracy", 0),
        "precision": latest.get("precision", 0),
        "recall": latest.get("recall", 0),
        "f1_score": latest.get("f1_score", 0),
        "round": latest.get("round", 0),
        "participating_factories": latest.get("participating_factories", []),
    }


def print_comparison(centralized, federated_sim, federated_actual=None):
    """Print comparison table."""
    print("\n" + "=" * 80)
    print("📈 PERFORMANCE COMPARISON: Centralized vs Federated")
    print("=" * 80)
    
    rows = [
        ("Metric", "Centralized", "Federated (Sim)", "Federated (Flower)"),
        ("Accuracy", f"{centralized['accuracy']:.4f}", f"{federated_sim['accuracy']:.4f}", 
         f"{federated_actual['accuracy']:.4f}" if federated_actual else "N/A"),
        ("Precision", f"{centralized['precision']:.4f}", f"{federated_sim['precision']:.4f}",
         f"{federated_actual['precision']:.4f}" if federated_actual else "N/A"),
        ("Recall", f"{centralized['recall']:.4f}", f"{federated_sim['recall']:.4f}",
         f"{federated_actual['recall']:.4f}" if federated_actual else "N/A"),
        ("F1-Score", f"{centralized['f1_score']:.4f}", f"{federated_sim['f1_score']:.4f}",
         f"{federated_actual['f1_score']:.4f}" if federated_actual else "N/A"),
        ("Train Time (s)", f"{centralized['train_time_sec']:.1f}", f"{federated_sim['train_time_sec']:.1f}", "N/A"),
        ("Rounds/Epochs", f"{centralized['epochs']} epochs", f"{federated_sim['rounds']} rounds × {federated_sim['local_epochs']} local epochs", 
         f"{federated_actual['round']} rounds" if federated_actual else "N/A"),
    ]
    
    for row in rows:
        print(f"  {row[0]:<18} | {row[1]:>14} | {row[2]:>16} | {row[3]}")
    
    # Calculate gap
    acc_gap = centralized['accuracy'] - federated_sim['accuracy']
    f1_gap = centralized['f1_score'] - federated_sim['f1_score']
    print(f"\n  Gap (Centralized - Federated Sim): Accuracy={acc_gap:.4f}, F1={f1_gap:.4f}")
    if acc_gap > 0:
        print(f"  → Centralized outperforms by {acc_gap*100:.2f}% accuracy")
    else:
        print(f"  → Federated matches or exceeds centralized!")


def save_report(centralized, federated_sim, federated_actual=None):
    """Save comparison report as JSON."""
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "centralized": centralized,
        "federated_simulation": federated_sim,
        "federated_actual": federated_actual,
        "summary": {
            "accuracy_gap": centralized['accuracy'] - federated_sim['accuracy'],
            "f1_gap": centralized['f1_score'] - federated_sim['f1_score'],
            "conclusion": "Federated matches centralized" if abs(centralized['accuracy'] - federated_sim['accuracy']) < 0.02 else "Centralized outperforms",
        }
    }
    out_path = Path("performance_comparison.json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n💾 Report saved to {out_path}")


def main():
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  Centralized vs Federated Learning - Performance Comparison  ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    
    # Load data
    print("\n📂 Loading factory data...")
    X, y = load_all_data()
    print(f"  Total: {len(X)} samples, {y.mean()*100:.1f}% failure rate")
    
    # Train centralized
    _, centralized_metrics, _ = train_centralized(X, y, epochs=20)
    
    # Simulate federated
    _, federated_metrics = train_federated_simulation(X, y, rounds=10, local_epochs=1)
    
    # Load actual FL metrics if available
    actual_fl = load_actual_fl_metrics()
    if actual_fl:
        print(f"\n📡 Actual Flower FL metrics loaded: round={actual_fl['round']}")
    
    # Compare
    print_comparison(centralized_metrics, federated_metrics, actual_fl)
    
    # Save report
    save_report(centralized_metrics, federated_metrics, actual_fl)
    
    print("\n✅ Comparison complete!")


if __name__ == "__main__":
    main()