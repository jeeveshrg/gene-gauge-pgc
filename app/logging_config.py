"""Structured logging setup.

We intentionally avoid logging any user-submitted body. Only coarse request
metadata (method, path, status, elapsed time) is logged. This keeps analytics
useful without leaking input data into logs.
"""

from __future__ import annotations

import logging
import sys

LOG_FORMAT = "%(asctime)s %(levelname)-5s %(name)s - %(message)s"


def configure_logging(level: int = logging.INFO) -> None:
    """Configure the root logger once, idempotently."""
    root = logging.getLogger()
    # If already configured by uvicorn, don't duplicate handlers.
    if any(getattr(h, "_genegauge", False) for h in root.handlers):
        return
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handler._genegauge = True  # type: ignore[attr-defined]
    root.addHandler(handler)
    root.setLevel(level)

    # Silence overly chatty loggers we don't control.
    for noisy in ("multipart", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
