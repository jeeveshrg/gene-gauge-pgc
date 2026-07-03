"""Normalize heterogeneous GWAS summary-statistic schemas to a common schema.

Different PGC/OpenMed configs use different column names and effect encodings
(odds ratio vs beta vs log-odds). This module maps them onto one schema:

    dataset_id, disorder, publication, variant_id, rsid, chromosome, position,
    effect_allele, other_allele, beta, odds_ratio, standard_error, p_value,
    sample_size, source_config

Effect-size handling:
  * If beta / log-odds is present, beta is used directly and odds_ratio = exp(beta).
  * If only odds ratio is present, beta = ln(odds_ratio).

A p-value column is required; its absence raises ``MissingPValueError`` so callers
can surface an actionable error instead of silently producing empty results.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import polars as pl

from app.data_sources.huggingface_loader import LoadedDataset

NORMALIZED_COLUMNS = [
    "dataset_id",
    "disorder",
    "publication",
    "variant_id",
    "rsid",
    "chromosome",
    "position",
    "effect_allele",
    "other_allele",
    "beta",
    "odds_ratio",
    "standard_error",
    "p_value",
    "sample_size",
    "source_config",
]

# Alias tables (lower-cased, punctuation-insensitive keys).
_ALIASES: dict[str, list[str]] = {
    "rsid": ["rsid", "rs", "snp", "snpid", "markername", "marker", "variant", "id"],
    "chromosome": ["chromosome", "chrom", "chr", "chr_name"],
    "position": ["position", "pos", "bp", "basepairlocation", "bpposition", "base_pair"],
    "effect_allele": ["effectallele", "ea", "a1", "allele1", "alt", "effect_allele"],
    "other_allele": ["otherallele", "nea", "a2", "allele2", "ref", "other_allele"],
    "beta": ["beta", "effect", "b", "logor", "log_or", "logodds", "logoddsratio"],
    "odds_ratio": ["oddsratio", "or", "odds_ratio"],
    "standard_error": ["standarderror", "se", "stderr", "sebeta", "se_beta", "std_err"],
    "p_value": ["pvalue", "pval", "p", "pvaluenominal", "p_value", "pvalnominal"],
    "sample_size": ["samplesize", "n", "ntotal", "neff", "n_eff", "nsamples", "n_total"],
}

# Aliases that carry log-odds rather than a linear beta (mapped to the beta slot).
_LOG_ODDS_ALIASES = {"logor", "log_or", "logodds", "logoddsratio"}


class MissingPValueError(ValueError):
    """Raised when no recognizable p-value column exists in the raw schema."""


@dataclass
class NormalizationResult:
    frame: pl.DataFrame
    column_mapping: dict[str, str]
    warnings: list[str] = field(default_factory=list)
    effect_encoding: str = "unknown"  # "beta" | "odds_ratio" | "log_odds"


def _canon(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def detect_columns(raw_columns: list[str]) -> dict[str, str]:
    """Map normalized field -> raw column name using alias tables.

    Uses first-match precedence following the alias ordering, so canonical names
    (e.g. ``effect_allele``) win over ambiguous short codes (e.g. ``a1``).
    """
    canon_to_raw: dict[str, str] = {}
    for raw in raw_columns:
        canon_to_raw.setdefault(_canon(raw), raw)

    mapping: dict[str, str] = {}
    for field_name, aliases in _ALIASES.items():
        for alias in aliases:
            if alias in canon_to_raw:
                mapping[field_name] = canon_to_raw[alias]
                break
    return mapping


def _is_log_odds_source(raw_col: str) -> bool:
    return _canon(raw_col) in _LOG_ODDS_ALIASES


def normalize_gwas_schema(loaded: LoadedDataset) -> NormalizationResult:
    """Normalize a loaded raw dataset into the common GWAS schema."""
    raw = loaded.frame
    mapping = detect_columns(list(raw.columns))
    warnings: list[str] = []

    if "p_value" not in mapping:
        raise MissingPValueError(
            "No p-value column found. Looked for aliases: "
            f"{_ALIASES['p_value']}. Raw columns: {list(raw.columns)}"
        )

    def col(field_name: str) -> pl.Expr:
        """Numeric expression for a normalized field, or null literal if absent."""
        src = mapping.get(field_name)
        if src is None:
            return pl.lit(None)
        return raw.get_column(src)

    def num(field_name: str) -> pl.Series:
        src = mapping.get(field_name)
        if src is None:
            return pl.Series(field_name, [None] * raw.height, dtype=pl.Float64)
        return raw.get_column(src).cast(pl.Float64, strict=False)

    def text(field_name: str) -> pl.Series:
        src = mapping.get(field_name)
        if src is None:
            return pl.Series(field_name, [None] * raw.height, dtype=pl.Utf8)
        return raw.get_column(src).cast(pl.Utf8, strict=False)

    # --- effect-size resolution -------------------------------------------
    beta_series = num("beta")
    or_series = num("odds_ratio")
    encoding = "unknown"

    has_beta_col = "beta" in mapping
    has_or_col = "odds_ratio" in mapping
    beta_is_logodds = has_beta_col and _is_log_odds_source(mapping["beta"])

    if has_beta_col:
        encoding = "log_odds" if beta_is_logodds else "beta"
        # Derive OR from beta where OR is missing.
        if not has_or_col:
            or_series = beta_series.map_elements(
                lambda b: (math.exp(b) if b is not None else None),
                return_dtype=pl.Float64,
            )
    elif has_or_col:
        encoding = "odds_ratio"
        beta_series = or_series.map_elements(
            lambda o: (math.log(o) if o is not None and o > 0 else None),
            return_dtype=pl.Float64,
        )
        warnings.append("beta derived from odds ratio via natural log.")
    else:
        warnings.append("No effect-size column (beta/odds ratio) found.")

    # --- allele normalization (upper-case) --------------------------------
    ea = text("effect_allele").str.to_uppercase()
    oa = text("other_allele").str.to_uppercase()

    # --- chromosome normalization (strip 'chr' prefix) --------------------
    chrom = (
        text("chromosome")
        .str.replace(r"(?i)^chr", "")
        .str.strip_chars()
    )

    rsid = text("rsid")
    position = num("position").cast(pl.Int64, strict=False)

    # --- canonical variant_id: chr:pos:other:effect (falls back to rsid) --
    n = raw.height
    variant_ids: list[str | None] = []
    rsid_list = rsid.to_list()
    chrom_list = chrom.to_list()
    pos_list = position.to_list()
    ea_list = ea.to_list()
    oa_list = oa.to_list()
    for i in range(n):
        c, p = chrom_list[i], pos_list[i]
        if c is not None and p is not None:
            a1 = ea_list[i] or "NA"
            a2 = oa_list[i] or "NA"
            variant_ids.append(f"{c}:{p}:{a2}:{a1}")
        else:
            variant_ids.append(rsid_list[i])

    out = pl.DataFrame(
        {
            "dataset_id": pl.Series([loaded.dataset_id] * n, dtype=pl.Utf8),
            "disorder": pl.Series([loaded.disorder] * n, dtype=pl.Utf8),
            "publication": pl.Series([loaded.publication] * n, dtype=pl.Utf8),
            "variant_id": pl.Series(variant_ids, dtype=pl.Utf8),
            "rsid": rsid,
            "chromosome": chrom,
            "position": position,
            "effect_allele": ea,
            "other_allele": oa,
            "beta": beta_series.cast(pl.Float64, strict=False),
            "odds_ratio": or_series.cast(pl.Float64, strict=False),
            "standard_error": num("standard_error"),
            "p_value": num("p_value"),
            "sample_size": num("sample_size").cast(pl.Int64, strict=False),
            "source_config": pl.Series([loaded.config_id] * n, dtype=pl.Utf8),
        }
    )

    # --- data-quality warnings --------------------------------------------
    n_bad_p = int(
        out.select(
            ((pl.col("p_value").is_null()) | (pl.col("p_value") < 0) | (pl.col("p_value") > 1)).sum()
        ).item()
    )
    if n_bad_p:
        warnings.append(f"{n_bad_p} row(s) have missing or out-of-range p-values.")

    return NormalizationResult(
        frame=out.select(NORMALIZED_COLUMNS),
        column_mapping=mapping,
        warnings=warnings,
        effect_encoding=encoding,
    )
