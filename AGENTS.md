# AGENTS.md

## Cursor Cloud specific instructions

GeneGauge is a small, self-contained FastAPI app (server-rendered Jinja2 templates
+ a small JSON API). No database, no SPA, no build step. Standard commands live in
`README.md`; only the non-obvious details are captured here.

- Python deps live in a virtualenv at `.venv` (created by the update script).
  Activate it before running anything: `source .venv/bin/activate`.
- Run the dev server: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`,
  then open http://127.0.0.1:8000. Health check: `GET /healthz`.
- Run tests: `pytest` (50 tests). Coverage: `pytest --cov=app --cov-report=term-missing`.
- There is no configured linter/formatter (no ruff/flake8/black in the deps or
  `pyproject.toml`); "lint" is effectively the test suite + type-free checks.
- Gotcha: `pyproject.toml` sets `filterwarnings = ["error::DeprecationWarning"]`,
  so any `DeprecationWarning` raised during a test run is promoted to a hard
  failure. Keep dependency versions in sync with `requirements.txt`.
- The reference population for percentiles is simulated in-process on startup
  (size/seed via `GENEGAUGE_POPULATION_SIZE` / `GENEGAUGE_RANDOM_SEED`). Results
  are deterministic for a given seed but reshuffle if the seed changes.
- Config is via `GENEGAUGE_*` env vars (see `.env.example`); copying to `.env` is
  optional, the app runs with safe defaults.

Note: this workspace contains several other independent repositories under
`/agent/repos/`. The dev environment here is set up for `gene-gauge`.
