"""Pydantic models for request / response payloads.

The models are deliberately strict: extra fields are forbidden, strings are
length-capped, and the value set for per-signal inputs is limited to 0, 1,
or 2. This is the outermost defense against injection-style payloads.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# Opaque per-signal identifier. Alphanumerics plus underscore / hyphen only.
SignalId = Annotated[
    str,
    StringConstraints(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9_\-]+$"),
]

# Integer input per signal - strictly 0, 1, or 2. We use Literal so Pydantic
# rejects anything else before the scoring engine even sees it.
SignalValue = Literal[0, 1, 2]


class ScoreRequest(BaseModel):
    """POST /api/score body."""

    model_config = ConfigDict(extra="forbid")

    values: dict[SignalId, SignalValue] = Field(
        ..., description="Map of signal_id to value (0, 1, or 2)."
    )


class ContributionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signal_id: str
    plain_label: str
    value: int
    weight: float
    contribution: float
    direction_hint: Literal["up", "down"]


class ScoreResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: float
    percentile: float
    band: Literal["low", "typical", "elevated"]
    population_size: int
    population_mean: float
    population_std: float
    top_up: list[ContributionOut]
    top_down: list[ContributionOut]
    # We do NOT return every contribution by default - that's only shown
    # inside the "See details" panel so the main UI stays readable.
    contributions: list[ContributionOut]


class SignalOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signal_id: str
    plain_label: str
    weight: float
    direction_hint: Literal["up", "down"]


class SignalsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signals: list[SignalOut]
    population_size: int


class DemoResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    values: dict[str, int]
