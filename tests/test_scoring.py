"""Tests for the scoring engine."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from app.data import load_signals
from app.scoring import (
    ScoringError,
    compute_percentile,
    demo_values,
    score_subject,
    simulate_population,
)


def test_score_is_weighted_sum(tmp_weights: Path) -> None:
    signals = load_signals(tmp_weights)
    pop = simulate_population(signals, size=500, seed=1)
    values = {"S001": 2, "S002": 1, "S003": 0}
    result = score_subject(signals, values, pop)
    # 2*0.5 + 1*(-0.3) + 0*0.1 = 0.7
    assert result.score == pytest.approx(0.7)


def test_percentile_within_bounds(tmp_weights: Path) -> None:
    signals = load_signals(tmp_weights)
    pop = simulate_population(signals, size=500, seed=1)
    values = {s.signal_id: 2 for s in signals}
    result = score_subject(signals, values, pop)
    assert 0.0 <= result.percentile <= 100.0


def test_percentile_edge_cases() -> None:
    pop = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    assert compute_percentile(-100.0, pop) == 0.0
    assert compute_percentile(100.0, pop) == 100.0
    # Middle value lands exactly at the median
    assert 40.0 <= compute_percentile(3.0, pop) <= 60.0


def test_score_rejects_missing_values(tmp_weights: Path) -> None:
    signals = load_signals(tmp_weights)
    pop = simulate_population(signals, size=500, seed=1)
    with pytest.raises(ScoringError, match="expected values"):
        score_subject(signals, {"S001": 1}, pop)


def test_score_rejects_wrong_id(tmp_weights: Path) -> None:
    signals = load_signals(tmp_weights)
    pop = simulate_population(signals, size=500, seed=1)
    with pytest.raises(ScoringError, match="missing value"):
        score_subject(
            signals,
            {"S001": 1, "S002": 1, "SXXX": 0},  # SXXX not in signals
            pop,
        )


@pytest.mark.parametrize("bad", [-1, 3, 99, "1", 1.5, True])
def test_score_rejects_out_of_range(tmp_weights: Path, bad: object) -> None:
    signals = load_signals(tmp_weights)
    pop = simulate_population(signals, size=500, seed=1)
    values = {"S001": 1, "S002": 1, "S003": 0}
    values["S001"] = bad  # type: ignore[assignment]
    with pytest.raises(ScoringError):
        score_subject(signals, values, pop)


def test_top_contributors(tmp_weights: Path) -> None:
    signals = load_signals(tmp_weights)
    pop = simulate_population(signals, size=500, seed=1)
    values = {"S001": 2, "S002": 2, "S003": 2}
    result = score_subject(signals, values, pop, top_n=3)
    # S001 (weight 0.5 * 2) is the biggest up; S002 (-0.3 * 2) is the biggest down.
    assert result.top_up[0].signal_id == "S001"
    assert result.top_down[0].signal_id == "S002"


def test_deterministic_population(tmp_weights: Path) -> None:
    signals = load_signals(tmp_weights)
    pop_a = simulate_population(signals, size=300, seed=7)
    pop_b = simulate_population(signals, size=300, seed=7)
    assert np.array_equal(pop_a, pop_b)


def test_demo_values_shape(tmp_weights: Path) -> None:
    signals = load_signals(tmp_weights)
    vals = demo_values(signals, seed=3)
    assert set(vals.keys()) == {s.signal_id for s in signals}
    assert all(v in (0, 1, 2) for v in vals.values())


def test_band_assignment(tmp_weights: Path) -> None:
    signals = load_signals(tmp_weights)
    pop = simulate_population(signals, size=1000, seed=1)
    # All-zero values should never land in "elevated".
    low_result = score_subject(
        signals, {"S001": 0, "S002": 0, "S003": 0}, pop
    )
    assert low_result.band in {"low", "typical"}


def test_population_size_guard(tmp_weights: Path) -> None:
    signals = load_signals(tmp_weights)
    with pytest.raises(ScoringError):
        simulate_population(signals, size=50, seed=1)
