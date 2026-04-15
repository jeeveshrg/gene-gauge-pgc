# GeneGauge

> A simple way to turn tiny signals into one clear score.

GeneGauge is a small, clean web app that teaches the core idea behind a
weighted-sum score the way a well-made calculator would. It takes a
handful of tiny signals, adds them up with per-signal weights, and
shows where the result lands against a large simulated population - all
in plain English.

It is deliberately layman-friendly. The main UI never says *SNP*,
*allele*, *GWAS*, or *polygenic risk score*. Those words live on a
dedicated `Details` page for readers who want the technical story.

## Why this exists

Complex scoring systems (polygenic risk scores, credit scores,
recommendation rankings) are all variations on the same pattern:
multiply inputs by weights, add, compare. That pattern is easy to
explain if the product doesn't get in the way. GeneGauge is a small,
honest demonstration of that - built to portfolio quality.

## Screenshots

```
docs/screenshots/
├── home.png         (placeholder)
├── calculator.png   (placeholder)
└── results.png      (placeholder)
```

> Screenshots are not bundled in the repo. Run the app locally and add
> your own if you want them in your fork.

## Features

- **Plain-English UI.** No jargon by default; technical detail tucked
  behind a `Details` page and `See details` disclosure.
- **Two input modes.** A one-click `Load demo person` or a manual
  0 / 1 / 2 stepper per signal.
- **One main score.** Plus a percentile against a simulated population,
  a three-band summary (lower / typical / higher), and the top
  contributors pushing the score up and down.
- **Strict input validation.** Pydantic v2 models reject anything
  outside `0, 1, 2`, any unknown signal ID, extra fields, or oversized
  bodies.
- **Security by default.** Strict CSP with per-request nonce, host
  allow-list, body-size cap, per-IP rate limiting, silent tracebacks,
  disabled OpenAPI surface.
- **Tested.** Unit tests for the scoring engine and data loader,
  integration tests for every route, and a security test suite that
  encodes the red-team findings.

## Tech stack

Python 3.11+, FastAPI, Starlette, Jinja2 templates, Pydantic v2, NumPy.
No SPA, no build step, no database.

## Project layout

```
gene-gauge/
├── app/
│   ├── __init__.py
│   ├── config.py              # pydantic-settings with safe defaults
│   ├── data.py                # weights loader + validation
│   ├── scoring.py             # pure scoring engine (weighted sum + percentile)
│   ├── models.py              # request/response pydantic models
│   ├── security.py            # size limit, rate limit, security headers
│   ├── logging_config.py      # stdout structured logs (no bodies)
│   ├── main.py                # FastAPI app + routes
│   ├── templates/             # Jinja2 templates (autoescape on)
│   └── static/                # CSS + a small vanilla JS file
├── data/
│   ├── weights.csv            # sample weights (simulated)
│   └── README.md              # how to swap in a real dataset
├── docs/
│   ├── ARCHITECTURE.md
│   ├── SECURITY.md
│   ├── THREAT_MODEL.md
│   ├── RED_TEAM.md
│   └── RESUME.md
├── scripts/
│   └── generate_sample_data.py
├── tests/
│   ├── conftest.py
│   ├── test_api.py
│   ├── test_data.py
│   ├── test_scoring.py
│   └── test_security.py
├── .env.example
├── .gitignore
├── LICENSE
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Getting started

### Prerequisites

- Python 3.11 or newer
- `pip`

### Install

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Configure (optional)

```bash
cp .env.example .env
# edit .env if you want a different port, host allow-list, etc.
```

### Run

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000).

### Generate fresh sample data

```bash
python scripts/generate_sample_data.py
```

## Running the tests

```bash
pytest
```

With coverage:

```bash
pytest --cov=app --cov-report=term-missing
```

## Using your own data

Replace `data/weights.csv` with a CSV that has exactly these columns:

```
signal_id,plain_label,weight,direction_hint
```

Or point `GENEGAUGE_WEIGHTS_PATH` at a file elsewhere inside the
project. See [`data/README.md`](data/README.md) for constraints.

## API reference

The app is server-rendered, but a small JSON API is available:

| Method | Path                | Purpose                                            |
|--------|---------------------|----------------------------------------------------|
| GET    | `/healthz`          | Liveness check (`{status, signals, version}`).     |
| GET    | `/api/signals`      | List of signals + population size.                 |
| GET    | `/api/demo`         | Generate a deterministic demo person's values.     |
| POST   | `/api/score`        | Score a `{signal_id -> 0|1|2}` map.                |

All responses are JSON with `application/json; charset=utf-8`. Errors
carry a short `detail` message and never leak tracebacks.

## Security

See [`docs/SECURITY.md`](docs/SECURITY.md) and
[`docs/RED_TEAM.md`](docs/RED_TEAM.md). TL;DR: validated inputs,
host / size / rate limits, strict CSP, no OpenAPI, no body logging,
zero pinned CVEs at the time of writing.

## Limitations

* This is a teaching / portfolio project. **Not a medical device. Not a
  diagnosis.** Sample data is simulated.
* The reference population is generated in-process; every restart
  reshuffles it within the configured seed.
* The UI is English-only and does not yet localize units.

## Roadmap

- Optional authenticated mode for hosted demos.
- A small "explain-your-own-weights" helper that visualises the weight
  histogram.
- Snapshot testing for templates.
- A containerised deployment recipe.

## License

[MIT](LICENSE).

---

**Not a diagnosis. Not medical advice. Educational demo only.**
