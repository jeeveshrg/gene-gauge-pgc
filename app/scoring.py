"""Scoring engine.

The math is intentionally simple and transparent. Each signal has a weight.
For a given person we receive an integer value of 0, 1, or 2 for each
signal. The score is the weighted sum.

We also keep a deterministic, simulated reference population so we can
tell the user *where they land* without any per-user data leaving the box.
Percentiles come from comparing the user's score against that population.

Nothing in this module touches the network, the filesystem, or logging.
It's pure math so it's easy to unit-test and reason about.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

import numpy as np

from .data import Signal

# Allowed integer values for user-provided signal counts.
ALLOWED_VALUES: frozenset[int] = frozenset({0, 1, 2})


@dataclass(frozen=True, slots=True)
class Contribution:
    """One signal's contribution to the final score."""

    signal_id: str
    plain_label: str
    value: int
    weight: float
    contribution: float
    direction_hint: str


@dataclass(frozen=True, slots=True)
class ScoreResult:
    """Output of :func:`score_subject`."""

    score: float
    percentile: float
    population_size: int
    population_mean: float
    population_std: float
    band: str  # "low", "typical", "elevated"
    top_up: list[Contribution] = field(default_factory=list)
    top_down: list[Contribution] = field(default_factory=list)
    contributions: list[Contribution] = field(default_factory=list)


class ScoringError(ValueError):
    """Raised when a subject's signal values are invalid for scoring."""


def _validate_values(signals: Sequence[Signal], values: Mapping[str, int]) -> list[int]:
    """Return a list of values aligned to ``signals`` order, validating inputs.

    We deliberately require the caller to provide a value for every known
    signal. Silently filling in zeros would hide bugs.
    """
    if len(values) != len(signals):
        raise ScoringError(
            f"expected values for {len(signals)} signals, got {len(values)}"
        )
    aligned: list[int] = []
    for s in signals:
        if s.signal_id not in values:
            raise ScoringError(f"missing value for signal {s.signal_id!r}")
        raw = values[s.signal_id]
        # Reject bool: True/False are technically int subclasses in Python.
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise ScoringError(f"value for {s.signal_id!r} must be an integer 0, 1, or 2")
        if raw not in ALLOWED_VALUES:
            raise ScoringError(f"value for {s.signal_id!r} must be 0, 1, or 2")
        aligned.append(raw)
    return aligned


def simulate_population(
    signals: Sequence[Signal],
    *,
    size: int,
    seed: int,
) -> np.ndarray:
    """Build a simulated reference population of scores.

    Each sample person gets independent 0/1/2 values per signal, drawn from
    a mild Binomial(2, 0.3) that mimics the kind of allele-count distribution
    you'd see on noisy public data - without claiming to *be* such data.
    """
    if size < 100:
        raise ScoringError("population size must be >= 100")
    rng = np.random.default_rng(seed)
    weights = np.array([s.weight for s in signals], dtype=np.float64)
    # Per-signal probability jittered per signal (reproducibly) so the
    # distribution is not a perfect normal curve.
    p = rng.uniform(0.15, 0.45, size=len(signals))
    draws = rng.binomial(n=2, p=p, size=(size, len(signals)))
    scores = draws @ weights
    return scores


def compute_percentile(score: float, population: np.ndarray) -> float:
    """Return the 0..100 percentile of ``score`` against ``population``."""
    if population.size == 0:
        return 50.0
    # Use mean of strict-below and <=: a standard definition that
    # handles ties reasonably.
    below = float(np.mean(population < score))
    at_or_below = float(np.mean(population <= score))
    pct = 100.0 * (below + at_or_below) / 2.0
    # Clamp for safety.
    return max(0.0, min(100.0, round(pct, 1)))


def _band_from_percentile(pct: float) -> str:
    if pct < 33.0:
        return "low"
    if pct < 67.0:
        return "typical"
    return "elevated"


def score_subject(
    signals: Sequence[Signal],
    values: Mapping[str, int],
    population: np.ndarray,
    *,
    top_n: int = 3,
) -> ScoreResult:
    """Score one subject and summarise where they land.

    ``values`` must be a mapping of ``signal_id -> int in {0, 1, 2}``.
    """
    aligned = _validate_values(signals, values)

    contributions: list[Contribution] = []
    total = 0.0
    for s, v in zip(signals, aligned):
        c = float(s.weight) * v
        total += c
        contributions.append(
            Contribution(
                signal_id=s.signal_id,
                plain_label=s.plain_label,
                value=v,
                weight=s.weight,
                contribution=c,
                direction_hint=s.direction_hint,
            )
        )

    pct = compute_percentile(total, population)
    band = _band_from_percentile(pct)

    # Biggest upward and downward reasons, by absolute contribution size.
    ups = [c for c in contributions if c.contribution > 0]
    downs = [c for c in contributions if c.contribution < 0]
    ups.sort(key=lambda c: c.contribution, reverse=True)
    downs.sort(key=lambda c: c.contribution)

    return ScoreResult(
        score=round(total, 4),
        percentile=pct,
        population_size=int(population.size),
        population_mean=float(round(np.mean(population), 4)),
        population_std=float(round(np.std(population), 4)),
        band=band,
        top_up=ups[:top_n],
        top_down=downs[:top_n],
        contributions=contributions,
    )


def demo_values(signals: Sequence[Signal], *, seed: int) -> dict[str, int]:
    """Generate a deterministic demo person's values.

    The user gets a plausible-feeling subject without ever touching private
    data. Using a seeded RNG keeps tests stable and makes the demo
    reproducible.
    """
    rng = np.random.default_rng(seed)
    p = rng.uniform(0.15, 0.45, size=len(signals))
    draws = rng.binomial(n=2, p=p)
    return {s.signal_id: int(v) for s, v in zip(signals, draws)}
