"""Weights dataset loader.

The on-disk format is a small CSV with the following columns:

    signal_id,plain_label,weight,direction_hint

* ``signal_id`` - stable opaque identifier (e.g. "S001"). Not shown to users.
* ``plain_label`` - short, human-friendly label shown in the UI (e.g.
  "Signal 1 - sleep pattern marker"). Kept deliberately layman-friendly; the
  product never renders raw scientific terms on the main screens.
* ``weight`` - per-unit effect size. Multiplied by the user's value (0, 1, 2).
* ``direction_hint`` - "up" or "down". Only used to colour the contribution
  chips in the UI; does not affect scoring math.

This file is the single seam where a real dataset (e.g. a polygenic risk
score weights file from a public GWAS catalog) would plug in. Only the
loader changes; the rest of the app stays the same.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

# Practical upper bound on signals we accept from a weights file. Keeps
# memory use predictable and makes the UI scannable.
MAX_SIGNALS = 500

VALID_DIRECTIONS = frozenset({"up", "down"})


class WeightsError(ValueError):
    """Raised when the weights file is malformed or unsafe."""


@dataclass(frozen=True, slots=True)
class Signal:
    """One weighted signal row from the dataset."""

    signal_id: str
    plain_label: str
    weight: float
    direction_hint: str

    def __post_init__(self) -> None:
        if not self.signal_id or len(self.signal_id) > 32:
            raise WeightsError("signal_id must be 1..32 chars")
        if not self.plain_label or len(self.plain_label) > 120:
            raise WeightsError("plain_label must be 1..120 chars")
        if self.direction_hint not in VALID_DIRECTIONS:
            raise WeightsError(f"direction_hint must be one of {sorted(VALID_DIRECTIONS)}")
        # Reject NaN / inf early - they would poison downstream math.
        if self.weight != self.weight or self.weight in (float("inf"), float("-inf")):
            raise WeightsError("weight must be a finite number")
        if abs(self.weight) > 10:
            raise WeightsError("weight magnitude must be <= 10 (sanity bound)")


def _iter_rows(path: Path) -> Iterable[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        required = {"signal_id", "plain_label", "weight", "direction_hint"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise WeightsError(f"weights file missing columns: {sorted(missing)}")
        for row in reader:
            yield row


def load_signals(path: str | Path) -> list[Signal]:
    """Load and validate every signal row from a CSV file.

    Raises :class:`WeightsError` if anything is wrong with the file.
    """
    p = Path(path)
    if not p.is_file():
        raise WeightsError(f"weights file not found: {p}")

    signals: list[Signal] = []
    seen_ids: set[str] = set()

    for idx, row in enumerate(_iter_rows(p), start=2):  # start=2: header is line 1
        sid = (row.get("signal_id") or "").strip()
        label = (row.get("plain_label") or "").strip()
        direction = (row.get("direction_hint") or "").strip().lower()
        raw_weight = (row.get("weight") or "").strip()

        if sid in seen_ids:
            raise WeightsError(f"duplicate signal_id at line {idx}: {sid!r}")
        try:
            weight = float(raw_weight)
        except ValueError as exc:
            raise WeightsError(f"invalid weight at line {idx}: {raw_weight!r}") from exc

        signals.append(
            Signal(
                signal_id=sid,
                plain_label=label,
                weight=weight,
                direction_hint=direction,
            )
        )
        seen_ids.add(sid)

        if len(signals) > MAX_SIGNALS:
            raise WeightsError(f"weights file has more than {MAX_SIGNALS} rows")

    if not signals:
        raise WeightsError("weights file contains no rows")
    return signals
