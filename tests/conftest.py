"""Shared pytest fixtures."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session", autouse=True)
def _clean_env() -> None:
    """Scrub GENEGAUGE_* env vars so tests don't inherit a dev .env."""
    for key in list(os.environ):
        if key.startswith("GENEGAUGE_"):
            del os.environ[key]
    os.environ["GENEGAUGE_RANDOM_SEED"] = "42"
    os.environ["GENEGAUGE_POPULATION_SIZE"] = "500"
    os.environ["GENEGAUGE_ALLOWED_HOSTS"] = "testserver,127.0.0.1,localhost"


@pytest.fixture
def tmp_weights(tmp_path: Path) -> Path:
    """Write a tiny valid weights file and return its path."""
    p = tmp_path / "weights.csv"
    p.write_text(
        "signal_id,plain_label,weight,direction_hint\n"
        "S001,Signal 1 - demo,0.5,up\n"
        "S002,Signal 2 - demo,-0.3,down\n"
        "S003,Signal 3 - demo,0.1,up\n",
        encoding="utf-8",
    )
    return p
