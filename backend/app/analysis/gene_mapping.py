"""Map variants to genes using a bundled demo gene annotation.

Mapping strategies:
  * ``gene_body``    variant position within [start, end]
  * ``window_10kb``  within +/-10 kb of the gene body
  * ``window_50kb``  within +/-50 kb of the gene body
  * ``nearest``      the single closest gene on the same chromosome

Range joins run in DuckDB so the approach scales to large variant tables without
materializing a Python cross-product. A variant may map to several genes for the
window/body methods; ``nearest`` returns exactly one gene per variant.

Scientific note: positional proximity does NOT establish causality. A mapped
gene is a positional candidate only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import duckdb
import polars as pl

from app import config

_METHOD_WINDOWS = {
    "gene_body": 0,
    "window_10kb": 10_000,
    "window_50kb": 50_000,
}
VALID_METHODS = set(_METHOD_WINDOWS) | {"nearest"}


@dataclass
class MappingResult:
    mappings: pl.DataFrame  # variant_id, rsid, chromosome, position, gene_symbol, gene_id, distance
    method: str
    window: int | None
    n_variants: int
    n_mapped_variants: int
    n_unmapped_variants: int
    genes: list[str] = field(default_factory=list)

    def to_summary(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "window": self.window,
            "n_variants": self.n_variants,
            "n_mapped_variants": self.n_mapped_variants,
            "n_unmapped_variants": self.n_unmapped_variants,
            "n_genes": len(self.genes),
            "genes": self.genes,
        }


def load_gene_annotation(path: str | Path | None = None) -> pl.DataFrame:
    """Load the gene annotation TSV, normalizing chromosome names."""
    path = Path(path) if path else config.GENE_ANNOTATION_FILE
    if not Path(path).exists():
        raise FileNotFoundError(f"Gene annotation file not found: {path}")
    ann = pl.read_csv(path, separator="\t")
    required = {"chromosome", "start", "end", "gene_symbol"}
    missing = required - set(ann.columns)
    if missing:
        raise ValueError(f"Annotation missing required columns: {missing}")
    if "gene_id" not in ann.columns:
        ann = ann.with_columns(pl.col("gene_symbol").alias("gene_id"))
    return ann.with_columns(
        pl.col("chromosome").cast(pl.Utf8).str.replace(r"(?i)^chr", "").str.strip_chars(),
        pl.col("start").cast(pl.Int64),
        pl.col("end").cast(pl.Int64),
    )


def map_variants_to_genes(
    variants: pl.DataFrame,
    annotation: pl.DataFrame | None = None,
    method: str = "window_10kb",
) -> MappingResult:
    """Map variants to genes with the requested strategy."""
    if method not in VALID_METHODS:
        raise ValueError(f"Unknown method {method!r}; expected one of {VALID_METHODS}")
    if annotation is None:
        annotation = load_gene_annotation()

    # Keep only variants with usable coordinates.
    variants = variants.filter(
        pl.col("chromosome").is_not_null() & pl.col("position").is_not_null()
    )
    keep_cols = [c for c in ["variant_id", "rsid", "chromosome", "position"] if c in variants.columns]
    v = variants.select(keep_cols).with_columns(
        pl.col("chromosome").cast(pl.Utf8), pl.col("position").cast(pl.Int64)
    )

    con = duckdb.connect()
    con.register("variants", v.to_arrow())
    con.register("genes", annotation.to_arrow())

    if method == "nearest":
        window = None
        query = """
            WITH dist AS (
                SELECT
                    v.variant_id, v.rsid, v.chromosome, v.position,
                    g.gene_symbol, g.gene_id,
                    GREATEST(0, GREATEST(g.start - v.position, v.position - g.end)) AS distance,
                    ROW_NUMBER() OVER (
                        PARTITION BY v.variant_id
                        ORDER BY GREATEST(0, GREATEST(g.start - v.position, v.position - g.end)) ASC,
                                 g.gene_symbol ASC
                    ) AS rn
                FROM variants v
                JOIN genes g ON v.chromosome = g.chromosome
            )
            SELECT variant_id, rsid, chromosome, position, gene_symbol, gene_id, distance
            FROM dist WHERE rn = 1
        """
        mappings = con.execute(query).pl()
    else:
        window = _METHOD_WINDOWS[method]
        query = f"""
            SELECT
                v.variant_id, v.rsid, v.chromosome, v.position,
                g.gene_symbol, g.gene_id,
                GREATEST(0, GREATEST(g.start - v.position, v.position - g.end)) AS distance
            FROM variants v
            JOIN genes g ON v.chromosome = g.chromosome
                AND v.position >= g.start - {window}
                AND v.position <= g.end + {window}
            ORDER BY v.variant_id, distance
        """
        mappings = con.execute(query).pl()

    con.close()

    n_variants = v.height
    mapped_ids = set(mappings.get_column("variant_id").to_list()) if mappings.height else set()
    genes = sorted(
        {g for g in mappings.get_column("gene_symbol").to_list()}
    ) if mappings.height else []

    return MappingResult(
        mappings=mappings,
        method=method,
        window=window,
        n_variants=n_variants,
        n_mapped_variants=len(mapped_ids),
        n_unmapped_variants=n_variants - len(mapped_ids),
        genes=genes,
    )
