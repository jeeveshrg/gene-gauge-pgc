"""Configuration loaded from environment variables with safe defaults.

We use pydantic-settings so every value is typed, validated at startup, and
impossible to silently misread. Anything sensitive should live here (not in
code), and nothing in here is logged at runtime.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Runtime settings for the GeneGauge app."""

    model_config = SettingsConfigDict(
        env_prefix="GENEGAUGE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    env: Literal["development", "production"] = "development"

    weights_path: str = "data/weights.csv"
    population_size: int = Field(default=2000, ge=100, le=50_000)
    random_seed: int = Field(default=42, ge=0, le=2**31 - 1)

    allowed_hosts: str = "127.0.0.1,localhost"
    max_body_bytes: int = Field(default=32_768, ge=1024, le=1_048_576)

    @field_validator("weights_path")
    @classmethod
    def _resolve_weights(cls, value: str) -> str:
        """Make sure the weights path resolves inside the project tree.

        We do not allow users to point the app at arbitrary files on disk.
        """
        path = (PROJECT_ROOT / value).resolve() if not Path(value).is_absolute() else Path(value).resolve()
        try:
            path.relative_to(PROJECT_ROOT)
        except ValueError as exc:  # pragma: no cover - config guard
            raise ValueError("weights_path must live inside the project root") from exc
        return str(path)

    @property
    def allowed_host_list(self) -> list[str]:
        return [h.strip() for h in self.allowed_hosts.split(",") if h.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
