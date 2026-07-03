"""Extract significant variants from a normalized GWAS frame.

Supported selection strategies:
  * ``genome_wide``  p < 5e-8
  * ``suggestive``   p < 1e-5
  * ``top_k``        the k smallest p-values regardless of threshold
  * ``custom``       p < a caller-supplied threshold
"""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from app import config

VALID_METHODS = {"genome_wide", "suggestive", "top_k", "custom"}


@dataclass
class SignificanceSelection:
    frame: pl.DataFrame
    method: str
    threshold: float | None
    k: int | None
    n_input: int
    n_selected: int


def _valid_p(frame: pl.DataFrame) -> pl.DataFrame:
    return frame.filter(
        pl.col("p_value").is_not_null()
        & (pl.col("p_value") >= 0)
        & (pl.col("p_value") <= 1)
    )


def extract_significant_variants(
    frame: pl.DataFrame,
    method: str = "genome_wide",
    *,
    k: int | None = None,
    custom_threshold: float | None = None,
) -> SignificanceSelection:
    """Select significant variants from a normalized frame.

    Parameters
    ----------
    frame:
        A normalized GWAS frame containing a ``p_value`` column.
    method:
        One of ``genome_wide``, ``suggestive``, ``top_k``, ``custom``.
    k:
        Number of variants to keep when ``method == "top_k"``.
    custom_threshold:
        p-value threshold when ``method == "custom"``.
    """
    if method not in VALID_METHODS:
        raise ValueError(f"Unknown method {method!r}; expected one of {VALID_METHODS}")
    if "p_value" not in frame.columns:
        raise ValueError("Frame has no 'p_value' column; normalize the schema first.")

    n_input = frame.height
    valid = _valid_p(frame)

    threshold: float | None = None
    if method == "genome_wide":
        threshold = config.GENOME_WIDE_SIGNIFICANCE
        selected = valid.filter(pl.col("p_value") < threshold)
    elif method == "suggestive":
        threshold = config.SUGGESTIVE_SIGNIFICANCE
        selected = valid.filter(pl.col("p_value") < threshold)
    elif method == "custom":
        if custom_threshold is None:
            raise ValueError("custom_threshold is required when method='custom'")
        threshold = float(custom_threshold)
        selected = valid.filter(pl.col("p_value") < threshold)
    else:  # top_k
        if k is None or k <= 0:
            raise ValueError("k must be a positive integer when method='top_k'")
        selected = valid.sort("p_value").head(k)

    selected = selected.sort("p_value")
    return SignificanceSelection(
        frame=selected,
        method=method,
        threshold=threshold,
        k=k,
        n_input=n_input,
        n_selected=selected.height,
    )
