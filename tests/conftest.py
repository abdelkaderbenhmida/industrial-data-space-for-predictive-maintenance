import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
FL_DIR = ROOT_DIR / "federated-learning"
IOT_DIR = ROOT_DIR / "iot-simulation"
DATA_SPACE_DIR = ROOT_DIR / "data-space"
DASHBOARD_DIR = ROOT_DIR / "dashboard" / "backend"

for p in [FL_DIR, IOT_DIR, DATA_SPACE_DIR, DASHBOARD_DIR]:
    if p.exists():
        sys.path.insert(0, str(p))
