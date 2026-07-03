"""Analysis persistence (history).

Uses a local JSON file by default so the app works fully offline. If Supabase
credentials are configured, results can additionally be mirrored to a Supabase
table/storage bucket — but the JSON store remains the source of truth for demo
mode. The store is intentionally simple and thread-safe for a single process.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Optional

from app import config

_LOCK = threading.Lock()


class AnalysisStore:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else config.STORE_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write_all({})

    # --- low-level -------------------------------------------------------
    def _read_all(self) -> dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _write_all(self, data: dict[str, Any]) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, default=str), encoding="utf-8")
        tmp.replace(self.path)

    # --- public API ------------------------------------------------------
    def save(self, analysis: dict[str, Any]) -> None:
        with _LOCK:
            data = self._read_all()
            data[analysis["id"]] = analysis
            self._write_all(data)

    def get(self, analysis_id: str) -> Optional[dict[str, Any]]:
        with _LOCK:
            return self._read_all().get(analysis_id)

    def list_summaries(self) -> list[dict[str, Any]]:
        with _LOCK:
            data = self._read_all()
        summaries = []
        for a in data.values():
            per = a.get("per_dataset", [])
            summaries.append(
                {
                    "id": a.get("id"),
                    "name": a.get("name"),
                    "status": a.get("status"),
                    "created_at": a.get("created_at"),
                    "disorders": [d.get("disorder") for d in per],
                    "n_datasets": len(per),
                    "demo_mode": a.get("params", {}).get("demo_mode", False),
                }
            )
        summaries.sort(key=lambda s: s.get("created_at") or "", reverse=True)
        return summaries

    def delete(self, analysis_id: str) -> bool:
        with _LOCK:
            data = self._read_all()
            if analysis_id in data:
                del data[analysis_id]
                self._write_all(data)
                return True
            return False


def supabase_enabled() -> bool:
    return bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY"))


store = AnalysisStore()
