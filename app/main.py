"""FastAPI application entry-point.

Design notes:

* Templates are server-rendered so the product is usable without
  client-side JavaScript. JS only adds interactivity where it genuinely
  helps (live score preview, demo button).
* The UI language is deliberately layman-friendly. Technical terms
  (SNP, allele, GWAS, PRS) are confined to the ``/details`` page.
* All scoring happens server-side, so users never touch weights or
  population data directly.
"""

from __future__ import annotations

import logging
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import __version__
from .config import PROJECT_ROOT, get_settings
from .data import Signal, WeightsError, load_signals
from .logging_config import configure_logging
from .models import (
    ContributionOut,
    DemoResponse,
    ScoreRequest,
    ScoreResponse,
    SignalOut,
    SignalsResponse,
)
from .scoring import ScoringError, demo_values, score_subject, simulate_population
from .security import (
    BodySizeLimitMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)

log = logging.getLogger("genegauge")

# ---------------------------------------------------------------------------
# Lifespan: load weights + simulate population exactly once.
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging()
    try:
        signals = load_signals(settings.weights_path)
    except WeightsError as exc:
        # We intentionally re-raise - an app with a broken weights file should
        # fail loudly at startup rather than serve misleading scores.
        log.error("Failed to load weights: %s", exc)
        raise
    population = simulate_population(
        signals, size=settings.population_size, seed=settings.random_seed
    )
    app.state.signals = signals
    app.state.population = population
    log.info(
        "GeneGauge %s ready: %d signals, %d simulated people",
        __version__,
        len(signals),
        population.size,
    )
    yield


# ---------------------------------------------------------------------------
# App construction.
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="GeneGauge",
        version=__version__,
        description="A simple way to turn tiny signals into one clear score.",
        lifespan=lifespan,
        docs_url=None,      # No auto docs exposed in this demo.
        redoc_url=None,
        openapi_url=None,
    )

    # --- Middleware (outermost first). ---
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=settings.allowed_host_list or ["*"]
    )
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_body_bytes)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    # --- Static + templates. ---
    app.mount(
        "/static",
        StaticFiles(directory=str(PROJECT_ROOT / "app" / "static")),
        name="static",
    )
    templates = Jinja2Templates(directory=str(PROJECT_ROOT / "app" / "templates"))
    # Jinja2 autoescape is on by default for .html / .htm. We assert this.
    assert templates.env.autoescape is True or callable(templates.env.autoescape)

    # --- Per-request CSP nonce. ---
    @app.middleware("http")
    async def add_nonce(request: Request, call_next):
        request.state.csp_nonce = secrets.token_urlsafe(16)
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        # Log coarse metadata only; never log bodies or query strings.
        log.info(
            "%s %s -> %s (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response

    # --- Error handling. No stack traces leak to the user. ---
    @app.exception_handler(RequestValidationError)
    async def _validation_error(_req: Request, _exc: RequestValidationError) -> JSONResponse:
        # We do NOT echo the exception detail to keep malicious inputs out
        # of downstream logs / UIs. The caller gets a stable message.
        return JSONResponse(
            {"detail": "Invalid input. Please check your values."}, status_code=422
        )

    @app.exception_handler(HTTPException)
    async def _http_error(_req: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def _unhandled(_req: Request, exc: Exception) -> JSONResponse:
        # Log with traceback server-side; send a short generic message to the client.
        log.exception("Unhandled error: %s", exc.__class__.__name__)
        return JSONResponse(
            {"detail": "Something went wrong on our side."}, status_code=500
        )

    # --- Helpers. ---
    def _signals(request: Request) -> list[Signal]:
        return request.app.state.signals

    def _population(request: Request) -> np.ndarray:
        return request.app.state.population

    def _render(request: Request, template: str, context: dict) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name=template,
            context={**context, "version": __version__, "nonce": request.state.csp_nonce},
        )

    # --- HTML routes. ---
    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request) -> HTMLResponse:
        return _render(request, "home.html", {"active": "home"})

    @app.get("/calculator", response_class=HTMLResponse)
    async def calculator(request: Request) -> HTMLResponse:
        return _render(
            request,
            "calculator.html",
            {
                "active": "calculator",
                "signals": _signals(request),
                "population_size": _population(request).size,
            },
        )

    @app.get("/how-it-works", response_class=HTMLResponse)
    async def how_it_works(request: Request) -> HTMLResponse:
        return _render(request, "how_it_works.html", {"active": "how"})

    @app.get("/details", response_class=HTMLResponse)
    async def details(request: Request) -> HTMLResponse:
        return _render(
            request,
            "details.html",
            {
                "active": "details",
                "signals": _signals(request),
                "population_size": _population(request).size,
            },
        )

    # --- JSON API. ---
    @app.get("/api/signals", response_model=SignalsResponse)
    async def api_signals(request: Request) -> SignalsResponse:
        signals = _signals(request)
        return SignalsResponse(
            signals=[
                SignalOut(
                    signal_id=s.signal_id,
                    plain_label=s.plain_label,
                    weight=s.weight,
                    direction_hint=s.direction_hint,  # type: ignore[arg-type]
                )
                for s in signals
            ],
            population_size=int(_population(request).size),
        )

    @app.get("/api/demo", response_model=DemoResponse)
    async def api_demo(request: Request) -> DemoResponse:
        settings = get_settings()
        # Shift the seed by the current second / N so repeat clicks give
        # variety while staying deterministic within a window.
        seed = settings.random_seed + int(time.time()) // 5
        values = demo_values(_signals(request), seed=seed)
        return DemoResponse(values=values)

    @app.post("/api/score", response_model=ScoreResponse)
    async def api_score(request: Request, body: ScoreRequest) -> ScoreResponse:
        signals = _signals(request)
        population = _population(request)
        known_ids = {s.signal_id for s in signals}
        submitted_ids = set(body.values.keys())
        if submitted_ids != known_ids:
            # Don't echo the diff - just say what's wrong in plain English.
            raise HTTPException(status_code=422, detail="Please fill in every signal.")
        try:
            result = score_subject(signals, body.values, population)
        except ScoringError:
            raise HTTPException(
                status_code=422, detail="One or more values were out of range."
            )

        def _co(c) -> ContributionOut:
            return ContributionOut(
                signal_id=c.signal_id,
                plain_label=c.plain_label,
                value=c.value,
                weight=c.weight,
                contribution=round(c.contribution, 4),
                direction_hint=c.direction_hint,  # type: ignore[arg-type]
            )

        return ScoreResponse(
            score=result.score,
            percentile=result.percentile,
            band=result.band,  # type: ignore[arg-type]
            population_size=result.population_size,
            population_mean=result.population_mean,
            population_std=result.population_std,
            top_up=[_co(c) for c in result.top_up],
            top_down=[_co(c) for c in result.top_down],
            contributions=[_co(c) for c in result.contributions],
        )

    @app.get("/healthz")
    async def healthz(request: Request) -> dict[str, object]:
        return {
            "status": "ok",
            "signals": len(_signals(request)),
            "population_size": int(_population(request).size),
            "version": __version__,
        }

    return app


app = create_app()
