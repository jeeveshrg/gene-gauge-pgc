# Self red-team report

A log of attack attempts run against the app during development, with
observed behaviour and fixes. Every item below was reproduced at least
once with `curl` against a local `uvicorn` instance, and most are also
captured as pytest tests in `tests/test_security.py`.

## Baseline

* Stack: Python 3.11+, FastAPI `0.135.3`, Starlette `0.49.1`,
  Pydantic `2.10.x`.
* Configuration: `GENEGAUGE_ALLOWED_HOSTS=127.0.0.1,localhost`,
  `GENEGAUGE_MAX_BODY_BYTES=32768`, default rate limit 60 req / 60 s
  per IP on `/api/*`.

## Attempts and outcomes

| # | Attempt | Outcome | Fix / note |
|---|---|---|---|
| 1 | Path traversal via `signal_id` (`"../../etc/passwd"`). | Rejected with 422. | Pydantic regex `^[A-Za-z0-9_\-]{1,32}$`. |
| 2 | XSS payload as `signal_id` (`"<script>alert(1)</script>"`). | Rejected with 422; payload never echoed back. | Same regex; generic error body. |
| 3 | Null byte in `signal_id`. | Rejected with 422. | Same regex. |
| 4 | Oversized body (>100 KB) with a big junk field. | Rejected with 413 before parsing. | `BodySizeLimitMiddleware`. |
| 5 | Non-integer value (`"1"`). | Rejected with 422. | `Literal[0, 1, 2]`. |
| 6 | Boolean value (`true`). | Rejected with 422. | Pydantic v2 with strict Literal rejects bools. |
| 7 | Float value (`1.5`). | Rejected with 422. | `Literal[0, 1, 2]`. |
| 8 | Crafted `Host: attacker.example`. | Rejected with 400. | `TrustedHostMiddleware`. |
| 9 | Static traversal (`/static/../app/main.py`). | 404. | Starlette `StaticFiles` resolves and rejects. |
| 10 | `OPTIONS` / `TRACE` on routes. | 405. | FastAPI method routing. |
| 11 | `GET` on `/api/score` (POST-only). | 405. | FastAPI method routing. |
| 12 | Huge integer value (`99...9`). | Rejected with 422. | `Literal[0,1,2]` blocks before the scoring engine runs. |
| 13 | Overlong `signal_id` (>32 chars). | Rejected with 422. | Regex length bound. |
| 14 | Malformed JSON (`{not-json`). | Rejected with 422, generic message. | FastAPI parser + our handler; no stack trace in body. |
| 15 | Form-encoded body instead of JSON. | Rejected with 422. | `ScoreRequest` demands a JSON object. |
| 16 | Deeply nested JSON (2000 levels). | Rejected with 400; server stayed up. | Starlette JSON parser; no custom fix needed. |
| 17 | `Host: <script>alert(1)</script>`. | Rejected with 400; header not echoed. | `TrustedHostMiddleware` + autoescape. |
| 18 | `GET /openapi.json`, `/docs`, `/redoc`. | 404. | Disabled in `FastAPI(...)`. |
| 19 | Direct request for `/data/weights.csv`. | 404. | `data/` is not mounted; only `app/static/` is. |
| 20 | Inspected `/api/signals` for caching headers. | No `Cache-Control` set. | Acceptable: payload is not secret and size is tiny. |
| 21 | Checked `Content-Type` on `/static/js/app.js`. | `text/javascript; charset=utf-8` with `X-Content-Type-Options: nosniff`. | Correct. |
| 22 | Tried to point `GENEGAUGE_WEIGHTS_PATH` at `/etc/passwd`. | Rejected at `Settings` load time (ValueError). | `field_validator` forces path inside project root. |
| 23 | BOM-prefixed JSON body. | Parsed as expected; scoring engine rejected the incomplete payload with 422. | No issue. |
| 24 | Burst > 60 requests to `/api/score`. | Later requests return 429. | `RateLimitMiddleware`. |

## Code-review findings and fixes

During review we also looked for classes of issue that don't show up in
black-box probing:

* **NaN / Inf weights.** A malicious or corrupt weights file could feed
  `inf` into the scoring math, producing junk percentiles. Fix: the
  `Signal` dataclass rejects non-finite weights and caps magnitude at
  10. Covered by `test_data.py::test_non_finite_weight_rejected`.
* **Bool-as-int drift.** Python treats `True` / `False` as `int`
  subclasses. The scoring engine uses an explicit `isinstance(raw,
  bool)` check to reject them before doing math. Covered by
  `test_scoring.py::test_score_rejects_out_of_range[True]`.
* **Silent zero-fill.** Accepting fewer values than signals would let
  the score drift in ways a caller doesn't expect. Fix: the engine
  demands a value for every signal and raises `ScoringError` otherwise.
* **Per-request log amplification.** Logging bodies would turn any
  payload into a persistence risk. Fix: only coarse request metadata is
  logged; bodies are never touched.
* **Dependency CVEs.** Initial pins had 8 known vulnerabilities across
  4 packages. Fix: bumped `fastapi`, `starlette`, `jinja2`,
  `python-multipart`, `pytest`, `pytest-cov`, `httpx`, `numpy`,
  `pydantic`, `pydantic-settings`, and re-ran `pip-audit` until clean.

## Final state

* `pip-audit -r requirements.txt` → **No known vulnerabilities found.**
* `pytest` → **50 passed**.
* Every attack attempt above is either a pytest case or trivially
  reproducible with `curl`.
