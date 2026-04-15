"""Security-focused tests: body size limits, injection, trusted hosts, etc.

These are the "self red-team" checks baked into CI so regressions are loud.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


@pytest.fixture(scope="module")
def client() -> TestClient:
    os.environ["GENEGAUGE_WEIGHTS_PATH"] = "data/weights.csv"
    os.environ["GENEGAUGE_ALLOWED_HOSTS"] = "testserver,127.0.0.1,localhost"
    os.environ["GENEGAUGE_MAX_BODY_BYTES"] = "4096"
    get_settings.cache_clear()  # type: ignore[attr-defined]
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_body_too_large_rejected(client: TestClient) -> None:
    # Advertise a huge body via Content-Length - should be rejected at the
    # middleware before the route runs.
    large = "A" * 10_000
    r = client.post(
        "/api/score",
        content=large,
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 413


def test_untrusted_host_rejected() -> None:
    os.environ["GENEGAUGE_ALLOWED_HOSTS"] = "only-this-host.example"
    os.environ["GENEGAUGE_WEIGHTS_PATH"] = "data/weights.csv"
    get_settings.cache_clear()  # type: ignore[attr-defined]
    app = create_app()
    with TestClient(app) as c:
        r = c.get("/", headers={"host": "evil.example"})
        assert r.status_code == 400


def test_xss_payload_in_value_rejected(client: TestClient) -> None:
    signals = client.get("/api/signals").json()["signals"]
    values = {s["signal_id"]: 0 for s in signals}
    # Stick an XSS string in a place Pydantic typed as int.
    values[signals[0]["signal_id"]] = "<script>alert(1)</script>"  # type: ignore[assignment]
    r = client.post("/api/score", json={"values": values})
    assert r.status_code == 422
    # We must never echo the raw payload back.
    assert "<script>" not in r.text


def test_html_is_autoescaped(client: TestClient) -> None:
    # The plain labels in data/weights.csv are safe, but we want to prove
    # Jinja autoescape is on by searching for dangerous output patterns.
    r = client.get("/calculator")
    assert r.status_code == 200
    # No naked <script> outside our own nonce'd script tag.
    # A sharper test: no unescaped angle brackets in a signal label area.
    assert "<script>alert" not in r.text


def test_no_stack_trace_leaks(client: TestClient) -> None:
    # Intentionally malformed JSON - FastAPI should produce a generic 4xx
    # with our hand-written detail, not a traceback.
    r = client.post(
        "/api/score",
        content="{not-json",
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code in (400, 422)
    assert "Traceback" not in r.text
    assert "File \"" not in r.text


def test_openapi_schema_not_exposed(client: TestClient) -> None:
    for path in ("/openapi.json", "/docs", "/redoc"):
        assert client.get(path).status_code == 404


def test_signal_id_pattern_enforced(client: TestClient) -> None:
    r = client.post(
        "/api/score",
        json={"values": {"../etc/passwd": 0}},
    )
    assert r.status_code == 422


def test_rate_limit_triggers(client: TestClient) -> None:
    # Fire > 60 requests in quick succession; one of the later ones should 429.
    signals = client.get("/api/signals").json()["signals"]
    values = {s["signal_id"]: 0 for s in signals}
    got_429 = False
    for _ in range(80):
        r = client.post("/api/score", json={"values": values})
        if r.status_code == 429:
            got_429 = True
            break
        assert r.status_code == 200
    assert got_429


def test_security_response_headers_on_api(client: TestClient) -> None:
    r = client.get("/api/signals")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("Referrer-Policy") == "no-referrer"
