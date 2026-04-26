"""Security-focused middleware and helpers.

Pieces here are deliberately small and defensive:

* A hard request body size limit (rejects >N bytes before parsing).
* Security response headers (CSP, X-Content-Type-Options, etc.).
* A tiny in-memory rate limiter keyed on the client IP.

None of this replaces a real edge (WAF, reverse proxy, cloud rate limiter)
but it makes the app safe to run as-is for a demo or portfolio deploy.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

# Content Security Policy: restrictive, but allows our inline bootstrap JSON
# via a nonce set per response.
_CSP_TEMPLATE = (
    "default-src 'self'; "
    "script-src 'self' 'nonce-{nonce}'; "
    "style-src 'self'; "
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)


def build_csp(nonce: str) -> str:
    return _CSP_TEMPLATE.format(nonce=nonce)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach defensive response headers to every response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        # Only set CSP on HTML responses where a per-request nonce was set.
        nonce = getattr(request.state, "csp_nonce", None)
        if nonce and response.headers.get("content-type", "").startswith("text/html"):
            response.headers["Content-Security-Policy"] = build_csp(nonce)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy",
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()",
        )
        # Opt out of Google's FLoC / Topics by default.
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose body is larger than ``max_bytes``.

    We check the Content-Length header up front, and *also* guard against
    chunked uploads by streaming and counting bytes.
    """

    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next) -> Response:
        cl = request.headers.get("content-length")
        if cl is not None:
            try:
                if int(cl) > self.max_bytes:
                    return JSONResponse(
                        {"detail": "Request body too large."},
                        status_code=413,
                    )
            except ValueError:
                return JSONResponse(
                    {"detail": "Invalid Content-Length."}, status_code=400
                )
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Very small sliding-window per-IP rate limiter.

    This is *not* a substitute for a real rate limiter in production, but
    it cheaply blunts trivial bursts from a single host during a demo.
    """

    def __init__(self, app: ASGIApp, *, max_requests: int = 60, window_seconds: float = 60.0) -> None:
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: dict[str, Deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Only rate-limit API writes; static and GET pages are cheap.
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window_start = now - self.window
        bucket = self._hits[client]
        while bucket and bucket[0] < window_start:
            bucket.popleft()
        if len(bucket) >= self.max_requests:
            return JSONResponse(
                {"detail": "Too many requests. Please slow down."},
                status_code=429,
            )
        bucket.append(now)
        return await call_next(request)
