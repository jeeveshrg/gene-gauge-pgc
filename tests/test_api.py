"""Integration tests for the FastAPI app."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


@pytest.fixture(scope="module")
def client(tmp_path_factory: pytest.TempPathFactory) -> TestClient:
    # Use the project's real weights file so tests exercise end-to-end.
    os.environ["GENEGAUGE_WEIGHTS_PATH"] = "data/weights.csv"
    get_settings.cache_clear()  # type: ignore[attr-defined]
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_home_renders(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "GeneGauge" in r.text
    assert "Not a diagnosis" in r.text or "not medical advice" in r.text.lower()


def test_calculator_renders_signals(client: TestClient) -> None:
    r = client.get("/calculator")
    assert r.status_code == 200
    # The radio inputs for at least one signal show up.
    assert 'name="S001"' in r.text


def test_security_headers_present(client: TestClient) -> None:
    r = client.get("/")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("Referrer-Policy") == "no-referrer"
    # CSP is set on HTML responses.
    csp = r.headers.get("Content-Security-Policy")
    assert csp is not None and "default-src 'self'" in csp


def test_api_signals(client: TestClient) -> None:
    r = client.get("/api/signals")
    assert r.status_code == 200
    body = r.json()
    assert "signals" in body and isinstance(body["signals"], list)
    assert len(body["signals"]) > 0
    for s in body["signals"]:
        assert set(s.keys()) == {"signal_id", "plain_label", "weight", "direction_hint"}


def test_api_demo_returns_values_for_every_signal(client: TestClient) -> None:
    signals = client.get("/api/signals").json()["signals"]
    sig_ids = {s["signal_id"] for s in signals}
    demo = client.get("/api/demo").json()
    assert set(demo["values"].keys()) == sig_ids
    assert all(v in (0, 1, 2) for v in demo["values"].values())


def test_api_score_happy_path(client: TestClient) -> None:
    signals = client.get("/api/signals").json()["signals"]
    values = {s["signal_id"]: 1 for s in signals}
    r = client.post("/api/score", json={"values": values})
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) >= {
        "score", "percentile", "band", "population_size",
        "top_up", "top_down", "contributions",
    }
    assert body["band"] in {"low", "typical", "elevated"}
    assert 0.0 <= body["percentile"] <= 100.0


def test_api_score_rejects_bad_values(client: TestClient) -> None:
    signals = client.get("/api/signals").json()["signals"]
    values = {s["signal_id"]: 1 for s in signals}
    values[signals[0]["signal_id"]] = 7  # out of range
    r = client.post("/api/score", json={"values": values})
    assert r.status_code == 422


def test_api_score_rejects_missing_signal(client: TestClient) -> None:
    signals = client.get("/api/signals").json()["signals"]
    values = {s["signal_id"]: 1 for s in signals[:-1]}  # drop last
    r = client.post("/api/score", json={"values": values})
    assert r.status_code == 422


def test_api_score_rejects_unknown_signal(client: TestClient) -> None:
    signals = client.get("/api/signals").json()["signals"]
    values = {s["signal_id"]: 1 for s in signals}
    values["SxxxUNKNOWN"] = 1
    r = client.post("/api/score", json={"values": values})
    # Pydantic rejects the ID pattern first (SxxxUNKNOWN is OK pattern-wise),
    # but our known-ids check then catches it.
    assert r.status_code == 422


def test_api_score_rejects_extra_fields(client: TestClient) -> None:
    signals = client.get("/api/signals").json()["signals"]
    values = {s["signal_id"]: 0 for s in signals}
    r = client.post("/api/score", json={"values": values, "evil": "x"})
    assert r.status_code == 422


def test_healthz(client: TestClient) -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["signals"] > 0


def test_openapi_is_disabled(client: TestClient) -> None:
    # We chose to not expose the schema publicly in this demo.
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
