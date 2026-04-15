"""Tests for data loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.data import MAX_SIGNALS, Signal, WeightsError, load_signals


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_load_valid_csv(tmp_weights: Path) -> None:
    sigs = load_signals(tmp_weights)
    assert len(sigs) == 3
    assert sigs[0].signal_id == "S001"
    assert sigs[0].direction_hint == "up"
    assert sigs[1].weight == pytest.approx(-0.3)


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(WeightsError, match="not found"):
        load_signals(tmp_path / "nope.csv")


def test_missing_columns(tmp_path: Path) -> None:
    p = _write(
        tmp_path / "bad.csv",
        "signal_id,plain_label,weight\nS001,foo,0.1\n",
    )
    with pytest.raises(WeightsError, match="missing columns"):
        load_signals(p)


def test_empty_file(tmp_path: Path) -> None:
    p = _write(tmp_path / "empty.csv", "signal_id,plain_label,weight,direction_hint\n")
    with pytest.raises(WeightsError, match="no rows"):
        load_signals(p)


def test_non_numeric_weight(tmp_path: Path) -> None:
    p = _write(
        tmp_path / "bad.csv",
        "signal_id,plain_label,weight,direction_hint\n"
        "S001,demo,not_a_number,up\n",
    )
    with pytest.raises(WeightsError, match="invalid weight"):
        load_signals(p)


@pytest.mark.parametrize("weight", ["inf", "-inf", "nan"])
def test_non_finite_weight_rejected(tmp_path: Path, weight: str) -> None:
    p = _write(
        tmp_path / "bad.csv",
        "signal_id,plain_label,weight,direction_hint\n"
        f"S001,demo,{weight},up\n",
    )
    with pytest.raises(WeightsError):
        load_signals(p)


def test_weight_magnitude_cap(tmp_path: Path) -> None:
    p = _write(
        tmp_path / "bad.csv",
        "signal_id,plain_label,weight,direction_hint\n"
        "S001,demo,999,up\n",
    )
    with pytest.raises(WeightsError, match="magnitude"):
        load_signals(p)


def test_duplicate_ids(tmp_path: Path) -> None:
    p = _write(
        tmp_path / "bad.csv",
        "signal_id,plain_label,weight,direction_hint\n"
        "S001,demo,0.1,up\n"
        "S001,demo2,0.2,up\n",
    )
    with pytest.raises(WeightsError, match="duplicate"):
        load_signals(p)


def test_bad_direction(tmp_path: Path) -> None:
    p = _write(
        tmp_path / "bad.csv",
        "signal_id,plain_label,weight,direction_hint\n"
        "S001,demo,0.1,sideways\n",
    )
    with pytest.raises(WeightsError, match="direction_hint"):
        load_signals(p)


def test_too_many_rows(tmp_path: Path) -> None:
    rows = "signal_id,plain_label,weight,direction_hint\n"
    rows += "\n".join(
        f"S{i:04d},demo,0.01,up" for i in range(MAX_SIGNALS + 5)
    )
    p = _write(tmp_path / "big.csv", rows + "\n")
    with pytest.raises(WeightsError, match="more than"):
        load_signals(p)


def test_signal_direct_validation() -> None:
    with pytest.raises(WeightsError):
        Signal(signal_id="", plain_label="x", weight=0.1, direction_hint="up")
    with pytest.raises(WeightsError):
        Signal(signal_id="ok", plain_label="", weight=0.1, direction_hint="up")
