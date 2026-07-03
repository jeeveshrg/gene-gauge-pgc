import os
import sys
from pathlib import Path

# Ensure the backend root (containing the `app` package) is importable.
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

# Force demo mode for deterministic, offline tests.
os.environ["GENEGAUGE_DEMO_MODE"] = "1"
