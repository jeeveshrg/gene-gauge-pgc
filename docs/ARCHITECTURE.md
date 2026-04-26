# Architecture

A short tour of how GeneGauge is wired.

## Goals that shape the design

1. **Layman-first UI.** Every screen must be understandable without any
   biology or statistics background. Technical language (SNP, allele, GWAS,
   PRS) only appears on the `/details` page.
2. **Boring tech.** One language (Python), one process, one command to
   run. No build step, no SPA, no database.
3. **Safe by default.** Inputs are strictly typed at the edge; errors never
   leak stack traces; secrets never live in code.
4. **Swappable data.** The on-disk weights file is the only coupling to
   "real" data. Any replacement that matches the schema works unchanged.

## Stack

| Layer           | Choice                                 |
|-----------------|----------------------------------------|
| HTTP server     | `uvicorn`                              |
| Web framework   | `FastAPI` (Starlette under the hood)   |
| Templates       | `Jinja2` (autoescape on)               |
| Validation      | `pydantic` v2 with `pydantic-settings` |
| Math            | `numpy`                                |
| Tests           | `pytest`                               |

Why this combination: it runs in a single process, has zero client-side
framework, and gives us strong type-checked request validation without
adding a service or a DB. It is a "serious engineer's default", not a
novelty stack.

## Process layout

```
browser  ──HTTP──▶  uvicorn  ──ASGI──▶  FastAPI
                                │
                                ├── Jinja2 templates (HTML pages)
                                ├── JSON routes (/api/*)
                                ├── Scoring engine (pure Python + numpy)
                                └── In-memory simulated population
```

Everything fits in one Python process. No external service is required.

## Request lifecycle

1. `TrustedHostMiddleware` rejects requests with an unexpected `Host` header.
2. `BodySizeLimitMiddleware` rejects payloads over `GENEGAUGE_MAX_BODY_BYTES`.
3. `RateLimitMiddleware` (per-IP sliding window) applies to `/api/*`.
4. `SecurityHeadersMiddleware` attaches CSP / XFO / XCTO / Referrer-Policy
   / Permissions-Policy / COOP / CORP to every response.
5. A tiny per-request middleware mints a CSP nonce and logs coarse request
   metadata (method, path, status, elapsed time). **Bodies are never logged.**
6. The route handler runs. Pydantic validates inputs before the handler
   sees them.
7. Exceptions are caught centrally. Users see a short, generic message;
   the server log records the traceback.

## Module map

```
app/
  __init__.py         # version + package marker
  config.py           # pydantic-settings, resolves weights path safely
  data.py             # CSV loader + Signal dataclass + validation
  scoring.py          # pure scoring engine (no I/O, no logging)
  models.py           # pydantic request/response models
  security.py         # middleware (size limit, rate limit, headers)
  logging_config.py   # structured stdout logging
  main.py             # create_app() + routes + lifespan
  templates/          # Jinja2 templates
  static/             # CSS + JS (served by StaticFiles)
```

## Data flow

1. **Startup.** `lifespan()` loads and validates `data/weights.csv`, then
   builds a simulated reference population once. Both live on
   `app.state` for the lifetime of the process.
2. **Request.** `/api/score` takes a `{signal_id -> value}` map,
   validates it, scores the subject, and computes a percentile against
   the already-cached population.
3. **Response.** The UI renders the score, percentile, band, and top
   contributors in plain English.

## Where real data plugs in

Replace `data/weights.csv` (or point `GENEGAUGE_WEIGHTS_PATH` at a
different file with the same four columns). No code changes needed.
See [`data/README.md`](../data/README.md) for the schema.

## What is *not* here (on purpose)

* **No database.** The app holds no user state. Each request is
  self-contained.
* **No authentication.** Nothing is logged, stored, or linked to a user.
* **No uploads.** File-ingest UX is inherently risky for a demo. If you
  need it later, keep it behind an auth boundary.
* **No OpenAPI spec.** `/docs`, `/redoc`, and `/openapi.json` are
  disabled so we don't advertise the shape of the API to drive-by
  scanners.
