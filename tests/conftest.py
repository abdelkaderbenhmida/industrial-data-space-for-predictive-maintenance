import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_WORKTREE = ROOT_DIR.parent / "backend-agent"
FL_DIR = BACKEND_WORKTREE / "federated-learning"
IOT_DIR = BACKEND_WORKTREE / "iot-simulation"

for p in [FL_DIR, IOT_DIR]:
    if p.exists():
        sys.path.insert(0, str(p))
