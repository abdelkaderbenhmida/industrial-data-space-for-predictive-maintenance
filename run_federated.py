#!/usr/bin/env python3
"""Run federated learning end-to-end: server + 3 clients."""
import subprocess
import time
import sys
import os
import signal

def main():
    venv_python = os.path.join(os.path.dirname(__file__), "venv", "bin", "python")
    fl_dir = os.path.join(os.path.dirname(__file__), "federated-learning")
    data_dir = os.path.join(os.path.dirname(__file__), "iot-simulation", "data")
    
    processes = []
    
    print("=" * 60)
    print("FEDERATED LEARNING - Industrial Data Space")
    print("=" * 60)
    
    # Start Flower server
    print("\n[1/4] Starting Flower server (port 8080, 5 rounds, min 2 clients)...")
    server = subprocess.Popen(
        [venv_python, "server.py", "--rounds", "5", "--min-clients", "2", "--port", "8080"],
        cwd=fl_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    processes.append(("server", server))
    time.sleep(3)
    
    if server.poll() is not None:
        print("ERROR: Server failed to start")
        return 1
    
    print("  Server PID:", server.pid)
    
    # Start 3 factory clients
    factories = ["FactoryA", "FactoryB", "FactoryC"]
    for i, factory in enumerate(factories):
        print(f"\n[{i+2}/4] Starting ML client for {factory}...")
        client_data = os.path.join(data_dir, factory)
        client = subprocess.Popen(
            [venv_python, "client.py",
             "--factory-id", factory,
             "--data-dir", client_data,
             "--server-address", "localhost:8080"],
            cwd=fl_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        processes.append((factory, client))
        time.sleep(1)
        
        if client.poll() is not None:
            print(f"  WARNING: {factory} client exited early")
        else:
            print(f"  {factory} PID: {client.pid}")
    
    # Wait for all to finish
    print("\n[5/5] Waiting for federated training to complete...")
    print("  (5 rounds x 3 clients = 15 training sessions)")
    print()
    
    for name, proc in processes:
        try:
            proc.wait(timeout=120)
            output = proc.stdout.read().decode() if proc.stdout else ""
            # Print last few lines of output
            lines = [l for l in output.strip().split("\n") if l.strip()]
            for line in lines[-5:]:
                print(f"  [{name}] {line}")
        except subprocess.TimeoutExpired:
            print(f"  [{name}] Timed out after 120s, killing...")
            proc.kill()
            proc.wait()
    
    # Print summary
    print("\n" + "=" * 60)
    print("FEDERATED LEARNING COMPLETE")
    print("=" * 60)
    
    # Check for saved models
    checkpoints_dir = os.path.join(fl_dir, "checkpoints")
    if os.path.exists(checkpoints_dir):
        models = os.listdir(checkpoints_dir)
        print(f"\nSaved models: {len(models)}")
        for m in sorted(models):
            print(f"  - {m}")
    else:
        print("\nNo checkpoint directory found")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
