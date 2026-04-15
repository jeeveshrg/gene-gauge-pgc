# Threat model

Short, honest, and grounded in what GeneGauge actually does.

## Scope

GeneGauge is a stateless scoring demo served over HTTP. It:

* reads a static weights file at startup,
* accepts a JSON map of `{signal_id -> 0|1|2}`,
* returns a score, percentile, and per-signal contributions,
* renders a handful of static HTML pages.

It does **not** store user data, run uploads, run background jobs, query
a database, or send email.

## Assets

| Asset                 | Why it matters                                             |
|-----------------------|------------------------------------------------------------|
| The running process   | Service availability during demos / deploys.              |
| The weights file      | Loaded once; should not be replaceable by a remote caller. |
| Log output            | Must not contain user inputs or secrets.                   |
| Browser-rendered HTML | Must not be a vector for reflected / stored XSS.           |

There is **no personal data** in the app by design.

## Trust boundaries

```
[ untrusted internet ]  →  [ uvicorn ]  →  [ FastAPI app ]
         │                     │                  │
         │                     │                  ├── Jinja2 templates (autoescaped)
         │                     │                  ├── Scoring engine (pure math)
         │                     │                  └── Read-only access to data/weights.csv
         │                     │
         └── HTTP request      └── ASGI
```

Everything from the network edge in is untrusted until validated.

## Adversaries we explicitly consider

| Adversary             | Capability                                          |
|-----------------------|-----------------------------------------------------|
| Drive-by scanner      | Scrapes paths, tries common exploits, looks at headers. |
| Malicious form poster | Crafts bodies to crash, confuse, or leak data.      |
| Resource-waster       | Floods requests to exhaust CPU / memory.            |
| Casual XSS tester     | Puts `<script>` in fields to see if the UI echoes them. |

We explicitly do **not** defend against:

* Compromise of the host OS.
* Side-channel timing attacks.
* Sophisticated botnets at scale (that is what a CDN / WAF is for).

## STRIDE-style checklist

| Threat                  | Mitigation                                                      |
|-------------------------|-----------------------------------------------------------------|
| **S**poofing host       | `TrustedHostMiddleware` with allow-list.                        |
| **T**ampering inputs    | Pydantic v2 strict models (`extra='forbid'`, `Literal[0,1,2]`). |
| **R**epudiation         | Out of scope: no user accounts, no writes.                      |
| **I**nformation leaks   | No stack traces to client; logs never record bodies/IDs.        |
| **D**enial of service   | Body-size limit (32 KB default); per-IP rate limit on `/api/*`. |
| **E**levation of priv.  | App runs as a single process with read-only data; no auth required to escalate into.|

## Misuse cases we've thought about

* **Path traversal via `signal_id`.** IDs are constrained to
  `^[A-Za-z0-9_\-]{1,32}$` via Pydantic regex before the route handler
  sees them.
* **Script injection via labels.** Labels come from a file we ship; the
  UI renders them through Jinja autoescape, never `|safe`. Even if a
  malicious file were swapped in, the browser would render text, not
  markup.
* **Arbitrary file read.** `weights_path` must resolve inside the
  project root (enforced in `Settings` validator). We do not expose any
  route that accepts a file path.
* **Nested / huge JSON.** The body-size middleware rejects oversized
  payloads up front. Values are strictly `Literal[0, 1, 2]`, so even
  clever typed nesting can't push the scoring engine off-path.
* **Leaking the weights API shape.** `/docs`, `/redoc`, and
  `/openapi.json` are disabled.

## Residual risk

* A determined attacker with network access and no rate limit upstream
  can still cause CPU / bandwidth cost. Deploy behind a reverse proxy
  or CDN with its own rate limiting in production.
* This is a demo. It is not hardened for real medical data or PII. Do
  not feed it either.
