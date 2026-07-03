"""Pairwise variant-level overlap between two disorders' significant variants.

Computes shared rsIDs, shared chromosome:position matches, Jaccard similarity,
and — where effect alleles are compatible — direction (sign) concordance of the
effect sizes. Allele flips are handled by inverting the second study's beta when
its effect/other alleles are swapped relative to the first.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import polars as pl


def compute_jaccard(set_a: set, set_b: set) -> float:
    """Jaccard similarity |A∩B| / |A∪B|. Empty ∪ empty is defined as 0.0."""
    if not set_a and not set_b:
        return 0.0
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


@dataclass
class DirectionConcordance:
    n_comparable: int
    n_concordant: int
    n_discordant: int
    concordance_rate: float | None
    details: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class VariantOverlapResult:
    disorder_a: str
    disorder_b: str
    n_a: int
    n_b: int
    shared_rsids: list[str]
    shared_positions: list[str]
    overlap_count: int
    jaccard_rsid: float
    jaccard_position: float
    direction: DirectionConcordance

    def to_dict(self) -> dict[str, Any]:
        return {
            "disorder_a": self.disorder_a,
            "disorder_b": self.disorder_b,
            "n_a": self.n_a,
            "n_b": self.n_b,
            "shared_rsids": self.shared_rsids,
            "shared_positions": self.shared_positions,
            "overlap_count": self.overlap_count,
            "jaccard_rsid": self.jaccard_rsid,
            "jaccard_position": self.jaccard_position,
            "direction_concordance": {
                "n_comparable": self.direction.n_comparable,
                "n_concordant": self.direction.n_concordant,
                "n_discordant": self.direction.n_discordant,
                "concordance_rate": self.direction.concordance_rate,
                "details": self.direction.details,
            },
        }


def _rsid_set(frame: pl.DataFrame) -> set[str]:
    if "rsid" not in frame.columns:
        return set()
    return {
        r for r in frame.get_column("rsid").to_list() if r not in (None, "", "NA")
    }


def _position_set(frame: pl.DataFrame) -> set[str]:
    out: set[str] = set()
    if not {"chromosome", "position"}.issubset(frame.columns):
        return out
    for c, p in zip(
        frame.get_column("chromosome").to_list(),
        frame.get_column("position").to_list(),
    ):
        if c is not None and p is not None:
            out.add(f"{c}:{p}")
    return out


def _sign(x: float | None) -> int | None:
    if x is None:
        return None
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def _direction_concordance(
    frame_a: pl.DataFrame, frame_b: pl.DataFrame, shared: set[str]
) -> DirectionConcordance:
    """Compare effect-size signs for variants shared by rsID.

    Concordant = same effect direction after aligning effect alleles.
    Variants with incompatible alleles or missing betas are not comparable.
    """
    cols = ["rsid", "beta", "effect_allele", "other_allele"]

    def index(frame: pl.DataFrame) -> dict[str, dict[str, Any]]:
        have = [c for c in cols if c in frame.columns]
        sub = frame.select(have).filter(pl.col("rsid").is_in(list(shared)))
        idx: dict[str, dict[str, Any]] = {}
        for row in sub.iter_rows(named=True):
            idx[row["rsid"]] = row
        return idx

    idx_a, idx_b = index(frame_a), index(frame_b)

    n_conc = n_disc = 0
    details: list[dict[str, Any]] = []
    for rsid in sorted(shared):
        a = idx_a.get(rsid)
        b = idx_b.get(rsid)
        if not a or not b:
            continue
        beta_a, beta_b = a.get("beta"), b.get("beta")
        sa, sb = _sign(beta_a), _sign(beta_b)
        if sa is None or sb is None or sa == 0 or sb == 0:
            continue
        ea_a, oa_a = a.get("effect_allele"), a.get("other_allele")
        ea_b, oa_b = b.get("effect_allele"), b.get("other_allele")

        aligned_sb = sb
        allele_status = "matched"
        if ea_a and ea_b:
            if ea_a == ea_b and oa_a == oa_b:
                allele_status = "matched"
            elif ea_a == oa_b and oa_a == ea_b:
                aligned_sb = -sb  # flipped strand/allele orientation
                allele_status = "flipped"
            else:
                allele_status = "incompatible"
                continue  # cannot compare direction
        concordant = sa == aligned_sb
        n_conc += int(concordant)
        n_disc += int(not concordant)
        details.append(
            {
                "rsid": rsid,
                "beta_a": beta_a,
                "beta_b": beta_b,
                "allele_status": allele_status,
                "concordant": concordant,
            }
        )

    n_comp = n_conc + n_disc
    rate = (n_conc / n_comp) if n_comp else None
    return DirectionConcordance(
        n_comparable=n_comp,
        n_concordant=n_conc,
        n_discordant=n_disc,
        concordance_rate=rate,
        details=details,
    )


def compare_variant_overlap(
    frame_a: pl.DataFrame,
    frame_b: pl.DataFrame,
    *,
    disorder_a: str = "A",
    disorder_b: str = "B",
) -> VariantOverlapResult:
    """Compare two frames of significant variants for a pair of disorders."""
    rs_a, rs_b = _rsid_set(frame_a), _rsid_set(frame_b)
    pos_a, pos_b = _position_set(frame_a), _position_set(frame_b)

    shared_rs = rs_a & rs_b
    shared_pos = pos_a & pos_b

    direction = _direction_concordance(frame_a, frame_b, shared_rs)

    return VariantOverlapResult(
        disorder_a=disorder_a,
        disorder_b=disorder_b,
        n_a=frame_a.height,
        n_b=frame_b.height,
        shared_rsids=sorted(shared_rs),
        shared_positions=sorted(shared_pos),
        overlap_count=len(shared_rs),
        jaccard_rsid=compute_jaccard(rs_a, rs_b),
        jaccard_position=compute_jaccard(pos_a, pos_b),
        direction=direction,
    )
