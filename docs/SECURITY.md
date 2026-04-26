# Security notes

## Reporting a vulnerability

If you find a security issue, please open a private GitHub advisory or
email the maintainer rather than filing a public issue.

## What we do

* **Input validation at the edge.** Every JSON route is typed with
  Pydantic v2 models that use `extra='forbid'`, regex-bound string
  fields, and `Literal[0, 1, 2]` for per-signal values. Anything else
  is rejected with a 422 and a generic message.
* **Host allow-list.** `TrustedHostMiddleware` rejects requests whose
  `Host` header is not in `GENEGAUGE_ALLOWED_HOSTS`.
* **Body-size cap.** Requests whose `Content-Length` exceeds
  `GENEGAUGE_MAX_BODY_BYTES` (32 KB default) get a 413 before the route
  is ever touched.
* **Rate limiting.** A small per-IP sliding window protects `/api/*`
  against trivial bursts. Real production deployments should still
  front the app with a CDN / WAF.
* **Response headers.** Every response carries
  `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: no-referrer`, a strict `Permissions-Policy`, and
  `Cross-Origin-*` headers. HTML responses also carry a strict CSP with
  a per-request `script-src` nonce.
* **Autoescaped templates.** Jinja2 autoescape is on. The app never
  uses `|safe` and never interpolates user input into HTML attributes
  without escaping. The client-side JS updates the DOM via
  `textContent`, never `innerHTML`.
* **Safe error surface.** A global exception handler converts any
  unhandled exception into a short generic 500 message. The traceback
  is logged server-side only.
* **No stack traces in validation errors.** We replace FastAPI's
  default `RequestValidationError` body with a short stable message so
  malicious payloads are not echoed back.
* **No OpenAPI surface.** `/docs`, `/redoc`, and `/openapi.json` are
  disabled to avoid advertising routes to drive-by scanners.
* **Minimal logging.** We log only method, path, status, and elapsed
  time. Bodies, query strings, and client IP payloads are never logged.
* **Dependency pinning + auditing.** Every dependency is pinned in
  `requirements.txt`. CI runs `pip-audit` against the lock.
* **No secrets in code.** Secrets belong in environment variables; see
  `.env.example`. `.env` is git-ignored.

## Self red-team findings

See [`RED_TEAM.md`](./RED_TEAM.md) for a log of attack attempts and
outcomes. The baseline was clean: every attempt was either blocked by
validation / middleware or required out-of-band access to succeed.

## Checklist before deploying publicly

- [ ] Set `GENEGAUGE_ENV=production` and a real `GENEGAUGE_ALLOWED_HOSTS`.
- [ ] Put the app behind TLS (e.g. via a reverse proxy).
- [ ] Use a real rate limiter at the edge.
- [ ] Pin a specific container / package version and rebuild regularly.
- [ ] Re-run `pip-audit` on the image before shipping.
- [ ] Keep the weights file outside of the web root on disk.
